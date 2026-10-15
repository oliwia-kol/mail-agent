import json
import logging
import smtplib
from time import monotonic
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException

from mail_agent.agent import InvalidToolCall, route
from mail_agent.config import Settings
from mail_agent.contracts import RouteRequest, RouteResponse
from mail_agent.observability import observe
from mail_agent.prompt import PROMPT_VERSION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mail_agent")
app = FastAPI(title="Mail Agent", docs_url="/api/v1/docs", redoc_url=None)
settings = Settings()


@app.get("/health/ready")
def ready():
    try:
        response = httpx.get(f"{settings.ollama_url}/api/tags", timeout=3)
        response.raise_for_status()
        models = response.json()["models"]
        if not any(m["name"] == settings.model for m in models):
            raise ValueError("Brak skonfigurowanego modelu")
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=3) as smtp:
            code, _ = smtp.noop()
            if code != 250:
                raise ValueError("SMTP nie potwierdziło gotowości")
    except Exception as exc:
        raise HTTPException(503, "Model lub SMTP nie jest gotowy") from exc
    return {"status": "ready"}


@app.post("/api/v1/route", response_model=RouteResponse)
def route_message(request: RouteRequest):
    request_id = str(uuid4())
    start = monotonic()
    status = "error"
    try:
        trace_input = {"email": "[masked]", "message_length": len(request.message)}
        if settings.langfuse_capture_content:
            trace_input["message"] = request.message
        with observe(
            settings,
            "route-request",
            request_id=request_id,
            as_type="agent",
            input=trace_input,
            metadata={"request_id": request_id, "prompt_version": PROMPT_VERSION},
        ) as span:
            result = route(settings, request, request_id)
            span.update(output=result)
        status = result["status"]
        return RouteResponse(request_id=request_id, **result)
    except InvalidToolCall as exc:
        raise HTTPException(502, {"request_id": request_id, "error": str(exc)}) from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(504, {"request_id": request_id, "error": "Timeout modelu"}) from exc
    except Exception as exc:
        # Nie zwracamy surowego błędu usługi: może zawierać tekst lub nagłówki maila.
        raise HTTPException(
            502,
            {"request_id": request_id, "error": "Błąd modelu lub SMTP; nie ponawiaj automatycznie"},
        ) from exc
    finally:
        logger.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "status": status,
                    "seconds": round(monotonic() - start, 3),
                    "model": settings.model,
                    "prompt": PROMPT_VERSION,
                }
            )
        )
