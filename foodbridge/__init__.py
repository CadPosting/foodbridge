"""FoodBridge Flask application factory."""
import logging
import os
import secrets
from typing import Any

from flask import Flask, abort, render_template, request, session


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    """Build and configure the app (the 'application factory' pattern)."""
    # LEARN: a factory lets tests create a fresh app with a throwaway
    # database, instead of sharing one global app.
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        # LEARN: the secret key signs the session cookie. If it leaks, anyone
        # can forge a login. It comes from an environment variable; without
        # one we generate a random key, so sessions just reset on restart.
        SECRET_KEY=os.environ.get("FOODBRIDGE_SECRET_KEY") or secrets.token_hex(32),
        DATABASE=os.path.join(app.instance_path, "foodbridge.db"),
        SESSION_COOKIE_HTTPONLY=True,   # JavaScript cannot read the cookie (limits XSS damage)
        SESSION_COOKIE_SAMESITE="Lax",  # cookie not sent on cross-site POSTs (CSRF defence)
    )
    if test_config:
        app.config.update(test_config)
    os.makedirs(app.instance_path, exist_ok=True)
    logging.basicConfig(level=logging.INFO)

    @app.before_request
    def check_csrf() -> None:
        # LEARN: CSRF = another website tricking your browser into submitting
        # a form here while you're logged in. Every form carries a random token
        # stored in your session; a forged request can't know it.
        if request.method == "POST" and not app.config.get("TESTING_SKIP_CSRF"):
            token = session.get("csrf_token")
            if not token or not secrets.compare_digest(token, request.form.get("csrf_token", "")):
                abort(400, "Invalid or missing CSRF token")

    @app.context_processor
    def inject_csrf() -> dict[str, Any]:
        def csrf_token() -> str:
            if "csrf_token" not in session:
                session["csrf_token"] = secrets.token_hex(16)
            return session["csrf_token"]
        return {"csrf_token": csrf_token}

    from . import admin, auth, db, listings
    db.init_app(app)
    app.register_blueprint(auth.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(listings.bp)
    @app.route("/")
    def index() -> str:
        return render_template("index.html")

    return app
