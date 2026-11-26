"""Verify a completed design using the handout benches and archive the measurements."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from itertools import product
import json
from pathlib import Path

import numpy as np
from bias_review import MOS, cm_loop, large_signal, monte_carlo, sweeps, write_rows
from measure import simulate
from review import check_limits


def run(out, dut):
    source = dut.read_text()
    out.mkdir(parents=True, exist_ok=True)
    raw = out / "decks"
    nominal = raw / "nominal"
    metrics, curves = simulate(dut, nominal)
    check_limits(metrics)
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    np.savez_compressed(out / "curves.npz", **curves)
    pts = sweeps(out, raw, source, MOS + ["m9", "m10"])
    monte_carlo(out, raw, source)
    large_signal(out, raw / "instrumented", source, nominal, lower=("M7", "M8", "M9", "M10"))

    def differential(case):
        corner, vdd, temp, seed = case
        label = f"{corner}_{vdd}_{temp}" if seed is None else f"seed_{seed}"
        name = raw / label / "differential"
        m, wave = simulate(dut, name, vdd, temp, corner, seed, full=False)
        row = dict(case=label, corner=corner, supply_V=vdd, temp_C=temp, seed=seed, **m)
        # Total error from the ideal step is supplementary to the separate handout limits.
        for edge, start, sign in (("rise", 25., 1), ("fall", 75.01, -1)):
            t = wave["time"] * 1e9 - start
            base = np.mean(wave["step"][(t >= -2) & (t <= -1)])
            y10 = np.interp(10., t, wave["step"]) - base
            row[edge + "_ideal10_pct"] = 100 * abs(y10 - sign * .25) / .25
        try:
            check_limits(m, full=False)
            row["within_limits"] = True
        except ValueError:
            row["within_limits"] = False
        return row

    with ThreadPoolExecutor(4) as workers:
        cases = product(("tt","ff","ss","fs","sf"), (1.1,1.2), (-25,-20,27,85), (None,))
        write_rows(out / "pvt.csv", list(workers.map(differential, cases)))
        samples = [("tt",1.1,27,i) for i in range(101,121)]
        write_rows(out / "mismatch.csv", list(workers.map(differential, samples)))
        def common_mode(args):
            point, node = args
            return cm_loop(out, raw, node, point, source)
        loops = workers.map(common_mode, product(pts, ("a","s","output_probe")))
        write_rows(out / "cm_loops.csv", [row for result in loops for row in result])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dut", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    run(args.output, args.dut)
