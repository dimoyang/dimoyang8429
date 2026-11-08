"""上传文件存储：本地磁盘实现，以及生产对象存储的抽象位。

当前只有 `local` 实现：文件落在 `MEDITOUR_UPLOAD_DIR`（默认
`backend/var/uploads`），按 UTC 日期分目录，文件名由服务端随机生成。
这只适用于单机部署；多实例时各节点磁盘互不可见，必须换成对象存储
（`s3` 预留位，未实现前显式报错而不是静默降级）。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings

LOCAL_BACKEND = "local"
S3_BACKEND = "s3"


class StorageError(RuntimeError):
    """存储配置错误（例如选择了尚未实现的后端）。"""


class LocalStorage:
    """落本机磁盘：<root>/YYYY/MM/DD/<uuid>.<ext>，返回可访问 URL。"""

    def __init__(self, root: Path, url_path: str, base_url: str = "") -> None:
        self.root = root
        self.url_path = url_path.rstrip("/")
        self.base_url = base_url.rstrip("/")

    def save(self, data: bytes, extension: str) -> tuple[str, str]:
        """写入文件并返回 (url, 站内相对路径)。"""
        now = datetime.now(timezone.utc)
        relative = Path(
            f"{now:%Y}",
            f"{now:%m}",
            f"{now:%d}",
            f"{uuid.uuid4().hex}{extension}",
        )
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

        path = f"{self.url_path}/{relative.as_posix()}"
        url = f"{self.base_url}{path}" if self.base_url else path
        return url, path


class S3Storage:
    """S3 兼容对象存储的抽象位。

    生产多实例部署需要实现这里（boto3 / 兼容 S3 协议的网关）。
    故意不提供半成品实现：配置了 s3 却在本地落盘会造成
    「部分节点能访问、部分节点 404」的隐蔽故障。
    """

    def __init__(self) -> None:
        raise StorageError(
            "S3 storage backend is not implemented yet; "
            "keep MEDITOUR_STORAGE_BACKEND=local for single-node deployments"
        )


_storage: LocalStorage | None = None


def get_storage() -> LocalStorage:
    """按配置返回存储实现。目前 local 是唯一可用实现。"""
    global _storage
    if _storage is not None:
        return _storage
    if settings.STORAGE_BACKEND == LOCAL_BACKEND:
        _storage = LocalStorage(
            root=settings.UPLOAD_DIR,
            url_path=settings.MEDIA_URL_PATH,
            base_url=settings.MEDIA_BASE_URL,
        )
        return _storage
    if settings.STORAGE_BACKEND == S3_BACKEND:
        S3Storage()
    raise StorageError(
        f"Unsupported MEDITOUR_STORAGE_BACKEND: {settings.STORAGE_BACKEND}"
    )
