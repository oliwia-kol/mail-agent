# Monitoring Langfuse

Lokalny Langfuse rejestruje obsługę zapytania, wywołanie modelu oraz wykonanie
narzędzia SMTP. Monitoring jest opcjonalny i nie wpływa na podstawowy start aplikacji.

## Uruchomienie

Wymagania: Docker Compose i Python 3 do wygenerowania lokalnych haseł.

```sh
python3 scripts/configure_monitoring.py
docker compose --env-file .env.langfuse -f docker-compose.yml -f compose.monitoring.yml up -d --build
```

Skrypt tworzy `.env.langfuse` z losowymi hasłami i kluczami. Nie nadpisuje
istniejącego pliku. Plik jest wykluczony z Git i kontekstu obrazu Docker.

| Ustawienie | Wartość |
|---|---|
| Panel | http://localhost:3000 |
| Projekt | Mail Agent PoC |
| Użytkownik | `operator@example.com` |
| Hasło | Pole `LF_ADMIN_PASSWORD` w `.env.langfuse` |

Langfuse korzysta z PostgreSQL, ClickHouse, Redis i MinIO oraz procesu worker.
Pierwszy start obejmuje inicjalizację baz. Gotowość API nie oznacza gotowości
panelu monitoringu. Konfiguracja bazuje na [oficjalnym Compose Langfuse](https://langfuse.com/self-hosting/deployment/docker-compose).

Przy zmianie modelu lub portów wpisz odpowiednie zmienne `MAIL_AGENT_*`
także do `.env.langfuse`: opcja `--env-file` zastępuje domyślne wczytanie `.env`.

## Odczyt śladu

1. Wyślij zapytanie opisane w README.
2. W panelu otwórz projekt **Mail Agent PoC** i listę śladów wykonania.
3. Odszukaj `request_id` z odpowiedzi API w metadanych śladu.

| Etap | Zapisane dane |
|---|---|
| `route-request` | Wejście i wynik całej obsługi |
| `ollama-routing` | Model, wersja instrukcji, parametry, wywołanie narzędzia i tokeny |
| `send_email` | Odbiorca i wynik SMTP |

Każdy etap zawiera czas wykonania i oznaczenie błędu, jeśli wystąpił.
Zapis odbywa się w tle, więc dane mogą pojawić się w panelu z opóźnieniem.

Funkcja `record_scores` umożliwia przypisanie ocen `valid_call`, `routing_ok`,
`smtp_ok` i `full_success` na podstawie porównania z oczekiwanym wynikiem.
Standardowe zapytanie API nie zawiera oczekiwanego odbiorcy i nie otrzymuje
automatycznej oceny poprawności klasyfikacji.

## Rejestrowane treści

Konfiguracja demonstracyjna zapisuje treść zgłoszenia i instrukcję modelu.
Jest przeznaczona do wiadomości syntetycznych. Pole adresu nadawcy jest
maskowane; dane osobowe wpisane w treść pozostają widoczne. Ukryte rozumowanie
modelu nie jest zapisywane.

Awaria Langfuse nie zatrzymuje wysyłki SMTP. Aplikacja nie ma trwałej kolejki
telemetrii, dlatego nie gwarantuje odzyskania niezapisanych śladów.
Sprawdzona konfiguracja: Langfuse 4.59.0, SDK 5.0.1.

## Zatrzymanie

```sh
docker compose --env-file .env.langfuse -f docker-compose.yml -f compose.monitoring.yml stop
```
