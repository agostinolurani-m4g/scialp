"""Command line interface for scialpi-log.

Questo modulo definisce i comandi della riga di comando tramite la
biblioteca ``click``. Permette di inizializzare il repository dei dati,
aggiungere gite, elencarle e visualizzarne i dettagli.
"""

from __future__ import annotations

import json
import click

from .trip_manager import init_data, add_trip, list_trips, read_trip


@click.group()
def cli() -> None:
    """Comando principale di scialpi-log.

    Esegui ``scialpi --help`` per la lista delle sottocomandi.
    """
    pass


@cli.command()
def init() -> None:
    """Inizializza la struttura delle cartelle per i dati."""
    base = init_data()
    click.echo(f"Cartella dati inizializzata in: {base}")


@cli.command()
@click.option("--date", required=True, help="Data della gita (YYYY-MM-DD)")
@click.option("--title", required=True, help="Titolo della gita")
@click.option("--area", required=True, help="Area geografica")
@click.option("--gain", type=int, help="Dislivello positivo in metri")
@click.option("--distance-km", type=float, help="Distanza in chilometri")
@click.option("--duration", help="Durata della gita (es. 6:10)")
@click.option("--difficulty", help="Grado di difficoltÃ ")
@click.option("--specs", help="Specifiche del percorso")
@click.option("--avalanche", type=int, help="Grado di pericolo valanghe (1-5)")
@click.option("--snow", help="Condizioni neve")
@click.option("--weather", help="Condizioni meteo")
@click.option("--notes", help="Note testuali")
def add(**kwargs) -> None:
    """Aggiunge una nuova gita alle registrazioni."""
    slug = add_trip(**kwargs)
    click.echo(f"Gita salvata con identificativo: {slug}")


@cli.command(name="list")
def _list() -> None:
    """Elenca tutte le gite registrate."""
    trips = list_trips()
    if not trips:
        click.echo("Nessuna gita registrata.")
        return
    for trip in trips:
        date = trip.get("date") or "----"
        title = trip.get("name") or "(senza titolo)"
        area = trip.get("description") or ""
        slug = trip.get("slug")
        click.echo(f"{date} | {title} | {area} | {slug}")


@cli.command()
@click.argument("slug")
@click.option("--json", "as_json", is_flag=True, help="Mostra l'output in formato JSON")
def show(slug: str, as_json: bool) -> None:
    """Mostra i dettagli di una gita specificata dallo slug."""
    trip = read_trip(slug)
    if not trip:
        click.echo("Gita non trovata.")
        raise SystemExit(1)
    if as_json:
        click.echo(json.dumps(trip, indent=2, ensure_ascii=False))
    else:
        click.echo(f"Slug: {trip.get('slug')}")
        click.echo(f"Data: {trip.get('date')}")
        click.echo(f"Nome: {trip.get('name')}")
        click.echo(f"Descrizione: {trip.get('description')}")
        if trip.get("gain"):
            click.echo(f"Dislivello: {trip['gain']} m")
        if trip.get("distance_km"):
            click.echo(f"Distanza: {trip['distance_km']} km")
        if trip.get("duration"):
            click.echo(f"Durata: {trip['duration']}")
        if trip.get("difficulty"):
            click.echo(f"DifficoltÃ : {trip['difficulty']}")
        if trip.get("specs"):
            click.echo(f"Specifiche: {trip['specs']}")
        if trip.get("avalanches_seen"):
            click.echo(f"Valanghe viste: {trip['avalanches_seen']}")
        if trip.get("snow_quality"):
            click.echo(f"Neve: {trip['snow_quality']}")
        if trip.get("weather"):
            click.echo(f"Meteo: {trip['weather']}")
        if trip.get("day_description"):
            click.echo("\nNote:\n" + trip["notes"])


# Permette di eseguire il comando anche con ``python -m scialpi.cli``
if __name__ == "__main__":  # pragma: no cover
    cli()
