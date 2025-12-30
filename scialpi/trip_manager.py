"""Gestione dei dati delle gite.

Separiamo il concetto di "gita" (percorso) dalla "gita del giorno".
- Percorso: nome, descrizione, difficolta, dislivello, distanza, traccia.
- Giornata: data, qualita neve, descrizione, meteo, valanghe viste.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import get_base_dir
from .utils import slugify


def init_data() -> Path:
    """Inizializza la struttura delle directory per i dati."""
    base_dir = get_base_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    routes_file = base_dir / "routes.json"
    if not routes_file.exists():
        routes_file.write_text("[]", encoding="utf-8")
    days_file = base_dir / "days.json"
    if not days_file.exists():
        days_file.write_text("[]", encoding="utf-8")
    avalanches_file = base_dir / "avalanches.json"
    if not avalanches_file.exists():
        avalanches_file.write_text("[]", encoding="utf-8")
    return base_dir


def _routes_path() -> Path:
    return get_base_dir() / "routes.json"


def _days_path() -> Path:
    return get_base_dir() / "days.json"


def _load_routes() -> List[Dict[str, Any]]:
    path = _routes_path()
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


def _save_routes(routes: List[Dict[str, Any]]) -> None:
    path = _routes_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(routes, f, indent=2, ensure_ascii=False)


def _load_days() -> List[Dict[str, Any]]:
    path = _days_path()
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


def _save_days(days: List[Dict[str, Any]]) -> None:
    path = _days_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(days, f, indent=2, ensure_ascii=False)


def _track_hash(track: Optional[List[List[float]]]) -> str:
    if not track:
        return ""
    m = hashlib.sha1()
    for point in track:
        try:
            lat = float(point[0])
            lon = float(point[1])
        except (TypeError, ValueError, IndexError):
            continue
        m.update(f"{lat:.5f},{lon:.5f};".encode("utf-8"))
    return m.hexdigest()[:8]


def _route_id(name: str, track: Optional[List[List[float]]]) -> str:
    base = slugify(name).lower()
    suffix = _track_hash(track)
    if suffix:
        return f"{base}-{suffix}"
    return base


def _get_route_by_id(route_id: str) -> Optional[Dict[str, Any]]:
    routes = _load_routes()
    for route in routes:
        if route.get("id") == route_id:
            return route
    return None


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return radius * c


def _compute_track_stats(track: Optional[List[List[float]]]) -> tuple[Optional[float], Optional[int]]:
    if not track or len(track) < 2:
        return None, None
    distance_km = 0.0
    gain_m = 0.0
    prev = track[0]
    for point in track[1:]:
        try:
            distance_km += _haversine_km(prev[0], prev[1], point[0], point[1])
        except (TypeError, ValueError, IndexError):
            pass
        if len(prev) > 2 and len(point) > 2:
            try:
                delta = float(point[2]) - float(prev[2])
                if delta > 0:
                    gain_m += delta
            except (TypeError, ValueError):
                pass
        prev = point
    return round(distance_km, 2), int(round(gain_m))


def _estimate_hours(distance_km: Optional[float], gain_m: Optional[int]) -> Optional[float]:
    if distance_km is None and gain_m is None:
        return None
    distance_part = (distance_km or 0.0) / 3.0
    gain_part = (gain_m or 0) / 400.0
    return round(distance_part + gain_part, 2)


def list_routes() -> List[Dict[str, Any]]:
    return _load_routes()


def get_route(route_id: str) -> Optional[Dict[str, Any]]:
    return _get_route_by_id(route_id)


def upsert_route(
    name: str,
    description: Optional[str] = None,
    difficulty: Optional[str] = None,
    track: Optional[List[List[float]]] = None,
    route_id: Optional[str] = None,
) -> Dict[str, Any]:
    routes = _load_routes()
    existing = None
    if route_id:
        for route in routes:
            if route.get("id") == route_id:
                existing = route
                break
    if existing and track:
        new_hash = _track_hash(track)
        if existing.get("track_hash") and new_hash and new_hash != existing.get("track_hash"):
            route_id = None
            existing = None
    if not existing:
        route_id = _route_id(name, track)
        existing = _get_route_by_id(route_id)
    if existing:
        if name:
            existing["name"] = name
        if description is not None:
            existing["description"] = description
        if difficulty is not None:
            existing["difficulty"] = difficulty
        if track:
            existing["track"] = track
            existing["track_hash"] = _track_hash(track)
            distance_km, gain_m = _compute_track_stats(track)
            existing["distance_km"] = distance_km
            existing["gain"] = gain_m
            if track:
                last = track[-1]
                existing["lat"] = float(last[0])
                existing["lon"] = float(last[1])
        _save_routes(routes)
        return existing

    distance_km, gain_m = _compute_track_stats(track)
    lat = None
    lon = None
    if track:
        last = track[-1]
        lat = float(last[0])
        lon = float(last[1])
    route = {
        "id": route_id,
        "name": name,
        "description": description,
        "difficulty": difficulty,
        "track": track or [],
        "track_hash": _track_hash(track),
        "distance_km": distance_km,
        "gain": gain_m,
        "lat": lat,
        "lon": lon,
    }
    routes.append(route)
    _save_routes(routes)
    return route


def list_days(route_id: Optional[str] = None) -> List[Dict[str, Any]]:
    days = _load_days()
    if route_id:
        days = [day for day in days if day.get("route_id") == route_id]
    return days


def get_day(day_id: str) -> Optional[Dict[str, Any]]:
    for day in _load_days():
        if day.get("id") == day_id:
            return day
    return None


def _day_id(route_id: str, date: str) -> str:
    base = slugify(f"{date}_{route_id}").lower()
    days = _load_days()
    candidate = base
    counter = 2
    existing = {day.get("id") for day in days}
    while candidate in existing:
        candidate = f"{base}_{counter}"
        counter += 1
    return candidate


def upsert_day(
    route_id: str,
    date: str,
    snow_quality: Optional[str] = None,
    description: Optional[str] = None,
    weather: Optional[str] = None,
    avalanches_seen: Optional[str] = None,
    visibility: str = "public",
    group_ids: Optional[List[str]] = None,
    people_ids: Optional[List[str]] = None,
    owner_id: Optional[str] = None,
    day_id: Optional[str] = None,
    activity_stats: Optional[Dict[str, Optional[float]]] = None,
) -> Dict[str, Any]:
    days = _load_days()
    existing = None
    if day_id:
        for day in days:
            if day.get("id") == day_id:
                existing = day
                break
    if existing:
        existing["route_id"] = route_id
        existing["date"] = date
        existing["snow_quality"] = snow_quality
        existing["description"] = description
        existing["weather"] = weather
        existing["avalanches_seen"] = avalanches_seen
        existing["visibility"] = visibility
        existing["group_ids"] = group_ids or []
        existing["people_ids"] = people_ids or []
        if owner_id:
            existing["owner_id"] = owner_id
        if activity_stats:
            existing["activity_distance_km"] = activity_stats.get("distance_km")
            existing["activity_gain_m"] = activity_stats.get("gain_m")
            existing["activity_loss_m"] = activity_stats.get("loss_m")
            existing["activity_duration_h"] = activity_stats.get("duration_h")
            existing["activity_pace_min_km"] = activity_stats.get("pace_min_km")
            existing["activity_vam"] = activity_stats.get("vam")
            existing["activity_up_hours"] = activity_stats.get("up_hours")
            existing["activity_down_hours"] = activity_stats.get("down_hours")
        _save_days(days)
        return existing

    day_id = _day_id(route_id, date)
    day = {
        "id": day_id,
        "route_id": route_id,
        "date": date,
        "snow_quality": snow_quality,
        "description": description,
        "weather": weather,
        "avalanches_seen": avalanches_seen,
        "visibility": visibility,
        "group_ids": group_ids or [],
        "people_ids": people_ids or [],
        "owner_id": owner_id,
        "activity_distance_km": activity_stats.get("distance_km") if activity_stats else None,
        "activity_gain_m": activity_stats.get("gain_m") if activity_stats else None,
        "activity_loss_m": activity_stats.get("loss_m") if activity_stats else None,
        "activity_duration_h": activity_stats.get("duration_h") if activity_stats else None,
        "activity_pace_min_km": activity_stats.get("pace_min_km") if activity_stats else None,
        "activity_vam": activity_stats.get("vam") if activity_stats else None,
        "activity_up_hours": activity_stats.get("up_hours") if activity_stats else None,
        "activity_down_hours": activity_stats.get("down_hours") if activity_stats else None,
    }
    days.append(day)
    _save_days(days)
    return day


# Funzioni legacy per la CLI e l'interfaccia esistente.

def add_trip(
    date: str,
    title: str,
    area: str,
    gain: Optional[int] = None,
    distance_km: Optional[float] = None,
    duration: Optional[str] = None,
    difficulty: Optional[str] = None,
    specs: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    track: Optional[List[List[float]]] = None,
    avalanche: Optional[int] = None,
    snow: Optional[str] = None,
    weather: Optional[str] = None,
    notes: Optional[str] = None,
) -> str:
    """Compatibilita: crea un percorso e una giornata."""
    init_data()
    route_description = specs or area
    route = upsert_route(
        name=title,
        description=route_description,
        difficulty=difficulty,
        track=track,
        route_id=None,
    )
    day = upsert_day(
        route_id=route["id"],
        date=date,
        snow_quality=snow,
        description=notes,
        weather=weather,
        avalanches_seen=str(avalanche) if avalanche is not None else None,
        day_id=None,
    )
    return day["id"]


def list_trips() -> List[Dict[str, Any]]:
    """Compatibilita: restituisce la lista delle giornate."""
    results: List[Dict[str, Any]] = []
    for day in _load_days():
        route = _get_route_by_id(day.get("route_id"))
        if not route:
            continue
        estimate_hours = _estimate_hours(route.get("distance_km"), route.get("gain"))
        results.append(
            {
                "slug": day.get("id"),
                "date": day.get("date"),
                "name": route.get("name"),
                "description": route.get("description"),
                "route_id": route.get("id"),
                "distance_km": route.get("distance_km"),
                "gain": route.get("gain"),
                "estimate_hours": estimate_hours,
            }
        )
    results.sort(key=lambda item: item.get("date", ""), reverse=True)
    return results


def read_trip(slug: str) -> Optional[Dict[str, Any]]:
    """Compatibilita: legge la giornata e unisce i dati del percorso."""
    day = get_day(slug)
    if not day:
        return None
    route = _get_route_by_id(day.get("route_id"))
    if not route:
        return None
    estimate_hours = _estimate_hours(route.get("distance_km"), route.get("gain"))
    result = {
        **route,
        "date": day.get("date"),
        "snow_quality": day.get("snow_quality"),
        "day_description": day.get("description"),
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
        "visibility": day.get("visibility"),
        "group_ids": day.get("group_ids", []),
        "people_ids": day.get("people_ids", []),
        "owner_id": day.get("owner_id"),
        "estimate_hours": estimate_hours,
        "slug": day.get("id"),
    }
    return result
