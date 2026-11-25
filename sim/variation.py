"""Sweep voltage/temperature, illustrative process stress and independent Vth mismatch."""
import argparse
import csv
import json
import tempfile
from concurrent.futures import ThreadPoolExecutor
from itertools import product
from pathlib import Path

import numpy as np

from measure import ROOT, simulate


def measure_case(case):
    corner, vdd, temp, seed = case
    with tempfile.TemporaryDirectory() as work:
        m, curves = simulate(ROOT/"round3/ota.cir", Path(work), vdd, temp, corner, seed, full=False)
    label = f"{corner}_{vdd}_{temp}" if seed is None else f"seed_{seed}"
    row = dict(case=label, corner=corner, supply_V=vdd, temp_C=temp, seed=seed, **m)
    return row, {label+"_t":curves["time"], label+"_v":curves["step"]}


def sweep(cases, name, workers, output):
    rows, waveforms = [], {}
    with ThreadPoolExecutor(workers) as pool:
        for row, curves in pool.map(measure_case, cases):
            rows.append(row)
            waveforms.update(curves)
    with (output/(name+".csv")).open("w") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    np.savez_compressed(output/(name+"_waves.npz"), **waveforms)
    return rows


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs",type=int,default=2)
    parser.add_argument("--out",type=Path,default=ROOT/"round3")
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    cases=list(product(("tt","ff","ss","sf","fs"),(1.1,1.2),(-25,27,85),(None,)))
    sweep(cases,"pvt",args.jobs,args.out)
    rows=sweep([("tt",1.1,27,s) for s in range(101,121)],"mismatch",args.jobs,args.out)
    print("Vth-only assumed mismatch, sample sigma (mV)", np.std([r["offset_mV"] for r in rows],ddof=1))
