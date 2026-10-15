# Porównanie modeli

Do programu wybrano **Gemmę4 12B GGUF Q4_K_M** (`gemma4:12b-it-q4_K_M`).
W lokalnym teście poprawnie wybrała dział i użyła funkcji wysyłki we wszystkich
sprawdzanych przypadkach. Następnie przeszła osobny test 150 nowych wiadomości
z wynikiem 147 poprawnych przekazań. Pomiary wykonano 15 października 2026.

## Jak porównano modele

Każdy model dostał te same 35 polskich zgłoszeń, po 7 na dział. Dodatkowe
20 prób zawierało polecenia mające nakłonić model do złamania zasad. Te próby
powstały na podstawie pięciu zgłoszeń ze znanym odbiorcą.

Oczekiwanych odbiorców sprawdził człowiek. Oczekiwania dla prób manipulacji
zatwierdzono po próbnym uruchomieniu, bez zmiany etykiet. Wiadomości wymyślono
na potrzeby projektu lub opracowano na podstawie publicznych zbiorów.
Nie były losową próbką poczty firmowej.

Modele dostały tę samą instrukcję `routing-v2-zero-shot`, bez przykładów.
Nie były dodatkowo trenowane. Ustawienia: temperatura 0, wyłączony tryb
rozumowania, kontekst 8192 tokeny, odpowiedź do 512 tokenów i czas oczekiwania
120 s. Instrukcję wcześniej poprawiano na tych danych, więc wyniki służyły
do wyboru modelu, a nie do niezależnej oceny gotowego rozwiązania.

Zapytania przechodziły przez klienta testowego FastAPI, prawdziwy model
w Ollamie, funkcję wysyłki i lokalny serwer SMTP aiosmtpd.
Aby zaliczyć próbę, model musiał wywołać narzędzie, a serwer otrzymać dokładnie
jeden mail do oczekiwanego działu, z właściwą treścią i `Reply-To`.
Błędy wywołania i błędne adresowanie pozostawały w wyniku.

## Wyniki porównania

Kolumny „Zgłoszenia” i „Próby manipulacji” pokazują liczbę zaliczonych prób.
„Wywołania” oznaczają samą poprawność funkcji i jej argumentów, niezależnie
od tego, czy wybrany dział był właściwy.

| Model | Zgłoszenia | Wywołania dla zgłoszeń | Próby manipulacji | Wywołania dla manipulacji | Mediana czasu |
|---|---:|---:|---:|---:|---:|
| Qwen3.5 9B Q4_K_M | 34/35 | 35/35 | 15/20 | 20/20 | 6,54 s |
| Bielik 11B v3 Q4_K_M | 35/35 | 35/35 | 14/20 | 18/20 | 2,72 s |
| Ministral3 8B Q4_K_M | 33/35 | 35/35 | 19/20 | 19/20 | 1,17 s |
| Gemma4 12B MLX NVFP4 | 35/35 | 35/35 | 20/20 | 20/20 | 1,26 s |
| **Gemma4 12B GGUF Q4_K_M** | **35/35** | **35/35** | **20/20** | **20/20** | **1,31 s** |

Łącznie wykonano 275 prób: ten sam zestaw 55 wiadomości dla pięciu
konfiguracji z czterech rodzin modeli. Nie było to 275 różnych spraw.
W wysłanych mailach zachowano treść i nagłówki. Kod blokował błędne lub
wielokrotne wywołania przed połączeniem z SMTP. Mail do niewłaściwego działu
był błędem, nawet jeśli jego wysyłka przebiegła poprawnie.

Czas obejmuje obsługę zapytania, odpowiedź modelu i wysyłkę. Mediana to
środkowa wartość zmierzonych czasów. W tabeli dotyczy zwykłych zgłoszeń.

## Dlaczego Gemma

Oba warianty Gemmy zaliczyły wszystkie próby. Do kontenerów wybrano wariant
GGUF, który sprawdzono osobno. Wyniki nie uzasadniały dodawania przykładów
do instrukcji ani dodatkowego trenowania modelu.

Bielik radził sobie ze zwykłymi zgłoszeniami, ale częściej mylił się przy
manipulacjach. Wyniki zależały także od instrukcji i wybranej wersji modelu;
nie opisują możliwości wszystkich modeli z tej rodziny.

Porównanie wykonano na Macu M4 z 24 GB RAM. Wersje: Ollama 0.40.4,
Python 3.14.3, langchain-ollama 1.1.0, langchain-core 1.6.10,
klient ollama 0.6.3 i FastAPI 0.143.2. Modele uruchamiano kolejno.
Warianty MLX i GGUF korzystały z innych sposobów uruchamiania i kwantyzacji,
czyli zmniejszenia precyzji zapisu wag modelu.

## Sprawdzenie w kontenerach

Wybraną Gemmę uruchomiono w Docker Compose razem z API i Mailpit.
Pięć zwykłych zgłoszeń, po jednym na dział, i te same 20 prób manipulacji
zakończyły się poprawną wysyłką. Sprawdzono jednego odbiorcę, treść,
`Reply-To` oraz zapis etapów obsługi w lokalnym Langfuse.

Kontenery działały jako linux/arm64 na Macu M4, z 16 GB RAM dla Dockera.
Ollama 0.40.4 korzystała z CPU, a API z Pythona 3.14.8.
Pierwsza odpowiedź, razem z ładowaniem modelu, zajęła 59,20 s.
Mediana kolejnych pięciu zgłoszeń z monitoringiem wyniosła 4,46 s,
a 20 prób manipulacji 6,85 s. Nie mierzono osobno czasu dodanego przez Langfuse.
Ponownie użyto wcześniejszych wiadomości; nie był to nowy zestaw testowy.

## Test 150 nowych wiadomości

Po wyborze modelu przygotowano 150 nowych wiadomości po polsku, po 30 na
dział: 20 typowych, 7 na granicy kategorii i 3 trudniejsze językowo lub
kontekstowo. Treści i oczekiwanych odbiorców opracował oraz sprawdził Codex.
Nie było niezależnego przeglądu przez człowieka. Oceniana Gemma nie ustalała,
jakie odpowiedzi uznać za poprawne.

Przed testem zapisano stałą wersję danych, instrukcji i konfiguracji.
Po obejrzeniu wyników nie zmieniano wiadomości ani oczekiwanych odbiorców.

| Dział | Poprawnie przekazane wiadomości |
|---|---:|
| HR | 30/30 |
| Kadry | 30/30 |
| Help-desk | 30/30 |
| IT | 29/30 |
| Other | 28/30 |
| Razem | **147/150 (98%)** |

Każde zapytanie przeszło przez działające API, model w kontenerze, funkcję
wysyłki i Mailpit. Wszystkie 150 wywołań miało poprawny format, a maile
zachowały treść i `Reply-To`. Trzy miały niewłaściwego odbiorcę.
Dla każdej próby odczytano trzy etapy obsługi i zapisano cztery wyniki oceny
w Langfuse. Zapytania wysyłano po jednym razie, bez automatycznych powtórzeń.

Pomyłki dotyczyły następujących spraw:

- Klucz do magazynku trafił do IT; oczekiwano `other`.
- Fotel biurowy trafił do IT; oczekiwano `other`.
- Odebranie dostępów odchodzącemu pracownikowi trafiło do kadr; oczekiwano IT.

W tych odpowiedziach przyjęto, że IT zajmuje się sprzętem informatycznym,
a nie całym wyposażeniem biura. Odebranie dostępów zinterpretowano jako
administrację uprawnieniami do systemów, choć wiadomość nie nazywała ich
wprost. To miejsca, w których granice działów wymagają szczególnej uwagi.

Wynik przekroczył ustalone przed testem minimum: 90% ogółem i 80% w każdym
dziale. Mediana czasu wyniosła 4,505 s, a 90% zapytań trwało nie dłużej niż
5,954 s w opisanym środowisku CPU.

Wiadomości przygotowano ze znajomością wcześniejszych wyników. To test
wymyślonych scenariuszy z odpowiedziami opracowanymi przez AI, a nie pomiar
skuteczności na poczcie rzeczywistej firmy. Pozostałych modeli nie sprawdzano
na tych 150 przykładach. Wyniki 100% z wcześniejszej tabeli dotyczą tylko
opisanych prób, a nie wszystkich możliwych wiadomości lub ataków.

## Dokumentacja techniczna

- [Wywoływanie narzędzi w Ollamie](https://docs.ollama.com/capabilities/tool-calling)
- [ChatOllama w LangChain](https://docs.langchain.com/oss/python/integrations/chat/ollama)
- [Gemma4](https://ollama.com/library/gemma4)
- [Ministral3](https://ollama.com/library/ministral-3)
- [Bielik](https://ollama.com/SpeakLeash/bielik-11b-v3.0-instruct)
- [Próby manipulowania instrukcją modelu — OWASP](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)

Linki opisują modele i integracje. Liczby w tabelach pochodzą z testów projektu.
