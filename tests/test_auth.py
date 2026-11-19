"""FB-03 acceptance checks (FR-01: register and log in, hashed passwords)."""
from flask import Flask
from flask.testing import FlaskClient

from foodbridge import create_app
from foodbridge.db import get_db

from .conftest import register


def test_register_stores_hashed_password_and_pending_status(client: FlaskClient, app: Flask) -> None:
    assert register(client).status_code == 302
    with app.app_context():
        user = get_db().execute("SELECT * FROM users WHERE email = 'bakery@example.com'").fetchone()
    assert user["password_hash"] != "correct-horse"
    assert user["status"] == "pending"


def test_cannot_self_register_as_admin(client: FlaskClient, app: Flask) -> None:
    register(client, role="admin")
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0


def test_duplicate_email_rejected(client: FlaskClient) -> None:
    register(client)
    assert b"already registered" in register(client).data


def test_short_password_rejected(client: FlaskClient) -> None:
    assert b"at least 8" in register(client, password="short").data


def test_login_and_logout(client: FlaskClient) -> None:
    register(client)
    resp = client.post("/auth/login", data={"email": "BAKERY@example.com", "password": "correct-horse"})
    assert resp.status_code == 302
    with client.session_transaction() as s:
        assert "user_id" in s
    client.post("/auth/logout")
    with client.session_transaction() as s:
        assert "user_id" not in s


def test_wrong_password_and_unknown_email_give_same_message(client: FlaskClient) -> None:
    register(client)
    wrong = client.post("/auth/login", data={"email": "bakery@example.com", "password": "nope-nope"})
    unknown = client.post("/auth/login", data={"email": "nobody@example.com", "password": "nope-nope"})
    assert b"Incorrect email or password." in wrong.data
    assert b"Incorrect email or password." in unknown.data


def test_post_without_csrf_token_is_rejected(tmp_path) -> None:
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "t.db")})
    resp = app.test_client().post("/auth/login", data={"email": "a@b.c", "password": "x"})
    assert resp.status_code == 400
