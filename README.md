# Mail Agent

Program przyjmuje wiadomość od pracownika i przekazuje ją do odpowiedniego
działu. Na przykład prośba o urlop trafia do kadr, a problem z logowaniem
do help-desku. Odbiorcę wybiera lokalny model językowy, który wywołuje funkcję
wysyłającą e-mail.

Maile można obejrzeć w testowej skrzynce Mailpit. Każdy zawiera oryginalną
treść i adres nadawcy w nagłówku `Reply-To`, aby dział mógł mu odpowiedzieć.

## Uruchomienie

Potrzebny jest Docker z aktualnym Docker Compose oraz internet do pobrania
obrazów kontenerów i modelu. Podstawowe uruchomienie nie wymaga kluczy API.

```sh
git clone https://github.com/oliwia-kol/mail-agent.git
cd mail-agent
docker compose up -d
```

Compose sam zbuduje aplikację i pobierze model. Same pliki modelu zajmują
około 8 GB; obrazy kontenerów potrzebują dodatkowego miejsca. Program sprawdzono
na Macu M4 z 24 GB RAM i z przydziałem 16 GB dla Dockera. Model w kontenerze
korzystał z procesora CPU.

Po pobraniu sprawdź, czy aplikacja jest gotowa:

```sh
curl http://localhost:8000/health/ready
```

Odpowiedź `{"status":"ready"}` oznacza, że model jest pobrany, a serwer
pocztowy odpowiada. Pierwsze zapytanie może potrwać około minuty, ponieważ
model musi się jeszcze załadować do pamięci.

Jeśli aplikacja jeszcze nie odpowiada, sprawdź postęp pobierania:

```sh
docker compose logs -f model-init
```

Usługa `model-init` kończy pracę po pobraniu modelu. Kod zakończenia 0 oznacza,
że pobieranie się udało.

## Wyślij wiadomość

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

Otwórz [Mailpit](http://localhost:8025). Powinna tam być jedna wiadomość do
`kadry@example.com`, z treścią zgłoszenia i `Reply-To: ola@example.com`.
Status `smtp_accepted` oznacza, że serwer pocztowy przyjął mail. Mailpit
zatrzymuje wiadomości u siebie — nie wysyła ich do rzeczywistych odbiorców.

Zapytanie możesz też wysłać z formularza w [dokumentacji API](http://localhost:8000/api/v1/docs).
Jeśli masz Pythona 3, skrypt sprawdzi wysyłkę i zawartość przechwyconego maila:

```sh
python3 scripts/check_delivery.py
```

Po błędzie nie ponawiaj wysyłki automatycznie. Serwer mógł już odebrać mail,
nawet jeśli aplikacja nie dostała potwierdzenia. Kolejne zapytanie może wysłać
wiadomość drugi raz.

## Jak działa program

FastAPI sprawdza adres nadawcy i treść wiadomości. Następnie LangChain
przekazuje modelowi reguły wyboru działu i opis funkcji `send_email(recipient)`.
Model działa lokalnie w Ollamie. Zwraca wywołanie tej funkcji z wybranym adresem,
a kod sprawdza argument i wysyła mail przez SMTP, czyli protokół pocztowy.

Kod dopuszcza pięć adresów i jedną wysyłkę na zapytanie. Treść maila oraz
`Reply-To` pobiera z zapytania, więc model nie ustala ich ponownie.
[Podział działów, pliki programu i przyjęte ograniczenia](docs/design.md).

Domyślny model to `gemma4:12b-it-q4_K_M`. Aby zmienić model lub porty 8000
i 8025, skopiuj `.env.example` do `.env` i zmień odpowiednie wartości.
Inny model trzeba osobno sprawdzić na polskich wiadomościach i wywołaniach funkcji.

## Zatrzymanie i ponowny start

```sh
docker compose stop
docker compose up -d
```

Pobrany model zostaje na dysku. Wiadomości w Mailpit znikają po restarcie
jego procesu. Po zmianie kodu użyj `docker compose up -d --build`.
Logi aplikacji pokaże `docker compose logs --tail=100 api`.

## Testy

Do uruchomienia testów na komputerze potrzebne są Python 3.12–3.14 i [uv](https://docs.astral.sh/uv/):

```sh
uv sync --locked
uv run pytest -q tests
uv run ruff check mail_agent tests scripts
```

Testy sprawdzają dane wejściowe, wywołanie funkcji, wysyłkę i monitoring.
Zamiast pytać model, podstawiają przygotowane odpowiedzi, aby sprawdzić
zachowanie kodu także przy błędach.

Osobno sprawdzono prawdziwy model: poprawnie przekazał **147 ze 150**
przygotowanych wiadomości. Wiadomości i oczekiwanych odbiorców opracowało AI.
[Opis testu, porównanie modeli i trzy pomyłki](docs/model-comparison.md).

Program służy do lokalnych testów. Nie ma logowania użytkowników i nie był
sprawdzany pod dużym obciążeniem. Wynik testu modelu nie określa skuteczności
na rzeczywistej poczcie firmy.

Opcjonalnie możesz włączyć [Langfuse](docs/monitoring.md), żeby zobaczyć kolejne
etapy obsługi wiadomości, ich czas i błędy.
