from collections.abc import Iterator

import pytest
from flask import Flask
from flask.testing import FlaskClient

from foodbridge import create_app
from foodbridge.db import init_db


@pytest.fixture
def app(tmp_path) -> Iterator[Flask]:
    # Each test gets its own throwaway database file.
    app = create_app({"TESTING": True, "TESTING_SKIP_CSRF": True,
                      "DATABASE": str(tmp_path / "test.db")})
    with app.app_context():
        init_db()
    yield app


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()


def register(client: FlaskClient, email: str = "bakery@example.com",
             password: str = "correct-horse", role: str = "donor"):
    return client.post("/auth/register", data={
        "email": email, "password": password, "org_name": "Test Bakery", "role": role})
