import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import server


# A Supabase /auth/v1/user response for a signed-in shopkeeper.
SUPABASE_USER_PAYLOAD = {
    'id': '11111111-2222-3333-4444-555555555555',
    'email': 'alice@example.com',
    'user_metadata': {
        'full_name': 'Alice Example',
        'avatar_url': 'https://example.com/avatar.png',
    },
}


def stub_supabase(monkeypatch, status_code, payload):
    """Stand in for the outbound GET {SUPABASE_URL}/auth/v1/user.

    Authentication is now a call to Supabase rather than a Mongo lookup, so the
    tests intercept that call instead of seeding a session collection.
    """
    class Response:
        def __init__(self):
            self.status_code = status_code

        def json(self):
            if isinstance(payload, Exception):
                raise payload
            return payload

    async def fake_get(self, url, headers=None, **kwargs):
        return Response()

    monkeypatch.setattr('httpx.AsyncClient.get', fake_get)


@pytest.fixture
def client(monkeypatch):
    # The dependency reads these as module globals at call time, so setting them
    # here keeps the suite independent of whatever is in backend/.env.
    monkeypatch.setattr(server, 'SUPABASE_URL', 'https://example.supabase.co')
    monkeypatch.setattr(server, 'SUPABASE_ANON_KEY', 'test-anon-key')

    # Default: Supabase rejects the token. Tests that need a valid one re-stub.
    stub_supabase(monkeypatch, 401, {'msg': 'invalid claim: missing sub claim'})
    return TestClient(server.app)


class TestSupabaseTokenAuth:
    def test_valid_token_is_accepted(self, client, monkeypatch):
        stub_supabase(monkeypatch, 200, SUPABASE_USER_PAYLOAD)
        response = client.get('/api/auth/me', headers={'Authorization': 'Bearer good-token'})
        assert response.status_code == 200
        body = response.json()['user']
        assert body['email'] == 'alice@example.com'
        assert body['user_id'] == SUPABASE_USER_PAYLOAD['id']
        assert body['name'] == 'Alice Example'

    def test_token_without_an_id_is_rejected(self, client, monkeypatch):
        # A 200 with no `id` is not a usable identity; it must not authenticate.
        stub_supabase(monkeypatch, 200, {'email': 'nobody@example.com'})
        response = client.get('/api/auth/me', headers={'Authorization': 'Bearer odd-token'})
        assert response.status_code == 401

    def test_non_dict_body_is_not_treated_as_a_user(self, client, monkeypatch):
        stub_supabase(monkeypatch, 200, ['not', 'a', 'user'])
        response = client.get('/api/auth/me', headers={'Authorization': 'Bearer odd-token'})
        assert response.status_code == 502

    def test_non_json_body_is_reported_as_upstream_failure(self, client, monkeypatch):
        stub_supabase(monkeypatch, 200, ValueError('not json'))
        response = client.get('/api/auth/me', headers={'Authorization': 'Bearer odd-token'})
        assert response.status_code == 502

    def test_unreachable_supabase_is_503_not_401(self, client, monkeypatch):
        # "We could not check" must be distinguishable from "your token is bad",
        # otherwise a network blip signs every user out of the app.
        async def boom(self, url, headers=None, **kwargs):
            raise OSError('connection refused')

        monkeypatch.setattr('httpx.AsyncClient.get', boom)
        response = client.get('/api/auth/me', headers={'Authorization': 'Bearer good-token'})
        assert response.status_code == 503

    def test_unconfigured_server_is_500_not_401(self, client, monkeypatch):
        monkeypatch.setattr(server, 'SUPABASE_URL', '')
        monkeypatch.setattr(server, 'SUPABASE_ANON_KEY', '')
        response = client.get('/api/auth/me', headers={'Authorization': 'Bearer anything'})
        assert response.status_code == 500


class TestAuthMe:
    def test_auth_me_no_header(self, client):
        response = client.get('/api/auth/me')
        assert response.status_code == 401

    def test_auth_me_garbage_token(self, client):
        response = client.get('/api/auth/me', headers={'Authorization': '******'})
        assert response.status_code == 401

    def test_auth_me_malformed_header(self, client):
        response = client.get('/api/auth/me', headers={'Authorization': 'garbage_token'})
        assert response.status_code == 401

    def test_auth_me_empty_bearer(self, client):
        response = client.get('/api/auth/me', headers={'Authorization': 'Bearer '})
        assert response.status_code == 401

    def test_auth_me_token_supabase_rejects(self, client):
        response = client.get('/api/auth/me', headers={'Authorization': 'Bearer bogus'})
        assert response.status_code == 401


class TestProtectedRoutes:
    """Every /api route that touches data must require a token. These were open
    to the internet before the audit."""

    def test_voice_assist_requires_auth(self, client):
        response = client.post('/api/voice/assist', json={'transcript': 'hello'})
        assert response.status_code == 401

    def test_voice_transcribe_requires_auth(self, client):
        response = client.post('/api/voice/transcribe', files={'file': ('a.m4a', b'x', 'audio/mp4')})
        assert response.status_code == 401


class TestHealthCheck:
    def test_root_endpoint(self, client):
        response = client.get('/api/')
        assert response.status_code == 200
        assert response.json().get('message') == 'Hello World'
