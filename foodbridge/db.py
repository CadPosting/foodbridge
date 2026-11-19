"""SQLite connection handling, one connection per request."""
import sqlite3

import click
from flask import Flask, current_app, g


def get_db() -> sqlite3.Connection:
    """Return this request's database connection, opening it on first use."""
    # LEARN: `g` is Flask's per-request storage. Keeping the connection there
    # (instead of a module-level global) means each request gets its own
    # connection and it is closed when the request ends.
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row  # rows behave like dicts: row["email"]
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc: BaseException | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    """Create the tables from schema.sql (wipes existing data)."""
    with current_app.open_resource("schema.sql") as f:
        get_db().executescript(f.read().decode("utf-8"))


@click.command("init-db")
def init_db_command() -> None:
    """Flask CLI: `flask --app foodbridge init-db`."""
    init_db()
    click.echo("Initialised the database.")


def init_app(app: Flask) -> None:
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
