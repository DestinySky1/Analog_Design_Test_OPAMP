"""Plot the seven testbench measurements from bias_review.py."""
import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

src, output = map(Path, sys.argv[1:])
with (src / "pvt_dc.csv").open() as f:
    corners = [r for r in csv.DictReader(f) if float(r["vdd_V"]) == 1.1 and int(r["temp_C"]) == 27]

def read(name):
    return np.genfromtxt(src / (name + ".csv"), delimiter=",", names=True)

fig, axes = plt.subplots(4, 2, figsize=(12, 12.5), constrained_layout=True)
blue, red, green = "#235b94", "#aa451c", "#168075"
plt.rcParams["lines.linewidth"] = 1.7

def panel(ax, title, x, y):
    ax.set(title=title, xlabel=x, ylabel=y)
    ax.grid(alpha=.18)
    ax.spines[["top", "right"]].set_visible(False)

ax = axes[0, 0]
panel(ax, "Branch currents at 1.1 V, 27 °C", "Model assumption", "Drain current (µA)")
for k, label, style, color in [("mtail_id","Mtail","o-",blue),("m5_id","M5","s-",red),("m6_id","M6","x--",green)]:
    ax.plot([r["corner"].upper() for r in corners], [float(r[k])*1e6 for r in corners], style, label=label, color=color)
ax.legend(ncol=3)

def twin(ax, x, y1, y2, left, right, title, xlabel):
    panel(ax, title, xlabel, left)
    ax.plot(x, y1, color=blue)
    other = ax.twinx()
    other.plot(x, y2, color=red)
    other.set_ylabel(right, color=red)
    ax.set_ylabel(left, color=blue)

t = read("temperature")
twin(axes[0, 1], t["temp_C"], t["supply_A"]*1e6, t["voc_V"], "Supply current (µA)", "Output CM (V)", "Temperature sweep, TT, 1.1 V", "Temperature (°C)")
v = read("vdd")
twin(axes[1, 0], v["vdd_V"], v["supply_A"]*1e6, v["mtail_margin_V"]*1e3, "Supply current (µA)", "Mtail headroom (mV)", "Supply sweep, TT, 27 °C", "Supply (V)")
cm = read("input_cm")
ax = axes[1, 1]
panel(ax, "Input common-mode sweep", "Input CM (V)", "Mtail current (µA)")
ax.plot(cm["input_cm_V"], cm["mtail_id"]*1e6, color=blue)
ax.axvline(.75, color="#666666", linestyle=":", label="Nominal 0.75 V")
ax.legend()
with np.load(src / "large_signal.npz") as tran:
    for ax, key, k, title, y in [(axes[2, 0], "stage2_from_vdd_A", 1e6, "Second-stage supply current", "Current (µA)"),
                                (axes[2, 1], "voc_V", 1e3, "Output common-mode transient", "Output CM (mV)")]:
        panel(ax, title, "Time (ns)", y)
        ax.plot(tran["time_s"]*1e9, tran[key]*k, color=blue)
mc = read("monte_carlo")
ax = axes[3, 0]
panel(ax, "20 assumed threshold-mismatch samples", "Open-loop output offset (V)", "M5 − M6 drain current (µA)")
ax.scatter(mc["vos_open_V"], mc["delta_i56_open_A"]*1e6, color=blue, s=20)
ax = axes[3, 1]
panel(ax, "Common-mode return ratio, TT, 1.1 V, 27 °C", "Frequency (Hz)", "Magnitude (dB)")
for name, color in [("a", blue), ("s", green), ("output_probe", red)]:
    with np.load(src / "cm" / "tt_1.1_27" / (name + ".npz")) as data:
        ax.semilogx(data["freq_Hz"], 20*np.log10(abs(data["loop"])), label=name, color=color)
ax.axhline(0, ls=":", color="#555555")
ax.legend(ncol=3, fontsize=8)
fig.suptitle("180 nm OTA   |   Bias, mismatch and common-mode measurements", fontsize=17)
fig.savefig(output, dpi=145)
