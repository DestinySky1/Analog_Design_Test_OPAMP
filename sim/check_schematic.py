"""Verify the RNL drawing against the simulation netlist and the Viewer export."""

import json
import subprocess
import tempfile
from pathlib import Path
from xml.etree import ElementTree


def geometry(path):
    # The browser and CLI assign different IDs to the same interactive objects.
    return ElementTree.canonicalize(from_file=path, exclude_attrs={"data-id"}, strip_text=True)


design = Path(__file__).resolve().parents[1] / "round3"
source = design / "ota.rnl.sp"
netlist = (design / "ota.cir").read_text().splitlines()
original = [line for line in netlist if line and not line.startswith("*")]
annotated = [line for line in source.read_text().splitlines() if line and not line.startswith("*")]
assert original == annotated, "The subcircuit or its electrical statements changed"

document = json.loads(subprocess.check_output(["rnl", "view", source, "--no-svg", "--status"]))
ota = next(level for level in document["levels"] if level["title"] == "ota")
assert not document["diagnostics"] and not ota["unplaced"]
assert ota["ports"] == original[0].split()[2:], "Port order differs from the simulation netlist"
instances = {line.split()[0] for line in original if not line.startswith(".")}
boxes = (document["objects"][hit["objects"][0]] for hit in ota["hits"] if hit["kind"] == "box")
drawn = {obj["name"] for obj in boxes if obj["kind"] == "instance"}
assert drawn == instances, f"Rendered instance mismatch: {drawn ^ instances}"

with tempfile.TemporaryDirectory() as out:
    subprocess.run(["rnl", "render", source, "-o", out], check=True)
    assert geometry(Path(out) / "ota.rnl.ota.svg") == geometry(design / "ota.rnl.svg"), (
        "The published SVG differs from the drawing rendered from the RNL"
    )

print(f"Verified {len(instances)} devices, {len(ota['ports'])} ports, electrical statements and SVG.")
