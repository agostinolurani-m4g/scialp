"""Gestione delle segnalazioni di valanghe.

Le valanghe sono memorizzate in un singolo file JSON (``avalanches.json``)
nella directory dei dati. Ogni segnalazione contiene un identificativo,
la posizione geografica, l'istante in cui è stata registrata e il numero
di conferme ricevute dagli altri utenti.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import get_base_dir


def _get_avalanches_path() -> Path:
    """Restituisce il percorso del file delle valanghe."""
    base_dir = get_base_dir()
    return base_dir / "avalanches.json"


def _load_raw() -> List[Dict[str, Any]]:
    path = _get_avalanches_path()
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


def _save_raw(data: List[Dict[str, Any]]) -> None:
    path = _get_avalanches_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _parse_iso_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value or not isinstance(value, str):
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def load_avalanches() -> List[Dict[str, Any]]:
    """Carica tutte le segnalazioni di valanghe dal file.

    Returns
    -------
    list
        Una lista di segnalazioni.
    """
    return _load_raw()


def add_avalanche(
    lat: float,
    lon: float,
    description: Optional[str] = None,
    size: Optional[str] = None,
    danger: Optional[int] = None,
    slope: Optional[float] = None,
    image: Optional[str] = None,
    created_by: Optional[str] = None,
) -> Dict[str, Any]:
    """Aggiunge una nuova segnalazione di valanga.

    Parameters
    ----------
    lat: float
        Latitudine della segnalazione.
    lon: float
        Longitudine della segnalazione.
    description: str, optional
        Descrizione testuale della valanga.
    size: str, optional
        Dimensione (es. "small", "medium", "large").
    danger: int, optional
        Grado di pericolo (1-5).
    slope: float, optional
        Pendenza stimata in gradi.
    image: str, optional
        Nome file dell'immagine salvata.

    Returns
    -------
    dict
        La segnalazione appena creata.
    """
    data = _load_raw()
    next_id = 1 + max((item.get("id", 0) for item in data), default=0)
    now_iso = datetime.now(timezone.utc).isoformat()
    record = {
        "id": next_id,
        "lat": lat,
        "lon": lon,
        "timestamp": now_iso,
        "confirmations": 1,
        "confirmation_user_ids": [created_by] if created_by else [],
        "created_by": created_by,
        "description": description,
        "size": size,
        "danger": danger,
        "slope": slope,
        "image": image,
    }
    data.append(record)
    _save_raw(data)
    return record


def confirm_avalanche(avalanche_id: int, user_id: str) -> Optional[Dict[str, Any]]:
    """Incrementa il contatore di conferme per la segnalazione indicata.

    Parameters
    ----------
    avalanche_id: int
        L'identificativo della segnalazione da confermare.

    Returns
    -------
    dict or None
        La segnalazione aggiornata, oppure ``None`` se non è stata trovata.
    """
    data = _load_raw()
    for item in data:
        if item.get("id") == avalanche_id:
            confirmation_users = item.get("confirmation_user_ids") or []
            if user_id in confirmation_users:
                item_copy = dict(item)
                item_copy["already_confirmed"] = True
                return item_copy
            confirmation_users.append(user_id)
            item["confirmation_user_ids"] = confirmation_users
            item["confirmations"] = int(item.get("confirmations", 0)) + 1
            _save_raw(data)
            item_copy = dict(item)
            item_copy["already_confirmed"] = False
            return item_copy
    return None


def filter_avalanches(start_iso: Optional[str] = None, end_iso: Optional[str] = None) -> List[Dict[str, Any]]:
    """Filtra le segnalazioni restituendo quelle comprese nell'intervallo temporale.

    Parameters
    ----------
    start_iso: str, optional
        Limite inferiore (incluso) come ISO 8601 (UTC). Se ``None`` nessun limite inferiore.
    end_iso: str, optional
        Limite superiore (incluso) come ISO 8601 (UTC). Se ``None`` nessun limite superiore.

    Returns
    -------
    list
        Una lista di segnalazioni nell'intervallo specificato, ordinate per data decrescente.
    """
    data = _load_raw()
    start_dt = _parse_iso_timestamp(start_iso)
    end_dt = _parse_iso_timestamp(end_iso)
    sortable: List[tuple[datetime, Dict[str, Any]]] = []
    for item in data:
        ts_dt = _parse_iso_timestamp(item.get("timestamp"))
        if not ts_dt:
            continue
        if start_dt and ts_dt < start_dt:
            continue
        if end_dt and ts_dt > end_dt:
            continue
        sortable.append((ts_dt, item))
    sortable.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in sortable]
