# Jak sprawdzić obsługę wiadomości w Langfuse

Langfuse zapisuje kolejne etapy obsługi wiadomości. Pozwala zobaczyć, co
zwrócił model, jakie narzędzie zostało wywołane i ile trwała wysyłka.
Działa lokalnie. Podstawowa wersja programu uruchamia się bez niego.

## Włączenie

Do utworzenia haseł potrzebny jest Python 3. Uruchom w katalogu projektu:

```sh
python3 scripts/configure_monitoring.py
docker compose --env-file .env.langfuse -f docker-compose.yml -f compose.monitoring.yml up -d --build
```

Skrypt zapisze losowe hasła i klucze w `.env.langfuse`. Jeśli ten plik już
istnieje, zachowa go bez zmian. Plik jest wykluczony z Git i obrazu aplikacji;
zostaw go na swoim komputerze.

Otwórz [panel Langfuse](http://localhost:3000). Zaloguj się jako
`operator@example.com`, używając hasła z pola `LF_ADMIN_PASSWORD`
w `.env.langfuse`.

Pierwszy start może potrwać dłużej, ponieważ Langfuse przygotowuje własne
bazy i magazyn danych: PostgreSQL, ClickHouse, Redis i MinIO. Oprócz panelu
uruchamia proces przetwarzający zapisane zdarzenia. Usługi są skonfigurowane
według [oficjalnego przykładu](https://langfuse.com/self-hosting/deployment/docker-compose).
API może już odpowiadać, kiedy panel Langfuse jeszcze się uruchamia.

## Gdzie znaleźć wiadomość

Wyślij zapytanie z README. W panelu otwórz projekt **Mail Agent PoC**
i widok śladów wykonania. Każdy ślad to zapis obsługi jednego zapytania.
Odszukaj `request_id` z odpowiedzi API w metadanych śladu.

W środku są trzy etapy:

- `route-request` — przyjęcie zapytania i wynik całej obsługi;
- `ollama-routing` — wywołanie modelu, jego ustawienia, wynik i liczba tokenów;
- `send_email` — wybrany odbiorca i potwierdzenie przyjęcia maila przez SMTP.

Przy każdym etapie widać czas, a w razie błędu także jego oznaczenie.
Zapis odbywa się w tle, więc wiadomość może pojawić się w panelu z opóźnieniem.

Aby zatrzymać aplikację razem z monitoringiem, użyj:

```sh
docker compose --env-file .env.langfuse -f docker-compose.yml -f compose.monitoring.yml stop
```

## Jakie dane są zapisywane

Ta konfiguracja zapisuje treść zgłoszenia i instrukcję modelu, dlatego
używaj wymyślonych wiadomości testowych. Adres z pola `email` jest ukryty
w zapisie, ale dane osobowe wpisane w treść pozostają widoczne. Ukrytego
rozumowania modelu nie zapisujemy.

Langfuse pokazuje wykonane czynności, ale sam nie wie, czy wybrany dział
jest prawidłowy. Funkcja `record_scores` pozwala dopisać wynik porównania
z oczekiwanym odbiorcą. Zwykłe zapytanie nie zawiera oczekiwanego odbiorcy,
więc API nie wystawia mu automatycznie oceny jakości.

Zestawy wiadomości i skrypty użyte do wcześniejszych pomiarów nie są
udostępnione w repozytorium. [Opis testów i wyników](model-comparison.md)
wyjaśnia, co sprawdzano.

Zapis i odczyt danych sprawdzono na Langfuse 4.59.0 z SDK 5.0.1.
Jeśli monitoring przestanie działać, program nadal może wysłać mail.
Niezapisane ślady mogą jednak zaginąć, ponieważ aplikacja nie ma trwałej
kolejki oczekującej na ich ponowne przesłanie.
