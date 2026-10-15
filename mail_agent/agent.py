import json
import logging
from collections.abc import Callable

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import StructuredTool
from langchain_ollama import ChatOllama
from pydantic import ValidationError

from mail_agent.config import Settings
from mail_agent.contracts import RouteRequest, SendEmailArgs
from mail_agent.mailer import deliver
from mail_agent.observability import observe
from mail_agent.prompt import PROMPT_VERSION, SYSTEM_PROMPT


class InvalidToolCall(ValueError):
    pass


def validate_call(response) -> dict:
    if response.invalid_tool_calls or len(response.tool_calls) != 1:
        raise InvalidToolCall("Wymagane jest jedno poprawne wywołanie narzędzia")
    call = response.tool_calls[0]
    if call["name"] != "send_email":
        raise InvalidToolCall("Niedozwolone narzędzie")
    try:
        SendEmailArgs.model_validate(call["args"])
    except ValidationError as exc:
        raise InvalidToolCall("Niepoprawne argumenty narzędzia") from exc
    return call


def encode_message(message: str) -> str:
    # Kodowanie dotyczy tekstu dla modelu. Mail zachowuje oryginalną treść.
    return (
        json.dumps({"message": message}, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )


def route(
    settings: Settings,
    request: RouteRequest,
    request_id: str,
    on_model_response: Callable[[AIMessage], None] | None = None,
) -> dict:
    # Funkcja korzysta z danych tego zapytania. Model podaje tylko odbiorcę.
    def send_email(recipient: str) -> dict:
        with observe(
            settings, "send_email", as_type="tool", input={"recipient": recipient}
        ) as span:
            result = deliver(settings, request, recipient, request_id)
            span.update(output=result)
            return result

    tool = StructuredTool.from_function(
        send_email,
        name="send_email",
        args_schema=SendEmailArgs,
        description="Przekaż oryginalne zgłoszenie do jednego dozwolonego działu przez SMTP.",
    )
    model = ChatOllama(
        base_url=settings.ollama_url,
        model=settings.model,
        temperature=0,
        reasoning=False,
        num_ctx=8192,
        num_predict=512,
        client_kwargs={"timeout": settings.model_timeout},
    ).bind_tools([tool])
    trace_input = {"prompt_version": PROMPT_VERSION}
    if settings.langfuse_capture_content:
        trace_input.update(system=SYSTEM_PROMPT, message=request.message)
    with observe(
        settings,
        "ollama-routing",
        as_type="generation",
        model=settings.model,
        version=PROMPT_VERSION,
        input=trace_input,
        model_parameters={
            "temperature": 0,
            "num_ctx": 8192,
            "num_predict": 512,
            "reasoning": False,
        },
    ) as span:
        response = model.invoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=encode_message(request.message)),
            ]
        )
        # W monitoringu zapisujemy wywołanie narzędzia i liczbę tokenów.
        span.update(
            output={
                "tool_calls": response.tool_calls,
                "invalid_tool_call_count": len(response.invalid_tool_calls),
            },
            usage_details={
                target: response.usage_metadata[source]
                for source, target in [
                    ("input_tokens", "input"),
                    ("output_tokens", "output"),
                    ("total_tokens", "total"),
                ]
                if response.usage_metadata and source in response.usage_metadata
            },
        )
    if on_model_response is not None:
        on_model_response(response)
    call = validate_call(response)
    logging.getLogger("mail_agent").info(
        "tool_call request_id=%s name=%s args=%s", request_id, call["name"], call["args"]
    )
    return tool.invoke(call["args"])
