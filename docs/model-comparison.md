# Wybór modelu do routingu wiadomości

Pomiar: 15 października 2026. Wybrano **Gemma4 12B GGUF Q4_K_M**
(`gemma4:12b-it-q4_K_M`) na podstawie lokalnego porównania routingu i odporności.
Model działa przez Ollamę i wywołuje narzędzie LangChain wysyłające e-mail.

## Metoda

Każda konfiguracja otrzymała te same 35 polskich zgłoszeń roboczych, po 7 na
dział, oraz 20 osobnych wariantów manipulacji instrukcjami. Warianty ataków
powstały z pięciu zatwierdzonych spraw. Referencje zatwierdzono przez człowieka;
nie były odpowiedziami modelu ocenianego. Scenariusze są syntetyczne lub
przetworzone z publicznych źródeł i nie stanowią losowej poczty realnej firmy.
Oczekiwania prób manipulacji zaakceptowano po diagnostyce, bez zmiany etykiet.

Użyto wspólnej instrukcji `routing-v2-zero-shot`, bez demonstracji i fine-tuningu.
Ustawienia: temperatura 0, wyłączone rozumowanie, kontekst 8192, limit generacji
512 tokenów, timeout modelu 120 s. Instrukcję wcześniej poprawiono na danych
roboczych; jest to pomiar doboru konfiguracji, nie niezależna walidacja końcowa.

Przepływ pomiaru: klient testowy FastAPI → rzeczywista Ollama → wywołanie narzędzia →
wykonanie funkcji → rzeczywisty lokalny SMTP aiosmtpd. Sprawdzano dział,
liczbę wiadomości, treść, Reply-To i powiązanie maila z requestem. Brak wywołania,
błędne argumenty i błędny dział pozostawały w mianowniku. Nie zastępowano
wywołania narzędzia odczytaniem adresu ze zwykłej odpowiedzi tekstowej.

## Wyniki

| Konfiguracja | Pełny sukces: zgłoszenia | Poprawne wywołanie: zgłoszenia | Pełny sukces: manipulacje | Poprawne wywołanie: manipulacje | Mediana zwykłego requestu |
|---|---:|---:|---:|---:|---:|
| Qwen3.5 9B Q4_K_M | 34/35 | 35/35 | 15/20 | 20/20 | 6,54 s |
| Bielik 11B v3 Q4_K_M | 35/35 | 35/35 | 14/20 | 18/20 | 2,72 s |
| Ministral3 8B Q4_K_M | 33/35 | 35/35 | 19/20 | 19/20 | 1,17 s |
| Gemma4 12B MLX NVFP4 | 35/35 | 35/35 | 20/20 | 20/20 | 1,26 s |
| **Gemma4 12B GGUF Q4_K_M** | **35/35** | **35/35** | **20/20** | **20/20** | **1,31 s** |

Łącznie: 275 requestów w pięciu konfiguracjach czterech rodzin. Nie są to
275 niezależne sprawy. We wszystkich wysłanych wiadomościach zachowano
poprawne nagłówki i treść. Niepoprawne lub wielokrotne wywołania blokowano przed
SMTP. Wysłanie do złego dozwolonego działu nadal było błędem pełnego zadania.

## Uzasadnienie wyboru i ograniczenia

Gemma uzyskała komplet poprawnych wyników w obu pulach, również w osobno
sprawdzonym GGUF, który wybrano do dalszej integracji kontenerowej. Nie było
potrzeby dodawania przykładów do promptu ani dostrajania wag.

Wyniki Bielika zależały od instrukcji i dystrybucji: słabszy wynik wcześniejszej
konfiguracji nie oznacza niezdolności całej rodziny do używania narzędzi.
Zachowanie modelu i zabezpieczenia kodu oceniano osobno; sama poprawność
schematu nie zapobiega skierowaniu do niewłaściwego działu.

Sprzęt pomiarowy: Apple M4, 24 GB. Ollama 0.40.4, Python 3.14.3,
langchain-ollama 1.1.0, langchain-core 1.6.10, klient ollama 0.6.3,
FastAPI 0.143.2. Modele uruchamiano kolejno. Mediana obejmuje request, model
i SMTP, nie tylko generację. MLX i GGUF różnią się backendem i kwantyzacją.

Sto procent dotyczy opisanej próby roboczej, nie dowolnej wiadomości lub ataku.
Tabela opisuje pomiar na hoście; sprawdzenie kontenerów opisano osobno poniżej.

## Sprawdzenie kontenerów

Wybraną Gemmę GGUF uruchomiono również przez Docker Compose: sieciowe API,
Ollama w kontenerze, prawdziwe narzędzie i Mailpit. Pięć zwykłych zgłoszeń,
po jednym na dział, oraz te same 20 zatwierdzonych manipulacji zakończyły się
poprawnym mailem: 5/5 i 20/20. Sprawdzono treść, odbiorcę, Reply-To,
jedną wiadomość na request i ślady trzech etapów w lokalnym Langfuse.

Środowisko: linux/arm64 w Docker Desktop na Macu M4, 16 GB dla Dockera,
Ollama 0.40.4, Python 3.14.8, obliczenia na CPU. Pierwszy request z ładowaniem
modelu: 59,20 s. Mediana pięciu kolejnych zgłoszeń z monitoringiem: 4,46 s;
mediana 20 manipulacji: 6,85 s. Nie jest to porównawczy pomiar narzutu Langfuse.
Ta kontrola integracji ponownie używa danych roboczych i nie zwiększa liczby
niezależnych przykładów ani nie zastępuje końcowego testu.

## Osobny test 150 nowych zgłoszeń

Po wyborze modelu przygotowano 150 nowych polskich zgłoszeń syntetycznych,
po 30 na dział: 20 typowych, 7 granicznych i 3 utrudnione językowo lub
kontekstem. Treści i referencje opracował oraz skontrolował Codex, bez
niezależnego przeglądu człowieka. Oceniana Gemma nie ustalała etykiet.
Dane, prompt i konfigurację zamrożono przed testem; nie zmieniano ich po wynikach.

| Dział | Pełny sukces |
|---|---:|
| HR | 30/30 |
| Kadry | 30/30 |
| Help-desk | 30/30 |
| IT | 29/30 |
| Other | 28/30 |
| Razem | **147/150 (98%)** |

Każda próba przeszła sieciowe API, kontener Ollamy, rzeczywisty wywołanie narzędzia
i Mailpit. Poprawność formatu wywołania, wykonania, oryginalnej treści i Reply-To:
150/150. Odczytano trzy obserwacje każdego requestu i zapisano cztery wyniki
oceny w Langfuse. Nie ponawiano automatycznie requestów.

Trzy błędy wyboru działu pozostały w wyniku: fizyczny klucz i fotel biurowy
trafiły do IT zamiast do other, a odebranie dostępów odchodzącemu pracownikowi
do kadr zamiast do IT. To wynik względem przyjętej polityki i referencji AI.

Wcześniej ustalone progi PoC, 90% ogółem i 80% na dział, zostały spełnione.
Mediana requestu: 4,505 s, p90: 5,954 s na CPU w opisanym środowisku.
Zbiór powstał po wyborze modelu, ze znajomością wcześniejszych wyników,
i nie jest losową pocztą firmy. 98% nie oznacza skuteczności produkcyjnej.
To dodatkowy sprawdzian wybranej konfiguracji; innych modeli nie porównywano
ponownie na tych 150 zgłoszeniach.

Źródła techniczne: [Ollama — narzędzia](https://docs.ollama.com/capabilities/tool-calling),
[LangChain — ChatOllama](https://docs.langchain.com/oss/python/integrations/chat/ollama),
[Gemma4](https://ollama.com/library/gemma4),
[Ministral3](https://ollama.com/library/ministral-3),
[Bielik](https://ollama.com/SpeakLeash/bielik-11b-v3.0-instruct),
[OWASP — prompt injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/).
Źródła opisują integracje; wartości w tabeli pochodzą z lokalnych pomiarów.
