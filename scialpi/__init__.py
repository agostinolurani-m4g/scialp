"""Main package for scialpi-log.

Questo modulo espone le principali funzioni utili a interagire con i dati
delle gite e delle valanghe. La logica è suddivisa in moduli separati
per mantenerla semplice.
"""

from .trip_manager import init_data, add_trip, list_trips, read_trip
from .avalanche_manager import (
    load_avalanches,
    add_avalanche,
    confirm_avalanche,
    filter_avalanches,
)

__all__ = [
    "init_data",
    "add_trip",
    "list_trips",
    "read_trip",
    "load_avalanches",
    "add_avalanche",
    "confirm_avalanche",
    "filter_avalanches",
]