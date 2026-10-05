"""An in-memory stand-in for Semantic Scholar, shaped like its API responses."""
from __future__ import annotations


def paper(pid, title, date, cites=100, inf=10, arxiv=""):
    return {"paperId": pid, "title": title, "publicationDate": date, "year": int(date[:4]),
            "citationCount": cites, "influentialCitationCount": inf, "venue": "",
            "authors": [{"name": "A. Author"}, {"name": "B. Author"}],
            "externalIds": {"ArXiv": arxiv} if arxiv else {}, "abstract": f"Abstract of {title}."}


class FakeSource:
    """A small citation world: root -> mid -> center -> follow-ups."""

    def __init__(self):
        P = {}
        P["root"] = paper("root", "Classic Volume Rendering", "1995-06-01", 3000, 400)
        P["mid"] = paper("mid", "NeRF: Neural Radiance Fields", "2020-03-19", 9000, 1500, "2003.08934")
        P["side"] = paper("side", "A Dataset Paper", "2021-01-01", 50, 1)
        P["center"] = paper("center", "3D Gaussian Splatting for Real-Time Rendering", "2023-08-08", 5000, 900, "2308.04079")
        P["f1"] = paper("f1", "Mip-Splatting: Alias-free 3DGS", "2023-11-27", 600, 90)
        P["f2"] = paper("f2", "2D Gaussian Splatting", "2024-03-26", 500, 80)
        P["f3"] = paper("f3", "Gaussian Opacity Fields", "2024-04-16", 300, 40)
        P["late"] = paper("late", "A Very Recent Splatting Paper", "2026-08-01", 3, 0)
        self.P = P
        self.refs = {"center": ["mid", "root", "side"], "mid": ["root"], "f1": ["center"],
                     "f2": ["center"], "f3": ["center", "f1"], "late": ["f2", "center"], "root": [], "side": []}
        self.calls = 0

    def _link(self, pid, influential):
        return {"paper": self.P[pid], "isInfluential": influential, "intents": ["methodology"] if influential else [],
                "contexts": [f"We build on {self.P[pid]['title']}."] if influential else []}

    def paper(self, pid):
        self.calls += 1
        key = {"arXiv:2308.04079": "center"}.get(pid, pid)
        if key not in self.P:
            from paper_constellation.s2 import S2Error
            raise S2Error("not found")
        return self.P[key]

    def match_title(self, q):
        return self.P["center"]

    def references(self, pid, limit=1000):
        self.calls += 1
        return [self._link(r, r != "side") for r in self.refs.get(pid, [])]

    def citations(self, pid, limit=2000):
        self.calls += 1
        out = [self._link(c, True) for c, rs in self.refs.items() if pid in rs]
        if pid == "center":  # plenty of dated citations for the trend
            for i in range(30):
                out.append({"paper": {"paperId": None, "publicationDate": f"2026-0{1 + i % 8}-15"},
                            "isInfluential": False, "intents": [], "contexts": []})
        return out

    def reference_ids(self, pids):
        return {p: set(self.refs.get(p, [])) for p in pids}
