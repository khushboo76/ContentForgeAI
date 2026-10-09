"""
Basic route tests. Generation-dependent tests are skipped without a real
GEMINI_API_KEY — they check wiring/validation, not live model output.
"""
import json
import os
import pytest
from fastapi.testclient import TestClient
from main import app

# Using TestClient as a context manager triggers the app's lifespan
# (init_db) — without it, the sqlite tables never get created.
client = TestClient(app)
with TestClient(app) as _startup_client:
    pass


def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_list_output_types():
    res = client.get("/api/output-types")
    assert res.status_code == 200
    types = res.json()["output_types"]
    assert "linkedin_post" in types
    assert "advisory" in types
    assert len(types) == 7


def test_generate_rejects_empty_output_types():
    res = client.post("/api/generate", json={"source_content": "hello", "output_types": []})
    assert res.status_code == 400


def test_generate_rejects_unknown_output_type():
    res = client.post("/api/generate", json={
        "source_content": "hello",
        "output_types": ["not_a_real_type"],
    })
    assert res.status_code == 400


def test_generate_rejects_empty_source():
    res = client.post("/api/generate", json={
        "source_content": "   ",
        "output_types": ["linkedin_post"],
    })
    assert res.status_code == 400


def test_ingest_url_rejects_invalid_url():
    res = client.post("/api/ingest-url", json={"url": "not-a-url"})
    assert res.status_code == 400


def test_generate_from_media_rejects_empty_output_types():
    res = client.post(
        "/api/generate-from-media",
        files={"file": ("test.png", b"fake-image-bytes", "image/png")},
        data={"output_types": "[]", "params": "{}"},
    )
    assert res.status_code == 400


def test_generate_from_media_rejects_unsupported_file_type():
    res = client.post(
        "/api/generate-from-media",
        files={"file": ("test.exe", b"fake-bytes", "application/octet-stream")},
        data={"output_types": json.dumps(["linkedin_post"]), "params": "{}"},
    )
    assert res.status_code == 415


@pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="requires a real API key")
def test_generate_live():
    res = client.post("/api/generate", json={
        "source_content": "A new city ordinance requires all e-scooters to be parked in designated zones starting next month.",
        "output_types": ["linkedin_post"],
    })
    assert res.status_code == 200
    body = res.json()
    assert body["results"]["linkedin_post"]["status"] == "done"
