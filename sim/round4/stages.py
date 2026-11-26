"""Size and verify stage 1, then stage 2, then connect the measured stages."""
import argparse
import json
from pathlib import Path
import numpy as np
from devices import LENGTHS, Lookup
from measure import VIC, model_text, prepare_ota, run_spice, table

VDD, VX, VO = 1.1, .52, .59
BETA, CC = .125, 200e-15
FC = 1.25 * -np.log(.005)/(2*np.pi*10e-9)
GM1 = 2*np.pi*FC*CC/BETA
COMP_C = 245e-15  # integrated Miller capacitor including the design reserve
ETA1, ETA5 = 17., 15.
I1 = GM1/ETA1
SENSE = 800e3
INPUT_R_BUDGET = 2e6
DRIVE_SHARE = .25
GM2 = 2*np.pi*(3.8*FC)*.9e-12
A1_MIN, A2_MIN = 48., 54.
FMIN = 4*FC
AC = "ac dec 80 1k 20G"


def mos(name, pins, kind, width, length):
    return f"M{name} {pins} {kind}ch W={width:.1f}u L={length:g}u"


def w(current, pt):
    return round(current/pt["j"],1)


def verify_stage(path, net, drive, vguess, load, stage):
    path.mkdir(parents=True,exist_ok=True)
    (path/"model.lib").write_text(model_text("tt",{}))
    (path/"dut.lib").write_text(prepare_ota(net,None)[0]+"\n")
    body = (f"Vdd vdd 0 1.1\nVp ip 0 dc {drive} ac .5\nVm im 0 dc {drive} ac -.5\n"
            f"Xp ip im op om vdd 0 block\nCLp op 0 {load}\nCLm om 0 {load}")
    if stage==1:  # conservative differential input-load budget
        body+=f"\nVx vx 0 {vguess}\nRlp op vx {INPUT_R_BUDGET}\nRlm om vx {INPUT_R_BUDGET}"
    run_spice(path,"local",body,"op\nwrdata op.txt v(op) v(om) i(vdd)\n"+AC+
              "\nwrdata gain.txt real(v(op,om)) imag(v(op,om))")
    _,vp,vm,supply=table(path,"op")[:,0]
    f,re,im=table(path,"gain")
    gain=np.abs(re+1j*im)
    idx=np.flatnonzero(gain<=gain[0]/np.sqrt(2))[0]
    pole=np.interp(gain[0]/np.sqrt(2),gain[idx-1:idx+1][::-1],f[idx-1:idx+1][::-1])
    return dict(cm_V=float((vp+vm)/2), supply_uA=-supply*1e6, gain=gain[0], pole_Hz=pole,
                load_F=load)


def first(lut):
    options=[]
    for ln in LENGTHS:
        # Solve Vtail = VIC - VGS with input-pair body effect included.
        tail=.16
        for _ in range(15):
            n=lut.point("n",ln,VX-tail,tail,eta=ETA1)
            tail=(tail+VIC-n["vg"])/2
        for lp in LENGTHS:
            p=lut.point("p",lp,VDD-VX,gate=VDD-VX)
            rout=1/(I1*(n["gd_per_a"]+p["gd_per_a"])+1/SENSE+1/INPUT_R_BUDGET)
            gain=GM1*rout
            if gain>=A1_MIN and min(n["ft"],p["ft"])>=FMIN:
                cap=n["cgg_per_um"]*w(I1,n)+p["cgg_per_um"]*w(I1,p)
                options.append((cap,ln,lp,n,p,tail,gain))
    if not options: raise ValueError("No device lengths meet stage 1 budgets")
    _,ln,lp,n,p,tail,gain=min(options,key=lambda row:row[0])
    # Conserve input-stage current at hot SS and reserve 25 mV below the estimated tail node.
    # Use the measured slow-corner tail-node floor of the preceding design as a conservative budget.
    hot_vds=.125
    t=lut.point("n",.60,hot_vds,sat=hot_vds-.025,corner="ss")
    ref=lut.point("n",.60,t["vg"],gate=t["vg"],corner="ss")
    # The reference diode shares the tail gate bias and carries one sixth of the target tail current.
    it=2*I1
    imirror=it/6
    lines=[f"Iref vdd b {imirror:.10g}",mos("ref","b b 0 0","n",w(imirror,ref),.60),
           mos("tail","t b 0 0","n",w(it,t),.60)]
    for i,(x,g) in enumerate((("xp","ip"),("xm","im")),1):
        lines.append(mos(i,f"{x} {g} t 0","n",w(I1,n),ln))
    for i,x in enumerate(("xp","xm"),3):
        lines.append(mos(i,f"{x} a vdd vdd","p",w(I1,p),lp))
    lines+=["R1 xp a 800k","R2 xm a 800k","C1 xp a 40f","C2 xm a 40f"]
    return lines,dict(ln=ln,lp=lp,wn=w(I1,n),wp=w(I1,p),n=n,p=p,tail=tail,
                      gain_budgeted=gain,gm_S=GM1,branch_A=I1,tail_hot=t,reference_hot=ref,
                      ref_width=w(imirror,ref),tail_width=w(it,t),feasible_lengths=len(options))


def second(lut, x):
    # Independent pull-down drive transistor; the other sink regulates the output common mode.
    opts=[]
    for lp in LENGTHS:
        p=lut.point("p",lp,VDD-VO,gate=VDD-x)
        for ld in LENGTHS:
            driver=lut.point("n",ld,VO,gate=x)
            # At fast/cold VDD=1.2, stage 1 drives ~0.662 V. Reserve at least
            # 60% of pull-up current for the common-mode sink at Vout=0.55 V.
            ff_p=lut.point("p",lp,1.2-.55,gate=1.2-.662,corner="ff")
            ff_d=lut.point("n",ld,.55,gate=.662,corner="ff")
            share=min(DRIVE_SHARE,.4*(ff_p["j"]/p["j"])/(ff_d["j"]/driver["j"]))
            for ln in LENGTHS:
                n=lut.point("n",ln,VO,gate=VO)
                current=GM2/(p["eta"]+share*driver["eta"])
                gds=current*(p["gd_per_a"]+(1-share)*n["gd_per_a"]+
                             share*driver["gd_per_a"])
                gain=GM2/(gds+1/SENSE)
                cap=p["cgg_per_um"]*w(current,p)+driver["cgg_per_um"]*w(current*share,driver)
                if gain>=A2_MIN and min(p["ft"],n["ft"],driver["ft"])>=FMIN:
                    opts.append((abs(p["eta"]-ETA5),cap,ln,lp,ld,n,p,driver,current,gain,share))
    if not opts: raise ValueError("No device lengths meet stage 2 budgets")
    _,cap,ln,lp,ld,n,p,driver,cur,gain,share=min(opts,key=lambda row:(row[0],row[1],row[2]))
    lines=[]
    for i,(o,g) in enumerate((("op","xp"),("om","xm")),5):
        lines.append(mos(i,f"{o} {g} vdd vdd","p",w(cur,p),lp))
    for i,o in enumerate(("op","om"),7):
        lines.append(mos(i,f"{o} s 0 0","n",w(cur*(1-share),n),ln))
    for i,(o,g) in enumerate((("op","xp"),("om","xm")),9):
        lines.append(mos(i,f"{o} {g} 0 0","n",w(cur*share,driver),ld))
    lines+=["R3 op s 800k","R4 om s 800k","C3 op s 40f","C4 om s 40f"]
    return lines,dict(ln=ln,lp=lp,ld=ld,wn=w(cur*(1-share),n),wp=w(cur,p),
                      wd=w(cur*share,driver),n=n,p=p,driver=driver,gm_S=GM2,branch_A=cur,
                      gain_budgeted=gain,cin_F=cap,drive_share=share,feasible_lengths=len(opts))


def subckt(name, pins, lines):
    return "\n".join([f".subckt {name} {pins}",*lines,f".ends {name}"])+"\n"


def main(root,lut_path):
    root.mkdir(parents=True,exist_ok=True)
    lut=Lookup(lut_path)
    one,b1=first(lut)
    s1=subckt("block","ip im xp xm vdd 0",one)
    m1=verify_stage(root/"stage1",s1,VIC,VX,.45e-12,1)
    two,b2=second(lut,m1["cm_V"])
    s2=subckt("block","xp xm op om vdd 0",two)
    m2=verify_stage(root/"stage2",s2,m1["cm_V"],VO,.45e-12,2)
    # Series-R Miller zero: 1/(2 pi Cc (Rz - 1/Gm2)); verified by the integrated transient.
    fzero=2.6*FC
    rz=round((1/GM2+1/(2*np.pi*COMP_C*fzero))/10)*10
    comp=[f"Rzp xp zp {rz}",f"Rzm xm zm {rz}",f"Ccp zp op {COMP_C*1e15:g}f",f"Ccm zm om {COMP_C*1e15:g}f"]
    for stage,net in (("stage1",s1),("stage2",s2)):
        (root/(stage+".cir")).write_text(net)
    (root/"ota.cir").write_text("* Two-stage differential OTA, gm/ID stage design, 180 nm\n"+
                                subckt("ota","ip im op om vdd 0",one+two+comp))
    metrics=dict(fc_budget_Hz=FC,stage1_design=b1,stage1_test=m1,stage2_design=b2,
                 stage2_test=m2,compensation=dict(R_ohm=rz,C_F=COMP_C,fzero_Hz=fzero))
    (root/"stages.json").write_text(json.dumps(metrics,indent=2)+"\n")
    print(m1,m2,rz)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lut",type=Path)
    parser.add_argument("out",type=Path)
    args=parser.parse_args()
    main(args.out,args.lut)
