"""Plot single-device tables, independently loaded stages, and measured complete-OTA responses."""
import csv
import json
from pathlib import Path
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from devices import Lookup, WIDTH

raw, out = map(Path, sys.argv[1:])
def rows(name):
    with (raw / (name+".csv")).open() as stream:
        return list(csv.DictReader(stream))
m = json.loads((raw/"metrics.json").read_text())
st = json.loads((out/"stages.json").read_text())
d = np.load(raw/"curves.npz")
lut = Lookup(out/"devices.npz")
teal, rust, navy = "#08766e","#b6502b","#203851"
plt.rcParams.update({"font.size":9, "legend.frameon":False, "axes.grid":True,"grid.alpha":.18,
                     "axes.spines.top":False,"axes.spines.right":False,"pdf.fonttype":42})
def save(fig, name):
    fig.savefig(out/(name+".pdf"),bbox_inches="tight",pad_inches=.06)
    plt.close(fig)
fig,axes=plt.subplots(2,2,figsize=(7.15,4.7),layout="constrained")
n,p=st["stage1_design"],st["stage2_design"]
for pol,length,drain,body,point,label,color in (
    ("n",n["ln"],.52-n["tail"],n["tail"],n["n"],"Input NMOS",teal),
    ("p",p["lp"],1.1-.59,0,p["p"],"Output PMOS",rust)):
    i,gm,gd,_,cap=lut.curve(pol,length,drain,body).T
    x=gm/i
    for ax,y,sel,ylabel in zip(axes.flat,(i/WIDTH*1e6,gm/gd,gm/(2*np.pi*cap)*1e-9),
            (point["j"]*1e6,point["ai"],point["ft"]*1e-9),("Current density (µA/µm)","Intrinsic gain (V/V)","Estimated transit frequency (GHz)")):
        mask=(x>5)&(x<25)&(i/WIDTH>1e-9)
        ax.semilogy(x[mask],y[mask],color=color,label=label)
        ax.plot(point["eta"],sel,"o",ms=4,color=color)
        ax.set(xlabel="Transconductance efficiency (1/V)",ylabel=ylabel)
axes[0,0].legend()
for i,color in [(1,teal),(2,rust)]:
    f,re,im=np.loadtxt(out/f"stage{i}_gain.txt",skiprows=1).T
    axes[1,1].semilogx(f/1e6,20*np.log10(np.hypot(re,im)),label=f"Stage {i}",color=color)
axes[1,1].set(xlabel="Frequency (MHz)",ylabel="Loaded stage gain (dB)",xlim=(.01,2000),ylim=(-25,40))
axes[1,1].legend()
save(fig,"sizing")
fig,axes=plt.subplots(3,2,figsize=(7.15,6.35),layout="constrained")
ax=axes.ravel()
f=d["freq"]/1e6
for a,curve,title,y in [(ax[0],"loop_mag",f"{m['loop_db']:.1f} dB DC   /   {m['ugb_MHz']:.1f} MHz",0),
                         (ax[1],"loop_phase",f"Phase margin {m['pm_deg']:.1f}°",m["pm_deg"]-180)]:
    a.semilogx(f,d[curve],color=teal);a.plot(m["ugb_MHz"],y,"o",color=rust,ms=4)
    a.set(xlim=(.001,3000),xlabel="Frequency (MHz)",ylabel="Loop gain (dB)" if curve=="loop_mag" else "Phase (deg)",title=title)
ax[2].plot(d["vout"],d["dc_gain"],color=teal);ax[2].set(xlabel="Differential output (V)",ylabel="DC gain (dB)",title=f"3 dB swing ±{m['swing_high_V']:.3f} V")
ax[3].plot(d["vic"],d["cm_gain"],color=teal);ax[3].set(xlabel="Input common mode (V)",ylabel="DC gain (dB)",ylim=(25,72),title=f"3 dB input range {m['icmr_low_V']:.3f}–{m['icmr_high_V']:.3f} V")
for a,vals in [(ax[2],("swing_low_V","swing_high_V")),(ax[3],("icmr_low_V","icmr_high_V"))]:
    for k in vals:a.axvline(m[k],color=rust,ls=":",lw=1)
for key,color in [("cmrr",teal),("psrr",rust)]:
    ax[4].semilogx(f,d[key],color=color,label=f"{key.upper()} {m[key+'_db']:.1f} dB")
ax[4].legend();ax[4].set(xlabel="Frequency (MHz)",ylabel="Rejection (dB)")
ax[5].loglog(d["noise_freq"],d["noise_density"]*1e9,color=teal)
ax[5].set(xlabel="Frequency (Hz)",ylabel="Output noise (nV/√Hz)",title=f"Integrated noise {m['noise_uV']:.1f} µV rms")
save(fig,"performance")
fig,axes=plt.subplots(2,2,figsize=(7.15,4.9),layout="constrained")
ax=axes.ravel()
ax[0].plot(d["time"]*1e9,d["step"]*1e3,color=teal)
ax[0].set(xlabel="Time (ns)",ylabel="Differential output (mV)")
for key,onset,col in [("rise",25,teal),("fall",75.01,rust)]:
    t=d["time"]*1e9-onset
    plateau=np.mean(d["step"][(t>=48)&(t<=49)])
    err=(d["step"]-plateau)*400
    ts=m[key+"_settle0.5_ns"]
    ax[1].plot(t,err,color=col,label=f"{key} {ts:.2f} ns")
    ax[1].plot(ts,np.interp(ts,t,err),"o",color=col,ms=3)
ax[1].legend()
for a,kind in [(ax[2],"pvt"),(ax[3],"mismatch")]:
    for row in rows(kind):
        t,y=np.loadtxt(raw/"decks"/row["case"]/"differential/step.txt",skiprows=1).T
        t=t*1e9-25
        a.plot(t,(y-np.mean(y[(t>=48)&(t<=49)]))*400,color=teal,alpha=.35,lw=.7)
    a.set_title("40 PVT conditions" if kind=="pvt" else "20 mismatch samples")
for a in ax[1:]:
    a.set(xlim=(3,12),ylim=(-3,3),xlabel="Time after edge (ns)",ylabel="Dynamic error (%)")
    a.axhspan(-.5,.5,alpha=.11,color=navy)
save(fig,"settling")
# Include the data for each condition compactly in the report.
r=rows("pvt")
with (out/"corners.tex").open("w") as f:
    for corner in ("tt","ff","ss","fs","sf"):
        for vdd in (1.1,1.2):
            vals=[corner.upper(),f"{vdd:.1f}"]
            for t in (-25,-20,27,85):
                row=next(q for q in r if q["corner"]==corner and float(q["supply_V"])==vdd and int(q["temp_C"])==t)
                vals.append(" / ".join(f"{float(row[k]):.1f}" for k in ("gain_db","ugb_MHz","pm_deg")))
            print(" & ".join(vals)+r" \\",file=f)
