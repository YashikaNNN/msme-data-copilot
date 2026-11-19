from pathlib import Path

from fastapi.testclient import TestClient


def test_upload_profile_pipeline_and_analytics(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    storage = tmp_path / "storage"
    storage.mkdir()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("STORAGE_DIR", str(storage))

    import app.database as database
    from app.database import init_db
    from app.main import app

    database.engine = None
    database.SessionLocal = None
    init_db()

    client = TestClient(app)
    sample = Path(__file__).resolve().parents[1] / "sample_data" / "sales.csv"
    with sample.open("rb") as handle:
        response = client.post(
            "/api/v1/datasets/upload",
            files={"file": ("sales.csv", handle, "text/csv")},
            data={"name": "Test sales", "category": "sales", "description": "unit test"},
        )
    assert response.status_code == 200, response.text
    dataset = response.json()
    assert dataset["row_count"] > 0
    assert dataset["quality_score"] is not None

    quality = client.get(f"/api/v1/datasets/{dataset['id']}/quality").json()
    assert quality["score"] is not None
    assert len(quality["issues"]) > 0

    pipeline = client.post(f"/api/v1/datasets/{dataset['id']}/pipeline/run")
    assert pipeline.status_code == 200, pipeline.text
    body = pipeline.json()
    assert body["status"] in {"success", "partial"}
    assert len(body["stages"]) == 6

    sales = client.get("/api/v1/analytics/sales").json()
    assert sales["available"] is True
    assert sales["orders"] > 0

    ask = client.post("/api/v1/copilot/ask", json={"question": "Which month had the highest sales?"})
    assert ask.status_code == 200, ask.text
    payload = ask.json()
    assert "answer" in payload
    assert payload["llm_note"]


def test_health(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'health.db'}")
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "storage"))
    import app.database as database
    from app.database import init_db
    from app.main import app

    database.engine = None
    database.SessionLocal = None
    init_db()
    client = TestClient(app)
    assert client.get("/api/v1/health").json()["status"] == "ok"
