"""Measure fully differential OTA decks with ngspice and the supplied BSIM3 card."""
import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "model/Modelfile_180n.scs"
DEVICES = ["ref", "tail"] + [str(i) for i in range(1, 9)]
AC = "ac dec 100 1k 100G"
VIC = 0.75
TARGET = 0.25


def model_text(corner, mismatch):
    """Translate dialect. Optional stress cases explicitly perturb supplied parameters."""
    text = MODEL.read_text()
    cards = re.split(r"(?m)^model ", text)[1:]
    generated = []
    for card in cards:
        head, body = card.split("\n", 1)
        name, _, polarity = head.split()
        pol = polarity[-1]
        # BSIM3 3.1 ngspice has no Spectre XL/XW card keywords.
        # Fold the supplied drawing offsets into instance dimensions below.
        body = re.sub(r"(?m)^\+xl\s*=\s*0\s+xw\s*=\s*-1e-8[^\S\n]*", "+", body)
        index = 0 if pol == "n" else 1
        speed = {"s": -1, "f": 1, "t": 0}[corner[index]]
        copies = [(name, 0)] + [(device, delta) for device, (kind, delta) in mismatch.items() if kind == name]
        for new_name, delta in copies:
            def replace(match):
                key, value = match.groups()
                v = float(value)
                if key == "u0":
                    v *= 1 + 0.12 * speed
                else:
                    v += (-1 if pol == "n" else 1) * 0.025 * speed + delta
                return f"{key} = {v:.12g}"
            changed = re.sub(r"\b(u0|vth0)\s*=\s*([^\s]+)", replace, body)
            generated.append(f".model {new_name} {pol}mos level=49\n{changed}")
    return "\n".join(generated)


def prepare_ota(source, seed):
    """Assign each MOS its own card in mismatch runs. Add explicit junction geometry."""
    rng = np.random.default_rng(seed)
    mismatch = {}
    lines = []
    for line in source.splitlines():
        if line.startswith("M"):
            words = line.split()
            w, length = (float(word.split("=")[1][:-1]) for word in words[6:8])
            line = line.replace(words[6], f"W={w-0.010:.9g}u", 1)
            # Rectangular diffusion on each side, no shared junction credit.
            line += f" AD={w * 0.25:.8g}p AS={w * 0.25:.8g}p PD={2*(w+0.25):.8g}u PS={2*(w+0.25):.8g}u"
            if seed is not None:
                kind = words[5]
                new_name = "card_" + words[0].lower()
                mismatch[new_name] = (kind, rng.normal(0, 0.003 / np.sqrt(w * length)))
                line = line.replace(" " + kind + " ", " " + new_name + " ")
        lines.append(line)
    return "\n".join(lines), mismatch


def run_spice(directory, name, body, control):
    sim = os.environ.get("NGSPICE") or shutil.which("ngspice") or "/workspace/.opamp-tools/bin/ngspice"
    deck = f"OTA bench {name}\n.include model.lib\n.include dut.lib\n{body}\n.control\nset wr_singlescale\nset wr_vecnames\nset numdgt=15\n{control}\nquit\n.endc\n.end\n"
    (directory / (name + ".cir")).write_text(deck)
    run = subprocess.run([sim, "-b", name + ".cir"], cwd=directory, capture_output=True, text=True)
    log = run.stdout + run.stderr
    (directory / (name + ".log")).write_text(log)
    if run.returncode or re.search(r"(?im)^\s*(?:fatal|error|panic)|simulation\(s\) aborted|timestep too small|unrecognized parameter|no such (?:vector|device)", log):
        raise RuntimeError(f"{name}: {log[-4000:]}")


def table(directory, name):
    return np.loadtxt(directory / (name + ".txt"), skiprows=1, ndmin=2).T


def bounds(x, gain, center, threshold):
    """Interpolate the contiguous band containing the chosen reference sample."""
    left = right = center
    while left > 0 and gain[left - 1] >= threshold:
        left -= 1
    while right + 1 < len(x) and gain[right + 1] >= threshold:
        right += 1
    lo = x[left] if left == 0 else np.interp(threshold, gain[left-1:left+1], x[left-1:left+1])
    hi = x[right] if right == len(x)-1 else np.interp(threshold, gain[right:right+2][::-1], x[right:right+2][::-1])
    return float(lo), float(hi)


def db(x):
    return 20 * np.log10(np.maximum(np.abs(x), 1e-30))


def transient(t, y):
    metrics = {}
    for edge, onset in [("rise", 25), ("fall", 75.01)]:
        time = t * 1e9 - onset
        plateau = np.mean(y[(time >= 48) & (time <= 49)])
        base = np.mean(y[(time >= -2) & (time <= -1)])
        metrics[edge + "_static_pct"] = abs(abs(plateau-base) / TARGET - 1) * 100
        for delay in (10, 40):
            metrics[f"{edge}_dynamic{delay}_pct"] = abs(np.interp(delay, time, y) - plateau) / TARGET * 100
        use = (time >= 0) & (time <= 49)
        for pct in (0.5, 1):
            error = abs(y[use] - plateau)
            out = np.flatnonzero(error > TARGET * pct / 100)
            i = out[-1] if len(out) else -1
            tx = time[use]
            settled = 0 if i == -1 else (float(tx[i]+(tx[i+1]-tx[i])*(error[i]-TARGET*pct/100)/(error[i]-error[i+1])) if i+1 < len(tx) else None)
            metrics[f"{edge}_settle{pct}_ns"] = settled
    return metrics


def simulate(source, directory, vdd=1.1, temp=27, corner="tt", seed=None, full=True):
    directory.mkdir(parents=True, exist_ok=True)
    dut, mismatch = prepare_ota(source.read_text(), seed)
    (directory / "dut.lib").write_text(dut + "\n")
    (directory / "model.lib").write_text(model_text(corner, mismatch))
    common = f""".temp {temp}
.options method=gear maxord=2 reltol=1e-5 vntol=1e-9 abstol=1e-14 gmin=1e-14
X1 ip im op om vdd 0 ota
Vdd vdd 0 dc {vdd}
"""
    # DC-only servo fixes differential operating point while keeping input CM at VIC.
    servo = f"Bp ip 0 v={VIC}-v(op,om)/2\nBm im 0 v={VIC}+v(op,om)/2"
    run_spice(directory, "servo", common+servo, "op\nwrdata offset.txt v(ip,im)")
    trim = table(directory, "offset")[1,0]
    bp, bm = VIC + trim / 2, VIC - trim / 2
    loads = "Clp op 0 250f\nClm om 0 250f\n"
    caps = "Csp srcp fp 1p\nCsm srcm fm 1p\nCfp fp om 250f\nCfm fm op 250f\n"
    # Differential two-port at the summing junction (KCL with the split nodes reunited).
    for j in (1, 2):
        body = common+loads+caps+"Vsrcp srcp 0 0\nVsrcm srcm 0 0\n"
        for name, node, bias, mag in [("gp","ip",bp,0.5),("gm","im",bm,-0.5),("fp","fp",bp,0.5),("fm","fm",bm,-0.5)]:
            active = (j == 1) == (name[0] == "g")
            body += f"V{name} {node} 0 dc {bias:.16g} ac {mag if active else 0}\n"
        run_spice(directory, "port"+str(j), body, AC+f"\nlet g=(i(vgm)-i(vgp))/2\nlet f=(i(vfm)-i(vfp))/2\nwrdata y{j}.txt real(g) imag(g) real(f) imag(f)")
    f, a,b,c,d = table(directory, "y1")
    _, e,h,k,l = table(directory, "y2")
    loop = (c+1j*d+e+1j*h)/(a+1j*b+k+1j*l)
    mag, phase = db(loop), np.unwrap(np.angle(loop))*180/np.pi
    cross = np.where((mag[:-1] >= 0) & (mag[1:] < 0))[0]
    if len(cross) != 1:
        raise ValueError(f"Expected one downward unity crossing, got {cross}")
    i = cross[0]
    frac = mag[i]/(mag[i]-mag[i+1])
    fu = f[i]*(f[i+1]/f[i])**frac
    pm = 180+phase[i]+frac*(phase[i+1]-phase[i])
    drive = f"Vcm cm 0 {VIC}\nVid id 0 dc {trim:.15g} ac 1\nEp ip cm id 0 0.5\nEm im cm id 0 -0.5\n"
    direct = common+drive+"Clp op 0 450f\nClm om 0 450f\n"
    op_expr = ["v(op)", "v(x1.xp)", "v(x1.t)", "v(x1.b)", "isupply"]
    op_expr += [f"@m.x1.m{m}[{attr}]" for m in DEVICES for attr in ("id","gm","gds","vds","vdsat")]
    ctl = "op\nlet isupply = -i(vdd)\nwrdata op.txt "+" ".join(op_expr)+"\n"+AC+"\nlet adm=v(op,om)\nwrdata adm.txt real(adm) imag(adm)"
    if full:
        ctl += "\ndc Vid -0.002 0.002 0.1u\nwrdata swing.txt v(op,om)\nalter Vid=0.1u\ndc Vcm 0 "+str(vdd)+" 0.001\nwrdata icmr.txt v(op,om)"
    run_spice(directory,"direct",direct,ctl)
    _, ar, ai = table(directory,"adm")
    adm = ar+1j*ai
    op = table(directory,"op")[1:,0]
    if len(op) != len(op_expr):
        raise RuntimeError("Operating point column count mismatch")
    branch_sum = sum(op[op_expr.index(f"@m.x1.m{m}[id]")] for m in ("ref","3","4","5","6"))
    if not np.isclose(op[4], branch_sum, rtol=1e-4, atol=1e-10):
        raise RuntimeError("Supply current disagrees with top-side branch sum")
    metrics = dict(gain_db=db(adm[0]),loop_db=mag[0],ugb_MHz=fu/1e6,pm_deg=pm,
                   power_uW=op[4]*vdd*1e6,voc_V=op[0],offset_mV=trim*1000)
    wave_body = common+loads+caps.replace(" fp "," ip ").replace(" fm "," im ")
    wave_body += f"""Vsrcp srcp 0 dc {bp:.16g} ac 1 pulse({bp:.16g} {bp+0.03125:.16g} 25n 10p 10p 50n 100n)
Vsrcm srcm 0 dc {bm:.16g} pulse({bm:.16g} {bm-0.03125:.16g} 25n 10p 10p 50n 100n)
* DC feeds: E scales voltage, F reflects coil current, Zin = 1 GH * s.
Etp htp 0 srcp ip 1m
Ltp htp 0 1
Ftp srcp ip Etp -1u
Etm htm 0 srcm im 1m
Ltm htm 0 1
Ftm srcm im Etm -1u
"""
    run_spice(directory,"tran",wave_body,"tran 10p 200n 0 10p\nwrdata step.txt v(op,om)")
    t, y = table(directory,"step")
    if t[-1] < 199.999e-9:
        raise RuntimeError("Incomplete transient")
    metrics.update(transient(t,y))
    curves = dict(freq=f, loop_mag=mag, loop_phase=phase, time=t, step=y)
    if full:
        x,y = table(directory,"swing")
        gs = db(y/np.where(abs(x)>1e-12,x,np.inf))
        mid = int(np.argmin(abs(x)))
        gs[mid] = db(adm[0])
        lo,hi = bounds(y,gs,mid,np.max(gs)-3)
        cm, ycm = table(directory,"icmr")
        gc = db(ycm/1e-7)
        low,high = bounds(cm,gc,int(np.argmin(abs(cm-VIC))),db(adm[0])-3)
        metrics.update(swing_low_V=lo,swing_high_V=hi,swing_V=hi-lo,icmr_low_V=low,icmr_high_V=high)
        curves.update(vout=y,dc_gain=gs,vic=cm,cm_gain=gc)
        for name in ("cmrr","psrr"):
            body=common.replace(f"dc {vdd}",f"dc {vdd} ac {int(name=='psrr')}")+f"Vcm ip 0 dc {VIC} ac {int(name=='cmrr')}\nVshort im ip 0\nClp op 0 450f\nClm om 0 450f"
            run_spice(directory,name,body,AC+f"\nwrdata {name}.txt real(v(op)) imag(v(op))")
            _,r,im = table(directory,name)
            ratio=db(adm/(r+1j*im))
            metrics[name+"_db"]=ratio[0]
            curves[name]=ratio
        run_spice(directory,"noise",wave_body,"noise v(op,om) Vsrcp dec 100 100k 100G 1\nsetplot noise1\nwrdata density.txt onoise_spectrum\nsetplot noise2\nwrdata noise.txt onoise_total\nprint all > noise_components.txt")
        metrics["noise_uV"]=table(directory,"noise")[1,0]*1e6
        curves["noise_freq"],curves["noise_density"]=table(directory,"density")
        metrics["op"] = dict(zip(op_expr,op))
    return metrics,curves


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("round",type=Path)
    parser.add_argument("--keep",type=Path)
    args=parser.parse_args()
    with tempfile.TemporaryDirectory() as temp:
        work=args.keep or Path(temp)
        metrics,curves=simulate(args.round/"ota.cir",work)
        (args.round/"metrics.json").write_text(json.dumps(metrics,indent=2)+"\n")
        np.savez_compressed(args.round/"curves.npz",**curves)
        shutil.copyfile(work/"noise_components.txt",args.round/"noise_components.txt")
        print(json.dumps({k:v for k,v in metrics.items() if k!="op"},indent=2))


if __name__ == "__main__":
    main()
