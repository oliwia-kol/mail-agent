# Mail Agent

Lokalny router zgłoszeń pracowników. Przyjmuje adres nadawcy i treść wiadomości,
a model językowy wybiera dział i wywołuje narzędzie wysyłające e-mail.
Mail trafia do testowej skrzynki Mailpit. Nagłówek `Reply-To` wskazuje nadawcę.

Projekt pokazuje integrację FastAPI, LangChain, Ollamy i SMTP.
Opcjonalny Langfuse pozwala prześledzić obsługę wiadomości.

## Uruchomienie

Potrzebujesz działającego Dockera z aktualnym Docker Compose oraz internetu
na czas pobierania obrazów i modelu. Nie trzeba instalować Pythona ani Ollamy
na komputerze, zakładać konta u dostawcy modelu ani podawać kluczy API.

Sprawdzone środowisko: Mac M4, 24 GB RAM, z przydziałem 16 GB dla Dockera.
Ollama w tej konfiguracji działa na CPU. Same wagi modelu zajmują około 8 GB;
obrazy kontenerów wymagają dodatkowego miejsca.

```sh
git clone https://github.com/oliwia-kol/mail-agent.git
cd mail-agent
docker compose up -d
```

Pierwszy start buduje API i automatycznie pobiera model. Poczekaj na gotowość:

```sh
docker compose ps -a
curl http://localhost:8000/health/ready
```

Odpowiedź `{"status":"ready"}` oznacza, że model jest pobrany i serwer SMTP
odpowiada. Pierwsze zapytanie może potrwać około minuty, bo model musi jeszcze
trafić do pamięci. Kolejne są zwykle szybsze. Postęp pobierania pokaże
`docker compose logs -f model-init`. Zakończenie `model-init` kodem 0 jest prawidłowe.

- [Dokumentacja API i formularz zapytania](http://localhost:8000/api/v1/docs)
- [Skrzynka testowa Mailpit](http://localhost:8025)

## Przykład

```sh
curl http://localhost:8000/api/v1/route \
  -H 'Content-Type: application/json' \
  -d '{"email":"ola@example.com","message":"Proszę o zaświadczenie o zatrudnieniu."}'
```

Przykładowa odpowiedź:

```json
{
  "request_id": "5afdc30c-1ab7-40b7-b792-885e994e88f4",
  "recipient": "kadry@example.com",
  "status": "smtp_accepted"
}
```

W Mailpit pojawi się wiadomość do kadr z oryginalną treścią i
`Reply-To: ola@example.com`. `smtp_accepted` oznacza przyjęcie przez serwer
pocztowy. Wiadomości nie są dostarczane do rzeczywistych osób.

Jeśli masz lokalnego Pythona 3, możesz sprawdzić cały przepływ skryptem:

```sh
python3 scripts/check_delivery.py
```

Skrypt wysyła jeden przykład i sprawdza odbiorcę, treść oraz `Reply-To` w Mailpit.

## Jak działa

1. FastAPI sprawdza adres i treść zgłoszenia.
2. LangChain przekazuje modelowi reguły działów i schemat `send_email(recipient)`.
3. Lokalny model Gemma4 12B wybiera odbiorcę przez wywołanie narzędzia.
4. Kod sprawdza wywołanie i wysyła oryginalną wiadomość przez SMTP.
5. API zwraca wynik; Mailpit pokazuje przechwycony e-mail.

Model może wybrać tylko jeden z pięciu adresów. Nie może zmienić treści,
adresu nadawcy ani dodać kopii do innych osób. Reguły działów i decyzje
techniczne opisuje [opis założeń](docs/design.md).

## Obsługa i konfiguracja

Domyślny model: `gemma4:12b-it-q4_K_M`. Opcjonalny plik `.env`, utworzony
na podstawie `.env.example`, pozwala zmienić model lub porty 8000 i 8025.
Inny model wymaga osobnego sprawdzenia polskiego języka i wywoływania narzędzi.

```sh
docker compose logs --tail=100 api
docker compose stop
docker compose up -d
```

Wagi pozostają w wolumenie między uruchomieniami. Mailpit domyślnie trzyma
pocztę tylko do restartu procesu. Po zmianie kodu przebuduj API poleceniem
`docker compose up -d --build`.

## Testy i wyniki

Testy kodu uruchomisz lokalnie przy użyciu Python 3.12–3.14 i [uv](https://docs.astral.sh/uv/):

```sh
uv sync --locked
uv run pytest -q tests
uv run ruff check mail_agent tests scripts
```

Testy sprawdzają walidację, wykonanie narzędzia, SMTP i monitoring. Model jest
w nich zastępowany kontrolowaną odpowiedzią. Osobny test rzeczywistego modelu
uzyskał **147/150 poprawnych przekazań** na syntetycznych polskich zgłoszeniach.
Referencje przygotowało AI; wynik nie określa skuteczności na rzeczywistej poczcie.
[Porównanie modeli i opis pomiaru](docs/model-comparison.md).

To lokalny PoC: bez logowania użytkowników i obsługi ruchu produkcyjnego.
Błędny wybór działu nadal jest możliwy. Po błędzie wysyłki nie ponawiaj
zapytania automatycznie — serwer mógł już przyjąć mail. Każde osobne zapytanie
może wysłać kolejną wiadomość.

[Uruchomienie lokalnego monitoringu Langfuse](docs/monitoring.md).
