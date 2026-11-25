"""Replay both DUTs and the variation matrix, and verify the published measurements."""
import csv
import json
import sys
from pathlib import Path

import numpy as np

from measure import ROOT, simulate
from offset_sensitivity import write_sensitivities
from variation import sweep
from itertools import product


def check_limits(metrics, full=True):
    limits = {"pm_deg":(60,180)}
    for edge in ("rise","fall"):
        for suffix,upper in [("static_pct",0.5),("dynamic10_pct",0.5),("settle0.5_ns",10)]:
            limits[f"{edge}_{suffix}"] = (0,upper)
    if full:
        limits.update(swing_V=(0.5,2.2),cmrr_db=(60,300),psrr_db=(60,300),noise_uV=(0,600))
    for key,(lo,hi) in limits.items():
        value=float(metrics[key])
        if not lo <= value <= hi:
            raise ValueError(f"{key}: {value} outside [{lo}, {hi}]")


def read_rows(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def main(dest):
    dest.mkdir(parents=True,exist_ok=True)
    for name in ("round1","round3"):
        m,curves=simulate(ROOT/name/"ota.cir",dest/name)
        (dest/name/"metrics.json").write_text(json.dumps(m,indent=2))
        original=json.loads((ROOT/name/"metrics.json").read_text())
        for key in ("gain_db","loop_db","ugb_MHz","pm_deg","swing_V","noise_uV",
                    "power_uW","cmrr_db","psrr_db","rise_static_pct","fall_static_pct",
                    "rise_dynamic10_pct","fall_dynamic10_pct","rise_settle0.5_ns","fall_settle0.5_ns"):
            np.testing.assert_allclose(m[key],original[key],rtol=0.005,atol=0.002,err_msg=f"{name}: {key}")
        if name=="round3":
            check_limits(m)
        if name=="round1" and (m["rise_static_pct"]<=.5 or m["pm_deg"]>=60):
            raise ValueError("Independent-version shortfalls did not reproduce")
        print(name, {k:round(m[k],4) for k in ("rise_static_pct","pm_deg","noise_uV","power_uW")})
    pvt=list(product(("tt","ff","ss","sf","fs"),(1.1,1.2),(-25,27,85),(None,)))
    mismatch=[("tt",1.1,27,s) for s in range(101,121)]
    for name,cases in [("pvt",pvt),("mismatch",mismatch)]:
        rows=sweep(cases,name,2,dest)
        saved=read_rows(ROOT/"round3"/(name+".csv"))
        if [r["case"] for r in rows] != [r["case"] for r in saved]:
            raise ValueError(f"{name}: case list differs")
        for r,expected in zip(rows,saved):
            check_limits(r,full=False)
            for key in ("gain_db","loop_db","ugb_MHz","pm_deg","offset_mV","rise_settle0.5_ns","fall_settle0.5_ns"):
                np.testing.assert_allclose(r[key],float(expected[key]),rtol=.006,atol=.03,err_msg=f"{r['case']} {key}")
        print(f"{name}: replayed {len(cases)} cases")
    sensitivity=dest/"offset_sensitivity.csv"
    write_sensitivities(sensitivity)
    for row,ref in zip(read_rows(sensitivity),read_rows(ROOT/"round3"/sensitivity.name)):
        np.testing.assert_allclose(float(row["variance_mV2"]),float(ref["variance_mV2"]),rtol=.005,atol=1e-6)


if __name__=="__main__":
    main(Path(sys.argv[1]))
