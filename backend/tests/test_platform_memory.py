import asyncio
import os
import subprocess
from typing import Any

import pytest
import json
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.main import app


def _try_get_db_connection_url() -> str:
    return os.getenv("DATABASE_URL", settings.database_url)


async def _postgres_available() -> bool:
    url = _try_get_db_connection_url()
    try:
        engine = create_async_engine(url, pool_pre_ping=True)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture
def llm_stub(monkeypatch):
    # Deterministic LLM output so tests don't call external providers.
    extraction_data = {
        "name": "John Doe",
        "role": "Software Engineer",
        "skills": ["Python", "FastAPI"],
        "experience_years": 3,
        "education": "B.Sc Computer Science",
        "summary": "Example summary."
    }

    verification_data = {
        "is_valid": True,
        "confidence": 0.87,
        "issues": []
    }

    def stub_generate_text(prompt: str) -> str:
        p = prompt.lower()
        if "strict verification system" in p or '"is_valid"' in p:
            return json.dumps(verification_data)
        return json.dumps(extraction_data)

    monkeypatch.setattr("app.extraction.engine.generate_text", stub_generate_text)
    return stub_generate_text


async def _ensure_schema_migrated():
    # Use alembic to create tables. This is only done when Postgres is available.
    subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        cwd=os.path.dirname(__file__) + "/..",
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


@pytest.mark.asyncio
async def test_invalid_input_empty_text_returns_400(client, llm_stub):
    if not await _postgres_available():
        pytest.skip("Postgres not reachable (set DATABASE_URL to run integration tests).")

    await _ensure_schema_migrated()

    token_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "test-empty@example.com"},
    )
    assert token_resp.status_code in (200, 201)
    token = token_resp.json()["access_token"]

    resp = client.post(
        "/api/v1/extract",
        json={"text": "   "},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_extract_creates_conversation_and_memory(client, llm_stub):
    if not await _postgres_available():
        pytest.skip("Postgres not reachable (set DATABASE_URL to run integration tests).")

    await _ensure_schema_migrated()

    # Clean up tables for repeatability.
    engine = create_async_engine(_try_get_db_connection_url(), pool_pre_ping=True)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                TRUNCATE TABLE
                  semantic_relationships,
                  semantic_memory,
                  extractions,
                  messages,
                  conversations,
                  users
                RESTART IDENTITY CASCADE;
                """
            )
        )
    await engine.dispose()

    token_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "test-memory@example.com"},
    )
    assert token_resp.status_code in (200, 201)
    token = token_resp.json()["access_token"]

    payload: dict[str, Any] = {
        "text": "John Doe is a software engineer with 3 years experience using Python and FastAPI.",
        "schema": {
            "name": "string",
            "role": "string",
            "skills": "list[string]",
            "experience_years": "int",
            "education": "string",
            "summary": "string",
        },
    }

    resp = client.post(
        "/api/v1/extract",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["conversation_id"] is not None
    assert body["extraction_id"] is not None
    assert body["result"]["confidence"] is not None

    # Validate memory + relationship edges returned by /memory.
    mem_resp = client.get(
        "/api/v1/memory",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert mem_resp.status_code == 200
    mem = mem_resp.json()
    assert len(mem["semantic"]) > 0
    # For the stubbed skills, relationship edges should exist.
    assert len(mem["relationships"]) > 0


def test_loader_ocr_fallback_path(monkeypatch):
    # Unit test loader fallback: if extracted text is too small, OCR fallback is used.
    from app.ingestion import loader as loader_mod

    monkeypatch.setattr(loader_mod, "load_pdf", lambda _: "x" * 10)  # too small
    monkeypatch.setattr(loader_mod, "ocr_pdf", lambda _: "OCR RESULT " + ("y" * 100))

    text = loader_mod.load_document("dummy_path.pdf")
    assert "OCR RESULT" in text

