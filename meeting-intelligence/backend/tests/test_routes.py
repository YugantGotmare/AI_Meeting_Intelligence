import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock, MagicMock
from app.main import app
from app.db.database import init_db, engine, Base


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_upload_valid_file(client):
    with patch("app.routes.meetings.run_agent", new_callable=AsyncMock):
        response = await client.post(
            "/meetings/upload",
            files={"file": ("test.mp3", b"fake audio content", "audio/mpeg")}
        )

    assert response.status_code == 200
    data = response.json()
    assert "meeting_id" in data
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_upload_invalid_file_type(client):
    response = await client.post(
        "/meetings/upload",
        files={"file": ("test.txt", b"not audio", "text/plain")}
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_meeting_not_found(client):
    response = await client.get("/meetings/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_meeting_after_upload(client):
    with patch("app.routes.meetings.run_agent", new_callable=AsyncMock):
        upload = await client.post(
            "/meetings/upload",
            files={"file": ("test.mp3", b"fake audio", "audio/mpeg")}
        )

    meeting_id = upload.json()["meeting_id"]
    response = await client.get(f"/meetings/{meeting_id}")

    assert response.status_code == 200
    assert response.json()["id"] == meeting_id


@pytest.mark.asyncio
async def test_list_meetings_empty(client):
    response = await client.get("/meetings/")
    assert response.status_code == 200
    assert response.json() == []