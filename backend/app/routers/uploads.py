"""员工图片上传：multipart 上传到本地磁盘并返回可访问 URL。

限制：
- 仅接受 jpeg / png / webp，且会校验文件头，不信任客户端声明的 MIME；
- 默认上限 5 MiB（`MEDITOUR_UPLOAD_MAX_BYTES`），超过返回 413；
- 文件名由服务端生成（uuid4），完全不使用客户端文件名，避免路径穿越。

当前实现只适用于单机：文件写在本机 `MEDITOUR_UPLOAD_DIR`。多实例部署
必须改用对象存储（`app/storage.py` 的 s3 预留位）或共享存储卷。
"""

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.config import settings
from app.deps import require_staff
from app.models import User
from app.schemas import UploadResponse
from app.storage import get_storage

router = APIRouter(prefix="/staff", tags=["staff"])

CHUNK_SIZE = 64 * 1024

# 声明的 content-type -> 允许的扩展名（同时用于与文件头比对）。
CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def _detect_image_extension(data: bytes) -> str | None:
    """按文件头判断真实图片格式；不认识就返回 None。"""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return None


@router.post(
    "/uploads",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="上传图片（员工）",
    description=(
        "需要 `staff` 角色。`multipart/form-data` 的 `file` 字段，"
        "仅支持 JPEG/PNG/WebP，默认上限 5 MiB。返回的 `url` 可直接用于"
        "套餐/目的地图片字段；`path` 是站内相对路径。"
        "当前实现写本机磁盘，仅单机可用，多实例需对象存储。"
    ),
    responses={
        401: {"description": "未登录或令牌无效"},
        403: {"description": "已登录但不是 staff"},
        413: {"description": "文件超过大小上限"},
        415: {"description": "文件类型不在白名单，或文件头与声明类型不符"},
        422: {"description": "缺少 file 字段或文件为空"},
    },
)
async def upload_image(
    file: UploadFile = File(..., description="JPEG / PNG / WebP 图片"),
    _staff: User = Depends(require_staff),
) -> UploadResponse:
    declared = (file.content_type or "").lower()
    if declared not in CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only image/jpeg, image/png and image/webp are supported",
        )

    buffer = bytearray()
    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        buffer.extend(chunk)
        if len(buffer) > settings.UPLOAD_MAX_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=(
                    "File exceeds the size limit of "
                    f"{settings.UPLOAD_MAX_BYTES} bytes"
                ),
            )
    await file.close()

    if not buffer:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Uploaded file is empty",
        )

    extension = _detect_image_extension(bytes(buffer[:16]))
    if extension is None or extension != CONTENT_TYPES[declared]:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File content does not match the declared image type",
        )

    url, path = get_storage().save(bytes(buffer), extension)
    return UploadResponse(
        url=url,
        path=path,
        filename=Path(path).name,
        size=len(buffer),
        content_type=declared,
    )
