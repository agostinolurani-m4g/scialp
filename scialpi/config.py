"""Configurazione per il percorso dei dati.

Definisce funzioni per ottenere la directory base in cui vengono salvati i dati
delle gite e delle valanghe. Se l'utente definisce la variabile di
ambiente ``SCIALPI_LOG_HOME`` i dati verranno salvati lì; altrimenti
verranno utilizzate le sottodirectory della cartella ``data/`` nella
repository.
"""

from __future__ import annotations

import os
from pathlib import Path

# Nome della variabile d'ambiente che definisce la directory dei dati
DATA_ENV = "SCIALPI_LOG_HOME"
# Default directory rispetto alla quale saranno salvati i file
DEFAULT_BASE = Path(__file__).resolve().parent.parent / "data"


def get_base_dir() -> Path:
    """Restituisce la directory base dei dati.

    Se la variabile d'ambiente ``SCIALPI_LOG_HOME`` è impostata, questa
    directory verrà utilizzata. Altrimenti viene ritornata la directory
    ``data/`` relativa alla posizione della repository.

    Returns
    -------
    pathlib.Path
        Il percorso alla directory base dei dati.
    """
    env_value = os.environ.get(DATA_ENV)
    if env_value:
        return Path(env_value)
    return DEFAULT_BASE
