from conftest import FIXTURES

from app.ingestion import loaders


def test_load_testcases_rows():
    docs = loaders.load_testcases(FIXTURES, "test_cases")
    assert len(docs) == 3
    ids = {d.payload.get("tc_id") for d in docs}
    assert {"TC-1001", "TC-1002", "TC-2044"} <= ids
    d = next(d for d in docs if d.payload["tc_id"] == "TC-1002")
    assert "error toast" in d.text.lower()
    assert d.payload["source_type"] == "test_cases"


def test_load_jira_tickets():
    docs = loaders.load_jira(FIXTURES, "jira_tickets")
    assert len(docs) >= 1
    d = docs[0]
    assert d.payload["ticket_key"] == "VWO-9001"
    assert d.payload["ticket_status"] == "Open"
    assert "JIRA VWO-9001" in d.text


def test_load_jenkins_failures_and_summary():
    docs = loaders.load_jenkins(FIXTURES, "jenkins_logs")
    kinds = [d.payload.get("unit") for d in docs]
    assert "summary" in kinds
    fails = [d for d in docs if d.payload.get("unit") != "summary"]
    assert fails
    assert any(d.payload.get("build_id") == "99" for d in docs)
    assert any("TimeoutException" in (d.payload.get("exception") or "") for d in fails)


def test_load_code_java_and_ts():
    docs = loaders.load_code(FIXTURES, "selenium_framework", "test-repo")
    java = [d for d in docs if d.payload.get("language") == "java"]
    assert java
    assert all(d.payload.get("repo") == "test-repo" for d in java)
    assert any("doLogin" in d.text for d in java)
    assert all(d.payload.get("line_start") for d in java)
    ts = [d for d in docs if d.payload.get("language") == "ts"]
    assert ts


def test_uids_stable():
    a = loaders.load_testcases(FIXTURES, "test_cases")
    b = loaders.load_testcases(FIXTURES, "test_cases")
    assert [d.uid for d in a] == [d.uid for d in b]
