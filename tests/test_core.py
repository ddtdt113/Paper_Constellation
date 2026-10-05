import datetime as dt
import json

import pytest

from paper_constellation import annotate, ids, layout, lineage
from paper_constellation.model import Edge, Graph, Node, short_label, transitive_reduce

from fake_source import FakeSource

TODAY = dt.date(2026, 10, 5)


@pytest.mark.parametrize("text,expected", [
    ("https://arxiv.org/abs/2308.04079", "arXiv:2308.04079"),
    ("https://arxiv.org/pdf/2308.04079v2", "arXiv:2308.04079"),
    ("arxiv.org/abs/2308.04079v1", "arXiv:2308.04079"),
    ("2308.04079", "arXiv:2308.04079"),
    ("arXiv:2003.08934", "arXiv:2003.08934"),
    ("https://www.alphaxiv.org/abs/2505.19175", "arXiv:2505.19175"),
    ("https://arxiv.org/abs/hep-th/9901001", "arXiv:hep-th/9901001"),
    ("https://doi.org/10.1145/3592433", "DOI:10.1145/3592433"),
    ("10.1145/3592433", "DOI:10.1145/3592433"),
    ("https://dl.acm.org/doi/10.1145/3592433", "DOI:10.1145/3592433"),
    ("https://www.semanticscholar.org/paper/3D-Gaussian/2cc1d857e86d5152ba7fe6a8355c2a0150cc280a",
     "2cc1d857e86d5152ba7fe6a8355c2a0150cc280a"),
    ("https://openreview.net/forum?id=abc123", "URL:https://openreview.net/forum?id=abc123"),
    ("https://aclanthology.org/2020.acl-main.1.pdf", "ACL:2020.acl-main.1"),
])
def test_parse_ids(text, expected):
    assert ids.parse(text).s2_id == expected


def test_parse_title_and_empty():
    assert ids.parse("Attention is all you need").query == "Attention is all you need"
    with pytest.raises(ValueError):
        ids.parse("   ")


def test_short_label():
    assert short_label("Mip-Splatting: Alias-free 3D Gaussian Splatting") == "Mip-Splatting"
    assert short_label("A very long title without any colon that keeps going") .endswith("…")


def test_transitive_reduce_keeps_center_links():
    es = [Edge("a", "b"), Edge("b", "c"), Edge("a", "c"), Edge("a", "x"), Edge("x", "c")]
    out = {(e.src, e.dst) for e in transitive_reduce(es, keep={"x"})}
    assert ("a", "c") not in out and ("a", "x") in out and ("x", "c") in out


def test_build_lineage():
    src = FakeSource()
    msgs = []
    g, ctx = lineage.build("https://arxiv.org/abs/2308.04079", src, progress=msgs.append, today=TODAY)
    by = g.by_id()
    assert g.center == "center" and by["center"].kind == "center"
    assert {"mid", "root"} <= set(by)                    # predecessors found
    assert {"f1", "f2", "f3"} <= set(by)                 # successors found
    assert by["mid"].kind == "ancestor" and by["f2"].kind == "descendant"
    pairs = {(e.src, e.dst) for e in g.edges}
    assert ("mid", "center") in pairs and ("center", "f1") in pairs
    assert ("f1", "f3") in pairs                         # link between two successors
    assert all(by[e.src].year <= by[e.dst].year + 0.25 for e in g.edges)
    assert g.trend and g.trend.bins and g.trend.verdict
    assert by["late"].status == "recent"
    assert msgs and ("mid", "center") in ctx


def test_roundtrip(tmp_path):
    src = FakeSource()
    g, _ = lineage.build("2308.04079", src, today=TODAY)
    p = tmp_path / "g.json"
    g.save(p)
    g2 = Graph.load(p)
    assert [n.id for n in g2.nodes] == [n.id for n in g.nodes]
    assert len(g2.edges) == len(g.edges) and g2.trend.bins == g.trend.bins


def test_annotate_applies_llm_answer():
    src = FakeSource()
    g, ctx = lineage.build("2308.04079", src, today=TODAY)
    answer = {
        "lanes": [{"key": "base", "name": "기반"}, {"key": "gs", "name": "스플래팅"}],
        "papers": [{"id": i, "lane": "base" if i in ("root", "mid") else "gs", "label": i.upper(),
                    "status": "active", "note": "핵심"} for i in ("root", "mid", "center", "f1", "f2", "f3")],
        "links": [{"src": "mid", "dst": "center", "solves": "느린 렌더링을 래스터화로"},
                  {"src": "center", "dst": "f1", "solves": "앨리어싱 제거"},
                  {"src": "root", "dst": "mid", "solves": "볼륨 적분을 학습에"}],
        "summary": "요약",
    }
    fake = lambda system, user, key, model: "```json\n" + json.dumps(answer, ensure_ascii=False) + "\n```"
    g = annotate.annotate(g, ctx, api_key="k", caller=fake)
    by = g.by_id()
    assert "late" not in by and "side" not in by
    assert [l.key for l in g.lanes] == ["base", "gs"]
    assert by["mid"].label == "MID" and by["mid"].lane == "base"
    sol = {(e.src, e.dst): e.solves for e in g.edges}
    assert sol[("mid", "center")] == "느린 렌더링을 래스터화로"
    assert g.summary == "요약"


def test_layout_no_overlap_and_time_order():
    from paper_constellation.examples import load as load_example
    g = load_example()
    lay = layout.compute(g)
    assert set(lay.pos) == {n.id for n in g.nodes}
    by = g.by_id()
    ordered = sorted(g.nodes, key=lambda n: n.year)
    xs = [lay.pos[n.id][0] for n in ordered]
    assert xs == sorted(xs)
    # stars in the same lane never share a position
    pts = list(lay.pos.values())
    assert len(set(pts)) == len(pts)
    assert lay.ticks and lay.lanes
    assert by["3dgs"].kind == "core"


def test_example_graph_is_annotated():
    from paper_constellation.examples import load as load_example
    g = load_example()
    assert len(g.nodes) == 53 and len(g.edges) == 69
    assert all(e.solves for e in g.edges)


def test_every_string_has_both_languages():
    from paper_constellation import i18n
    missing = [k for k, v in i18n.STRINGS.items() if not v.get("ko") or not v.get("en")]
    assert not missing


def test_errors_follow_language():
    from paper_constellation import i18n
    from paper_constellation.s2 import S2Error
    e = S2Error("s2.http", code=500, detail="x")
    try:
        i18n.set_language("en")
        assert str(e) == "Semantic Scholar error 500: x"
        i18n.set_language("ko")
        assert str(e) == "Semantic Scholar 오류 500: x"
    finally:
        i18n.set_language("ko")


def test_trend_describe_in_both_languages():
    from paper_constellation import i18n, trend
    g, _ = lineage.build("2308.04079", FakeSource(), today=TODAY)
    try:
        i18n.set_language("en")
        v_en, d_en = trend.describe(g.trend)
        i18n.set_language("ko")
        v_ko, d_ko = trend.describe(g.trend)
    finally:
        i18n.set_language("ko")
    assert v_en == "Accelerating" and v_ko == "가속 중"
    assert "citations in the last year" in d_en and "최근 1년" in d_ko


def test_llm_prompt_language():
    assert "English" in annotate.system_prompt("en") and "Korean" in annotate.system_prompt("ko")
    assert "{LANG}" not in annotate.system_prompt("en")


def test_example_has_english():
    from paper_constellation.examples import load as load_example
    g = load_example()
    assert g.title_en and g.summary_en
    assert all(n.note_en for n in g.nodes) and all(e.solves_en for e in g.edges)
    assert all(l.name_en for l in g.lanes)


def test_https_uses_a_ca_bundle():
    import ssl
    from paper_constellation.net import ssl_context
    ctx = ssl_context()
    assert isinstance(ctx, ssl.SSLContext) and ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.cert_store_stats()["x509_ca"] > 0
