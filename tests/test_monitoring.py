import json
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langfuse import Langfuse
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic import ValidationError

from mail_agent.api import app
from mail_agent.config import Settings
from mail_agent.observability import record_scores


def enabled(**overrides):
    return Settings(
        langfuse_enabled=True,
        langfuse_public_key="pk-lf-test",
        langfuse_secret_key="sk-lf-test",
        **overrides,
    )


def model_response():
    return AIMessage(
        content="HIDDEN_THOUGHT_CANARY",
        additional_kwargs={"reasoning_content": "HIDDEN_THOUGHT_CANARY"},
        tool_calls=[
            {"id": "one", "name": "send_email", "args": {"recipient": "kadry@example.com"}}
        ],
        usage_metadata={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
    )


def test_real_sdk_records_parent_model_and_tool_without_hidden_reasoning():
    exporter = InMemorySpanExporter()
    monitor = Langfuse(
        public_key="pk-lf-test-" + uuid4().hex,
        secret_key="sk-lf-test",
        base_url="http://localhost:3000",
        tracer_provider=TracerProvider(),
        span_exporter=exporter,
    )
    try:
        with (
            patch("mail_agent.api.settings", enabled(langfuse_capture_content=True)),
            patch("mail_agent.observability.get_monitor", return_value=monitor),
            patch("mail_agent.agent.ChatOllama") as model,
            patch("mail_agent.agent.deliver") as send,
        ):
            model.return_value.bind_tools.return_value.invoke.return_value = model_response()
            send.return_value = {"status": "smtp_accepted", "recipient": "kadry@example.com"}
            result = TestClient(app).post(
                "/api/v1/route", json={"email": "ola@example.com", "message": "Proszę o urlop"}
            )
        monitor.flush()
        spans = exporter.get_finished_spans()
        assert result.status_code == 200
        assert {span.name for span in spans} == {"route-request", "ollama-routing", "send_email"}
        assert len({span.context.trace_id for span in spans}) == 1
        root = next(span for span in spans if span.name == "route-request")
        assert all(
            span.parent.span_id == root.context.span_id for span in spans if span is not root
        )
        serialized = json.dumps([dict(span.attributes) for span in spans], ensure_ascii=False)
        assert "HIDDEN_THOUGHT_CANARY" not in serialized
        assert "ola@example.com" not in serialized
        assert "kadry@example.com" in serialized
        inputs = [
            json.loads(span.attributes.get("langfuse.observation.input", "{}")) for span in spans
        ]
        assert any(item.get("message") == "Proszę o urlop" for item in inputs)
        send.assert_called_once()
    finally:
        monitor.shutdown()


def test_monitoring_failure_cannot_retry_smtp_or_break_success():
    with (
        patch("mail_agent.api.settings", enabled()),
        patch("mail_agent.observability.get_monitor", side_effect=RuntimeError("unavailable")),
        patch("mail_agent.agent.ChatOllama") as model,
        patch("mail_agent.agent.deliver") as send,
    ):
        model.return_value.bind_tools.return_value.invoke.return_value = model_response()
        send.return_value = {"status": "smtp_accepted", "recipient": "kadry@example.com"}
        result = TestClient(app).post(
            "/api/v1/route", json={"email": "ola@example.com", "message": "Urlop"}
        )
        assert result.status_code == 200
        send.assert_called_once()


def test_monitoring_disabled_does_not_create_client():
    with (
        patch("mail_agent.observability._client") as client,
        patch("mail_agent.agent.ChatOllama") as model,
        patch("mail_agent.agent.deliver") as send,
    ):
        model.return_value.bind_tools.return_value.invoke.return_value = model_response()
        send.return_value = {"status": "smtp_accepted", "recipient": "kadry@example.com"}
        with patch("mail_agent.api.settings", Settings()):
            assert (
                TestClient(app)
                .post("/api/v1/route", json={"email": "ola@example.com", "message": "Urlop"})
                .status_code
                == 200
            )
        client.assert_not_called()


def test_cloud_monitoring_not_enabled_by_local_profile():
    with pytest.raises(ValidationError, match="lokalny"):
        enabled(langfuse_url="https://cloud.langfuse.com")


def test_score_failure_is_nonblocking():
    with patch("mail_agent.observability.get_monitor", side_effect=RuntimeError("offline")):
        record_scores(enabled(), "test-request", {"routing_ok": True})
