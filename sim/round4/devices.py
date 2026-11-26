"""Build BSIM3 device tables before sizing either amplifier stage (PYTHONPATH=sim)."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
from measure import model_text, prepare_ota, run_spice, table

LENGTHS = np.array([.18, .30, .42, .50, .60, .75, .90])
DRAINS = np.array([.08, .12, .16, .20, .28, .36, .44, .50, .55, .60, .68, .75])
GATES = np.linspace(.24,.90,67)
BODIES = np.array([0., .12, .18, .24])
FIELDS = ("id", "gm", "gds", "vdsat", "cgg")
WIDTH = 10.0  # drawn micrometres


def bench(case):
    root, profile, length, body = case
    polarity, corner, temp = profile
    sign = 1 if polarity == "n" else -1
    path = root / f"{polarity}_{corner}_{temp}_L{length:.2f}_B{body:.2f}"
    path.mkdir(parents=True, exist_ok=True)
    text = []
    sources = [f".temp {temp}", "Vctrl ctrl 0 dc 0.24 ac 1", f"Vbulk b 0 {-sign*body}"]
    for i, vds in enumerate(DRAINS):
        sources.extend([f"Vd{i} d{i} 0 {sign*vds}",f"Eg{i} g{i} 0 ctrl 0 {sign}"])
        text.append(f"M{i} d{i} g{i} 0 b {polarity}ch W={WIDTH}u L={length}u")
    (path/"model.lib").write_text(model_text(corner, {}))
    (path/"dut.lib").write_text(prepare_ota("\n".join(text), None)[0]+"\n")
    dc_vars = " ".join(f"@m{i}[{k}]" for i in range(len(DRAINS)) for k in FIELDS[:-1])
    cap_vars = " ".join(f"imag(i(eg{i}))" for i in range(len(DRAINS)))
    ctrl = (f"save all {dc_vars}\ndc Vctrl .24 .90 .01\nwrdata dc.txt {dc_vars}\n"
            "unset wr_vecnames\n"+ "foreach gate " + " ".join(f"{v:.2f}" for v in GATES) + "\n"
            f"alter Vctrl=$gate\nac lin 1 1Meg 1Meg\nwrdata caps.txt {cap_vars}\nset appendwrite\ndestroy $curplot\nend")
    # ngspice appends AC rows; a replay must start with a fresh file.
    (path/"caps.txt").unlink(missing_ok=True)
    run_spice(path, "devices", "\n".join(sources), ctrl)
    x, *values = table(path,"dc")
    np.testing.assert_allclose(x,GATES,atol=1e-11)
    data = np.array(values).reshape(len(DRAINS),4,len(GATES)).transpose(0,2,1)
    caps = abs(np.loadtxt(path/"caps.txt")[:,1:].T)/(2*np.pi*1e6)
    result = np.concatenate((abs(data),caps[:,:,None]),axis=2)
    if not np.isfinite(result).all() or np.min(caps)<=0:
        raise ValueError("Invalid device table")
    return result


def scan(root):
    root.mkdir(parents=True,exist_ok=True)
    records = {}
    for pol, corner, temp in (("n","tt",27),("p","tt",27),("n","ss",85), ("n","ff",-25), ("p","ff",-25)):
        bodies = BODIES if pol == "n" and corner != "ff" else BODIES[:1]
        cases = [(root/"decks",(pol,corner,temp),l,b) for l in LENGTHS for b in bodies]
        with ThreadPoolExecutor(4) as workers:
            values = np.array(list(workers.map(bench,cases)))
        records[pol+"_"+corner] = values.reshape(len(LENGTHS),len(bodies),len(DRAINS),len(GATES),len(FIELDS))
    np.savez_compressed(root/"devices.npz",lengths_um=LENGTHS,vsb_V=BODIES,vds_V=DRAINS,
                        vgs_V=GATES,fields=FIELDS,width_um=WIDTH,**records)


class Lookup:
    def __init__(self, path):
        with np.load(path) as archive:
            self.data = {k: archive[k] for k in ("n_tt", "p_tt", "n_ss", "n_ff", "p_ff")}

    def curve(self, pol, length, drain, body=0., corner="tt"):
        grid = self.data[pol+"_"+corner][list(LENGTHS).index(length)]
        def bracket(axis, value):
            if not axis[0]-1e-10 <= value <= axis[-1]+1e-10:
                raise ValueError(f"Bias {value} outside characterized range {axis}")
            hi = min(max(1,np.searchsorted(axis,value)),len(axis)-1)
            return hi,(value-axis[hi-1])/(axis[hi]-axis[hi-1])
        j,w = bracket(DRAINS,drain)
        g = grid[:,j-1]*(1-w)+grid[:,j]*w
        if len(g) == 1:
            assert body == 0
            return g[0]
        i,u = bracket(BODIES,body)
        return g[i-1]*(1-u)+g[i]*u

    def point(self, pol, length, drain, body=0., *, eta=None, gate=None, sat=None, corner="tt"):
        cr = self.curve(pol,length,drain,body,corner)
        if eta is not None:
            # Above 1 uA/mm drawn width the inversion-efficiency branch is monotone near the design point.
            valid = cr[:,0]/WIDTH > 1e-9
            axis, gv = (cr[valid,1]/cr[valid,0])[::-1],GATES[valid][::-1]
            if np.count_nonzero(np.diff(axis >= eta)) != 1:
                raise ValueError(f"gm/ID {eta} has no unique characterized solution")
            crossing = np.flatnonzero(np.diff(axis >= eta))[0]
            gate = np.interp(eta,axis[crossing:crossing+2],gv[crossing:crossing+2])
        if sat is not None:
            if not cr[0,3] < sat < cr[-1,3]: raise ValueError("Uncharacterized VDSAT")
            gate = np.interp(sat,cr[:,3],GATES)
        if gate is None or not GATES[0] <= gate <= GATES[-1]: raise ValueError("Invalid gate voltage")
        current,gm,gd,vsat,cgg = (np.interp(gate,GATES,col) for col in cr.T)
        return dict(vg=gate,j=current/WIDTH,eta=gm/current,ai=gm/gd,ft=gm/(2*np.pi*cgg),
                    gd_per_a=gd/current,cgg_per_um=cgg/WIDTH,sat=vsat)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out",type=Path)
    scan(parser.parse_args().out)
