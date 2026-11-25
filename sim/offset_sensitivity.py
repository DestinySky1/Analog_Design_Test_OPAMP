"""First-order Vth sensitivity at the auto-zero DC operating point."""
import csv
import tempfile
from pathlib import Path

from measure import ROOT, VIC, model_text, prepare_ota, run_spice, table


def write_sensitivities(output):
    source = (ROOT / "round3/ota.cir").read_text()
    dut, devices = prepare_ota(source, 101)
    widths = {}
    for line in source.splitlines():
        if line.startswith("M"):
            words = line.split()
            widths["card_" + words[0].lower()] = [float(x.split("=")[1][:-1]) for x in words[6:8]]
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        (work / "dut.lib").write_text(dut+"\n")
        for name in devices:
            voltages = []
            for delta in (-1e-5,1e-5):
                cards = {k: (kind, delta if k == name else 0) for k, (kind, _) in devices.items()}
                (work / "model.lib").write_text(model_text("tt", cards))
                body = f".temp 27\n.options reltol=1e-6 vntol=1e-10\nX1 ip im op om vdd 0 ota\nVdd vdd 0 1.1\nBp ip 0 v={VIC}-v(op,om)/2\nBm im 0 v={VIC}+v(op,om)/2\n"
                run_spice(work,"sensitivity",body,"op\nwrdata offset.txt v(ip,im)")
                voltages.append(table(work,"offset")[1,0])
            slope=(voltages[1]-voltages[0])/2e-5
            w, length=widths[name]
            sig=3/(w*length)**0.5
            rows.append([name[5:],*voltages,slope,sig,(slope*sig)**2])
    with output.open("w") as f:
        writer=csv.writer(f, lineterminator="\n")
        writer.writerow(["device","null_at_minus10u_V","null_at_plus10u_V","dnull_dVth","sigma_Vth_mV","variance_mV2"])
        writer.writerows(rows)
    print("Linearized assumed sigma (mV)",sum(r[-1] for r in rows)**0.5)


if __name__ == "__main__":
    write_sensitivities(ROOT/"round3/offset_sensitivity.csv")
