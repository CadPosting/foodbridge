"""FB-12 acceptance checks (FR-01: admin approval, server-side role checks)."""
from collections.abc import Iterator

import pytest
from flask import Flask
from flask.testing import FlaskClient
from werkzeug.security import generate_password_hash

from foodbridge import create_app
from foodbridge.auth import role_required
from foodbridge.db import get_db, init_db

from .conftest import register

PASSWORD = "correct-horse"


@pytest.fixture
def app(tmp_path) -> Iterator[Flask]:
    """Like the shared fixture, plus a donor-only test route and an admin user."""
    app = create_app({"TESTING": True, "TESTING_SKIP_CSRF": True,
                      "DATABASE": str(tmp_path / "test.db")})

    @app.route("/donor-only", methods=("POST",))
    @role_required("donor")
    def donor_only() -> str:
        return "posted"

    with app.app_context():
        init_db()
        get_db().execute(
            "INSERT INTO users (email, password_hash, org_name, role, status)"
            " VALUES ('admin@example.com', ?, 'Admin', 'admin', 'approved')",
            (generate_password_hash(PASSWORD),))
        get_db().commit()
    yield app


def login(client: FlaskClient, email: str) -> None:
    client.post("/auth/login", data={"email": email, "password": PASSWORD})


def user_id(app: Flask, email: str) -> int:
    with app.app_context():
        return get_db().execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()["id"]


def test_logged_out_user_is_sent_to_login(client: FlaskClient) -> None:
    resp = client.post("/donor-only")
    assert resp.status_code == 302 and "/auth/login" in resp.headers["Location"]


def test_pending_donor_cannot_post(client: FlaskClient) -> None:
    register(client)
    login(client, "bakery@example.com")
    assert client.post("/donor-only").status_code == 403


def test_admin_approves_then_donor_can_post(client: FlaskClient, app: Flask) -> None:
    register(client)
    uid = user_id(app, "bakery@example.com")
    login(client, "admin@example.com")
    assert client.post(f"/admin/accounts/{uid}/approve").status_code == 302
    client.post("/auth/logout")
    login(client, "bakery@example.com")
    assert client.post("/donor-only").data == b"posted"


def test_approved_charity_blocked_from_donor_route(client: FlaskClient, app: Flask) -> None:
    register(client, email="charity@example.com", role="charity")
    uid = user_id(app, "charity@example.com")
    login(client, "admin@example.com")
    client.post(f"/admin/accounts/{uid}/approve")
    client.post("/auth/logout")
    login(client, "charity@example.com")
    assert client.post("/donor-only").status_code == 403


def test_rejected_account_stays_blocked(client: FlaskClient, app: Flask) -> None:
    register(client)
    uid = user_id(app, "bakery@example.com")
    login(client, "admin@example.com")
    client.post(f"/admin/accounts/{uid}/reject")
    client.post("/auth/logout")
    login(client, "bakery@example.com")
    assert client.post("/donor-only").status_code == 403


def test_non_admin_cannot_open_or_use_admin_pages(client: FlaskClient, app: Flask) -> None:
    register(client)
    uid = user_id(app, "bakery@example.com")
    login(client, "bakery@example.com")
    assert client.get("/admin/accounts").status_code == 403
    assert client.post(f"/admin/accounts/{uid}/approve").status_code == 403


def test_admin_cannot_change_another_admin(client: FlaskClient, app: Flask) -> None:
    login(client, "admin@example.com")
    uid = user_id(app, "admin@example.com")
    assert client.post(f"/admin/accounts/{uid}/reject").status_code == 404


def test_unknown_decision_is_404(client: FlaskClient, app: Flask) -> None:
    register(client)
    uid = user_id(app, "bakery@example.com")
    login(client, "admin@example.com")
    assert client.post(f"/admin/accounts/{uid}/delete").status_code == 404


def test_admin_page_lists_pending_accounts(client: FlaskClient) -> None:
    register(client)
    login(client, "admin@example.com")
    page = client.get("/admin/accounts")
    assert page.status_code == 200 and b"bakery@example.com" in page.data


def test_create_admin_command(app: Flask) -> None:
    result = app.test_cli_runner().invoke(
        args=["auth", "create-admin", "boss@example.com", "--password", "long-enough-pw"])
    assert "created" in result.output
    with app.app_context():
        row = get_db().execute("SELECT role, status FROM users WHERE email = 'boss@example.com'").fetchone()
    assert (row["role"], row["status"]) == ("admin", "approved")
