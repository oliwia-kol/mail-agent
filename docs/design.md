# Jak zbudowany jest program

Program obsługuje wiadomości pracowników do wewnętrznych działów firmy.
Jego zadaniem jest wybranie odbiorcy i przekazanie całej wiadomości.
Prośba o zakup sprzętu pozostaje prośbą — wysłanie jej do IT nie zatwierdza zakupu.

## Który dział dostaje wiadomość

| Adres | Sprawy |
|---|---|
| `human-resources@example.com` | Rekrutacja, szkolenia, rozwój, oceny pracy i relacje między pracownikami |
| `kadry@example.com` | Urlopy, czas pracy, nadgodziny, płace, dokumenty zatrudnienia i dane pracowników |
| `help-desk@example.com` | Naprawa i konfiguracja posiadanego sprzętu, problemy z aplikacjami, logowaniem i zwykłym dostępem |
| `it@example.com` | Przydział, wymiana i rozbudowa sprzętu, infrastruktura, wspólne usługi, kopie zapasowe i cyberbezpieczeństwo |
| `other@example.com` | Pozostałe sprawy, wiadomości zbyt niejasne lub zawierające osobne prośby do różnych działów |

Ten podział przyjęto na potrzeby projektu. W konkretnej firmie część obowiązków
może być przypisana inaczej.

Liczy się to, o co prosi nadawca. Jeśli nie może zalogować się do portalu
urlopowego, wiadomość trafia do help-desku. Jeśli chce rozliczyć urlop,
trafia do kadr. „Laptop nie działa, może trzeba go wymienić” to prośba
o diagnozę dla help-desku. „Proszę o przydział nowego laptopa” trafia do IT.

Jedna wiadomość ma jednego odbiorcę. Kilka próśb do tego samego działu może
trafić do niego razem. Jeśli prośby dotyczą różnych działów, cała wiadomość
trafia do `other@example.com`. Program nie dzieli jej na osobne maile.

## Obsługa wiadomości

1. FastAPI przyjmuje `email` i `message`, a następnie sprawdza ich poprawność.
2. LangChain przekazuje do Ollamy instrukcję wyboru działu i opis funkcji wysyłki.
3. Model zwraca wywołanie `send_email` z adresem odbiorcy.
4. Kod sprawdza wywołanie, ustawia treść oraz nagłówki i łączy się z Mailpit przez SMTP.
5. Po przyjęciu maila przez serwer API zwraca wynik.

Model jest pytany raz. Ma wybrać dział i wywołać funkcję, więc dodatkowa
pętla planowania nie jest tu potrzebna. FastAPI udostępnia też dokumentację
API, a Mailpit pozwala obejrzeć wynik wysyłki. Kontener aplikacji korzysta
z oficjalnego obrazu Pythona.

## Co znajduje się w plikach

| Plik | Zawartość |
|---|---|
| `mail_agent/api.py` | Obsługa zapytań HTTP, sprawdzanie gotowości i zwracanie błędów |
| `mail_agent/contracts.py` | Wymagane pola zapytania, format odpowiedzi i lista odbiorców |
| `mail_agent/agent.py` | Rozmowa z modelem oraz sprawdzenie i wykonanie jego wywołania |
| `mail_agent/prompt.py` | Instrukcja, według której model wybiera dział |
| `mail_agent/mailer.py` | Przygotowanie maila i wysyłka przez SMTP |
| `mail_agent/config.py` | Odczyt ustawień ze zmiennych środowiskowych |
| `mail_agent/observability.py` | Zapis przebiegu obsługi i wyników testów w Langfuse |

## Co sprawdza kod

Tekst wiadomości może zawierać polecenia skierowane do modelu, także próbę
zmiany odbiorcy lub zasad. Dlatego aplikacja traktuje go jako dane do
sklasyfikowania. Przekazuje go w polu JSON, a przed wysyłką sprawdza wynik:

- wywołana funkcja musi nazywać się `send_email`;
- musi wystąpić dokładnie jedno wywołanie;
- jedynym argumentem jest `recipient`, z adresem z dozwolonej listy.

Niepoprawne wywołanie zatrzymuje wysyłkę. Poprawny format nie daje jednak
pewności, że model wybrał właściwy dział.

Treść maila i `Reply-To` pochodzą z zapytania do API. Model nie ustawia
kopii CC lub BCC i nie ma funkcji pozwalających czytać pliki czy wykonywać
polecenia systemowe.

Po błędzie SMTP kod nie próbuje wysyłać ponownie. Przerwane połączenie może
oznaczać, że serwer przyjął mail, ale potwierdzenie nie dotarło do aplikacji.
Osobne zapytania HTTP są obsługiwane osobno, również gdy mają tę samą treść.

## Ustawienia i błędy

| Ustawienie | Wartość |
|---|---|
| Długość wiadomości | 1–8000 znaków; same odstępy są odrzucane |
| Czas oczekiwania w kliencie HTTP modelu | 120 s |
| Czas oczekiwania na operację SMTP | 10 s |
| Liczba wywołań funkcji wysyłki | Dokładnie jedno |
| Model | Gemma4 12B GGUF Q4_K_M |
| Temperatura | 0 |
| Długość kontekstu | 8192 tokeny |
| Limit odpowiedzi modelu | 512 tokenów |

Tokeny to jednostki tekstu używane przez model. Limit 8000 znaków dotyczy
pola `message`; nie określa wielkości całego zapytania ani nie gwarantuje,
że dowolny tekst zmieści się w kontekście. Model korzysta z instrukcji bez
przykładów. Nie był dodatkowo trenowany do tego projektu. Temperatura 0
ogranicza losowość, ale nie zapewnia identycznych odpowiedzi we wszystkich
wersjach środowiska.

| Status HTTP | Znaczenie |
|---|---|
| 200 | Serwer pocztowy przyjął wiadomość |
| 422 | Dane wejściowe są niepoprawne |
| 502 | Błąd modelu, wywołania funkcji lub wysyłki |
| 504 | Przekroczony czas oczekiwania na model |

Kategoria `other` służy do przekazywania nierozpoznanych spraw.
Awaria usługi kończy się błędem HTTP.

## Uruchomienie i przechowywanie danych

Compose uruchamia Ollamę, po czym `model-init` pobiera model. API startuje
po zakończeniu pobierania. Endpoint `/health/ready` sprawdza, czy model jest
dostępny i serwer SMTP odpowiada. Nie wykonuje zapytania do modelu, więc
pierwsza odpowiedź może być wolniejsza przez ładowanie go do pamięci.

Pliki modelu zostają w wolumenie Dockera, czyli wydzielonym miejscu na dane
kontenera. Poczta Mailpit domyślnie znika po restarcie jego procesu.
Porty są udostępnione tylko na lokalnym komputerze, przez `localhost`.
Internet jest potrzebny do pobrania modelu i obrazów; obsługa wiadomości
odbywa się lokalnie.

Langfuse można dołączyć osobno. Ma własne bazy, a klucze i hasła tworzy
lokalny skrypt. Awaria Langfuse nie zatrzymuje wysyłki, ale zapis przebiegu
obsługi może przepaść. [Instrukcja monitoringu](monitoring.md).

W [teście 150 wiadomości](model-comparison.md) wystąpiły trzy pomyłki wyboru
działu. Dotyczyły wyposażenia biura i odebrania dostępów pracownikowi.
Te granice trzeba ustalić dokładnie przy dopasowaniu programu do firmy.
Program nie ma logowania użytkowników, ograniczenia liczby zapytań ani testu
pracy pod dużym obciążeniem.
