"""One gm/ID sizing iteration for the third-round OTA tail mirror."""
import argparse
import csv
from pathlib import Path

import numpy as np

from bias_review import DC_INPUT, circuit, dc, setup
from measure import ROOT, model_text, prepare_ota, run_spice, simulate, table

DUT = ROOT / "round3/ota.cir"
UNIT_W = 10.0  # drawn micrometres
HEADROOM = 0.020  # chosen design margin, V


def mirror_lines(source):
    return {line.split()[0]: line.split() for line in source.splitlines()
            if line.startswith(("Mref ", "Mtail "))}


def main(out):
    out.mkdir(parents=True, exist_ok=True)
    with (ROOT / "audit/bias/pvt_dc.csv").open() as stream:
        baseline = list(csv.DictReader(stream))
    worst = min(baseline, key=lambda r: float(r["mtail_margin_V"]))
    source = DUT.read_text()
    mirror = mirror_lines(source)
    length = mirror["Mtail"][7]
    assert mirror["Mref"][7] == length
    corner, temp = worst["corner"], float(worst["temp_C"])
    vds = float(worst["mtail_vds"])
    target = vds - HEADROOM
    reference = (f"Mn d g 0 0 nch W={UNIT_W}u {length}\n"
                 f"Md g g 0 0 nch W={UNIT_W}u {length}")
    devices, _ = prepare_ota(reference, None)
    (out / "dut.lib").write_text(devices + "\n")
    (out / "model.lib").write_text(model_text(corner, {}))
    run_spice(out, "mirror_lut", f".temp {temp}\nVd d 0 {vds}\nVg g 0 0",
              "save all @mn[id] @mn[gm] @mn[vdsat] @md[id]\ndc Vg 0.25 0.85 0.001\n"
              "wrdata transfer.txt @mn[id] @mn[gm] @mn[vdsat] @md[id]")
    vg, itail, gm, vdsat, iref = table(out, "transfer")
    assert np.all(np.diff(vdsat) > 0) and vdsat[0] < target < vdsat[-1]
    per_width_t, per_width_r = itail / UNIT_W, iref / UNIT_W
    efficiency = np.interp(target, vdsat, gm / itail)
    jtail = np.interp(target, vdsat, per_width_t)
    jref = np.interp(target, vdsat, per_width_r)
    np.savetxt(out / "lut.csv", np.column_stack((vg, vdsat, gm / itail, per_width_t, per_width_r)),
               header="VGS_V,VDSAT_V,gm_over_Id_1_per_V,Jtail_A_per_um,Jref_A_per_um",
               delimiter=",", comments="")
    for name, current, density in (("Mref", float(worst["mref_id"]), jref),
                                   ("Mtail", float(worst["mtail_id"]), jtail)):
        words = mirror[name].copy()
        width = current / density
        words[6] = f"W={round(width, 1):.1f}u"
        source = source.replace(" ".join(mirror[name]), " ".join(words))
        print(f"{name}: J={density*1e6:.4f} uA/um, W={width:.3f} um -> {words[6]}")
    print(f"target VDSAT={target*1000:.2f} mV, gm/ID={efficiency:.2f} 1/V")
    candidate = out / "candidate.cir"
    candidate.write_text(source)
    cases = [r for r in baseline if float(r["mtail_margin_V"]) < 0
             or (r["corner"], r["vdd_V"], r["temp_C"]) == ("tt", "1.1", "27")]
    summary = []
    for row in cases:
        c, v, t = row["corner"], float(row["vdd_V"]), float(row["temp_C"])
        work = out / f"{c}_{v}_{t:g}"
        setup(work, c, source=source)
        _, (op,) = dc(work, "bias", circuit(t, v) + DC_INPUT)
        result = dict(corner=c, VDD_V=v, temp_C=t, before_V=float(row["mtail_margin_V"]),
                      after_V=op["mtail_margin_V"], tail_A=op["mtail_id"])
        if row == worst or c == "tt":
            metrics, _ = simulate(candidate, work / "performance", vdd=v, temp=t, corner=c, full=False)
            for k in ("pm_deg", "rise_static_pct", "fall_static_pct", "rise_settle0.5_ns",
                      "fall_settle0.5_ns", "rise_dynamic10_pct", "fall_dynamic10_pct", "power_uW"):
                result[k] = metrics[k]
        summary.append(result)
    with (out / "verification.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(dict.fromkeys(k for r in summary for k in r)),
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(summary)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    main(parser.parse_args().output)
