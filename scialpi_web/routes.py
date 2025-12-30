"""Route definitions for the scialpi-log web app."""

from __future__ import annotations

import json
import math
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from functools import wraps
from datetime import datetime, date
from typing import Any, Dict, List, Optional
from uuid import uuid4

from flask import (
    Blueprint,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    send_from_directory,
    url_for,
)
from werkzeug.utils import secure_filename

from scialpi.config import get_base_dir
from scialpi.trip_manager import (
    add_trip,
    get_day,
    get_route,
    init_data,
    list_days,
    list_routes,
    list_trips,
    read_trip,
    upsert_day,
    upsert_route,
)
from scialpi.user_manager import (
    add_friend,
    authenticate,
    create_group,
    create_invite,
    create_reset_token,
    create_user,
    consume_reset_token,
    get_user,
    get_user_by_email,
    init_user_data,
    is_friend,
    is_member,
    list_groups,
    list_groups_for_user,
    list_invites_for_user,
    list_users,
    set_user_photo,
    set_password,
)
from scialpi.day_media import add_day_photo, init_media_data, list_day_photos
from scialpi.post_manager import (
    add_comment,
    add_post,
    get_post,
    init_social_data,
    list_comments,
    list_posts,
)
from scialpi.avalanche_manager import (
    load_avalanches,
    add_avalanche as _add_avalanche,
    confirm_avalanche as _confirm_avalanche,
    filter_avalanches,
)

bp = Blueprint("scialpi", __name__, static_folder="static", static_url_path="/scialpi/static")


@bp.app_context_processor
def _inject_user():
    return {"current_user": _current_user()}


def _current_user() -> Optional[Dict[str, Any]]:
    user_id = session.get("user_id")
    if not user_id:
        return None
    return get_user(str(user_id))


def _login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not _current_user():
            return redirect(url_for("scialpi.login"))
        return view(*args, **kwargs)

    return wrapper


def _parse_csv_ids(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _parse_filter_date(value: Optional[str]) -> Optional["date"]:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_day_date(value: Optional[str]) -> Optional["date"]:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    if "-" in text:
        try:
            return datetime.fromisoformat(text).date()
        except ValueError:
            pass
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 8:
        try:
            return datetime.strptime(digits[:8], "%d%m%Y").date()
        except ValueError:
            return None
    return None


def _build_day_cards(days: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not days:
        return []
    day_ids = [day.get("id") for day in days if day.get("id")]
    photo_map: Dict[str, str] = {}
    for photo in list_day_photos(day_ids):
        day_id = photo.get("day_id")
        if day_id and day_id not in photo_map:
            photo_map[day_id] = photo.get("filename")
    cards = []
    for day in days:
        route = get_route(day.get("route_id"))
        if not route:
            continue
        photo_filename = photo_map.get(day.get("id"))
        photo_url = (
            url_for("scialpi.day_photo_file", filename=photo_filename)
            if photo_filename
            else None
        )
        cards.append(
            {
                "id": day.get("id"),
                "date": day.get("date"),
                "route_name": route.get("name"),
                "difficulty": route.get("difficulty"),
                "gain": route.get("gain"),
                "distance_km": route.get("distance_km"),
                "visibility": day.get("visibility") or "public",
                "photo_url": photo_url,
            }
        )
    return cards


def _parse_route_filters(args) -> Dict[str, Any]:
    visibility_filter = (args.get("visibility") or "all").lower()
    selected_group_ids = _parse_csv_ids(args.get("group_ids"))
    difficulty_filter = (args.get("difficulty") or "").strip().lower()
    filter_date = _parse_filter_date(args.get("date"))
    try:
        min_distance = float(args.get("min_distance")) if args.get("min_distance") else None
    except (TypeError, ValueError):
        min_distance = None
    try:
        max_distance = float(args.get("max_distance")) if args.get("max_distance") else None
    except (TypeError, ValueError):
        max_distance = None
    try:
        min_gain = float(args.get("min_gain")) if args.get("min_gain") else None
    except (TypeError, ValueError):
        min_gain = None
    try:
        max_gain = float(args.get("max_gain")) if args.get("max_gain") else None
    except (TypeError, ValueError):
        max_gain = None
    return {
        "visibility": visibility_filter,
        "group_ids": selected_group_ids,
        "difficulty": difficulty_filter,
        "date": filter_date,
        "min_distance": min_distance,
        "max_distance": max_distance,
        "min_gain": min_gain,
        "max_gain": max_gain,
    }


def _route_matches(route: Dict[str, Any], filters: Dict[str, Any]) -> bool:
    difficulty_filter = filters.get("difficulty")
    if difficulty_filter:
        if difficulty_filter not in (route.get("difficulty") or "").lower():
            return False
    distance = route.get("distance_km")
    min_distance = filters.get("min_distance")
    max_distance = filters.get("max_distance")
    if min_distance is not None and (distance is None or distance < min_distance):
        return False
    if max_distance is not None and (distance is None or distance > max_distance):
        return False
    gain = route.get("gain")
    min_gain = filters.get("min_gain")
    max_gain = filters.get("max_gain")
    if min_gain is not None and (gain is None or gain < min_gain):
        return False
    if max_gain is not None and (gain is None or gain > max_gain):
        return False
    return True


def _day_matches(day: Dict[str, Any], user: Optional[Dict[str, Any]], filters: Dict[str, Any]) -> bool:
    visibility_filter = filters.get("visibility", "all")
    selected_group_ids = filters.get("group_ids") or []
    filter_date = filters.get("date")
    if filter_date:
        day_date = _parse_day_date(day.get("date"))
        if not day_date or day_date != filter_date:
            return False
    if visibility_filter == "all":
        return _is_day_visible(day, user)
    if visibility_filter == "friends":
        if not user:
            return False
        owner_id = day.get("owner_id")
        if owner_id and owner_id == user.get("id"):
            return True
        return bool(owner_id and is_friend(user.get("id"), owner_id))
    if visibility_filter == "groups":
        if day.get("visibility") != "groups":
            return False
        if not selected_group_ids:
            return False
        group_set = set(selected_group_ids)
        day_groups = [gid for gid in (day.get("group_ids") or []) if gid in group_set]
        if not day_groups:
            return False
        for group_id in day_groups:
            group = next((g for g in list_groups() if g.get("id") == group_id), None)
            if group and group.get("is_public"):
                return True
            if user and is_member(user.get("id"), group_id):
                return True
        return False
    return _is_day_visible(day, user)


def _is_day_visible(day: Dict[str, Any], user: Optional[Dict[str, Any]]) -> bool:
    visibility = day.get("visibility") or "public"
    owner_id = day.get("owner_id")
    if visibility == "public":
        return True
    if owner_id and user and user.get("id") == owner_id:
        return True
    if visibility == "private":
        return False
    if visibility == "friends":
        if not user:
            return False
        return bool(owner_id and is_friend(user.get("id"), owner_id))
    if visibility == "people":
        if not user:
            return False
        return user.get("id") in (day.get("people_ids") or [])
    if visibility == "groups":
        group_ids = day.get("group_ids") or []
        for group_id in group_ids:
            group = next((g for g in list_groups() if g.get("id") == group_id), None)
            if group and group.get("is_public"):
                return True
        if not user:
            return False
        for group_id in group_ids:
            group = next((g for g in list_groups() if g.get("id") == group_id), None)
            if group and group.get("is_public"):
                return True
            if is_member(user.get("id"), group_id):
                return True
        return False
    return False


def _parse_gpx(file_storage) -> List[List[float]]:
    try:
        content = file_storage.read()
        root = ET.fromstring(content)
    except Exception:
        return []
    points: List[List[float]] = []
    for elem in root.findall(".//{*}trkpt") + root.findall(".//{*}rtept"):
        try:
            lat = float(elem.attrib.get("lat"))
            lon = float(elem.attrib.get("lon"))
        except (TypeError, ValueError):
            continue
        ele = None
        ele_node = elem.find(".//{*}ele")
        if ele_node is not None and ele_node.text:
            try:
                ele = float(ele_node.text.strip())
            except (TypeError, ValueError):
                ele = None
        if ele is not None:
            points.append([lat, lon, ele])
        else:
            points.append([lat, lon])
    return points


def _fetch_elevations(points: List[List[float]]) -> List[List[float]]:
    if not points:
        return []
    results: List[List[float]] = []
    chunk_size = 100
    for i in range(0, len(points), chunk_size):
        chunk = points[i : i + chunk_size]
        locations = "|".join(f"{p[0]},{p[1]}" for p in chunk)
        url = (
            "https://api.open-elevation.com/api/v1/lookup?locations="
            + urllib.parse.quote(locations)
        )
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            data = payload.get("results", [])
            if len(data) != len(chunk):
                return points
            for point, item in zip(chunk, data):
                elev = item.get("elevation")
                if elev is None:
                    results.append(point)
                else:
                    results.append([point[0], point[1], float(elev)])
        except Exception:
            return points
    return results


def _ensure_elevation(points: List[List[float]]) -> List[List[float]]:
    if not points:
        return points
    needs = any(len(p) < 3 or p[2] is None for p in points)
    if not needs:
        return points
    fetched = _fetch_elevations(points)
    enriched: List[List[float]] = []
    for original, fetched_point in zip(points, fetched):
        if len(original) > 2 and original[2] is not None:
            enriched.append([original[0], original[1], float(original[2])])
        elif len(fetched_point) > 2:
            enriched.append([fetched_point[0], fetched_point[1], float(fetched_point[2])])
        else:
            enriched.append(original)
    return enriched


def _parse_iso_time(value: Optional[str]) -> Optional["datetime"]:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _parse_activity_gpx(file_storage) -> List[Dict[str, Any]]:
    try:
        content = file_storage.read()
        root = ET.fromstring(content)
    except Exception:
        return []
    points: List[Dict[str, Any]] = []
    for elem in root.findall(".//{*}trkpt") + root.findall(".//{*}rtept"):
        try:
            lat = float(elem.attrib.get("lat"))
            lon = float(elem.attrib.get("lon"))
        except (TypeError, ValueError):
            continue
        ele = None
        ele_node = elem.find(".//{*}ele")
        if ele_node is not None and ele_node.text:
            try:
                ele = float(ele_node.text.strip())
            except (TypeError, ValueError):
                ele = None
        time_node = elem.find(".//{*}time")
        ts = _parse_iso_time(time_node.text.strip()) if time_node is not None and time_node.text else None
        points.append({"lat": lat, "lon": lon, "ele": ele, "time": ts})
    return points


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371000.0
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return radius * c


def _compute_activity_stats(points: List[Dict[str, Any]]) -> Dict[str, Optional[float]]:
    if not points or len(points) < 2:
        return {
            "distance_km": None,
            "gain_m": None,
            "loss_m": None,
            "duration_h": None,
            "pace_min_km": None,
            "vam": None,
            "up_hours": None,
            "down_hours": None,
        }
    distance_m = 0.0
    gain_m = 0.0
    loss_m = 0.0
    total_seconds = 0.0
    up_seconds = 0.0
    down_seconds = 0.0
    prev = points[0]
    for point in points[1:]:
        distance_m += haversine_meters(prev["lat"], prev["lon"], point["lat"], point["lon"])
        if prev.get("ele") is not None and point.get("ele") is not None:
            delta = float(point["ele"]) - float(prev["ele"])
            if delta > 0:
                gain_m += delta
            elif delta < 0:
                loss_m += abs(delta)
        if prev.get("time") and point.get("time"):
            delta_t = (point["time"] - prev["time"]).total_seconds()
            if delta_t > 0:
                total_seconds += delta_t
                if point.get("ele") is not None and prev.get("ele") is not None:
                    if delta > 0:
                        up_seconds += delta_t
                    elif delta < 0:
                        down_seconds += delta_t
        prev = point
    distance_km = round(distance_m / 1000, 2) if distance_m > 0 else None
    duration_h = round(total_seconds / 3600, 2) if total_seconds > 0 else None
    pace_min_km = None
    if distance_km and total_seconds > 0:
        pace_min_km = round((total_seconds / 60) / distance_km, 1)
    vam = None
    if duration_h and gain_m > 0:
        vam = round(gain_m / duration_h, 0)
    up_hours = round(up_seconds / 3600, 2) if up_seconds > 0 else None
    down_hours = round(down_seconds / 3600, 2) if down_seconds > 0 else None
    return {
        "distance_km": distance_km,
        "gain_m": int(round(gain_m)) if gain_m else None,
        "loss_m": int(round(loss_m)) if loss_m else None,
        "duration_h": duration_h,
        "pace_min_km": pace_min_km,
        "vam": vam,
        "up_hours": up_hours,
        "down_hours": down_hours,
    }

@bp.record_once
def _ensure_data_dir(_state) -> None:
    # assicurati che la struttura dati sia pronta
    init_data()
    init_user_data()
    init_media_data()
    init_social_data()


@bp.route("/")
def index() -> str:
    """Homepage con la vista attivita."""
    return render_template("activities.html")


@bp.route("/activities")
def activities_page() -> str:
    return render_template("activities.html")


@bp.route("/profile")
@_login_required
def profile_page() -> str:
    user = _current_user()
    days = [day for day in list_days() if day.get("owner_id") == user.get("id")]
    days.sort(key=lambda item: item.get("date", ""), reverse=True)
    public_days = [day for day in days if _is_day_visible(day, None)]
    photo_filename = user.get("photo_filename") if user else None
    photo_url = (
        url_for("scialpi.user_photo_file", filename=photo_filename)
        if photo_filename
        else None
    )
    return render_template(
        "profile.html",
        user=user,
        user_photo_url=photo_url,
        my_days=_build_day_cards(days),
        public_days=_build_day_cards(public_days),
    )


@bp.route("/profile/photo", methods=["POST"])
@_login_required
def profile_photo_upload() -> Any:
    user = _current_user()
    image = request.files.get("photo")
    if not image or not image.filename:
        return redirect(url_for("scialpi.profile_page"))
    base_dir = get_base_dir()
    upload_dir = base_dir / "user_photos"
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = secure_filename(image.filename)
    filename = f"{uuid4().hex}_{safe_name}"
    image.save(upload_dir / filename)
    set_user_photo(user.get("id"), filename)
    return redirect(url_for("scialpi.profile_page"))


@bp.route("/users/photos/<path:filename>")
def user_photo_file(filename: str):
    base_dir = get_base_dir()
    upload_dir = base_dir / "user_photos"
    return send_from_directory(upload_dir, filename)


@bp.route("/people")
def people_page() -> str:
    query = (request.args.get("q") or "").strip().lower()
    user = _current_user()
    results = []
    for entry in list_users():
        if user and entry.get("id") == user.get("id"):
            continue
        name = entry.get("name") or ""
        email = entry.get("email") or ""
        if query and query not in name.lower() and query not in email.lower():
            continue
        photo_filename = entry.get("photo_filename")
        photo_url = (
            url_for("scialpi.user_photo_file", filename=photo_filename)
            if photo_filename
            else None
        )
        results.append(
            {
                "id": entry.get("id"),
                "name": name,
                "is_guide": entry.get("is_guide"),
                "cai_courses": entry.get("cai_courses"),
                "score": entry.get("score"),
                "photo_url": photo_url,
            }
        )
    results.sort(key=lambda item: item.get("name", "").lower())
    return render_template("people.html", query=query, results=results)


@bp.route("/people/<user_id>")
def people_profile(user_id: str) -> str:
    person = get_user(user_id)
    if not person:
        abort(404)
    view_mode = (request.args.get("view") or "").lower()
    viewer = None if view_mode == "public" else _current_user()
    days = [
        day
        for day in list_days()
        if day.get("owner_id") == user_id and _is_day_visible(day, viewer)
    ]
    days.sort(key=lambda item: item.get("date", ""), reverse=True)
    photo_filename = person.get("photo_filename")
    photo_url = (
        url_for("scialpi.user_photo_file", filename=photo_filename)
        if photo_filename
        else None
    )
    return render_template(
        "user_profile.html",
        person=person,
        person_photo_url=photo_url,
        day_cards=_build_day_cards(days),
        is_friend=bool(viewer and is_friend(viewer.get("id"), user_id)),
        public_preview=view_mode == "public",
    )


@bp.route("/activities/<day_id>")
def activity_detail(day_id: str) -> str:
    day = get_day(day_id)
    if not day:
        abort(404)
    if not _is_day_visible(day, _current_user()):
        abort(403)
    people_emails = []
    for person_id in day.get("people_ids") or []:
        person = get_user(person_id)
        if person and person.get("email"):
            people_emails.append(person.get("email"))
    day["people_emails"] = people_emails
    route = get_route(day.get("route_id"))
    photos = list_day_photos([day_id])
    posts = list_posts(day_id)
    enriched_posts = []
    for post in posts:
        author = get_user(post.get("user_id")) if post.get("user_id") else None
        comments = list_comments(post.get("id"))
        enriched_comments = []
        for comment in comments:
            comment_author = get_user(comment.get("user_id")) if comment.get("user_id") else None
            enriched_comments.append(
                {
                    **comment,
                    "author_name": comment_author.get("name") if comment_author else "Utente",
                }
            )
        enriched_posts.append(
            {
                **post,
                "author_name": author.get("name") if author else "Utente",
                "comments": enriched_comments,
            }
        )
    return render_template(
        "activity_detail.html",
        day=day,
        route=route,
        photos=photos,
        posts=enriched_posts,
    )


@bp.route("/activities/<day_id>/posts", methods=["POST"])
@_login_required
def activity_post_create(day_id: str):
    day = get_day(day_id)
    if not day:
        abort(404)
    if not _is_day_visible(day, _current_user()):
        abort(403)
    text = (request.form.get("text") or "").strip()
    if not text:
        return redirect(url_for("scialpi.activity_detail", day_id=day_id))
    user = _current_user()
    add_post(day_id, user.get("id"), text)
    return redirect(url_for("scialpi.activity_detail", day_id=day_id))


@bp.route("/posts/<post_id>/comments", methods=["POST"])
@_login_required
def activity_comment_create(post_id: str):
    post = get_post(post_id)
    if not post:
        abort(404)
    day_id = post.get("day_id")
    day = get_day(day_id) if day_id else None
    if not day or not _is_day_visible(day, _current_user()):
        abort(403)
    text = (request.form.get("text") or "").strip()
    if not text:
        return redirect(url_for("scialpi.activity_detail", day_id=day_id))
    user = _current_user()
    add_comment(post_id, user.get("id"), text)
    return redirect(url_for("scialpi.activity_detail", day_id=day_id))


@bp.route("/register", methods=["GET", "POST"])
def register() -> str:
    if request.method == "POST":
        name = request.form.get("name") or ""
        email = request.form.get("email") or ""
        password = request.form.get("password") or ""
        is_guide = bool(request.form.get("is_guide"))
        cai_courses = request.form.get("cai_courses") or None
        if not name or not email or not password:
            return render_template("register.html", error="Compila tutti i campi.")
        if get_user_by_email(email):
            return render_template("register.html", error="Email gia registrata.")
        user = create_user(name, email, password, is_guide=is_guide, cai_courses=cai_courses)
        session["user_id"] = user["id"]
        return redirect(url_for("scialpi.trips_map"))
    return render_template("register.html")


@bp.route("/login", methods=["GET", "POST"])
def login() -> str:
    if request.method == "POST":
        email = request.form.get("email") or ""
        password = request.form.get("password") or ""
        user = authenticate(email, password)
        if not user:
            return render_template("login.html", error="Credenziali non valide.")
        session["user_id"] = user["id"]
        return redirect(url_for("scialpi.trips_map"))
    return render_template("login.html")


@bp.route("/logout")
def logout() -> str:
    session.pop("user_id", None)
    return redirect(url_for("scialpi.index"))


@bp.route("/reset", methods=["GET", "POST"])
def reset_request() -> str:
    if request.method == "POST":
        email = request.form.get("email") or ""
        user = get_user_by_email(email)
        if not user:
            return render_template("reset_request.html", error="Email non trovata.")
        token = create_reset_token(user["id"])
        return render_template("reset_request.html", token=token)
    return render_template("reset_request.html")


@bp.route("/reset/<token>", methods=["GET", "POST"])
def reset_password(token: str) -> str:
    if request.method == "POST":
        password = request.form.get("password") or ""
        if not password:
            return render_template("reset_set.html", token=token, error="Inserisci una nuova password.")
        user_id = consume_reset_token(token)
        if not user_id:
            return render_template("reset_set.html", token=token, error="Token non valido.")
        set_password(user_id, password)
        return redirect(url_for("scialpi.login"))
    return render_template("reset_set.html", token=token)


@bp.route("/community")
@_login_required
def community() -> str:
    user = _current_user()
    groups = list_groups_for_user(user["id"]) if user else []
    invites = list_invites_for_user(user["email"]) if user else []
    return render_template("community.html", groups=groups, invites=invites)


@bp.route("/trips/new", methods=["GET", "POST"])
def trip_create() -> str:
    """Crea una nuova gita tramite form web."""
    if request.method == "POST":
        date = request.form.get("date")
        title = request.form.get("title")
        area = request.form.get("area")
        lat = request.form.get("lat") or None
        lon = request.form.get("lon") or None
        gain = request.form.get("gain") or None
        distance_km = request.form.get("distance_km") or None
        duration = request.form.get("duration") or None
        difficulty = request.form.get("difficulty") or None
        specs = request.form.get("specs") or None
        avalanche = request.form.get("avalanche") or None
        snow = request.form.get("snow") or None
        weather = request.form.get("weather") or None
        notes = request.form.get("notes") or None
        track_points_raw = request.form.get("track_points") or ""
        gpx_file = request.files.get("gpx")
        # Converte alcuni campi
        try:
            lat_float = float(lat) if lat else None
            lon_float = float(lon) if lon else None
        except (TypeError, ValueError):
            lat_float = None
            lon_float = None
        gain_int = int(gain) if gain else None
        distance_float = float(distance_km) if distance_km else None
        avalanche_int = int(avalanche) if avalanche else None
        track_points: List[List[float]] = []
        if gpx_file and gpx_file.filename:
            track_points = _parse_gpx(gpx_file)
        elif track_points_raw:
            try:
                parsed = json.loads(track_points_raw)
                if isinstance(parsed, list):
                    for point in parsed:
                        if (
                            isinstance(point, list)
                            and len(point) >= 2
                            and isinstance(point[0], (int, float))
                            and isinstance(point[1], (int, float))
                        ):
                            if len(point) >= 3 and isinstance(point[2], (int, float)):
                                track_points.append([float(point[0]), float(point[1]), float(point[2])])
                            else:
                                track_points.append([float(point[0]), float(point[1])])
            except json.JSONDecodeError:
                track_points = []
        if track_points:
            track_points = _ensure_elevation(track_points)
            if lat_float is None or lon_float is None:
                last_point = track_points[-1]
                lat_float = float(last_point[0])
                lon_float = float(last_point[1])
        slug = add_trip(
            date=date,
            title=title,
            area=area,
            lat=lat_float,
            lon=lon_float,
            gain=gain_int,
            distance_km=distance_float,
            duration=duration,
            difficulty=difficulty,
            specs=specs,
            track=track_points,
            avalanche=avalanche_int,
            snow=snow,
            weather=weather,
            notes=notes,
        )
        return redirect(url_for("scialpi.trip_detail", slug=slug))
    return redirect(url_for("scialpi.trips_map"))


@bp.route("/trips/map")
def trips_map() -> str:
    """Mappa con le gite registrate e form per aggiungerne una nuova."""
    return render_template("trips_map.html")


@bp.route("/api/trips")
def trips_api() -> Any:
    """API per leggere le gite registrate (usata dalla mappa)."""
    trips = list_trips()
    return jsonify(trips)


@bp.route("/api/routes", methods=["GET", "POST"])
def routes_api() -> Any:
    """API per leggere o creare percorsi."""
    if request.method == "POST":
        if not _current_user():
            return jsonify({"error": "Login richiesto"}), 401
        data = request.form or request.get_json(silent=True) or {}
        route_id = data.get("route_id") or None
        name = data.get("name") or None
        description = data.get("description") or None
        difficulty = data.get("difficulty") or None
        track_points: List[List[float]] = []
        gpx_file = request.files.get("gpx")
        track_points_raw = data.get("track_points") or ""
        if gpx_file and gpx_file.filename:
            track_points = _parse_gpx(gpx_file)
        elif track_points_raw:
            try:
                parsed = json.loads(track_points_raw)
                if isinstance(parsed, list):
                    for point in parsed:
                        if (
                            isinstance(point, list)
                            and len(point) >= 2
                            and isinstance(point[0], (int, float))
                            and isinstance(point[1], (int, float))
                        ):
                            if len(point) >= 3 and isinstance(point[2], (int, float)):
                                track_points.append([float(point[0]), float(point[1]), float(point[2])])
                            else:
                                track_points.append([float(point[0]), float(point[1])])
            except json.JSONDecodeError:
                track_points = []
        if track_points:
            track_points = _ensure_elevation(track_points)
        if not route_id and not track_points:
            return jsonify({"error": "Traccia obbligatoria per creare il percorso"}), 400
        if not name:
            return jsonify({"error": "Nome percorso obbligatorio"}), 400
        route = upsert_route(
            name=name,
            description=description,
            difficulty=difficulty,
            track=track_points or None,
            route_id=route_id,
        )
        return jsonify(route), 201
    filters = _parse_route_filters(request.args)

    routes = list_routes()
    user = _current_user()
    payload = []
    for route in routes:
        days = list_days(route.get("id"))
        visible_days = [day for day in days if _day_matches(day, user, filters)]
        if not visible_days:
            continue
        if not _route_matches(route, filters):
            continue
        payload.append(
            {
                "id": route.get("id"),
                "name": route.get("name"),
                "description": route.get("description"),
                "difficulty": route.get("difficulty"),
                "gain": route.get("gain"),
                "distance_km": route.get("distance_km"),
                "lat": route.get("lat"),
                "lon": route.get("lon"),
            }
        )
    return jsonify(payload)


@bp.route("/api/routes/<route_id>")
def route_detail_api(route_id: str) -> Any:
    """API per i dettagli di un percorso."""
    route = get_route(route_id)
    if not route:
        return jsonify({"error": "Percorso non trovato"}), 404
    user = _current_user()
    days = [day for day in list_days(route_id) if _is_day_visible(day, user)]
    days.sort(key=lambda item: item.get("date", ""), reverse=True)
    for day in days:
        people_emails = []
        for person_id in day.get("people_ids") or []:
            person = get_user(person_id)
            if person and person.get("email"):
                people_emails.append(person.get("email"))
        day["people_emails"] = people_emails
    photos = list_day_photos([day.get("id") for day in days])
    return jsonify({"route": route, "days": days, "photos": photos})


@bp.route("/api/groups", methods=["GET", "POST"])
def groups_api() -> Any:
    user = _current_user()
    if request.method == "POST":
        if not user:
            return jsonify({"error": "Login richiesto"}), 401
        data = request.form or request.get_json(silent=True) or {}
        name = data.get("name") or ""
        description = data.get("description") or None
        is_public = bool(data.get("is_public"))
        if not name:
            return jsonify({"error": "Nome gruppo obbligatorio"}), 400
        group = create_group(name, user["id"], description, is_public)
        return jsonify(group), 201
    groups = list_groups()
    visible = []
    for group in groups:
        if group.get("is_public"):
            visible.append(group)
            continue
        if user and is_member(user.get("id"), group.get("id")):
            visible.append(group)
    return jsonify(visible)


@bp.route("/api/groups/<group_id>/invite", methods=["POST"])
def group_invite_api(group_id: str) -> Any:
    user = _current_user()
    if not user:
        return jsonify({"error": "Login richiesto"}), 401
    data = request.form or request.get_json(silent=True) or {}
    email = data.get("email") or ""
    if not email:
        return jsonify({"error": "Email obbligatoria"}), 400
    invite = create_invite(group_id, email, user.get("id"))
    return jsonify(invite), 201


@bp.route("/api/friends", methods=["POST"])
def friends_api() -> Any:
    user = _current_user()
    if not user:
        return jsonify({"error": "Login richiesto"}), 401
    data = request.form or request.get_json(silent=True) or {}
    email = data.get("email") or ""
    if not email:
        return jsonify({"error": "Email obbligatoria"}), 400
    friend = add_friend(user.get("id"), email)
    if not friend:
        return jsonify({"error": "Utente non trovato"}), 404
    return jsonify(friend), 201


@bp.route("/api/days", methods=["GET", "POST"])
def days_api() -> Any:
    """API per creare o modificare una giornata."""
    if request.method == "GET":
        filters = _parse_route_filters(request.args)
        user = _current_user()
        days_source = list_days()
        photo_map: Dict[str, str] = {}
        for photo in list_day_photos([day.get("id") for day in days_source]):
            day_id = photo.get("day_id")
            if day_id and day_id not in photo_map:
                photo_map[day_id] = photo.get("filename")
        payload = []
        for day in days_source:
            if not _day_matches(day, user, filters):
                continue
            route = get_route(day.get("route_id"))
            if not route or not _route_matches(route, filters):
                continue
            owner_name = None
            if day.get("owner_id"):
                owner = get_user(day.get("owner_id"))
                if owner:
                    owner_name = owner.get("name")
            photo_filename = photo_map.get(day.get("id"))
            photo_url = (
                url_for("scialpi.day_photo_file", filename=photo_filename)
                if photo_filename
                else None
            )
            payload.append(
                {
                    "id": day.get("id"),
                    "route_id": day.get("route_id"),
                    "date": day.get("date"),
                    "snow_quality": day.get("snow_quality"),
                    "description": day.get("description"),
                    "weather": day.get("weather"),
                    "avalanches_seen": day.get("avalanches_seen"),
                    "activity_distance_km": day.get("activity_distance_km"),
                    "activity_gain_m": day.get("activity_gain_m"),
                    "activity_loss_m": day.get("activity_loss_m"),
                    "activity_duration_h": day.get("activity_duration_h"),
                    "activity_pace_min_km": day.get("activity_pace_min_km"),
                    "activity_vam": day.get("activity_vam"),
                    "activity_up_hours": day.get("activity_up_hours"),
                    "activity_down_hours": day.get("activity_down_hours"),
                    "route_name": route.get("name"),
                    "route_difficulty": route.get("difficulty"),
                    "route_gain": route.get("gain"),
                    "route_distance_km": route.get("distance_km"),
                    "lat": route.get("lat"),
                    "lon": route.get("lon"),
                    "owner_name": owner_name,
                    "photo_filename": photo_filename,
                    "photo_url": photo_url,
                }
            )
        payload.sort(key=lambda item: item.get("date", ""), reverse=True)
        return jsonify(payload)

    data = request.form or request.get_json(silent=True) or {}
    user = _current_user()
    if not user:
        return jsonify({"error": "Login richiesto"}), 401
    day_id = data.get("day_id") or None
    existing_day = get_day(day_id) if day_id else None
    if day_id and not existing_day:
        return jsonify({"error": "Giornata non trovata"}), 404
    if existing_day and existing_day.get("owner_id") and existing_day.get("owner_id") != user.get("id"):
        return jsonify({"error": "Non autorizzato"}), 403
    route_id = data.get("route_id") or None
    date = data.get("date") or None
    if not route_id and existing_day:
        route_id = existing_day.get("route_id")
    if not date and existing_day:
        date = existing_day.get("date")
    if not route_id or not date:
        return jsonify({"error": "Percorso e data sono obbligatori"}), 400
    visibility = data.get("visibility") if "visibility" in data else None
    if visibility in ("", None):
        visibility = existing_day.get("visibility") if existing_day else "public"
    raw_group_ids = data.get("group_ids") if "group_ids" in data else None
    group_ids = _parse_csv_ids(raw_group_ids) if raw_group_ids is not None else (existing_day.get("group_ids") or [] if existing_day else [])
    people_raw = data.get("people_emails") if "people_emails" in data else None
    people_emails = _parse_csv_ids(people_raw) if people_raw is not None else (existing_day.get("people_ids") or [] if existing_day else [])
    people_ids = []
    if people_raw is None and existing_day:
        people_ids = existing_day.get("people_ids") or []
    else:
        for email in people_emails:
            person = get_user_by_email(email)
            if person:
                people_ids.append(person.get("id"))
    activity_stats = None
    activity_gpx = request.files.get("activity_gpx")
    if activity_gpx and activity_gpx.filename:
        points = _parse_activity_gpx(activity_gpx)
        if len(points) < 2:
            return jsonify({"error": "GPX attivita non valido"}), 400
        activity_stats = _compute_activity_stats(points)
    day = upsert_day(
        route_id=route_id,
        date=date,
        snow_quality=data.get("snow_quality") if "snow_quality" in data else existing_day.get("snow_quality") if existing_day else None,
        description=data.get("day_description") if "day_description" in data else existing_day.get("description") if existing_day else None,
        weather=data.get("weather") if "weather" in data else existing_day.get("weather") if existing_day else None,
        avalanches_seen=data.get("avalanches_seen") if "avalanches_seen" in data else existing_day.get("avalanches_seen") if existing_day else None,
        visibility=visibility,
        group_ids=group_ids,
        people_ids=people_ids,
        owner_id=user.get("id"),
        day_id=day_id,
        activity_stats=activity_stats,
    )
    return jsonify(day), 201


@bp.route("/api/days/<day_id>")
def day_detail_api(day_id: str) -> Any:
    """API per i dettagli di una giornata."""
    day = get_day(day_id)
    if not day:
        return jsonify({"error": "Giornata non trovata"}), 404
    if not _is_day_visible(day, _current_user()):
        return jsonify({"error": "Non autorizzato"}), 403
    people_emails = []
    for person_id in day.get("people_ids") or []:
        person = get_user(person_id)
        if person and person.get("email"):
            people_emails.append(person.get("email"))
    day["people_emails"] = people_emails
    return jsonify(day)


@bp.route("/api/trips/<slug>")
def trip_detail_api(slug: str) -> Any:
    """API per leggere i dettagli di una gita."""
    trip = read_trip(slug)
    if not trip:
        return jsonify({"error": "Gita non trovata"}), 404
    return jsonify(trip)


@bp.route("/trips/<slug>")
def trip_detail(slug: str) -> str:
    """Mostra i dettagli di una gita."""
    trip = read_trip(slug)
    if not trip:
        abort(404)
    # Converte le note in HTML usando markdown se presenti
    from markdown import markdown  # import qui per evitare dipendenza se non usata

    notes_html: Optional[str] = None
    notes = trip.get("notes")
    if notes:
        try:
            notes_html = markdown(notes)
        except Exception:
            notes_html = notes
    return render_template("trip_detail.html", trip=trip, notes_html=notes_html)


@bp.route("/avalanches")
def avalanches_page() -> str:
    """Mostra la pagina per segnalare e consultare le valanghe."""
    return render_template("avalanches.html")


@bp.route("/api/avalanches", methods=["GET", "POST"])
def avalanches_api() -> Any:
    """API per creare e leggere le segnalazioni di valanghe."""
    if request.method == "POST":
        # Crea una nuova segnalazione
        image_filename = None
        if request.files or request.form:
            data = request.form
        else:
            data = request.get_json(silent=True) or {}
        try:
            lat = float(data.get("lat"))
            lon = float(data.get("lon"))
        except (TypeError, ValueError):
            return jsonify({"error": "Latitudine e longitudine non validi"}), 400
        description = data.get("description") or None
        size = data.get("size") or None
        danger = data.get("danger") or None
        slope = data.get("slope") or None
        try:
            danger_int = int(danger) if danger else None
        except (TypeError, ValueError):
            return jsonify({"error": "Pericolo non valido"}), 400
        try:
            slope_float = float(slope) if slope else None
        except (TypeError, ValueError):
            return jsonify({"error": "Pendenza non valida"}), 400
        image = request.files.get("image")
        if image and image.filename:
            base_dir = get_base_dir()
            upload_dir = base_dir / "avalanche_images"
            upload_dir.mkdir(parents=True, exist_ok=True)
            safe_name = secure_filename(image.filename)
            image_filename = f"{uuid4().hex}_{safe_name}"
            image.save(upload_dir / image_filename)
        user = _current_user()
        record = _add_avalanche(
            lat,
            lon,
            description=description,
            size=size,
            danger=danger_int,
            slope=slope_float,
            image=image_filename,
            created_by=user.get("id") if user else None,
        )
        return jsonify(record), 201
    # GET: filtra per intervallo temporale
    start_param = request.args.get("start")
    end_param = request.args.get("end")
    avalanches: List[Dict[str, Any]]
    if start_param or end_param:
        avalanches = filter_avalanches(start_param, end_param)
    else:
        avalanches = load_avalanches()
        avalanches.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return jsonify(avalanches)


@bp.route("/api/avalanches/<int:avalanche_id>/confirm", methods=["POST"])
def avalanches_confirm_api(avalanche_id: int) -> Any:
    """API per confermare una segnalazione di valanga."""
    user = _current_user()
    if not user:
        return jsonify({"error": "Login richiesto"}), 401
    record = _confirm_avalanche(avalanche_id, user.get("id"))
    if not record:
        return jsonify({"error": "Segnalazione non trovata"}), 404
    if record.get("already_confirmed"):
        return jsonify({"error": "Gia confermata"}), 409
    return jsonify(record)


@bp.route("/avalanches/images/<path:filename>")
def avalanches_image(filename: str):
    """Serve le immagini salvate per le segnalazioni di valanghe."""
    base_dir = get_base_dir()
    upload_dir = base_dir / "avalanche_images"
    return send_from_directory(upload_dir, filename)


@bp.route("/api/days/<day_id>/photos", methods=["POST"])
def day_photos_api(day_id: str) -> Any:
    user = _current_user()
    if not user:
        return jsonify({"error": "Login richiesto"}), 401
    day = get_day(day_id)
    if not day:
        return jsonify({"error": "Giornata non trovata"}), 404
    if day.get("owner_id") and day.get("owner_id") != user.get("id"):
        return jsonify({"error": "Non autorizzato"}), 403
    if not day.get("owner_id"):
        upsert_day(
            route_id=day.get("route_id"),
            date=day.get("date"),
            snow_quality=day.get("snow_quality"),
            description=day.get("description"),
            weather=day.get("weather"),
            avalanches_seen=day.get("avalanches_seen"),
            visibility=day.get("visibility") or "public",
            group_ids=day.get("group_ids") or [],
            people_ids=day.get("people_ids") or [],
            owner_id=user.get("id"),
            day_id=day_id,
        )
        day = get_day(day_id) or day
    image = request.files.get("image")
    if not image or not image.filename:
        return jsonify({"error": "Immagine mancante"}), 400
    try:
        lat = float(request.form.get("lat")) if request.form.get("lat") else None
        lon = float(request.form.get("lon")) if request.form.get("lon") else None
    except (TypeError, ValueError):
        lat = None
        lon = None
    base_dir = get_base_dir()
    upload_dir = base_dir / "day_photos"
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = secure_filename(image.filename)
    filename = f"{uuid4().hex}_{safe_name}"
    image.save(upload_dir / filename)
    record = add_day_photo(day_id, filename, lat, lon, user.get("id"))
    return jsonify(record), 201


@bp.route("/days/photos/<path:filename>")
def day_photo_file(filename: str):
    base_dir = get_base_dir()
    upload_dir = base_dir / "day_photos"
    return send_from_directory(upload_dir, filename)
