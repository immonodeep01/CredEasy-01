import asyncio
import os
import sys
from pathlib import Path

import httpx
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


def test_compact_voice_context_preserves_answer_data_and_drops_internal_metadata():
    context = {
        'shopName': 'Shop',
        'language': 'en',
        'totalReceivable': 125,
        'parties': [{
            'id': 'internal-party-id',
            'name': 'Ramesh',
            'phone': '9876543210',
            'type': 'CUSTOMER',
            'balance': 125,
            'photoUri': 'private-image-path',
        }],
        'recentTransactions': [{
            'id': 'internal-transaction-id',
            'party': 'Ramesh',
            'amount': 125,
            'kind': 'GAVE',
            'date': '2026-10-06',
            'photoUri': 'private-image-path',
        }],
        'inventory': [{
            'id': 'internal-item-id',
            'name': 'Rice',
            'currentStock': 5,
            'unit': 'kg',
            'price': 40,
            'sku': 'RICE-1',
            'createdAt': '2026-10-06',
            'photoUri': 'private-image-path',
        }],
        'inventoryMovements': [{
            'id': 'internal-movement-id',
            'itemId': 'internal-item-id',
            'itemName': 'Rice',
            'type': 'sale',
            'quantityChange': -1,
            'quantityAfter': 5,
            'createdAt': '2026-10-06',
            'syncStatus': 'SYNCED',
        }],
        'unrecognized': 'not sent to the model',
    }

    result = server.compact_voice_context(context)

    assert result['shopName'] == 'Shop'
    assert result['totalReceivable'] == 125
    assert result['parties'] == [{
        'name': 'Ramesh', 'phone': '9876543210', 'type': 'CUSTOMER', 'balance': 125,
    }]
    assert result['recentTransactions'] == [{
        'party': 'Ramesh', 'amount': 125, 'kind': 'GAVE', 'date': '2026-10-06',
    }]
    assert result['inventory'] == [{
        'name': 'Rice', 'currentStock': 5, 'unit': 'kg', 'price': 40, 'sku': 'RICE-1',
    }]
    assert result['inventoryMovements'] == [{
        'itemName': 'Rice', 'type': 'sale', 'quantityChange': -1,
        'quantityAfter': 5, 'createdAt': '2026-10-06',
    }]
    assert 'unrecognized' not in result


@pytest.fixture
def client(monkeypatch):
    # The dependency reads these as module globals at call time, so setting them
    # here keeps the suite independent of whatever is in backend/.env.
    server.USER_RATE_LIMIT_BUCKETS.clear()
    monkeypatch.setattr(server, 'SUPABASE_URL', 'https://example.supabase.co')
    monkeypatch.setattr(server, 'SUPABASE_ANON_KEY', 'test-anon-key')
    monkeypatch.delenv('GOOGLE_CLOUD_PROJECT', raising=False)
    monkeypatch.delenv('GCLOUD_PROJECT', raising=False)

    # Default: Supabase rejects the token. Tests that need a valid one re-stub.
    stub_supabase(monkeypatch, 401, {'msg': 'invalid claim: missing sub claim'})
    previous_httpx_client = getattr(server.app.state, 'httpx_client', None)
    test_httpx_client = httpx.AsyncClient()
    server.app.state.httpx_client = test_httpx_client
    test_client = TestClient(server.app)

    async def allow_voice_limit(*args, **kwargs):
        return None

    monkeypatch.setattr(server, 'enforce_shared_voice_rate_limit', allow_voice_limit)
    yield test_client
    asyncio.run(test_httpx_client.aclose())
    if previous_httpx_client is None:
        del server.app.state.httpx_client
    else:
        server.app.state.httpx_client = previous_httpx_client
    test_client.close()


class TestSupabaseTokenAuth:
    def test_valid_token_is_accepted(self, client, monkeypatch):
        stub_supabase(monkeypatch, 200, SUPABASE_USER_PAYLOAD)
        response = client.get('/api/auth/me', headers={'Authorization': 'Bearer good-token'})
        assert response.status_code == 200, response.text
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


def test_voice_provider_circuit_opens_after_consecutive_failures():
    provider = 'test-provider'
    server.VOICE_PROVIDER_CIRCUITS.pop(provider, None)

    for _ in range(server.VOICE_CIRCUIT_FAILURE_THRESHOLD):
        server.record_voice_provider_failure(provider)

    with pytest.raises(server.HTTPException) as error:
        server.check_voice_provider_circuit(provider)
    assert error.value.status_code == 503

    server.record_voice_provider_success(provider)
    server.check_voice_provider_circuit(provider)


def test_shared_voice_rate_limit_rejects_when_database_quota_is_exhausted(monkeypatch):
    server.USER_RATE_LIMIT_BUCKETS.clear()
    monkeypatch.setattr(server, 'SUPABASE_URL', 'https://example.supabase.co')
    monkeypatch.setattr(server, 'SUPABASE_ANON_KEY', 'test-anon-key')
    results = iter([True, False])

    class Response:
        status_code = 200

        def json(self):
            return next(results)

    class SupabaseHttpClient:
        async def post(self, *args, **kwargs):
            return Response()

    async def check():
        await server.enforce_shared_voice_rate_limit(
            'user-1',
            'Bearer test-token',
            SupabaseHttpClient(),
        )
        with pytest.raises(server.HTTPException) as error:
            await server.enforce_shared_voice_rate_limit(
                'user-1',
                'Bearer test-token',
                SupabaseHttpClient(),
            )
        assert error.value.status_code == 429

    asyncio.run(check())


def test_legacy_transaction_list_is_page_limited(client, monkeypatch):
    monkeypatch.setitem(
        client.app.dependency_overrides,
        server.get_authenticated_user,
        lambda: {'user_id': SUPABASE_USER_PAYLOAD['id']},
    )
    requests = []

    class Response:
        def __init__(self, payload):
            self.status_code = 200
            self.payload = payload

        def json(self):
            return self.payload

    class SupabaseHttpClient:
        async def get(self, url, *, headers, params=None, **kwargs):
            requests.append((url, params))
            return Response([{'id': 'tx-1'}])

    server.app.state.httpx_client = SupabaseHttpClient()
    response = client.get(
        '/api/transactions?page_size=25&offset=50',
        headers={'Authorization': 'Bearer pagination-test-token'},
    )

    assert response.status_code == 200, response.json()
    assert response.json()['transactions'] == [{'id': 'tx-1'}]
    assert response.json()['next_offset'] is None
    assert requests[0][1]['limit'] == 25
    assert requests[0][1]['offset'] == 50


def test_legacy_transaction_list_rejects_oversized_pages(client, monkeypatch):
    monkeypatch.setitem(
        client.app.dependency_overrides,
        server.get_authenticated_user,
        lambda: {'user_id': SUPABASE_USER_PAYLOAD['id']},
    )
    response = client.get(
        '/api/transactions?page_size=51',
        headers={'Authorization': '******'},
    )

    assert response.status_code == 422

    def test_auth_me_malformed_header(self, client):
        response = client.get('/api/auth/me', headers={'Authorization': 'garbage_token'})
        assert response.status_code == 401

    def test_auth_me_empty_bearer(self, client):
        response = client.get('/api/auth/me', headers={'Authorization': 'Bearer '})
        assert response.status_code == 401

    def test_auth_me_token_supabase_rejects(self, client):
        response = client.get('/api/auth/me', headers={'Authorization': 'Bearer bogus'})
        assert response.status_code == 401


class TestLedgerWritesUseCallerIdentity:
    def test_party_and_transaction_upserts_forward_the_verified_user_token(
        self, client, monkeypatch
    ):
        stub_supabase(monkeypatch, 200, SUPABASE_USER_PAYLOAD)
        captured = []

        class Response:
            status_code = 201
            text = ''

        async def fake_post(self, url, headers=None, json=None, **kwargs):
            captured.append((url, headers, json))
            return Response()

        monkeypatch.setattr('httpx.AsyncClient.post', fake_post)
        request_headers = {'Authorization': 'Bearer verified-user-token'}

        party_response = client.post(
            '/api/parties',
            headers=request_headers,
            json={
                'id': 'party-1',
                'name': 'Alice Store',
                'phone': '',
                'type': 'CUSTOMER',
                'opening_balance': 0,
                'created_at': '',
            },
        )
        transaction_response = client.post(
            '/api/transactions',
            headers=request_headers,
            json={
                'id': 'transaction-1',
                'party_id': 'party-1',
                'amount': 10,
                'type': 'DEBIT',
                'note': '',
                'date': '2026-10-06T00:00:00Z',
                'sync_status': 'SYNCED',
            },
        )

        assert party_response.status_code == 200
        assert transaction_response.status_code == 200
        assert len(captured) == 2
        for _, headers, row in captured:
            assert headers['Authorization'] == 'Bearer verified-user-token'
            assert headers['apikey'] == 'test-anon-key'
            assert row['user_id'] == SUPABASE_USER_PAYLOAD['id']


class TestProtectedRoutes:
    """Every /api route that touches data must require a token. These were open
    to the internet before the audit."""

    def test_voice_assist_requires_auth(self, client):
        response = client.post("/api/voice/assist", json={"transcript": "hello"})
        assert response.status_code == 401

    def test_voice_transcribe_requires_auth(self, client):
        response = client.post(
            "/api/voice/transcribe", files={"file": ("a.m4a", b"x", "audio/mp4")}
        )
        assert response.status_code == 401

    def test_voice_transcribe_streams_interim_and_final_google_results(
        self, client, monkeypatch
    ):
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")

        async def authenticate(authorization):
            if authorization != "Bearer test-token":
                raise server.HTTPException(status_code=401)
            return {"user_id": SUPABASE_USER_PAYLOAD["id"]}

        monkeypatch.setattr(server, "get_authenticated_user", authenticate)
        captured = []

        class FakeSpeechClient:
            async def streaming_recognize(self, requests, timeout):
                async def responses():
                    async for request in requests:
                        captured.append(request)
                        if request.get("audio"):
                            yield type(
                                "Response",
                                (),
                                {
                                    "results": [
                                        type(
                                            "Result",
                                            (),
                                            {
                                                "alternatives": [
                                                    type(
                                                        "Alternative",
                                                        (),
                                                        {"transcript": "Ramesh owes"},
                                                    )()
                                                ],
                                                "is_final": False,
                                                    "language_code": "hi-IN",
                                            },
                                        )()
                                    ]
                                },
                            )()
                    yield type(
                        "Response",
                        (),
                        {
                            "results": [
                                type(
                                    "Result",
                                    (),
                                    {
                                        "alternatives": [
                                            type(
                                                "Alternative",
                                                (),
                                                {
                                                    "transcript": "Ramesh owes five hundred rupees."
                                                },
                                            )()
                                        ],
                                        "is_final": True,
                                            "language_code": "hi-IN",
                                    },
                                )()
                            ]
                        },
                    )()

                return responses()

        monkeypatch.setattr(
            server, "get_google_speech_client", lambda: FakeSpeechClient()
        )

        with client.websocket_connect("/api/voice/transcribe/stream") as websocket:
            websocket.send_json({"authorization": "Bearer test-token"})
            assert websocket.receive_json()["type"] == "ready"
            websocket.send_bytes(b"\x00" * 3200)
            interim = websocket.receive_json()
            assert interim == {
                "type": "transcript",
                "final": "",
                "interim": "Ramesh owes",
                "language": "hi-IN",
            }
            websocket.send_json({"type": "finish"})
            final = websocket.receive_json()
            assert final["type"] == "transcript"
            complete = websocket.receive_json()
            assert complete == {
                "type": "complete",
                "text": "Ramesh owes five hundred rupees.",
                "language": "hi-IN",
            }

        assert captured[0]["recognizer"] == (
            "projects/test-project/locations/asia-southeast1/recognizers/_"
        )
        assert captured[0]["streaming_config"]["config"]["model"] == "chirp_3"
        assert (
            captured[0]["streaming_config"]["config"]["explicit_decoding_config"][
                "sample_rate_hertz"
            ]
            == 16000
        )
        assert (
            captured[0]["streaming_config"]["streaming_features"]["interim_results"]
            is True
        )
        assert captured[1]["audio"] == b"\x00" * 3200

    def test_voice_transcribe_stream_rejects_missing_project(self, client, monkeypatch):
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
        monkeypatch.delenv("GCLOUD_PROJECT", raising=False)

        async def authenticate(authorization):
            if authorization != "Bearer test-token":
                raise server.HTTPException(status_code=401)
            return {"user_id": SUPABASE_USER_PAYLOAD["id"]}

        monkeypatch.setattr(server, "get_authenticated_user", authenticate)
        with client.websocket_connect("/api/voice/transcribe/stream") as websocket:
            websocket.send_json({"authorization": "Bearer test-token"})
            error = websocket.receive_json()

        assert error == {
            "type": "error",
            "code": "GOOGLE_CLOUD_NOT_CONFIGURED",
            "detail": "Google Cloud Speech-to-Text is not configured on the server",
        }

    def test_voice_transcribe_stream_bounds_slow_finalization(self, client, monkeypatch):
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
        monkeypatch.setattr(server, "STREAM_FINALIZE_TIMEOUT_SECONDS", 0.01)

        async def authenticate(authorization):
            return {"user_id": SUPABASE_USER_PAYLOAD["id"]}

        class FakeSpeechClient:
            async def streaming_recognize(self, requests, timeout):
                async def responses():
                    await asyncio.Event().wait()
                    yield None

                return responses()

        monkeypatch.setattr(server, "get_authenticated_user", authenticate)
        monkeypatch.setattr(server, "get_google_speech_client", lambda: FakeSpeechClient())

        with client.websocket_connect("/api/voice/transcribe/stream") as websocket:
            websocket.send_json({"authorization": "******"})
            assert websocket.receive_json()["type"] == "ready"
            websocket.send_json({"type": "finish"})
            assert websocket.receive_json() == {"type": "complete", "text": ""}

    def test_voice_transcribe_uses_google_cloud_speech_v2(self, client, monkeypatch):
        monkeypatch.setitem(
            client.app.dependency_overrides,
            server.get_authenticated_user,
            lambda: {"user_id": SUPABASE_USER_PAYLOAD["id"]},
        )
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
        captured = {}

        class FakeSpeechClient:
            async def recognize(self, request):
                captured.update(request)
                alternatives = [
                    type("Alternative", (), {"transcript": "Add five hundred"})(),
                    type("Alternative", (), {"transcript": "ignored alternative"})(),
                ]
                first_result = type(
                    "Result",
                    (),
                    {"alternatives": alternatives, "language_code": "en-IN"},
                )()
                second_result = type(
                    "Result",
                    (),
                    {
                        "alternatives": [
                            type(
                                "Alternative", (), {"transcript": "rupees to Ramesh."}
                            )()
                        ],
                        "language_code": "en-IN",
                    },
                )()
                return type(
                    "RecognizeResponse", (), {"results": [first_result, second_result]}
                )()

        monkeypatch.setattr(
            server, "get_google_speech_client", lambda: FakeSpeechClient()
        )

        response = client.post(
            "/api/voice/transcribe",
            files={"file": ("speech.wav", b"audio-bytes", "audio/wav")},
        )

        assert response.status_code == 200
        assert response.json()["text"] == "Add five hundred rupees to Ramesh."
        assert response.json()["language"] == "en-IN"
        assert (
            captured["recognizer"]
            == "projects/test-project/locations/asia-southeast1/recognizers/_"
        )
        assert captured["config"]["auto_decoding_config"] == {}
        assert captured["config"]["language_codes"] == ["en-IN", "hi-IN"]
        assert captured["config"]["model"] == "chirp_3"
        assert captured["content"] == b"audio-bytes"

    def test_voice_transcribe_uses_configured_google_speech_location(
        self, client, monkeypatch
    ):
        monkeypatch.setitem(
            client.app.dependency_overrides,
            server.get_authenticated_user,
            lambda: {"user_id": SUPABASE_USER_PAYLOAD["id"]},
        )
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
        monkeypatch.setenv("GOOGLE_CLOUD_SPEECH_LOCATION", "us")
        captured = {}

        class FakeSpeechClient:
            async def recognize(self, request):
                captured.update(request)
                return type("RecognizeResponse", (), {"results": []})()

        monkeypatch.setattr(
            server, "get_google_speech_client", lambda: FakeSpeechClient()
        )

        response = client.post(
            "/api/voice/transcribe",
            files={"file": ("speech.wav", b"audio-bytes", "audio/wav")},
        )

        assert response.status_code == 200
        assert (
            captured["recognizer"]
            == "projects/test-project/locations/us/recognizers/_"
        )

    def test_voice_transcribe_does_not_fallback_after_configured_google_fails(
        self, client, monkeypatch
    ):
        monkeypatch.setitem(
            client.app.dependency_overrides,
            server.get_authenticated_user,
            lambda: {"user_id": SUPABASE_USER_PAYLOAD["id"]},
        )
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")

        class FakeSpeechClient:
            async def recognize(self, request):
                raise RuntimeError("provider unavailable")

        monkeypatch.setattr(
            server, "get_google_speech_client", lambda: FakeSpeechClient()
        )
        monkeypatch.setattr(
            server,
            "get_groq_api_key",
            lambda: (_ for _ in ()).throw(AssertionError("must not fall back to Groq")),
        )

        response = client.post(
            "/api/voice/transcribe",
            files={"file": ("recording.m4a", b"audio-bytes", "audio/mp4")},
        )

        assert response.status_code == 502

    def test_voice_transcribe_uses_legacy_provider_until_google_is_configured(
        self, client, monkeypatch
    ):
        monkeypatch.setitem(
            client.app.dependency_overrides,
            server.get_authenticated_user,
            lambda: {"user_id": SUPABASE_USER_PAYLOAD["id"]},
        )
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
        monkeypatch.delenv("GCLOUD_PROJECT", raising=False)
        monkeypatch.setattr(server, "get_groq_api_key", lambda: "test-groq-key")

        class FakeTranscriptions:
            async def create(self, **kwargs):
                assert kwargs["model"] == "whisper-large-v3-turbo"
                assert kwargs["file"] == ("recording.m4a", b"audio-bytes")
                return type("Transcription", (), {"text": "Add five hundred rupees."})()

        fake_client = type(
            "FakeGroqClient",
            (),
            {"audio": type("Audio", (), {"transcriptions": FakeTranscriptions()})()},
        )()
        monkeypatch.setattr(server, "get_groq_client", lambda: fake_client)

        response = client.post(
            "/api/voice/transcribe",
            files={"file": ("recording.m4a", b"audio-bytes", "audio/mp4")},
        )

        assert response.status_code == 200
        assert response.json()["text"] == "Add five hundred rupees."

    def test_voice_speak_returns_async_sdk_audio_content(self, client, monkeypatch):
        stub_supabase(monkeypatch, 200, SUPABASE_USER_PAYLOAD)
        monkeypatch.delenv('GOOGLE_CLOUD_PROJECT', raising=False)
        monkeypatch.delenv('GCLOUD_PROJECT', raising=False)
        monkeypatch.setattr(server, 'get_sarvam_api_key', lambda: None)
        monkeypatch.setattr(server, 'get_openai_api_key', lambda: 'test-openai-key')

        audio_bytes = b'\x00' * 256

        class FakeSpeech:
            async def create(self, **kwargs):
                assert kwargs['input'] == 'Hello there.'
                return type('AudioResponse', (), {'content': audio_bytes})()

        fake_client = type(
            'FakeOpenAIClient',
            (),
            {'audio': type('Audio', (), {'speech': FakeSpeech()})()},
        )()
        monkeypatch.setattr(server, 'get_openai_client', lambda: fake_client)

        response = client.post(
            '/api/voice/speak',
            headers={'Authorization': 'Bearer test-token'},
            json={'text': 'Hello there.', 'lang': 'en'},
        )

        assert response.status_code == 200
        assert response.headers['content-type'].startswith('audio/mpeg')
        assert response.content == audio_bytes

    def test_voice_speak_uses_sarvam_bulbul_and_maps_hindi_locale(self, client, monkeypatch):
        import base64

        monkeypatch.delenv('GOOGLE_CLOUD_PROJECT', raising=False)
        monkeypatch.delenv('GCLOUD_PROJECT', raising=False)
        monkeypatch.setitem(
            client.app.dependency_overrides,
            server.get_authenticated_user,
            lambda: {"user_id": SUPABASE_USER_PAYLOAD["id"]},
        )
        monkeypatch.setattr(server, 'get_sarvam_api_key', lambda: 'test-sarvam-key')
        monkeypatch.delenv('SARVAM_TTS_MODEL', raising=False)
        audio_bytes = b'\x01' * 256
        captured = {}

        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {"audios": [base64.b64encode(audio_bytes).decode("ascii")]}

        async def fake_post(self, url, headers=None, json=None, **kwargs):
            captured.update(url=url, headers=headers, body=json)
            return Response()

        monkeypatch.setattr('httpx.AsyncClient.post', fake_post)
        response = client.post(
            '/api/voice/speak',
            headers={'Authorization': '******'},
            json={'text': 'नमस्ते', 'lang': 'hi'},
        )

        assert response.status_code == 200
        assert response.headers['content-type'].startswith('audio/mpeg')
        assert response.content == audio_bytes
        assert captured["url"] == "https://api.sarvam.ai/text-to-speech"
        assert captured["headers"]["api-subscription-key"] == "test-sarvam-key"
        assert captured["body"]["model"] == "bulbul:v3"
        assert captured["body"]["language_code"] == "hi-IN"
        assert captured["body"]["speaker"] == "rehan"
        assert captured["body"]["output_audio_codec"] == "mp3"

    def test_voice_speak_uses_google_cloud_text_to_speech(self, client, monkeypatch):
        monkeypatch.setitem(
            client.app.dependency_overrides,
            server.get_authenticated_user,
            lambda: {"user_id": SUPABASE_USER_PAYLOAD["id"]},
        )
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
        audio_bytes = b"\x01" * 256
        captured = {}

        class FakeTtsClient:
            async def synthesize_speech(self, request, **kwargs):
                captured["options"] = kwargs
                captured.update(request)
                return type("SynthesizeResponse", (), {"audio_content": audio_bytes})()

        monkeypatch.setattr(server, "get_google_tts_client", lambda: FakeTtsClient())

        response = client.post(
            "/api/voice/speak",
            json={"text": "नमस्ते", "lang": "hi"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("audio/mpeg")
        assert response.content == audio_bytes
        assert float(response.headers["x-credeasy-backend-duration-ms"]) >= 0
        assert response.headers["x-credeasy-tts-provider"] == "google-cloud"
        assert response.headers["x-credeasy-tts-language"] == "hi-IN"
        assert response.headers["x-credeasy-tts-voice"] == "hi-IN-Chirp3-HD-Puck"
        assert captured["input"] == {"text": "नमस्ते"}
        assert captured["voice"] == {
            "language_code": "hi-IN",
            "name": "hi-IN-Chirp3-HD-Puck",
        }
        assert captured["audio_config"] == {
            "audio_encoding": "MP3",
            "speaking_rate": 0.98,
        }
        assert captured["options"] == {
            "timeout": server.VOICE_TTS_TIMEOUT_SECONDS,
            "retry": None,
        }

        response = client.post(
            "/api/voice/speak",
            json={"text": "Hello there.", "lang": "en"},
        )

        assert response.status_code == 200
        assert captured["voice"] == {
            "language_code": "en-IN",
            "name": "en-IN-Chirp3-HD-Puck",
        }
        assert captured["audio_config"] == {
            "audio_encoding": "MP3",
            "speaking_rate": 0.98,
        }

    def test_voice_speak_detects_hindi_reply_when_ui_language_is_english(
        self, client, monkeypatch
    ):
        monkeypatch.setitem(
            client.app.dependency_overrides,
            server.get_authenticated_user,
            lambda: {"user_id": SUPABASE_USER_PAYLOAD["id"]},
        )
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
        captured = {}

        class FakeTtsClient:
            async def synthesize_speech(self, request, **kwargs):
                captured.update(request)
                return type(
                    "SynthesizeResponse", (), {"audio_content": b"\x01" * 256}
                )()

        monkeypatch.setattr(server, "get_google_tts_client", lambda: FakeTtsClient())

        response = client.post(
            "/api/voice/speak",
            json={"text": "नमस्ते, मैं आपकी मदद करूँगा।", "lang": "en"},
        )

        assert response.status_code == 200
        assert response.headers["x-credeasy-tts-language"] == "hi-IN"
        assert captured["voice"]["name"] == "hi-IN-Chirp3-HD-Puck"

    def test_voice_speak_converts_rupee_amounts_to_spoken_words(self, client, monkeypatch):
        monkeypatch.setitem(
            client.app.dependency_overrides,
            server.get_authenticated_user,
            lambda: {"user_id": SUPABASE_USER_PAYLOAD["id"]},
        )
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
        captured = {}

        class FakeTtsClient:
            async def synthesize_speech(self, request, **kwargs):
                captured.update(request)
                return type("SynthesizeResponse", (), {"audio_content": b"\x01" * 256})()

        monkeypatch.setattr(server, "get_google_tts_client", lambda: FakeTtsClient())
        response = client.post(
            "/api/voice/speak",
            json={"text": "Ravi ka balance ₹2,350 hai.", "lang": "en"},
        )
        assert response.status_code == 200
        assert captured["input"]["text"] == "Ravi ka balance two thousand three hundred fifty rupees hai."

        response = client.post(
            "/api/voice/speak",
            json={"text": "रवि का बकाया ₹2,350.50 है।", "lang": "hi"},
        )
        assert response.status_code == 200
        assert captured["input"]["text"] == "रवि का बकाया दो हज़ार तीन सौ पचास रुपये पचास पैसे है।"

        response = client.post(
            "/api/voice/speak",
            json={"text": "Your balance is ₹46,500.", "lang": "en"},
        )
        assert response.status_code == 200
        assert captured["input"]["text"] == "Your balance is forty six thousand five hundred rupees."

        response = client.post(
            "/api/voice/speak",
            json={
                "text": "Your balance is ₹66,254; the fee is ₹1,265 and tax is ₹1.",
                "lang": "en",
            },
        )
        assert response.status_code == 200
        assert captured["input"]["text"] == (
            "Your balance is sixty six thousand two hundred fifty four rupees; "
            "the fee is one thousand two hundred sixty five rupees and tax is one rupee."
        )

        response = client.post(
            "/api/voice/speak",
            json={"text": "Collect 66,254 rupees from Ravi.", "lang": "en"},
        )
        assert response.status_code == 200
        assert captured["input"]["text"] == (
            "Collect sixty six thousand two hundred fifty four rupees from Ravi."
        )

        response = client.post(
            "/api/voice/speak",
            json={"text": "आपका बकाया ₹46,500 है।", "lang": "hi"},
        )
        assert response.status_code == 200
        assert captured["input"]["text"] == "आपका बकाया छियालीस हज़ार पाँच सौ रुपये है।"

        response = client.post(
            "/api/voice/speak",
            json={"text": "आपका बकाया ₹66,254 है।", "lang": "hi"},
        )
        assert response.status_code == 200
        assert captured["input"]["text"] == "आपका बकाया छियासठ हज़ार दो सौ चौवन रुपये है।"

        response = client.post(
            "/api/voice/speak",
            json={"text": "Your balance is 46,500 rupees.", "lang": "en"},
        )
        assert response.status_code == 200
        assert captured["input"]["text"] == "Your balance is forty six thousand five hundred rupees."

        response = client.post(
            "/api/voice/speak",
            json={"text": "The recorded amount is 46,500.", "lang": "en"},
        )
        assert response.status_code == 200
        assert captured["input"]["text"] == "The recorded amount is forty six thousand five hundred."

    def test_voice_speak_does_not_fallback_after_configured_google_fails(
        self, client, monkeypatch
    ):
        monkeypatch.setitem(
            client.app.dependency_overrides,
            server.get_authenticated_user,
            lambda: {"user_id": SUPABASE_USER_PAYLOAD["id"]},
        )
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")

        class FakeTtsClient:
            async def synthesize_speech(self, request, **kwargs):
                raise RuntimeError("provider unavailable")

        monkeypatch.setattr(server, "get_google_tts_client", lambda: FakeTtsClient())
        monkeypatch.setattr(
            server,
            "get_sarvam_api_key",
            lambda: (_ for _ in ()).throw(
                AssertionError("must not fall back to Sarvam")
            ),
        )

        response = client.post("/api/voice/speak", json={"text": "Hello", "lang": "en"})

        assert response.status_code == 502

    def test_voice_speak_rejects_non_object_sarvam_response(self, client, monkeypatch):
        monkeypatch.setitem(
            client.app.dependency_overrides,
            server.get_authenticated_user,
            lambda: {"user_id": SUPABASE_USER_PAYLOAD["id"]},
        )
        monkeypatch.setattr(server, "get_sarvam_api_key", lambda: "test-sarvam-key")

        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return ["invalid"]

        async def fake_post(self, url, headers=None, json=None, **kwargs):
            return Response()

        monkeypatch.setattr('httpx.AsyncClient.post', fake_post)
        response = client.post(
            '/api/voice/speak',
            json={'text': 'Hello', 'lang': 'en'},
        )

        assert response.status_code == 502
        assert response.json()['detail'] == 'TTS returned an invalid response. Please try again.'

    def test_voice_assist_uses_gemini_flash_lite_json_response(self, client, monkeypatch):
        monkeypatch.setitem(
            client.app.dependency_overrides,
            server.get_authenticated_user,
            lambda: {"user_id": SUPABASE_USER_PAYLOAD["id"]},
        )
        monkeypatch.delenv('GEMINI_PROVIDER', raising=False)
        monkeypatch.setattr(server, 'get_gemini_api_key', lambda: 'test-gemini-key')
        monkeypatch.delenv('GEMINI_MODEL', raising=False)
        captured = {}

        class FakeCompletions:
            async def create(self, **kwargs):
                captured.update(kwargs)
                message = type(
                    'Message',
                    (),
                    {'content': '{"reply":"Hello!","actions":[]}'} ,
                )()
                choice = type('Choice', (), {'message': message})()
                return type('Completion', (), {'choices': [choice]})()

        fake_client = type(
            'FakeGeminiClient',
            (),
            {'chat': type('Chat', (), {'completions': FakeCompletions()})()},
        )()
        monkeypatch.setattr(server, 'get_gemini_client', lambda: fake_client)

        response = client.post(
            '/api/voice/assist',
            headers={'Authorization': '******'},
            json={'transcript': 'Hello', 'context': {}, 'lang': 'en'},
        )

        assert response.status_code == 200
        assert response.json()['reply'] == 'Hello!'
        assert captured['model'] == 'gemini-2.5-flash-lite'
        assert captured['response_format'] == {'type': 'json_object'}

    def test_voice_assist_uses_gemini_25_flash_lite_model(self, client, monkeypatch):
        monkeypatch.setitem(
            client.app.dependency_overrides,
            server.get_authenticated_user,
            lambda: {"user_id": SUPABASE_USER_PAYLOAD["id"]},
        )
        monkeypatch.delenv('GEMINI_PROVIDER', raising=False)
        monkeypatch.setattr(server, 'get_gemini_api_key', lambda: 'test-gemini-key')
        monkeypatch.setenv('GEMINI_MODEL', 'gemini-2.5-flash-lite')
        captured = {}

        class FakeCompletions:
            async def create(self, **kwargs):
                captured.update(kwargs)
                message = type('Message', (), {'content': '{"reply":"Hello!","actions":[]}'} )()
                choice = type('Choice', (), {'message': message})()
                return type('Completion', (), {'choices': [choice]})()

        fake_client = type(
            'FakeGeminiClient',
            (),
            {'chat': type('Chat', (), {'completions': FakeCompletions()})()},
        )()
        monkeypatch.setattr(server, 'get_gemini_client', lambda: fake_client)

        response = client.post(
            '/api/voice/assist',
            headers={'Authorization': '******'},
            json={'transcript': 'Hello', 'context': {}, 'lang': 'en'},
        )

        assert response.status_code == 200
        assert captured['model'] == 'gemini-2.5-flash-lite'

    def test_voice_assist_does_not_fallback_after_configured_gemini_fails(self, client, monkeypatch):
        monkeypatch.setitem(
            client.app.dependency_overrides,
            server.get_authenticated_user,
            lambda: {"user_id": SUPABASE_USER_PAYLOAD["id"]},
        )
        monkeypatch.delenv('GEMINI_PROVIDER', raising=False)
        monkeypatch.setattr(server, 'get_gemini_api_key', lambda: 'test-gemini-key')
        monkeypatch.setattr(server, 'get_groq_api_key', lambda: 'test-groq-key')

        class FakeCompletions:
            async def create(self, **kwargs):
                raise RuntimeError('provider unavailable')

        fake_client = type(
            'FakeGeminiClient',
            (),
            {'chat': type('Chat', (), {'completions': FakeCompletions()})()},
        )()
        monkeypatch.setattr(server, 'get_gemini_client', lambda: fake_client)
        monkeypatch.setattr(
            server,
            'get_groq_client',
            lambda: (_ for _ in ()).throw(AssertionError('must not fall back to Groq')),
        )

        response = client.post(
            '/api/voice/assist',
            json={'transcript': 'Hello', 'context': {}, 'lang': 'en'},
        )

        assert response.status_code == 502
        assert response.json()['detail'] == 'The assistant is unavailable. Please try again.'

    def test_voice_assist_explains_depleted_gemini_credits(self, client, monkeypatch):
        monkeypatch.setitem(
            client.app.dependency_overrides,
            server.get_authenticated_user,
            lambda: {"user_id": SUPABASE_USER_PAYLOAD["id"]},
        )
        monkeypatch.setattr(server, 'get_gemini_api_key', lambda: 'test-gemini-key')

        class ProviderError(RuntimeError):
            status_code = 402

        class FakeCompletions:
            async def create(self, **kwargs):
                raise ProviderError('prepayment credits are depleted')

        fake_client = type(
            'FakeGeminiClient',
            (),
            {'chat': type('Chat', (), {'completions': FakeCompletions()})()},
        )()
        monkeypatch.setattr(server, 'get_gemini_client', lambda: fake_client)

        response = client.post(
            '/api/voice/assist',
            json={'transcript': 'Hello', 'context': {}, 'lang': 'en'},
        )

        assert response.status_code == 503
        assert 'no remaining credits' in response.json()['detail']
        assert 'GEMINI_API_KEY' in response.json()['detail']

    def test_vertex_openai_base_url_uses_supported_endpoint_hosts(self):
        assert server._get_vertex_openai_base_url(
            'test-project', 'us'
        ) == (
            'https://aiplatform.us.rep.googleapis.com/v1beta1/projects/'
            'test-project/locations/us/endpoints/openapi'
        )
        assert server._get_vertex_openai_base_url(
            'test-project', 'global'
        ) == (
            'https://aiplatform.googleapis.com/v1beta1/projects/'
            'test-project/locations/global/endpoints/openapi'
        )
        assert server._get_vertex_openai_base_url(
            'test-project', 'us-central1'
        ) == (
            'https://us-central1-aiplatform.googleapis.com/v1beta1/projects/'
            'test-project/locations/us-central1/endpoints/openapi'
        )

    def test_vertex_voice_client_disables_retries_and_uses_short_timeout(self, monkeypatch):
        monkeypatch.setenv('GOOGLE_CLOUD_PROJECT', 'test-project')
        monkeypatch.setenv('VERTEX_AI_LOCATION', 'us')
        monkeypatch.setattr(
            server,
            '_vertex_credentials',
            type('Credentials', (), {'valid': True, 'token': 'test-token'})(),
        )
        monkeypatch.setattr(server, '_vertex_gemini_client', None)
        monkeypatch.setattr(server, '_vertex_client_token', None)
        captured = {}

        def fake_openai_client(**kwargs):
            captured.update(kwargs)
            return object()

        monkeypatch.setattr(server, 'AsyncOpenAI', fake_openai_client)

        server._get_vertex_gemini_client()

        assert captured['timeout'] == server.VOICE_ASSIST_TIMEOUT_SECONDS
        assert captured['max_retries'] == 0

    def test_voice_assist_uses_vertex_without_gemini_api_key(self, client, monkeypatch):
        monkeypatch.setitem(
            client.app.dependency_overrides,
            server.get_authenticated_user,
            lambda: {"user_id": SUPABASE_USER_PAYLOAD["id"]},
        )
        monkeypatch.setenv('GEMINI_PROVIDER', 'vertex')
        monkeypatch.setenv('GOOGLE_CLOUD_PROJECT', 'test-project')
        monkeypatch.setenv('VERTEX_AI_LOCATION', 'us-central1')
        monkeypatch.delenv('GEMINI_API_KEY', raising=False)
        captured = {}

        class FakeCompletions:
            async def create(self, **kwargs):
                captured.update(kwargs)
                message = type(
                    'Message',
                    (),
                    {'content': '{"reply":"Hello!","actions":[]}'} ,
                )()
                choice = type('Choice', (), {'message': message})()
                return type('Completion', (), {'choices': [choice]})()

        fake_client = type(
            'FakeVertexClient',
            (),
            {'chat': type('Chat', (), {'completions': FakeCompletions()})()},
        )()

        async def fake_vertex_client():
            return fake_client

        monkeypatch.setattr(server, 'get_vertex_gemini_client', fake_vertex_client)
        monkeypatch.setattr(
            server,
            'get_groq_client',
            lambda: (_ for _ in ()).throw(AssertionError('must not fall back to Groq')),
        )

        response = client.post(
            '/api/voice/assist',
            json={
                'transcript': 'Hello',
                'context': {},
                'lang': 'en',
                'history': [
                    {'user': f'older question {index}', 'assistant': f'older answer {index}'}
                    for index in range(5)
                ],
            },
        )

        assert response.status_code == 200
        assert response.json()['reply'] == 'Hello!'
        assert float(response.headers['x-credeasy-backend-duration-ms']) >= 0
        assert captured['model'] == 'google/gemini-2.5-flash-lite'
        assert captured['response_format'] == {'type': 'json_object'}
        assert captured['max_tokens'] == server.VOICE_ASSIST_MAX_OUTPUT_TOKENS
        assert [message['content'] for message in captured['messages'][1:-1]] == [
            'older question 2',
            'older answer 2',
            'older question 3',
            'older answer 3',
            'older question 4',
            'older answer 4',
        ]

    def test_vertex_failure_does_not_fall_back_to_another_provider(self, client, monkeypatch):
        monkeypatch.setitem(
            client.app.dependency_overrides,
            server.get_authenticated_user,
            lambda: {"user_id": SUPABASE_USER_PAYLOAD["id"]},
        )
        monkeypatch.setenv('GEMINI_PROVIDER', 'vertex')
        monkeypatch.setenv('GOOGLE_CLOUD_PROJECT', 'test-project')
        monkeypatch.setattr(server, 'get_gemini_api_key', lambda: None)
        monkeypatch.setattr(server, 'get_groq_api_key', lambda: 'test-groq-key')

        async def unavailable_vertex_client():
            raise RuntimeError('Vertex is unavailable')

        monkeypatch.setattr(server, 'get_vertex_gemini_client', unavailable_vertex_client)
        monkeypatch.setattr(
            server,
            'get_groq_client',
            lambda: (_ for _ in ()).throw(AssertionError('must not fall back to Groq')),
        )

        response = client.post(
            '/api/voice/assist',
            json={'transcript': 'Hello', 'context': {}, 'lang': 'en'},
        )

        assert response.status_code == 502
        assert response.json()['detail'] == 'The assistant is unavailable. Please try again.'


class TestDeleteAccount:
    def test_supabase_error_summary_redacts_sensitive_values(self):
        class Response:
            headers = {}

            @staticmethod
            def json():
                return {
                    "code": "unexpected_failure",
                    "message": (
                        "Could not delete user alice@example.com "
                        "11111111-2222-3333-4444-555555555555 Bearer secret-token"
                    ),
                }

        code, message = server._supabase_error_summary(Response())

        assert code == "unexpected_failure"
        assert "alice@example.com" not in message
        assert "11111111-2222-3333-4444-555555555555" not in message
        assert "secret-token" not in message

    def test_missing_service_role_key_returns_actionable_unavailable_status(
        self, client, monkeypatch
    ):
        monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
        monkeypatch.setitem(
            client.app.dependency_overrides,
            server.get_authenticated_user,
            lambda: {"user_id": SUPABASE_USER_PAYLOAD["id"]},
        )

        response = client.delete(
            "/api/auth/account",
            headers={"Authorization": "******"},
        )

        assert response.status_code == 503
        assert "SUPABASE_SERVICE_ROLE_KEY" in response.json()["detail"]

    def test_account_deletion_removes_nested_media_before_auth_user(
        self, client, monkeypatch
    ):
        stub_supabase(monkeypatch, 200, SUPABASE_USER_PAYLOAD)
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
        calls = []

        class Response:
            headers = {}

            def __init__(self, status_code, payload=None):
                self.status_code = status_code
                self.text = ""
                self.payload = payload

            def json(self):
                return self.payload

        async def fake_post(self, url, headers=None, json=None, **kwargs):
            assert headers["Authorization"] == "Bearer test-service-role-key"
            assert headers["apikey"] == "test-service-role-key"
            prefix = json["prefix"]
            calls.append(("list", prefix))
            listings = {
                SUPABASE_USER_PAYLOAD["id"]: [
                    {"name": "business-id", "id": None, "metadata": None}
                ],
                f'{SUPABASE_USER_PAYLOAD["id"]}/business-id': [
                    {"name": "profile", "id": None, "metadata": None}
                ],
                f'{SUPABASE_USER_PAYLOAD["id"]}/business-id/profile': [
                    {"name": "photo.png", "id": "object-id", "metadata": {}}
                ],
            }
            return Response(200, listings.get(prefix, []))

        async def fake_request(self, method, url, headers=None, json=None, **kwargs):
            calls.append(("request", method, url, json))
            return Response(200, {})

        async def fake_delete(self, url, headers=None, **kwargs):
            calls.append(("delete", url))
            return Response(200, {"id": SUPABASE_USER_PAYLOAD["id"]})

        monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
        monkeypatch.setattr("httpx.AsyncClient.request", fake_request)
        monkeypatch.setattr("httpx.AsyncClient.delete", fake_delete)

        response = client.delete(
            "/api/auth/account",
            headers={"Authorization": "Bearer test-user-token"},
        )

        assert response.status_code == 200
        assert response.json()["success"] is True
        media_delete = next(call for call in calls if call[0] == "request" and "storage" in call[2])
        account_delete = next(call for call in calls if call[0] == "delete" and "admin/users" in call[1])
        assert media_delete[1] == "DELETE"
        assert media_delete[3]["prefixes"] == [
            f'{SUPABASE_USER_PAYLOAD["id"]}/business-id/profile/photo.png'
        ]
        assert calls.index(media_delete) < calls.index(account_delete)

    def test_media_cleanup_failure_preserves_auth_account(self, client, monkeypatch):
        stub_supabase(monkeypatch, 200, SUPABASE_USER_PAYLOAD)
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
        calls = []

        class Response:
            status_code = 500

            def json(self):
                return {"message": "storage failure"}

        async def fail_media_list(self, url, headers=None, json=None, **kwargs):
            calls.append(url)
            return Response()

        async def fake_delete(self, url, headers=None, json=None, **kwargs):
            calls.append(url)
            return Response()

        monkeypatch.setattr("httpx.AsyncClient.post", fail_media_list)
        monkeypatch.setattr("httpx.AsyncClient.delete", fake_delete)

        response = client.delete(
            "/api/auth/account",
            headers={"Authorization": "Bearer test-user-token"},
        )

        assert response.status_code == 502
        assert not any("/auth/v1/admin/users/" in call for call in calls)

    def test_supabase_account_deletion_failure_returns_actionable_status(
        self, client, monkeypatch
    ):
        stub_supabase(monkeypatch, 200, SUPABASE_USER_PAYLOAD)
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")

        class Response:
            headers = {}

            def __init__(self, status_code, payload=None):
                self.status_code = status_code
                self.text = ""
                self.payload = payload

            def json(self):
                return self.payload

        async def empty_media_list(self, url, headers=None, json=None, **kwargs):
            return Response(200, [])

        async def failed_account_delete(self, url, headers=None, json=None, **kwargs):
            return Response(500, {"message": "upstream details are not returned to the client"})

        monkeypatch.setattr("httpx.AsyncClient.post", empty_media_list)
        monkeypatch.setattr("httpx.AsyncClient.delete", failed_account_delete)

        response = client.delete(
            "/api/auth/account",
            headers={"Authorization": "Bearer test-user-token"},
        )

        assert response.status_code == 502
        assert "HTTP 500" in response.json()["detail"]
        assert "upstream details" not in response.json()["detail"]


class TestHealthCheck:
    def test_root_endpoint(self, client):
        response = client.get('/api/')
        assert response.status_code == 200
        assert response.json().get('message') == 'Hello World'
