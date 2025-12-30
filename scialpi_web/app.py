"""Entry point for the Flask web application."""

from __future__ import annotations

import os

from flask import Flask

from .routes import bp


def create_app() -> Flask:
    """Crea e configura una nuova applicazione Flask."""
    app = Flask(__name__)
    app.secret_key = os.environ.get("SCIALPI_SECRET_KEY", "scialpi-dev-key")
    # Registriamo il blueprint che contiene tutte le route
    app.register_blueprint(bp)
    return app


def main() -> None:
    """Punto di ingresso quando eseguito come comando di console."""
    app = create_app()
    # Esegui il server sul loopback per evitare binding su tutte le interfacce
    app.run(host="127.0.0.1", port=8000, debug=False)


if __name__ == "__main__":
    main()
