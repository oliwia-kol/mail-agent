from email import policy
from email.parser import BytesParser
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from aiosmtpd.controller import Controller
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from mail_agent.agent import InvalidToolCall, validate_call
from mail_agent.api import app
from mail_agent.config import Settings


@pytest.mark.parametrize("smtp_code,expected_status", [(250, 200), (421, 503), (550, 503)])
def test_readiness_checks_smtp_reply(smtp_code, expected_status):
    settings = Settings()
    with (
        patch("mail_agent.api.settings", settings),
        patch("mail_agent.api.httpx.get") as get,
        patch("mail_agent.api.smtplib.SMTP") as smtp,
    ):
        get.return_value.json.return_value = {"models": [{"name": settings.model}]}
        smtp.return_value.__enter__.return_value.noop.return_value = (smtp_code, b"status")
        assert TestClient(app).get("/health/ready").status_code == expected_status


@pytest.mark.parametrize(
    "calls",
    [
        [],
        [{"name": "wrong", "args": {}}],
        [{"name": "send_email", "args": {"recipient": "evil@example.org"}}],
        [{"name": "send_email", "args": {"recipient": "it@example.com", "message": "zmiana"}}],
        [{"name": "send_email", "args": {"recipient": "it@example.com"}}] * 2,
    ],
)
def test_reject_invalid_call(calls):
    with pytest.raises(InvalidToolCall):
        validate_call(SimpleNamespace(tool_calls=calls, invalid_tool_calls=[]))


@pytest.mark.parametrize(
    "body",
    [
        {"email": "wrong", "message": "test"},
        {"email": "x@example.com", "message": "   "},
        {"email": "x@example.com", "message": "a" * 8001},
        {"email": "x@example.com", "message": "test", "recipient": "it@example.com"},
        {"email": "x@example.com\r\nBcc:evil@example.com", "message": "test"},
    ],
)
def test_bad_input(body):
    with patch("mail_agent.api.route") as route:
        assert TestClient(app).post("/api/v1/route", json=body).status_code == 422
        route.assert_not_called()


def test_api_tool_real_smtp():
    class Capture:
        async def handle_DATA(self, server, session, envelope):
            self.message = BytesParser(policy=policy.default).parsebytes(envelope.content)
            return "250 OK"

    capture = Capture()
    smtp = Controller(capture, hostname="127.0.0.1", port=11025)
    smtp.start()
    try:
        response = AIMessage(
            content="",
            tool_calls=[
                {"id": "call-1", "name": "send_email", "args": {"recipient": "kadry@example.com"}}
            ],
        )
        with (
            patch("mail_agent.agent.ChatOllama") as model,
            patch("mail_agent.api.settings", Settings(smtp_port=11025)),
        ):
            model.return_value.bind_tools.return_value.invoke.return_value = response
            result = TestClient(app).post(
                "/api/v1/route",
                json={"email": "ola@example.com", "message": "Proszę o urlop.\nDziękuję!"},
            )
        assert result.status_code == 200
        assert capture.message["Reply-To"] == "ola@example.com"
        assert capture.message["To"] == "kadry@example.com"
        assert (
            capture.message.get_content().replace("\r\n", "\n").rstrip("\n")
            == "Proszę o urlop.\nDziękuję!"
        )
        assert capture.message["X-Request-ID"] == result.json()["request_id"]
    finally:
        smtp.stop()


def test_model_failure_does_not_send():
    with patch("mail_agent.agent.ChatOllama") as model, patch("mail_agent.agent.deliver") as send:
        model.return_value.bind_tools.return_value.invoke.side_effect = RuntimeError("offline")
        result = TestClient(app).post(
            "/api/v1/route", json={"email": "x@example.com", "message": "urlop"}
        )
        assert result.status_code == 502
        send.assert_not_called()


@pytest.mark.parametrize(
    "calls",
    [
        [],
        [
            {"id": "one", "name": "send_email", "args": {"recipient": "it@example.com"}},
            {"id": "two", "name": "send_email", "args": {"recipient": "kadry@example.com"}},
        ],
        [{"id": "bad", "name": "send_email", "args": {"recipient": "outside@example.org"}}],
    ],
)
def test_invalid_model_response_never_sends(calls):
    with patch("mail_agent.agent.ChatOllama") as model, patch("mail_agent.agent.deliver") as send:
        model.return_value.bind_tools.return_value.invoke.return_value = AIMessage(
            content="wysłałem", tool_calls=calls
        )
        result = TestClient(app).post(
            "/api/v1/route", json={"email": "x@example.com", "message": "urlop"}
        )
        assert result.status_code == 502
        send.assert_not_called()


def test_smtp_failure_not_retried_or_reported_as_success():
    with patch("mail_agent.agent.ChatOllama") as model, patch("mail_agent.agent.deliver") as send:
        model.return_value.bind_tools.return_value.invoke.return_value = AIMessage(
            content="",
            tool_calls=[
                {"id": "one", "name": "send_email", "args": {"recipient": "it@example.com"}}
            ],
        )
        send.side_effect = OSError("connection lost")
        result = TestClient(app).post(
            "/api/v1/route", json={"email": "x@example.com", "message": "nowy laptop"}
        )
        assert result.status_code == 502
        send.assert_called_once()
