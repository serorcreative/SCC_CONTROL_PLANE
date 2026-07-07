"""Tests de supervision : runtime, jobs, sessions, événements, agents, moteurs."""

from __future__ import annotations


def test_supervise_runtime(cp):
    data = cp.supervise_runtime()
    assert data["self_check"]["ok"] is True
    assert "echo" in data["kinds"]
    assert data["supervisor"]["plans"] >= 2  # branchement BrainAI sollicité


def test_supervise_jobs(cp):
    data = cp.supervise_jobs()
    assert data["count"] == 2
    assert data["by_status"].get("succeeded") == 2
    assert data["t3_guardrail_observed"] is True


def test_supervise_sessions(cp):
    data = cp.supervise_sessions()
    assert data["count"] == 1
    assert data["sessions"][0]["actor"] == "control-plane"


def test_supervise_events(cp):
    data = cp.supervise_events()
    assert data["count"] > 0
    assert data["governance"]["approvals"] >= 1  # validation humaine T3
    assert "job.succeeded" in data["by_type"]


def test_supervise_agents(cp):
    data = cp.supervise_agents()
    assert data["total"] == 20
    assert sum(data["by_autonomy"].values()) == 20
    assert "SCC-AGENT-0020" in data["out_orphans"]


def test_supervise_engines(cp):
    data = cp.supervise_engines()
    assert data["state"] == "ok"
    know = data["engines"]["engine_knowledge"]
    assert know["present"] is True
    assert "CONTRACT:knowledge.json" in know["produces"]
