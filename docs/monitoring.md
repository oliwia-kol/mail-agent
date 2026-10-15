# Lokalny monitoring Langfuse

Langfuse pokazuje przebieg obsługi wiadomości: wejście, wywołanie modelu,
narzędzie, wynik, czas i błędy. Działa lokalnie i jest opcjonalny.

## Uruchomienie

Oprócz Dockera potrzebny jest Python 3 do jednorazowego wygenerowania haseł:

```sh
python3 scripts/configure_monitoring.py
docker compose --env-file .env.langfuse -f docker-compose.yml -f compose.monitoring.yml up -d --build
```

Panel: [localhost:3000](http://localhost:3000). Konto: `operator@example.com`.
Hasło odczytasz z pola `LF_ADMIN_PASSWORD` w lokalnym `.env.langfuse`.
Skrypt nie nadpisuje istniejącego pliku. Nie udostępniaj tego pliku ani nie
przenoś kluczy do kodu. Git i Docker wykluczają go z publikacji.

Pierwszy start inicjalizuje PostgreSQL, ClickHouse, Redis i MinIO.
Panel i proces worker korzystają z tych usług; gotowość API nie oznacza
jeszcze gotowości panelu. Układ bazuje na [oficjalnym Compose Langfuse](https://langfuse.com/self-hosting/deployment/docker-compose).

## Odczyt przykładu

Wyślij zapytanie z README i otwórz projekt Mail Agent PoC w panelu.
W widoku śladów odszukaj obsługę po `request_id` z odpowiedzi API, zapisanym
w metadanych. Ślad zawiera:

- `route-request` — całą obsługę zapytania;
- `ollama-routing` — model, wersję instrukcji, argumenty wywołania i liczbę tokenów;
- `send_email` — odbiorcę i potwierdzenie SMTP.

Błędy są oznaczane przy etapie, w którym wystąpiły. Zapis jest asynchroniczny,
więc ślad może pojawić się z opóźnieniem. Pełny zestaw usług zatrzymasz przez:

```sh
docker compose --env-file .env.langfuse -f docker-compose.yml -f compose.monitoring.yml stop
```

## Dane i ocena

Profil demonstracyjny zapisuje treść zgłoszenia i instrukcję modelu.
Używaj danych syntetycznych. Pole adresu nadawcy jest maskowane, ale dane
wpisane w treść nie są automatycznie anonimizowane. Ukryte rozumowanie modelu
nie jest rejestrowane.

Sam ślad nie mówi, czy dział wybrano prawidłowo. Funkcja `record_scores`
pozwala zapisać wynik porównania z odpowiedzią referencyjną. Zwykłe zapytania
API nie mają takiej referencji, więc nie otrzymują automatycznej oceny jakości.
Zestawy i skrypty wcześniejszej oceny nie są częścią tego repozytorium;
[opis metody i wyników](model-comparison.md) zawiera zakres pomiaru.

Sprawdzono zapis i odczyt śladów oraz ocen w Langfuse 4.59.0 z SDK 5.0.1.
Awaria monitoringu nie ponawia SMTP i nie blokuje wysyłki. Integracja nie ma
trwałej kolejki, więc nie gwarantuje odzyskania niezapisanych śladów po awarii.
