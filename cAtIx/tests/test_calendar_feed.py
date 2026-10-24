"""The personal calendar GET /users/my-calendar.ics (worker/feed.py): the InNoHassle token of the user opens their calendar, and
no other token does. The tokens are signed here by a key of our own, put in place of InNoHassle's keys."""

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from catix import personal_calendar
from catix.worker import feed

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class Keys:
    def get_signing_keys(self):
        return [jwt.PyJWK.from_dict({**jwt.algorithms.RSAAlgorithm.to_jwk(KEY.public_key(), as_dict=True), "use": "sig", "kid": "public"})]


def token(key=KEY, **claims) -> str:
    """Like InNoHassle's: RS256 and no `kid` in the header."""
    return jwt.encode({"uid": "u1", "scope": "me", "exp": int(time.time()) + 3600, **claims}, key, algorithm="RS256")


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(feed, "_keys", Keys())
    monkeypatch.setattr(personal_calendar, "ics", lambda user_key: f"BEGIN:VCALENDAR\r\nX-USER:{user_key}\r\nEND:VCALENDAR\r\n")
    return TestClient(feed.app)


def get(client, bearer: str | None):
    return client.get("/users/my-calendar.ics", headers={"Authorization": f"Bearer {bearer}"} if bearer else {})


def test_the_token_of_a_user_opens_their_calendar(client):
    resp = get(client, token(telegram_id=42))
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/calendar")
    assert "X-USER:tg:42" in resp.text


def test_no_token_or_a_foreign_signature_or_an_expired_token_opens_nothing(client):
    assert get(client, None).status_code in (401, 403)
    assert get(client, token(OTHER, telegram_id=42)).status_code == 401
    assert get(client, token(telegram_id=42, exp=int(time.time()) - 10)).status_code == 401
    assert get(client, "not-a-jwt").status_code == 401


def test_an_account_without_telegram_has_no_calendar(client):
    assert get(client, token()).status_code == 403
