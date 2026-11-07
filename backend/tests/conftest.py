"""pytest 配置：使用独立的测试数据库，避免污染本地开发数据。"""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

TEST_DB = BACKEND_DIR / "test_meditour.db"
if TEST_DB.exists():
    TEST_DB.unlink()

os.environ.setdefault("MEDITOUR_SECRET_KEY", "test-secret-key-for-pytest")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{TEST_DB.as_posix()}")

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def auth_headers(client) -> dict[str, str]:
    """注册独立测试账号并返回 Bearer 头，避免依赖种子用户。"""
    email = "pytest-user@meditour.com"
    password = "Pytest123456"
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Pytest User",
            "preferred_language": "en",
        },
    )
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
