import asyncio

import server
from fastapi.testclient import TestClient


def make_scope(path, headers=()):
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": list(headers),
        "server": ("testserver", 80),
        "client": ("testclient", 12345),
    }


def test_audio_upload_limit_includes_file_size_and_multipart_framing(monkeypatch):
    monkeypatch.setattr(server, "MAX_AUDIO_BYTES", 25)
    monkeypatch.setattr(server, "MAX_MULTIPART_OVERHEAD_BYTES", 7)

    assert server.request_body_limit("/api/voice/transcribe") == (
        32,
        "Audio must be 25 MB or smaller",
    )


def test_chunked_request_body_is_rejected_at_the_stream_limit(monkeypatch):
    monkeypatch.setattr(server, "MAX_REQUEST_BYTES", 4)
    chunks = iter([
        {"type": "http.request", "body": b"1234", "more_body": True},
        {"type": "http.request", "body": b"5", "more_body": False},
    ])
    sent = []

    async def receive():
        return next(chunks)

    async def send(message):
        sent.append(message)

    async def consume_request(scope, receive, send):
        while (await receive())["more_body"]:
            pass

    async def run():
        middleware = server.RequestBodyLimitMiddleware(consume_request)
        await middleware(make_scope("/api/other"), receive, send)

    asyncio.run(run())

    assert sent[0]["type"] == "http.response.start"
    assert sent[0]["status"] == 413
    assert b"Request body too large" in sent[1]["body"]


def test_chunked_api_upload_returns_413_without_content_length(monkeypatch):
    monkeypatch.setattr(server, "MAX_REQUEST_BYTES", 4)

    response = TestClient(server.app).post(
        "/api/voice/assist",
        content=iter([b"1234", b"5"]),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 413


def test_audio_route_accepts_content_length_above_default_request_limit(monkeypatch):
    monkeypatch.setattr(server, "MAX_REQUEST_BYTES", 4)
    monkeypatch.setattr(server, "MAX_AUDIO_BYTES", 8)
    monkeypatch.setattr(server, "MAX_MULTIPART_OVERHEAD_BYTES", 1)
    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    async def return_no_content(scope, receive, send):
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    async def run():
        middleware = server.RequestBodyLimitMiddleware(return_no_content)
        await middleware(
            make_scope(
                "/api/voice/transcribe",
                [(b"content-length", b"6")],
            ),
            receive,
            send,
        )

    asyncio.run(run())

    assert sent[0]["status"] == 204
