from conftest import FIXTURES

from app.core import chunking as ck


def test_chunk_text_boundaries():
    text = ("Sentence one is here. " * 300).strip()
    chunks = ck.chunk_text(text, size=500, overlap=80)
    assert len(chunks) > 3
    assert all(len(c) <= 620 for c in chunks)
    assert all(c.strip() for c in chunks)


def test_split_code_java_units():
    src = (FIXTURES / "Mini.java").read_text()
    units = ck.split_code(src, "java")
    assert units, "no units extracted from Mini.java"
    blob = "\n".join(u["text"] for u in units)
    assert "doLogin" in blob and "getErrorToast" in blob
    named = [u for u in units if u.get("name")]
    assert named, "expected at least one named unit"
    for u in units:
        assert 1 <= u["line_start"] <= u["line_end"]


def test_split_code_ts_units():
    src = (FIXTURES / "mini.spec.ts").read_text()
    units = ck.split_code(src, "ts")
    blob = "\n".join(u["text"] for u in units)
    assert "waitForCouponBanner" in blob
    assert any(u.get("name") for u in units)


def test_split_code_fallback_on_prose():
    units = ck.split_code("no braces here, just words " * 100, "java")
    assert units
    assert all(u["name"] is None for u in units)


def test_split_log_failures():
    parsed = ck.split_log_failures((FIXTURES / "mini.log").read_text())
    assert parsed["failures"], "no failure blocks found"
    f = parsed["failures"][0]
    assert f["exception"] and "Exception" in f["exception"]
    assert f["test_name"] and "LoginTest" in f["test_name"]
    assert parsed["summary"]


def test_split_headings_trail():
    sections = ck.split_headings((FIXTURES / "mini.md").read_text())
    trails = [t for t, _ in sections]
    assert any("Handbook > Bug triage" == t for t in trails)
    assert any("Handbook > Flaky policy" == t for t in trails)


def test_split_transcript_keeps_turns():
    text = (FIXTURES.parent.parent / "data" / "07_meeting_notes" /
            "sample_sprint42_planning.md").read_text()
    chunks = ck.split_transcript(text, size=600, overlap=100)
    assert len(chunks) >= 2
    assert any("Pramod:" in c for c in chunks)
