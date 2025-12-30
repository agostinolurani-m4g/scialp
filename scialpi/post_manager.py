from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .config import get_base_dir


def init_social_data() -> None:
    base_dir = get_base_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    for name in ("posts.json", "comments.json"):
        path = base_dir / name
        if not path.exists():
            path.write_text("[]", encoding="utf-8")


def _path(name: str):
    return get_base_dir() / name


def _load_list(name: str) -> List[Dict[str, Any]]:
    path = _path(name)
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


def _save_list(name: str, data: List[Dict[str, Any]]) -> None:
    path = _path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def add_post(day_id: str, user_id: str, text: str) -> Dict[str, Any]:
    posts = _load_list("posts.json")
    post = {
        "id": uuid4().hex,
        "day_id": day_id,
        "user_id": user_id,
        "text": text,
        "created_at": _now_iso(),
    }
    posts.append(post)
    _save_list("posts.json", posts)
    return post


def get_post(post_id: str) -> Optional[Dict[str, Any]]:
    for post in _load_list("posts.json"):
        if post.get("id") == post_id:
            return post
    return None


def list_posts(day_id: str) -> List[Dict[str, Any]]:
    posts = [p for p in _load_list("posts.json") if p.get("day_id") == day_id]
    posts.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return posts


def add_comment(post_id: str, user_id: str, text: str) -> Dict[str, Any]:
    comments = _load_list("comments.json")
    comment = {
        "id": uuid4().hex,
        "post_id": post_id,
        "user_id": user_id,
        "text": text,
        "created_at": _now_iso(),
    }
    comments.append(comment)
    _save_list("comments.json", comments)
    return comment


def list_comments(post_id: str) -> List[Dict[str, Any]]:
    comments = [c for c in _load_list("comments.json") if c.get("post_id") == post_id]
    comments.sort(key=lambda item: item.get("created_at", ""))
    return comments
