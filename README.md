# Mail Agent

## English summary

A local LLM agent that classifies employee messages and routes them to internal
departments through validated tool calls. Built with FastAPI, LangChain and Ollama,
with SMTP delivery to Mailpit, Docker Compose setup and optional Langfuse tracing.

## Opis projektu

Lokalny agent do routingu wewnętrznych zgłoszeń pracowników. API przyjmuje
adres nadawcy i treść wiadomości. Model językowy wybiera dział i wywołuje
narzędzie `send_email`, które przekazuje zgłoszenie do testowego serwera pocztowego.
Nagłówek `Reply-To` zawiera adres nadawcy.

**Technologie:** Python, FastAPI, LangChain, Ollama, Mailpit, Docker Compose.
Opcjonalny monitoring: Langfuse.

## Uruchomienie

Wymagania: Docker z aktualnym Docker Compose oraz dostęp do internetu podczas
pobierania obrazów i modelu. Pliki modelu zajmują około 8 GB, poza miejscem
potrzebnym na obrazy. Środowisko testowe: Mac M4, 24 GB RAM, 16 GB dla Dockera;
obliczenia modelu na CPU.

```sh
git clone https://github.com/oliwia-kol/mail-agent.git
cd mail-agent
docker compose up -d
```

Compose buduje API i automatycznie pobiera model. Gotowość aplikacji:

```sh
curl http://localhost:8000/health/ready
```

Odpowiedź: `{"status":"ready"}`. Pierwsze zapytanie może potrwać około minuty
ze względu na ładowanie modelu do pamięci. Postęp pobierania:
`docker compose logs -f model-init`. Zakończenie `model-init` kodem 0 jest prawidłowe.

| Usługa | Adres |
|---|---|
| Dokumentacja API | http://localhost:8000/api/v1/docs |
| Skrzynka Mailpit | http://localhost:8025 |

## API

`POST /api/v1/route`

```sh
curl http://localhost:8000/api/v1/route \
  -H 'Content-Type: application/json' \
  -d '{"email":"ola@example.com","message":"Proszę o zaświadczenie o zatrudnieniu."}'
```

Odpowiedź:

```json
{
  "request_id": "5afdc30c-1ab7-40b7-b792-885e994e88f4",
  "recipient": "kadry@example.com",
  "status": "smtp_accepted"
}
```

Mailpit przechwytuje wiadomość do `kadry@example.com` z oryginalną treścią
i `Reply-To: ola@example.com`. Status `smtp_accepted` oznacza przyjęcie przez
serwer SMTP. Mailpit nie dostarcza poczty do rzeczywistych odbiorców.

## Architektura

FastAPI odpowiada za HTTP i walidację danych. LangChain przekazuje instrukcję
oraz schemat narzędzia do lokalnego modelu w Ollamie. Po otrzymaniu wywołania
`send_email(recipient)` aplikacja sprawdza argumenty i wykonuje wysyłkę SMTP.
Dozwolone jest jedno wywołanie z adresem z zamkniętej listy pięciu działów.
Treść i `Reply-To` pochodzą z zapytania do API.

[Architektura i zasady routingu](docs/design.md).

## Konfiguracja i obsługa

Domyślny model: `gemma4:12b-it-q4_K_M`. Plik `.env.example` zawiera ustawienia
modelu i portów. Zmiany można wprowadzić w lokalnej kopii `.env`.

```sh
docker compose stop                     # Zatrzymanie
docker compose up -d                    # Ponowny start
docker compose up -d --build            # Przebudowanie po zmianie kodu
docker compose logs --tail=100 api      # Logi aplikacji
```

Model pozostaje w wolumenie Dockera. Wiadomości Mailpit są przechowywane
do restartu jego procesu. Każde zapytanie może wysłać nowy mail; po błędzie
SMTP nie należy ponawiać wysyłki automatycznie.

## Testy

Testy kodu wymagają Pythona 3.12–3.14 i [uv](https://docs.astral.sh/uv/).

```sh
uv sync --locked
uv run pytest -q tests
uv run ruff check mail_agent tests scripts
```

Kontrola działającego API, modelu i dostarczenia wiadomości do Mailpit:

```sh
python3 scripts/check_delivery.py
```

Projekt jest lokalnym PoC bez uwierzytelniania i limitowania ruchu.
Wyniki klasyfikacji oraz zakres testów opisuje [raport oceny modeli](docs/model-comparison.md).

[Konfiguracja Langfuse i odczyt monitoringu](docs/monitoring.md).
Zgłoszenia błędów: [GitHub Issues](https://github.com/oliwia-kol/mail-agent/issues).
