from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from werkzeug.security import check_password_hash, generate_password_hash

from .config import get_base_dir


def init_user_data() -> None:
    base_dir = get_base_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    for name in ("users.json", "groups.json", "memberships.json", "invites.json", "friends.json", "reset_tokens.json"):
        path = base_dir / name
        if not path.exists():
            path.write_text("[]", encoding="utf-8")


def _path(name: str) -> Path:
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


def create_user(
    name: str,
    email: str,
    password: str,
    is_guide: bool = False,
    cai_courses: Optional[str] = None,
) -> Dict[str, Any]:
    users = _load_list("users.json")
    user = {
        "id": uuid4().hex,
        "name": name,
        "email": email.lower(),
        "password_hash": generate_password_hash(password),
        "is_guide": bool(is_guide),
        "cai_courses": cai_courses,
        "score": 0,
        "created_at": _now_iso(),
    }
    users.append(user)
    _save_list("users.json", users)
    return user


def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    for user in _load_list("users.json"):
        if user.get("id") == user_id:
            return user
    return None


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    email = email.lower()
    for user in _load_list("users.json"):
        if user.get("email") == email:
            return user
    return None


def authenticate(email: str, password: str) -> Optional[Dict[str, Any]]:
    user = get_user_by_email(email)
    if not user:
        return None
    if check_password_hash(user.get("password_hash", ""), password):
        return user
    return None


def set_password(user_id: str, new_password: str) -> None:
    users = _load_list("users.json")
    for user in users:
        if user.get("id") == user_id:
            user["password_hash"] = generate_password_hash(new_password)
            _save_list("users.json", users)
            return


def create_reset_token(user_id: str) -> str:
    tokens = _load_list("reset_tokens.json")
    token = uuid4().hex
    tokens.append({"token": token, "user_id": user_id, "created_at": _now_iso()})
    _save_list("reset_tokens.json", tokens)
    return token


def consume_reset_token(token: str) -> Optional[str]:
    tokens = _load_list("reset_tokens.json")
    for entry in tokens:
        if entry.get("token") == token:
            user_id = entry.get("user_id")
            tokens = [t for t in tokens if t.get("token") != token]
            _save_list("reset_tokens.json", tokens)
            return user_id
    return None


def list_groups() -> List[Dict[str, Any]]:
    return _load_list("groups.json")


def list_groups_for_user(user_id: str) -> List[Dict[str, Any]]:
    memberships = _load_list("memberships.json")
    group_ids = {m.get("group_id") for m in memberships if m.get("user_id") == user_id}
    return [g for g in _load_list("groups.json") if g.get("id") in group_ids]


def is_member(user_id: str, group_id: str) -> bool:
    for membership in _load_list("memberships.json"):
        if membership.get("user_id") == user_id and membership.get("group_id") == group_id:
            return True
    return False


def create_group(name: str, owner_id: str, description: Optional[str], is_public: bool) -> Dict[str, Any]:
    groups = _load_list("groups.json")
    group = {
        "id": uuid4().hex,
        "name": name,
        "description": description,
        "is_public": bool(is_public),
        "owner_id": owner_id,
        "created_at": _now_iso(),
    }
    groups.append(group)
    _save_list("groups.json", groups)
    memberships = _load_list("memberships.json")
    memberships.append({"id": uuid4().hex, "group_id": group["id"], "user_id": owner_id, "role": "owner"})
    _save_list("memberships.json", memberships)
    return group


def create_invite(group_id: str, email: str, inviter_id: str) -> Dict[str, Any]:
    invites = _load_list("invites.json")
    invite = {
        "id": uuid4().hex,
        "group_id": group_id,
        "email": email.lower(),
        "inviter_id": inviter_id,
        "status": "pending",
        "created_at": _now_iso(),
    }
    invites.append(invite)
    _save_list("invites.json", invites)
    return invite


def list_invites_for_user(email: str) -> List[Dict[str, Any]]:
    email = email.lower()
    return [inv for inv in _load_list("invites.json") if inv.get("email") == email]


def add_friend(user_id: str, friend_email: str) -> Optional[Dict[str, Any]]:
    friend = get_user_by_email(friend_email)
    if not friend:
        return None
    friendships = _load_list("friends.json")
    for entry in friendships:
        if entry.get("user_id") == user_id and entry.get("friend_id") == friend.get("id"):
            return entry
    friendships.append({"id": uuid4().hex, "user_id": user_id, "friend_id": friend.get("id"), "status": "accepted"})
    friendships.append({"id": uuid4().hex, "user_id": friend.get("id"), "friend_id": user_id, "status": "accepted"})
    _save_list("friends.json", friendships)
    return friend


def is_friend(user_id: str, other_id: str) -> bool:
    for entry in _load_list("friends.json"):
        if entry.get("user_id") == user_id and entry.get("friend_id") == other_id:
            return True
    return False
