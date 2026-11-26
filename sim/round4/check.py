"""Compare fresh measurements to the published design and enforce the design limits."""
import csv
import json
import sys
from pathlib import Path

import numpy as np
from measure import ROOT
from review import check_limits

data = Path(sys.argv[1])
published = ROOT / "round4"
for name in ("ota.cir", "stage1.cir", "stage2.cir"):
    assert (data / "stages" / name).read_bytes() == (published / name).read_bytes(), name
with np.load(data / "scan/devices.npz") as replay, np.load(published / "devices.npz") as reference:
    for key in reference.files:
        if key == "fields":
            np.testing.assert_array_equal(replay[key], reference[key])
        else:
            np.testing.assert_allclose(replay[key], reference[key], rtol=1e-4, atol=1e-18)
for stage in ("stage1", "stage2"):
    ref = json.loads((published / "stages.json").read_text())[stage + "_test"]
    act = json.loads((data / "stages/stages.json").read_text())[stage + "_test"]
    for k in ref:
        np.testing.assert_allclose(act[k], ref[k], rtol=.001)
metrics = json.loads((data / "review/metrics.json").read_text())
check_limits(metrics)
original = json.loads((published / "metrics.json").read_text())
for k in ("gain_db","loop_db","ugb_MHz","pm_deg","noise_uV","power_uW","cmrr_db","psrr_db","swing_V"):
    np.testing.assert_allclose(metrics[k], original[k], rtol=.002, err_msg=k)
for name, count in (("pvt",40), ("mismatch",20), ("pvt_dc",40), ("monte_carlo",20), ("cm_loops",120)):
    with (data / "review" / (name+".csv")).open() as actual, (published / (name+".csv")).open() as expected:
        rows, baseline = list(csv.DictReader(actual)), list(csv.DictReader(expected))
        assert len(rows) == count
        for r, b in zip(rows, baseline, strict=True):
            for k, value in b.items():
                try:
                    numeric = float(value)
                except ValueError:
                    assert r[k] == value
                else:
                    np.testing.assert_allclose(float(r[k]), numeric, rtol=.001, atol=1e-8, err_msg=k)
            if name in ("pvt", "mismatch"):
                check_limits(r, full=False)
            if name == "pvt_dc":
                assert min(float(v) for k, v in r.items() if k.endswith("_margin_V")) > 0
            if name == "cm_loops" and r["probe"] != "output_probe":
                assert r["crossing"] == "down" and float(r["pm_deg"]) >= 60
print("Device tables, both stage benches, complete OTA, 40 PVT, 20 mismatch and 120 CM probes verified.")
