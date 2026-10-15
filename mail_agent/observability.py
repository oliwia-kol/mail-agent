import logging
from contextlib import contextmanager
from functools import lru_cache

from langfuse import Langfuse

from mail_agent.config import Settings

logger = logging.getLogger("mail_agent.monitoring")


@lru_cache(maxsize=2)
def _client(base_url: str, public_key: str, secret_key: str):
    return Langfuse(
        base_url=base_url,
        public_key=public_key,
        secret_key=secret_key,
        timeout=1,
        environment="local-poc",
    )


def get_monitor(settings: Settings):
    if not settings.langfuse_enabled:
        return None
    return _client(
        settings.langfuse_url,
        settings.langfuse_public_key,
        settings.langfuse_secret_key.get_secret_value(),
    )


class Observation:
    def __init__(self, span=None):
        self.span = span

    def update(self, **values):
        if self.span is not None:
            try:
                self.span.update(**values)
            except Exception:  # noqa: BLE001 — awaria monitoringu nie przerywa obsługi maila
                logger.warning("Nie udało się uzupełnić zapisu w Langfuse")


@contextmanager
def observe(settings: Settings, name: str, *, request_id=None, **values):
    context = None
    observation = Observation()
    if settings.langfuse_enabled:
        try:
            client = get_monitor(settings)
            if request_id:
                values["trace_context"] = {"trace_id": client.create_trace_id(seed=request_id)}
            context = client.start_as_current_observation(name=name, **values)
            observation = Observation(context.__enter__())
        except Exception:  # noqa: BLE001 — awaria monitoringu nie przerywa obsługi maila
            context = None
            logger.warning("Langfuse jest niedostępny. Obsługa wiadomości trwa dalej.")
    try:
        yield observation
    except Exception as exc:
        observation.update(level="ERROR", status_message=type(exc).__name__)
        raise
    finally:
        if context is not None:
            try:
                context.__exit__(None, None, None)
            except Exception:  # noqa: BLE001 — awaria monitoringu nie przerywa obsługi maila
                logger.warning("Nie udało się zakończyć zapisu w Langfuse")


def record_scores(settings: Settings, request_id: str, scores: dict):
    if not settings.langfuse_enabled:
        return
    try:
        client = get_monitor(settings)
        for name, value in scores.items():
            client.create_score(
                trace_id=client.create_trace_id(seed=request_id),
                name=name,
                value=int(value),
                data_type="BOOLEAN",
            )
    except Exception:  # noqa: BLE001 — awaria monitoringu nie przerywa obsługi maila
        logger.warning("Nie udało się zapisać wyników testu w Langfuse")
