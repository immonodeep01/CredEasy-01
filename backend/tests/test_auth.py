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
    monkeypatch.delenv('GOOGLE_CLOUD_PROJECT', raising=False)
    monkeypatch.delenv('GCLOUD_PROJECT', raising=False)

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
            == "projects/test-project/locations/global/recognizers/_"
        )
        assert captured["config"]["auto_decoding_config"] == {}
        assert captured["config"]["language_codes"] == ["en-IN", "hi-IN"]
        assert captured["config"]["model"] == "chirp_3"
        assert captured["content"] == b"audio-bytes"

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
            async def synthesize_speech(self, request):
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
            "speaking_rate": 1.05,
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
            "speaking_rate": 1.05,
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
            async def synthesize_speech(self, request):
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
            async def synthesize_speech(self, request):
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

    def test_voice_assist_does_not_fallback_after_configured_gemini_fails(self, client, monkeypatch):
        monkeypatch.setitem(
            client.app.dependency_overrides,
            server.get_authenticated_user,
            lambda: {"user_id": SUPABASE_USER_PAYLOAD["id"]},
        )
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


class TestDeleteAccount:
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

        async def fake_delete(self, url, headers=None, json=None, **kwargs):
            calls.append(("delete", url, json))
            if "/auth/v1/admin/users/" in url:
                return Response(200, {"id": SUPABASE_USER_PAYLOAD["id"]})
            return Response(200, {})

        monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
        monkeypatch.setattr("httpx.AsyncClient.delete", fake_delete)

        response = client.delete(
            "/api/auth/account",
            headers={"Authorization": "Bearer test-user-token"},
        )

        assert response.status_code == 200
        assert response.json()["success"] is True
        media_delete = next(call for call in calls if call[0] == "delete" and "storage" in call[1])
        account_delete = next(call for call in calls if call[0] == "delete" and "admin/users" in call[1])
        assert media_delete[2]["prefixes"] == [
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
