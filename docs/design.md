# Założenia i budowa

Aplikacja przekazuje wewnętrzne zgłoszenia pracowników do działów przykładowej
firmy. Nie rozwiązuje zgłoszeń ani nie zatwierdza zakupów lub zmian uprawnień.

## Podział spraw

| Adres | Zakres |
|---|---|
| `human-resources@example.com` | Rekrutacja, szkolenia, rozwój, oceny i relacje pracownicze |
| `kadry@example.com` | Urlopy, czas pracy, nadgodziny, płace, dokumenty zatrudnienia i dane pracowników |
| `help-desk@example.com` | Diagnoza, naprawa i konfiguracja posiadanego sprzętu, aplikacje, logowanie i standardowy dostęp |
| `it@example.com` | Przydział, wymiana i rozbudowa sprzętu, infrastruktura, wspólne usługi, kopie zapasowe i cyberbezpieczeństwo |
| `other@example.com` | Sprawy poza zakresem, zbyt mało informacji lub niezależne prośby do różnych działów |

To przyjęty podział organizacyjny. W innej firmie katalog spraw może wyglądać
inaczej. Decyduje cel prośby: problem logowania do portalu urlopowego trafia
do help-desku, a rozliczenie urlopu do kadr. Awaria laptopa z sugestią wymiany
wymaga diagnozy help-desku; jednoznaczny wniosek o nowy laptop trafia do IT.

Jedna wiadomość ma jednego odbiorcę. Kilka próśb do tego samego działu trafia
do niego razem. Niezależne sprawy do różnych działów trafiają w całości do
`other`. Nie dzielimy treści ani nie rozsyłamy jej do kilku odbiorców.

## Przepływ

`POST /api/v1/route → FastAPI → LangChain → Ollama → send_email → Mailpit`

FastAPI zapewnia walidację i dokumentację OpenAPI. LangChain przekazuje
schemat narzędzia i odczytuje odpowiedź modelu. Ollama uruchamia model lokalnie.
Mailpit przechwytuje pocztę, dzięki czemu można sprawdzić wynik bez wysyłania
wiadomości do ludzi. API korzysta z oficjalnego obrazu Pythona.

Agent wykonuje jedno wywołanie modelu i jedno narzędzie. Nie ma dodatkowej
pętli planowania: zadanie kończy się po potwierdzeniu SMTP. To wystarcza do
wyboru odbiorcy i przekazania wiadomości.

| Plik | Odpowiedzialność |
|---|---|
| `mail_agent/api.py` | HTTP, gotowość usług, odpowiedzi i błędy |
| `mail_agent/contracts.py` | Pola wejściowe, odpowiedź i dozwoleni odbiorcy |
| `mail_agent/agent.py` | Wywołanie modelu, kontrola i wykonanie narzędzia |
| `mail_agent/prompt.py` | Instrukcja wyboru działu |
| `mail_agent/mailer.py` | Oryginalna treść, nagłówki i SMTP |
| `mail_agent/config.py` | Konfiguracja ze zmiennych środowiskowych |
| `mail_agent/observability.py` | Ślady wykonania w Langfuse i zapis ocen |

## Granice wykonania

Treść zgłoszenia jest niezaufana. Model dostaje ją jako zakodowane pole JSON,
ale samo kodowanie nie gwarantuje odporności na manipulacje. Kod sprawdza,
czy model wywołał dokładnie jedno `send_email` z jedynym argumentem `recipient`
i adresem z listy. Brak wywołania, dodatkowe pola lub kilka wywołań blokują wysyłkę.

Treść i `Reply-To` pochodzą z walidowanego zapytania, a nie z odpowiedzi modelu.
Model nie dostaje narzędzi do plików, terminala ani przeglądarki. SMTP nie jest
ponawiane po błędzie, ponieważ wynik przerwanego połączenia bywa niejednoznaczny.
Nie ma deduplikacji osobnych zapytań HTTP.

| Ograniczenie | Wartość |
|---|---|
| Treść | 1–8000 znaków, nie może zawierać samych odstępów |
| Oczekiwanie na odpowiedź modelu | 120 s, timeout klienta HTTP |
| Oczekiwanie SMTP | 10 s |
| Wywołania narzędzia | Dokładnie jedno |
| Model | Gemma4 12B GGUF Q4_K_M |
| Parametry modelu | Temperatura 0, kontekst 8192, maksymalnie 512 generowanych tokenów |

Limit znaków nie jest limitem całego żądania HTTP ani gwarancją zmieszczenia
każdego tekstu w kontekście. Model dostaje reguły bez przykładów; nie stosujemy
fine-tuningu. Ustawienie temperatury 0 nie jest gwarancją identycznych wyników
między wersjami środowiska.

Błędne wejście daje HTTP 422. Nieprawidłowe wywołanie narzędzia lub awaria
usługi daje 502, a timeout modelu 504. `other` oznacza kategorię wiadomości,
a nie awarię. Sukces 200 następuje po potwierdzeniu SMTP.

## Start i dane

Compose najpierw uruchamia Ollamę, a usługa `model-init` pobiera model.
API startuje po zakończeniu inicjalizacji. `/health/ready` sprawdza obecność
modelu i odpowiedź SMTP. Nie wykonuje generacji ani nie gwarantuje, że model
jest już załadowany do RAM. Internet jest potrzebny przy pobieraniu zależności;
sama obsługa zgłoszeń używa lokalnych usług.

Wagi są trwałe, skrzynka Mailpit domyślnie nie jest. Porty są dostępne tylko
przez localhost. Podstawowy start nie wymaga sekretów ani monitoringu.
Opcjonalny lokalny Langfuse ma własne bazy i klucze, generowane na komputerze.
Rejestruje etapy oraz błędy; jego awaria nie blokuje wysyłki, ale ślad może zaginąć.

## Zakres jakości

Testy kodu i pomiar jakości modelu są oddzielne. W pomiarze 150 nowych
syntetycznych wiadomości trzy trafiły do niewłaściwego działu. Granica między
wyposażeniem IT a sprawami biurowymi oraz odebranie dostępów wymagają szczególnej
uwagi przy dostosowaniu polityki do firmy. Wyniki opisuje [porównanie modeli](model-comparison.md).
To demonstracja integracji, bez uwierzytelniania, limitowania ruchu i testu obciążeniowego.
