"""员工图片上传：类型/大小限制、随机文件名与静态访问。"""

import re
import secrets

from app.config import settings
from app.database import SessionLocal
from app.staff import grant_staff

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 64


def _make_staff(client) -> dict[str, str]:
    email = f"upload-{secrets.token_hex(4)}@meditour.com"
    password = "Staff123456"
    created = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Upload Staff"},
    )
    assert created.status_code == 201, created.text
    with SessionLocal() as db:
        grant_staff(db, email)
        db.commit()
    login = client.post(
        "/api/v1/auth/login", data={"username": email, "password": password}
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _upload(client, headers, content: bytes, filename: str, content_type: str):
    return client.post(
        "/api/v1/staff/uploads",
        files={"file": (filename, content, content_type)},
        headers=headers,
    )


def test_staff_uploads_image_with_generated_name(
    client, upload_dir, auth_headers
) -> None:
    staff_headers = _make_staff(client)

    response = _upload(
        client,
        staff_headers,
        PNG_BYTES,
        "../../etc/passwd.png",
        "image/png",
    )
    assert response.status_code == 201, response.text
    body = response.json()

    assert body["size"] == len(PNG_BYTES)
    assert body["content_type"] == "image/png"
    # 日期分目录 + 32 位十六进制随机名 + 服务端决定的扩展名。
    assert re.fullmatch(
        r"/media/uploads/\d{4}/\d{2}/\d{2}/[0-9a-f]{32}\.png", body["path"]
    ), body["path"]
    assert body["url"] == body["path"]
    assert "passwd" not in body["path"]
    assert body["filename"].endswith(".png")

    stored = upload_dir / body["path"].removeprefix("/media/uploads/")
    assert stored.read_bytes() == PNG_BYTES

    # 返回的 URL 可以通过后端静态服务直接访问。
    served = client.get(body["url"])
    assert served.status_code == 200
    assert served.content == PNG_BYTES


def test_upload_requires_staff(client, auth_headers) -> None:
    denied = _upload(client, auth_headers, PNG_BYTES, "a.png", "image/png")
    assert denied.status_code == 403

    anonymous = client.post(
        "/api/v1/staff/uploads",
        files={"file": ("a.png", PNG_BYTES, "image/png")},
    )
    assert anonymous.status_code == 401


def test_upload_rejects_wrong_type_and_spoofed_content(client) -> None:
    staff_headers = _make_staff(client)

    text = _upload(client, staff_headers, b"hello", "a.txt", "text/plain")
    assert text.status_code == 415

    # 声明 png 但内容是 jpeg：文件头校验不通过。
    spoofed = _upload(client, staff_headers, JPEG_BYTES, "a.png", "image/png")
    assert spoofed.status_code == 415
    assert "does not match" in spoofed.json()["detail"]

    # 声明 octet-stream（浏览器未识别类型）同样拒绝。
    octet = _upload(
        client, staff_headers, PNG_BYTES, "a.bin", "application/octet-stream"
    )
    assert octet.status_code == 415


def test_upload_rejects_oversized_and_empty_files(client) -> None:
    staff_headers = _make_staff(client)

    oversized = b"\x89PNG\r\n\x1a\n" + b"0" * settings.UPLOAD_MAX_BYTES
    too_big = _upload(
        client, staff_headers, oversized, "big.png", "image/png"
    )
    assert too_big.status_code == 413

    empty = _upload(client, staff_headers, b"", "empty.png", "image/png")
    assert empty.status_code == 422
