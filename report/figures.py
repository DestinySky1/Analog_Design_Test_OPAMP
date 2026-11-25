"""Render figures from the archived sample arrays. All voltages are differential unless noted."""
import csv
import json
import os
import re
from pathlib import Path

os.environ.setdefault("MPLBACKEND","Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Rectangle

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
data=np.load(ROOT/"round3/curves.npz")
first=np.load(ROOT/"round1/curves.npz")
m=json.loads((ROOT/"round3/metrics.json").read_text())
op=m["op"]
teal="#006d70"
navy="#233953"
orange="#ab5225"
plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False,
                     "axes.labelcolor":navy,"xtick.color":navy,"ytick.color":navy,
                     "legend.frameon":False,"axes.grid":True,"grid.alpha":.19,
                     "pdf.fonttype":42})
def save(fig,name):
    fig.savefig(HERE/(name+".pdf"),bbox_inches="tight",pad_inches=.06)
    plt.close(fig)

def nominal():
    fig,ax=plt.subplots(2,2,figsize=(7.6,5.7),layout="constrained")
    f=data["freq"]/1e6
    for c,label,color in [(first,"Independent",orange),(data,"Revised",teal)]:
        ax[0,0].semilogx(f,c["loop_mag"],label=label,color=color)
        ax[0,1].semilogx(f,c["loop_phase"],color=color)
    ax[0,0].axhline(0,color=navy,lw=.7)
    ax[0,0].plot(m["ugb_MHz"],0,"o",color=teal)
    ax[0,0].set(xlabel="Frequency (MHz)",ylabel="Loop gain (dB)",ylim=(-50,60),title="(a) Differential loop")
    ax[0,0].legend(loc="lower left")
    ax[0,0].text(.04,.58,f"{m['loop_db']:.1f} dB\n{m['ugb_MHz']:.1f} MHz",transform=ax[0,0].transAxes)
    ax[0,1].plot(m["ugb_MHz"],-180+m["pm_deg"],"o",color=teal)
    ax[0,1].axhline(-180,color=navy,lw=.7)
    ax[0,1].set(xlabel="Frequency (MHz)",ylabel="Phase (deg)",title=f"(b) Phase margin {m['pm_deg']:.1f}°")
    for a in ax[0]:
        a.set_xlim(.001,10000)
    ax[1,0].plot(data["vout"],data["dc_gain"],color=teal)
    ax[1,0].axhline(np.max(data["dc_gain"])-3,color=navy,ls="--",lw=.8)
    for key in ("swing_low_V","swing_high_V"):
        ax[1,0].axvline(m[key],color=orange,ls=":")
    ax[1,0].set(xlabel="Differential output (V)",ylabel="Large-signal gain (dB)",title=f"(c) Swing ±{m['swing_high_V']:.3f} V")
    ax[1,1].plot(data["vic"],data["cm_gain"],color=teal)
    ax[1,1].axhline(m["gain_db"]-3,color=navy,ls="--",lw=.8)
    for key in ("icmr_low_V","icmr_high_V"):
        ax[1,1].axvline(m[key],color=orange,ls=":")
    ax[1,1].set(xlabel="Input common mode (V)",ylabel="DC gain (dB)",ylim=(25,75),title="(d) Input range 0.443–0.927 V")
    save(fig,"frequency")

def time_noise():
    fig,axs=plt.subplots(2,3,figsize=(7.65,4.9),layout="constrained")
    ax=axs.flatten()
    for c,label,color in [(first,"Independent",orange),(data,"Revised",teal)]:
        ax[0].plot(c["time"]*1e9,c["step"]*1e3,label=label,color=color)
        for j,(key,onset) in enumerate([("rise",25),("fall",75.01)],1):
            t=c["time"]*1e9-onset
            plateau=np.mean(c["step"][(t>=48)&(t<=49)])
            err=(c["step"]-plateau)/.25*100
            ax[j].plot(t,err,color=color)
            if c is data:
                ts=m[key+"_settle0.5_ns"]
                ax[j].axvline(ts,color=teal,lw=.9,ls=":")
                ax[j].plot(ts,np.interp(ts,t,err),"o",color=teal,ms=3)
            ax[j].axhspan(-.5,.5,color=teal,alpha=.07)
            ax[j].set(xlim=(2,17),ylim=(-3,3),xlabel="After edge (ns)",ylabel="Dynamic error (%)",title=f"({chr(97+j)}) {key.title()} {m[key+'_settle0.5_ns']:.2f} ns")
    ax[0].set(xlim=(0,200),xlabel="Time (ns)",ylabel="Output (mV)",title="(a) Full response")
    ax[0].legend(fontsize=8)
    ax[3].semilogx(data["freq"],data["cmrr"],label="CMRR, 95.1 dB",color=teal)
    ax[3].semilogx(data["freq"],data["psrr"],label="PSRR, 103.7 dB",color=orange)
    ax[3].set(xlabel="Frequency (Hz)",ylabel="Rejection (dB)",title="(d) Input / supply")
    ax[3].legend(fontsize=8)
    ax[4].loglog(data["noise_freq"],data["noise_density"]*1e9,color=teal)
    ax[4].set(xlabel="Frequency (Hz)",ylabel="Noise (nV/√Hz)",title="(e) Output density")
    txt=(ROOT/"round3/noise_components.txt").read_text()
    comps=[(k,float(v)) for k,v in re.findall(r"(?m)^onoise_total\.([mr]\.x1\.\w+) = ([\deE+.-]+)$",txt)]
    groups={"Input M1/2":("m1","m2"),"Load M3/4":("m3","m4"),"M5/6":("m5","m6"),"M7/8":("m7","m8"),"Rz pair":("rzp","rzm")}
    powers=[sum((v/(m["noise_uV"]*1e-6))**2*100 for k,v in comps if k.split(".")[-1] in names) for names in groups.values()]
    ax[5].barh(list(groups),powers,color=teal)
    ax[5].set(xlabel="Variance share (%)",title="(f) Noise budget")
    save(fig,"time_noise")

def variation():
    fig,ax=plt.subplots(1,3,figsize=(7.6,2.3),layout="constrained")
    for a,kind,label in [(ax[0],"pvt","30 P/V/T cases"),(ax[1],"mismatch","20 Vth samples")]:
        waves=np.load(ROOT/f"round3/{kind}_waves.npz")
        for k in waves.files:
            if k.endswith("_t"):
                t=waves[k]*1e9-25
                y=waves[k[:-2]+"_v"]
                dc=np.mean(y[(t>=48)&(t<=49)])
                a.plot(t,(y-dc)*400,alpha=.38,color=teal,lw=.85)
        a.axhspan(-.5,.5,color=orange,alpha=.15)
        a.set(xlim=(2,14),ylim=(-4,4),xlabel="After rising edge (ns)",ylabel="Error (%)",title=label)
    rows=list(csv.DictReader((ROOT/"round3/mismatch.csv").open()))
    ax[2].hist([float(r["offset_mV"]) for r in rows],bins=7,color=teal,edgecolor="white")
    ax[2].set(xlabel="Input null (mV)",ylabel="Samples",title="Offset distribution")
    save(fig,"variation")

def schematic():
    fig, ax=plt.subplots(figsize=(7.65,4.8))
    ax.set(xlim=(0,16.5),ylim=(0,10));ax.axis("off")
    def line(x,y,X,Y):
        ax.plot([x,X],[y,Y],color=navy,lw=1.25,solid_capstyle="round")
    def label(x,y,text,**kw):
        ax.text(x,y,text,ha=kw.pop("ha","center"),va="center",fontsize=kw.pop("fontsize",9),**kw)
    def dot(x,y): ax.plot(x,y,"o",ms=2.8,color=navy)
    def mos(x,y,p,gate,ident):
        line(x,y-.55,x+.26,y-.55);line(x+.26,y-.55,x+.26,y+.55);line(x+.26,y+.55,x,y+.55)
        line(x+.03,y-.44,x+.03,y+.44)
        gx=x-.18 if p else x+.03
        if p: ax.add_patch(Circle((x-.07,y),.105,facecolor="white",edgecolor=navy,lw=1))
        line(x-.54,y,gx,y);label(x-.62,y,gate,ha="right",color=teal)
        sizes = {"M1":"18/.55","M2":"18/.55","M3":"28/.42","M4":"28/.42",
                 "M5":"64.4/.42","M6":"64.4/.42","M7":"22/.64","M8":"22/.64",
                 "Mref":"6/.60","Mtail":"36/.60"}
        label(x+.43,y,ident+"\n"+sizes[ident],ha="left",fontsize=8)
    def rail(x,y,s):
        line(x-.28,y,x+.28,y);label(x,y+.29,s)
    label(.1,9.65,"Transistor core",ha="left",weight="bold",fontsize=11)
    for x,upper,lower,gate1,gate2,node,low in [(2.2,"M3","M1","a","ip","xp","t"),(5.2,"M4","M2","a","im","xm","t"),
                                               (9.3,"M5","M7","xp","s","op","0"),(12.4,"M6","M8","xm","s","om","0")]:
        mos(x,8,True,gate1,upper);mos(x,5.7,False,gate2,lower)
        line(x,8.55,x,9.02);rail(x,9.02,"VDD")
        line(x,7.45,x,6.25);dot(x,6.88);line(x,6.88,x+.4,6.88);label(x+.48,6.88,node,ha="left",color=teal)
        line(x,5.15,x,4.85);label(x,4.63,low,color=teal)
    label(3.7,4.05,"xp, xm = 0.508 V   ·   46.7 µA/side")
    label(10.85,4.05,"op, om = 0.591 V   ·   105.4 µA/side")
    line(.1,3.7,16,3.7)
    label(.1,3.28,"Tail bias",ha="left",weight="bold")
    mos(2.1,1.5,False,"b","Mref");mos(5.0,1.5,False,"b","Mtail")
    for x,nd in [(2.1,"b"),(5.0,"t")]:
        line(x,2.05,x,2.35);label(x,2.6,nd,color=teal)
        line(x,.95,x,.65);label(x,.42,"0")
    label(.13,2.83,"VDD → 17.2 µA → b",ha="left",fontsize=8)
    label(3.8,.08,"b = 0.550 V   ·   t = 0.161 V",fontsize=8)
    label(7.2,3.28,"Common-mode sensing and Miller branches",ha="left",weight="bold")
    for row,s in enumerate(["xp, xm  →  (800 kΩ ∥ 40 fF each)  →  a",
                             "op, om  →  (800 kΩ ∥ 40 fF each)  →  s",
                             "xp  →  4.15 kΩ  →  200 fF  →  op",
                             "xm  →  4.15 kΩ  →  200 fF  →  om"]):
        label(7.2,2.57-row*.62,s,ha="left")
    save(fig,"schematic")

if __name__=="__main__":
    schematic();nominal();time_noise();variation()
