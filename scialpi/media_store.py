from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import boto3

from .config import get_base_dir

MEDIA_DIRS = {
    "day": "day_photos",
    "user": "user_photos",
    "avalanche": "avalanche_images",
}


def _media_dir(kind: str) -> str:
    if kind not in MEDIA_DIRS:
        raise ValueError(f"Unsupported media kind: {kind}")
    return MEDIA_DIRS[kind]


def _provider() -> str:
    return os.environ.get("SCIALPI_MEDIA_PROVIDER", "local").lower().strip()


def s3_enabled() -> bool:
    return _provider() == "s3"


def local_dir(kind: str) -> Path:
    return get_base_dir() / _media_dir(kind)


def _s3_settings() -> dict:
    return {
        "bucket": os.environ.get("SCIALPI_S3_BUCKET"),
        "endpoint": os.environ.get("SCIALPI_S3_ENDPOINT"),
        "region": os.environ.get("SCIALPI_S3_REGION", "auto"),
        "access_key": os.environ.get("SCIALPI_S3_ACCESS_KEY"),
        "secret_key": os.environ.get("SCIALPI_S3_SECRET_KEY"),
    }


def _s3_client():
    settings = _s3_settings()
    missing = [key for key, value in settings.items() if not value and key != "region"]
    if missing:
        raise RuntimeError(f"Missing S3 settings: {', '.join(missing)}")
    return boto3.client(
        "s3",
        endpoint_url=settings["endpoint"],
        region_name=settings["region"],
        aws_access_key_id=settings["access_key"],
        aws_secret_access_key=settings["secret_key"],
    )


def _s3_key(kind: str, filename: str) -> str:
    return f"{_media_dir(kind)}/{filename}"


def media_public_url(kind: str, filename: Optional[str]) -> Optional[str]:
    if not filename:
        return None
    if not s3_enabled():
        return None
    base_url = os.environ.get("SCIALPI_MEDIA_BASE_URL", "").strip().rstrip("/")
    if base_url:
        return f"{base_url}/{_media_dir(kind)}/{quote(filename)}"
    settings = _s3_settings()
    endpoint = (settings.get("endpoint") or "").rstrip("/")
    bucket = settings.get("bucket")
    if not endpoint or not bucket:
        return None
    return f"{endpoint}/{bucket}/{_media_dir(kind)}/{quote(filename)}"


def save_media(kind: str, file_storage, filename: str) -> None:
    if s3_enabled():
        client = _s3_client()
        settings = _s3_settings()
        key = _s3_key(kind, filename)
        content_type = getattr(file_storage, "mimetype", None) or "application/octet-stream"
        try:
            file_storage.stream.seek(0)
        except Exception:
            pass
        client.upload_fileobj(
            file_storage.stream,
            settings["bucket"],
            key,
            ExtraArgs={
                "ContentType": content_type,
                "CacheControl": "public, max-age=86400",
            },
        )
        return
    target_dir = local_dir(kind)
    target_dir.mkdir(parents=True, exist_ok=True)
    file_storage.save(target_dir / filename)
