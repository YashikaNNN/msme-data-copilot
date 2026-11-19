from pathlib import Path

from fastapi.testclient import TestClient


def _auth_headers(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "business_name": "Test Retail",
            "owner_name": "Test Owner",
            "email": "owner@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 200, response.text
    token = response.json()["token"]
    return {"Authorization": f"Bearer {token}"}


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
    headers = _auth_headers(client)
    sample = Path(__file__).resolve().parents[1] / "sample_data" / "sales.csv"
    with sample.open("rb") as handle:
        response = client.post(
            "/api/v1/datasets/upload",
            headers=headers,
            files={"file": ("sales.csv", handle, "text/csv")},
            data={"name": "Test sales", "category": "sales", "description": "unit test"},
        )
    assert response.status_code == 200, response.text
    dataset = response.json()
    assert dataset["row_count"] > 0
    assert dataset["quality_score"] is not None

    quality = client.get(f"/api/v1/datasets/{dataset['id']}/quality", headers=headers).json()
    assert quality["score"] is not None
    assert len(quality["issues"]) > 0
    assert quality["plain_summary"]

    pipeline = client.post(f"/api/v1/datasets/{dataset['id']}/pipeline/run", headers=headers)
    assert pipeline.status_code == 200, pipeline.text
    body = pipeline.json()
    assert body["status"] in {"success", "partial"}
    assert len(body["stages"]) == 6
    assert body["stages"][0]["label"]

    sales = client.get("/api/v1/analytics/sales", headers=headers).json()
    assert sales["available"] is True
    assert sales["orders"] > 0

    ask = client.post(
        "/api/v1/copilot/ask",
        headers=headers,
        json={"question": "Which month had the highest sales?"},
    )
    assert ask.status_code == 200, ask.text
    payload = ask.json()
    assert "answer" in payload
    assert payload["llm_note"]

    me = client.get("/api/v1/auth/me", headers=headers).json()
    assert me["business"]["business_name"] == "Test Retail"


def test_business_isolation(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'iso.db'}")
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "storage"))
    import app.database as database
    from app.database import init_db
    from app.main import app

    database.engine = None
    database.SessionLocal = None
    init_db()
    client = TestClient(app)

    first = client.post(
        "/api/v1/auth/register",
        json={
            "business_name": "Shop A",
            "owner_name": "A",
            "email": "a@example.com",
            "password": "password123",
        },
    ).json()
    second = client.post(
        "/api/v1/auth/register",
        json={
            "business_name": "Shop B",
            "owner_name": "B",
            "email": "b@example.com",
            "password": "password123",
        },
    ).json()
    headers_a = {"Authorization": f"Bearer {first['token']}"}
    headers_b = {"Authorization": f"Bearer {second['token']}"}

    sample = Path(__file__).resolve().parents[1] / "sample_data" / "sales.csv"
    with sample.open("rb") as handle:
        uploaded = client.post(
            "/api/v1/datasets/upload",
            headers=headers_a,
            files={"file": ("sales.csv", handle, "text/csv")},
            data={"name": "A sales", "category": "sales", "description": ""},
        )
    assert uploaded.status_code == 200
    dataset_id = uploaded.json()["id"]

    denied = client.get(f"/api/v1/datasets/{dataset_id}", headers=headers_b)
    assert denied.status_code == 404

    listed = client.get("/api/v1/datasets", headers=headers_b).json()
    assert listed["items"] == []


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
