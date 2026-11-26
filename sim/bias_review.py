"""Run the seven bias and common-mode checks for the released third-round OTA."""
import argparse
import csv
from itertools import product
from pathlib import Path
from zipfile import ZipFile

import numpy as np

from measure import DEVICES, ROOT, VIC, db, model_text, prepare_ota, run_spice, simulate, table


DUT = (ROOT / "round3/ota.cir").read_text()
OPTIONS = ".options method=gear maxord=2 reltol=1e-5 vntol=1e-9 abstol=1e-14 gmin=1e-14"
PINS = "ip im op om vdd 0"
MOS = ["m" + suffix for suffix in DEVICES]
ATTRS = ("id", "vds", "vdsat")
VECTORS = ["v(op)", "v(om)", "v(x1.a)", "v(x1.s)", "v(ip,im)", "i(vdd)"]
VECTORS += [f"@m.x1.{m}[{attr}]" for m in MOS for attr in ATTRS]
HEADERS = ["op_V", "om_V", "a_V", "s_V", "vid_V", "supply_A"]
HEADERS += [f"{m}_{attr}" for m in MOS for attr in ATTRS]
DC_INPUT = f"Vcm cm 0 {VIC}\nVid id 0 0\nEp ip cm id 0 0.5\nEm im cm id 0 -0.5"
CAPS = "Clp op 0 250f\nClm om 0 250f"


def setup(path, corner="tt", seed=None, source=DUT):
    path.mkdir(parents=True, exist_ok=True)
    circuit, variations = prepare_ota(source, seed)
    (path / "dut.lib").write_text(circuit + "\n")
    (path / "model.lib").write_text(model_text(corner, variations))


def circuit(temp=27, vdd=1.1, pins=PINS):
    return f".temp {temp}\n{OPTIONS}\nVdd vdd 0 {vdd}\nX1 {pins} ota\n"


def dc(path, name, body, command="op"):
    vectors = " ".join(VECTORS)
    run_spice(path, name, body, f"save all {vectors}\n{command}\nwrdata {name}.txt {vectors}")
    scale, *values = table(path, name)
    rows = []
    for value in zip(*values, strict=True):
        r = dict(zip(HEADERS, value, strict=True))
        r["supply_A"] *= -1
        r["voc_V"] = (r["op_V"] + r["om_V"]) / 2
        r["vod_V"] = r["op_V"] - r["om_V"]
        for m in MOS:
            r[f"{m}_margin_V"] = abs(r[f"{m}_vds"]) - abs(r[f"{m}_vdsat"])
        if not np.isfinite(list(r.values())).all():
            raise ValueError(f"Non-finite DC data in {path}/{name}")
        rows.append(r)
    return scale, rows


def write_rows(path, rows):
    with path.open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sweeps(out, raw):
    rows = []
    for corner, vdd, temp in product(("tt", "ff", "ss", "fs", "sf"), (1.1, 1.2), (-25, -20, 27, 85)):
        path = raw / f"{corner}_{vdd}_{temp}"
        setup(path, corner)
        _, (r,) = dc(path, "op", circuit(temp, vdd) + DC_INPUT)
        rows.append(dict(corner=corner, vdd_V=vdd, temp_C=temp, **r))
    write_rows(out / "pvt_dc.csv", rows)
    path = raw / "tt_1.1_27"
    for name, column, cmd in (("vdd", "vdd_V", "dc Vdd 1.1 1.2 0.005"),
                              ("temperature", "temp_C", "dc temp -25 85 1"),
                              ("input_cm", "input_cm_V", "dc Vcm 0 1.1 0.001")):
        body = circuit() + DC_INPUT
        if name == "input_cm":
            body = body.replace("Vid id 0 0", "Vid id 0 0.1u")
        values, measurements = dc(path, name, body, cmd)
        write_rows(out / (name + ".csv"), [{column: v, **r} for v, r in zip(values, measurements, strict=True)])
    return rows


def monte_carlo(out, raw):
    rows = []
    for seed in range(101, 121):
        path = raw / f"seed_{seed}"
        setup(path, seed=seed)
        _, (zero,) = dc(path, "untrimmed", circuit() + DC_INPUT)
        servo = f"Bp ip 0 v={VIC}-v(op,om)/2\nBm im 0 v={VIC}+v(op,om)/2"
        _, (trim,) = dc(path, "autozero", circuit() + servo)
        rows.append(dict(seed=seed, vos_open_V=zero["vod_V"], voc_open_V=zero["voc_V"],
                         autozero_vid_V=trim["vid_V"], residual_vod_V=trim["vod_V"],
                         **{f"{m}_{label}_A": r[m+"_id"] for label, r in (("open", zero), ("az", trim))
                            for m in ("mtail", "m5", "m6", "m7", "m8")},
                         delta_i56_open_A=zero["m5_id"]-zero["m6_id"],
                         delta_i56_az_A=trim["m5_id"]-trim["m6_id"]))
    write_rows(out / "monte_carlo.csv", rows)


def large_signal(out, path):
    # Zero-volt meters include source and bulk displacement currents at the stage supply pins.
    lines = []
    for line in DUT.splitlines():
        fields = line.split()
        if fields and fields[0] in ("M5", "M6", "M7", "M8"):
            node = "stage_vdd" if fields[0] in ("M5", "M6") else "stage_gnd"
            fields[3:5] = [node, node]
            line = " ".join(fields)
        if line.startswith(".ends"):
            lines.extend(("Vs2p vdd stage_vdd 0", "Vs2n stage_gnd 0 0"))
        lines.append(line)
    setup(path, source="\n".join(lines))
    # Instrument the exact input/feedback circuit used for the released third-round transient.
    with ZipFile(ROOT / "audit/nominal.zip") as archive:
        original = archive.read("round3/tran.cir").decode()
        reference = np.loadtxt(archive.open("round3/step.txt"), skiprows=1)
    body = original.split(".include dut.lib\n", 1)[1].split(".control", 1)[0]
    ids = " ".join(f"@m.x1.m{i}[id]" for i in (5, 6, 7, 8))
    run_spice(path, "large_signal", body,
              f"save all {ids}\ntran 10p 200n 0 10p\nwrdata large_signal.txt v(op) v(om) {ids} i(v.x1.vs2p) i(v.x1.vs2n)")
    t, op, om, i5, i6, i7, i8, supply, ground = table(path, "large_signal")
    if t[-1] < 199.999e-9 or np.ptp(i5) < 1e-6:
        raise ValueError("Incomplete transient or device currents")
    np.testing.assert_allclose(np.interp(reference[:, 0], t, op-om), reference[:, 1], atol=2e-5)
    np.savez_compressed(out / "large_signal.npz", time_s=t, op_V=op, om_V=om, vod_V=op-om,
                        voc_V=(op+om)/2, m5_A=i5, m6_A=i6, m7_A=i7, m8_A=i8,
                        stage2_from_vdd_A=supply, stage2_to_gnd_A=ground,
                        upper_channel_sum_A=i5+i6, lower_channel_sum_A=i7+i8)


def split_gate(node):
    devices = {"a": ("M3", "M4"), "s": ("M7", "M8")}[node]
    lines = []
    for line in DUT.splitlines():
        words = line.split()
        if words[:1] == [".subckt"]:
            line += f" {node} gate_probe"
        elif words and words[0] in devices:
            assert words[2] == node
            words[2] = "gate_probe"
            line = " ".join(words)
        lines.append(line)
    return "\n".join(lines)


def cm_loop(out, raw, location, op):
    # Close the external capacitive feedback in CM; keep the other internal CM loop closed.
    # 1e20 H supplies DC while appearing open even at the first AC point, 1 Hz.
    feedback = ("Vcm cm 0 0.75\nLp ip cm 1e20\nLm im cm 1e20\n"
                "Csp ip 0 1p\nCsm im 0 1p\nCfp ip om 250f\nCfm im op 250f\n" + CAPS)
    external = location == "output_probe"
    case = f"{op['corner']}_{op['vdd_V']}_{op['temp_C']}"
    path = raw / case / ("cm_" + location)
    curves = out / "cm" / case
    curves.mkdir(parents=True, exist_ok=True)
    setup(path, op["corner"], source=DUT if external else split_gate(location))
    pins = "ip im dp dm vdd 0" if external else PINS + " rx tx"
    body = circuit(op["temp_C"], op["vdd_V"], pins) + feedback + "\n"
    pairs = [("dp", "op"), ("dm", "om")] if external else [("tx", "rx")]
    bias = op["voc_V"] if external else op[location+"_V"]
    columns = []
    for active in (0, 1):
        drives = []
        for k, pair in enumerate(pairs):
            for side, node in enumerate(pair):
                drives.append(f"V{side}_{k} {node} 0 dc {bias:.16g} ac {int(side == active)}")
        sums = ["+".join(f"i(v{side}_{k})" for k in range(len(pairs))) for side in (0, 1)]
        name = "port" + str(active)
        run_spice(path, name, body + "\n".join(drives),
                  f"ac dec 100 1 10G\nlet y0=-({sums[0]})\nlet y1=-({sums[1]})\n"
                  f"wrdata {name}.txt real(y0) imag(y0) real(y1) imag(y1)")
        f, r0, i0, r1, i1 = table(path, name)
        columns.append((r0 + 1j*i0, r1 + 1j*i1))
    (y00, y10), (y01, y11) = columns
    loop = (y10 + y01) / (y00 + y11)
    # Independent, rejoined-loop common injection verifies the admittance and port normalization.
    joined = []
    for k, (left, right) in enumerate(pairs):
        joined.extend((f"Vjoin{k} {left} {right} 0", f"Icheck{k} 0 {left} ac {1/len(pairs)}"))
    node = pairs[0][0]
    run_spice(path, "joined", body+"\n".join(joined), f"ac dec 100 1 10G\nwrdata joined.txt real(v({node})) imag(v({node}))")
    _, zr, zi = table(path, "joined")
    zclosed = 1 / (y00+y10+y01+y11)
    np.testing.assert_allclose(zclosed, zr+1j*zi, rtol=0.001, atol=1e-6)
    mag = db(loop)
    angle = np.rad2deg(np.unwrap(np.angle(loop)))
    if angle[0] > 90:
        angle -= 360
    np.savez_compressed(curves / (location+".npz"), freq_Hz=f, loop=loop, phase_deg=angle,
                        y00=y00, y10=y10, y01=y01, y11=y11, z_joined=zr+1j*zi)
    crossings = []
    for i in np.flatnonzero(np.diff(mag >= 0)):
        weight = mag[i] / (mag[i]-mag[i+1])
        freq = f[i] * (f[i+1]/f[i])**weight
        phase = angle[i] + weight*(angle[i+1]-angle[i])
        crossings.append((freq, phase, "down" if mag[i]>mag[i+1] else "up"))
    rows = []
    for freq, phase, direction in crossings or [(None, None, "none")]:
        rows.append(dict(corner=op["corner"], vdd_V=op["vdd_V"], temp_C=op["temp_C"],
                         probe=location, gain_1Hz_dB=mag[0], max_dB=max(mag), crossing=direction,
                         unity_Hz=freq, phase_deg=phase, pm_deg=180+phase if direction=="down" else None))
    return rows



def verify_tables(out):
    # Reconcile all recorded DC points, seeded samples and identified loop crossings.
    for ref in sorted((ROOT / "audit/bias").glob("*.csv")):
        with ref.open() as baseline, (out / ref.name).open() as replay:
            expected, actual = csv.DictReader(baseline), csv.DictReader(replay)
            if expected.fieldnames != actual.fieldnames:
                raise ValueError(f"{ref.name}: column mismatch")
            for a, b in zip(expected, actual, strict=True):
                for key, value in a.items():
                    try:
                        number = float(value)
                    except ValueError:
                        if b[key] != value:
                            raise ValueError(f"{ref.name}: {key} differs")
                    else:
                        np.testing.assert_allclose(float(b[key]), number, rtol=0.001, atol=1e-9,
                                                   err_msg=f"{ref.name}: {key}")
    for name, count in (("temperature", 111), ("vdd", 21), ("input_cm", 1101)):
        with (out / (name + ".csv")).open() as f:
            if len(list(csv.DictReader(f))) != count:
                raise ValueError(f"Incomplete {name} sweep")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    out = parser.parse_args().output
    raw = out / "decks"
    operating_points = sweeps(out, raw)
    monte_carlo(out, raw)
    large_signal(out, raw / "large_signal")
    rows = []
    for op in operating_points:
        for location in ("output_probe", "a", "s"):
            rows.extend(cm_loop(out, raw, location, op))
    write_rows(out / "cm_loops.csv", rows)
    # Handout II specifies -20 °C; the released 30-case matrix used Handout I's -25 °C.
    cold_rows, cold_waves = [], {}
    for corner, vdd in product(("tt", "ff", "ss", "fs", "sf"), (1.1, 1.2)):
        case = f"{corner}_{vdd}_-20"
        metrics, curves = simulate(ROOT / "round3/ota.cir", raw / case / "differential",
                                   vdd=vdd, temp=-20, corner=corner, full=False)
        cold_rows.append(dict(case=case, corner=corner, supply_V=vdd, temp_C=-20, seed=None, **metrics))
        cold_waves[case + "_t"] = curves["time"]
        cold_waves[case + "_v"] = curves["step"]
    write_rows(out / "minus20_differential.csv", cold_rows)
    np.savez_compressed(out / "minus20_differential_waves.npz", **cold_waves)
    verify_tables(out)


if __name__ == "__main__":
    main()
