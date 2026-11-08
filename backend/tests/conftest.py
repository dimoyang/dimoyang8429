"""pytest 配置：使用独立的测试数据库，避免污染本地开发数据。"""

import os
import shutil
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

TEST_DB = BACKEND_DIR / "test_meditour.db"
if TEST_DB.exists():
    TEST_DB.unlink()

os.environ.setdefault(
    "MEDITOUR_SECRET_KEY", "test-secret-key-for-pytest-32-bytes-minimum"
)
os.environ.setdefault("DATABASE_URL", f"sqlite:///{TEST_DB.as_posix()}")
os.environ.setdefault("MEDITOUR_TESTING", "1")
# 固定关闭演示账号，避免开发者本地 .env 开启开关后影响断言。
os.environ["MEDITOUR_SEED_DEMO_USER"] = "0"

# 邮件固定走 file 后端，写进测试专用 outbox，避免污染本地开发目录。
TEST_OUTBOX = BACKEND_DIR / "test_mail_outbox.log"
if TEST_OUTBOX.exists():
    TEST_OUTBOX.unlink()
os.environ.setdefault("MEDITOUR_MAIL_BACKEND", "file")
os.environ.setdefault("MEDITOUR_MAIL_OUTBOX", str(TEST_OUTBOX))
os.environ.setdefault("MEDITOUR_RESET_TOKEN_EXPIRE_MINUTES", "30")

# 上传目录固定到 var/ 下的测试目录（var/ 已被 gitignore），避免污染开发目录。
TEST_UPLOADS = BACKEND_DIR / "var" / "test_uploads"
shutil.rmtree(TEST_UPLOADS, ignore_errors=True)
os.environ.setdefault("MEDITOUR_UPLOAD_DIR", str(TEST_UPLOADS))
# 测试断言相对路径，不依赖外部域名配置。
os.environ["MEDITOUR_MEDIA_BASE_URL"] = ""
# 缩小两个体积上限，让全局请求体限制与上传限制都能用小载荷验证；
# 全局上限仍大于上传上限，保持“先过中间件、再由上传接口拒绝”的顺序。
os.environ["MEDITOUR_UPLOAD_MAX_BYTES"] = str(512 * 1024)
os.environ["MEDITOUR_MAX_REQUEST_BYTES"] = str(1024 * 1024)

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


@pytest.fixture(scope="session")
def mail_outbox() -> Path:
    """开发环境 file 邮件后端的输出文件。"""
    return TEST_OUTBOX


@pytest.fixture(scope="session")
def upload_dir() -> Path:
    """测试专用的本地上传目录。"""
    return TEST_UPLOADS
