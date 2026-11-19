"""FB-03: registration, login and logout (FR-01)."""
import functools
import logging
import sqlite3
from typing import Any, Callable

from flask import (Blueprint, flash, g, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db

bp = Blueprint("auth", __name__, url_prefix="/auth")
log = logging.getLogger(__name__)

# Admins are created by the team, never through the public form.
SELF_REGISTER_ROLES = ("donor", "charity")
MIN_PASSWORD_LENGTH = 8


@bp.route("/register", methods=("GET", "POST"))
def register() -> Any:
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        org_name = request.form.get("org_name", "").strip()
        role = request.form.get("role", "")

        error = None
        if not email or "@" not in email:
            error = "A valid email is required."
        elif len(password) < MIN_PASSWORD_LENGTH:
            error = f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        elif not org_name:
            error = "Organisation name is required."
        elif role not in SELF_REGISTER_ROLES:
            # LEARN: never trust form values. Without this check someone could
            # edit the HTML and register themselves as 'admin'.
            error = "Choose donor or charity."

        if error is None:
            try:
                # LEARN: '?' placeholders make SQLite treat input as data, never
                # as SQL, which blocks SQL injection.
                # generate_password_hash salts and hashes the password (scrypt),
                # so the database never stores the real password.
                get_db().execute(
                    "INSERT INTO users (email, password_hash, org_name, role) VALUES (?, ?, ?, ?)",
                    (email, generate_password_hash(password), org_name, role),
                )
                get_db().commit()
            except sqlite3.IntegrityError:
                error = "That email is already registered."
            else:
                log.info("New %s account registered", role)
                flash("Account created. An administrator must approve it before you can post or reserve.")
                return redirect(url_for("auth.login"))
        flash(error)
    return render_template("auth/register.html")


@bp.route("/login", methods=("GET", "POST"))
def login() -> Any:
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        # LEARN: same message for "no such email" and "wrong password", so an
        # attacker can't use the form to find out which emails are registered.
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Incorrect email or password.")
            return render_template("auth/login.html")

        # LEARN: clear the old session before logging in. This stops
        # 'session fixation', where an attacker plants a session id beforehand.
        session.clear()
        session["user_id"] = user["id"]
        return redirect(url_for("index"))
    return render_template("auth/login.html")


@bp.route("/logout", methods=("POST",))
def logout() -> Any:
    # LEARN: logout is POST, not a link, so another site can't log you out
    # just by embedding an image pointing at /auth/logout.
    session.clear()
    return redirect(url_for("index"))


@bp.before_app_request
def load_logged_in_user() -> None:
    """Make the current user available as g.user on every request."""
    user_id = session.get("user_id")
    g.user = None if user_id is None else get_db().execute(
        "SELECT id, email, org_name, role, status FROM users WHERE id = ?", (user_id,)
    ).fetchone()


def login_required(view: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator for routes that need a logged-in user (FB-12 builds role checks on this)."""
    @functools.wraps(view)
    def wrapped(**kwargs: Any) -> Any:
        if g.user is None:
            return redirect(url_for("auth.login"))
        return view(**kwargs)
    return wrapped
