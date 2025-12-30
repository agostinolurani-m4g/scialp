from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .config import get_base_dir


def init_media_data() -> None:
    base_dir = get_base_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    photos_path = base_dir / "day_photos.json"
    if not photos_path.exists():
        photos_path.write_text("[]", encoding="utf-8")
    photos_dir = base_dir / "day_photos"
    photos_dir.mkdir(parents=True, exist_ok=True)


def _photos_path() -> Path:
    return get_base_dir() / "day_photos.json"


def _load_photos() -> List[Dict[str, Any]]:
    path = _photos_path()
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def _save_photos(photos: List[Dict[str, Any]]) -> None:
    path = _photos_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(photos, f, indent=2, ensure_ascii=False)


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def add_day_photo(
    day_id: str,
    filename: str,
    lat: Optional[float],
    lon: Optional[float],
    owner_id: Optional[str],
) -> Dict[str, Any]:
    photos = _load_photos()
    record = {
        "id": uuid4().hex,
        "day_id": day_id,
        "filename": filename,
        "lat": lat,
        "lon": lon,
        "owner_id": owner_id,
        "created_at": _now_iso(),
    }
    photos.append(record)
    _save_photos(photos)
    return record


def list_day_photos(day_ids: List[str]) -> List[Dict[str, Any]]:
    if not day_ids:
        return []
    day_set = set(day_ids)
    return [p for p in _load_photos() if p.get("day_id") in day_set]
