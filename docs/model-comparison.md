# Ocena modeli

| Element | Wartość |
|---|---|
| Data pomiarów | 15 października 2026 |
| Wybrany model | Gemma4 12B GGUF Q4_K_M |
| Model w Ollamie | `gemma4:12b-it-q4_K_M` |
| Instrukcja | `routing-v2-zero-shot` |
| Dane porównawcze | 35 zgłoszeń i 20 prób manipulacji |
| Dodatkowy zestaw wybranego modelu | 150 nowych zgłoszeń syntetycznych |

## Kryteria oceny

Zaliczenie próby wymaga poprawnego wywołania `send_email`, właściwego działu,
jednej wiadomości przyjętej przez SMTP oraz zgodności treści i `Reply-To`.
Brak wywołania, błędne argumenty i błędny dział są wliczane do wyników jako błędy.

Poprawność formatu wywołania jest liczona niezależnie od wyboru działu.
Mail do błędnego, ale dozwolonego odbiorcy może mieć poprawne argumenty
narzędzia i nadal oznacza niezaliczoną próbę.

## Porównanie konfiguracji

Każda konfiguracja otrzymała ten sam zestaw 35 polskich zgłoszeń, po 7 na
dział, oraz 20 prób zmiany instrukcji modelu. Próby manipulacji były wariantami
pięciu zgłoszeń. Oczekiwani odbiorcy zostali sprawdzeni przez człowieka;
oczekiwania dla manipulacji zatwierdzono po diagnostyce, bez zmiany etykiet.
Dane były syntetyczne lub opracowane z publicznych zbiorów.

Instrukcję dopracowano na danych roboczych przed porównaniem. Wyniki tego
etapu służą doborowi konfiguracji, nie niezależnej ocenie końcowej.

| Parametr | Wartość |
|---|---|
| Temperatura | 0 |
| Tryb rozumowania | Wyłączony |
| Kontekst | 8192 tokeny |
| Limit odpowiedzi | 512 tokenów |
| Timeout modelu | 120 s |
| Przykłady w instrukcji | Brak |
| Dodatkowy trening | Brak |

Przepływ testu: klient FastAPI → Ollama → wywołanie narzędzia → SMTP aiosmtpd.
Modele uruchamiano kolejno na Macu M4 z 24 GB RAM. Wersje: Ollama 0.40.4,
Python 3.14.3, langchain-ollama 1.1.0, langchain-core 1.6.10, klient ollama
0.6.3, FastAPI 0.143.2. MLX i GGUF różnią się silnikiem wykonania i kwantyzacją.

### Wyniki

„Zaliczone” obejmuje wszystkie kryteria wysyłki. „Poprawne wywołania” dotyczy
nazwy narzędzia i argumentów. Czas jest medianą obsługi zwykłego zgłoszenia,
łącznie z modelem i SMTP.

| Model | Zaliczone zgłoszenia | Poprawne wywołania | Zaliczone manipulacje | Poprawne wywołania | Mediana |
|---|---:|---:|---:|---:|---:|
| Qwen3.5 9B Q4_K_M | 34/35 | 35/35 | 15/20 | 20/20 | 6,54 s |
| Bielik 11B v3 Q4_K_M | 35/35 | 35/35 | 14/20 | 18/20 | 2,72 s |
| Ministral3 8B Q4_K_M | 33/35 | 35/35 | 19/20 | 19/20 | 1,17 s |
| Gemma4 12B MLX NVFP4 | 35/35 | 35/35 | 20/20 | 20/20 | 1,26 s |
| **Gemma4 12B GGUF Q4_K_M** | **35/35** | **35/35** | **20/20** | **20/20** | **1,31 s** |

Łącznie wykonano 275 zapytań: 55 wiadomości dla każdej z pięciu konfiguracji.
Treść i nagłówki wysłanych maili były zgodne z wejściem. Kod blokował błędne
lub wielokrotne wywołania przed SMTP.

### Wybór modelu

Oba warianty Gemmy zaliczyły 35 zgłoszeń i 20 prób manipulacji. Wariant GGUF
wybrano do kontenerowej Ollamy po sprawdzeniu jego wywołań narzędzi i wysyłki.
Bielik uzyskał 35/35 dla zwykłych zgłoszeń i 14/20 dla manipulacji.
Wyniki dotyczą konkretnych wersji modeli i instrukcji.

## Weryfikacja w Docker Compose

Środowisko: API, Ollama i Mailpit, linux/arm64 na Macu M4, 16 GB RAM dla
Dockera, Ollama 0.40.4, Python 3.14.8. Model działał na CPU; monitoring
Langfuse był włączony.

| Zakres | Wynik |
|---|---:|
| Zwykłe zgłoszenia, po jednym na dział | 5/5 |
| Próby manipulacji | 20/20 |
| Pierwsze zapytanie z ładowaniem modelu | 59,20 s |
| Mediana pięciu zgłoszeń | 4,46 s |
| Mediana manipulacji | 6,85 s |

Kontrola obejmowała odbiorcę, jedną wiadomość, treść, Reply-To i trzy etapy
w Langfuse. Użyto ponownie danych roboczych. Czasu dodanego przez monitoring
nie mierzono oddzielnie.

## Test 150 nowych zgłoszeń

Zestaw zawierał po 30 polskich wiadomości na dział: 20 typowych, 7 granicznych
i 3 trudniejsze językowo lub kontekstowo. Treści i oczekiwanych odbiorców
przygotował oraz skontrolował Codex, bez niezależnego przeglądu człowieka.
Oceniana Gemma nie ustalała odpowiedzi referencyjnych.

Dane, instrukcję i konfigurację zamrożono przed testem. Etykiety i treści
pozostały niezmienione po odczytaniu wyników. Każde zapytanie przechodziło
przez sieciowe API, kontener Ollamy, narzędzie i Mailpit, bez ponawiania POST.

### Wyniki

| Dział | Zaliczone zgłoszenia |
|---|---:|
| HR | 30/30 |
| Kadry | 30/30 |
| Help-desk | 30/30 |
| IT | 29/30 |
| Other | 28/30 |
| **Łącznie** | **147/150 (98%)** |

| Kontrola | Wynik |
|---|---:|
| Format wywołania narzędzia | 150/150 |
| Wykonanie SMTP, treść i Reply-To | 150/150 |
| Komplet trzech etapów w Langfuse | 150/150 |
| Mediana czasu | 4,505 s |
| 90. percentyl czasu | 5,954 s |

Dla każdego zapytania zapisano cztery oceny w Langfuse. Wynik spełnia progi
ustalone przed testem: minimum 90% ogółem i 80% w każdym dziale.

### Błędy

| Sprawa | Oczekiwany dział | Wynik |
|---|---|---|
| Klucz do magazynku | Other | IT |
| Fotel biurowy | Other | IT |
| Odebranie dostępów odchodzącemu pracownikowi | IT | Kadry |

Założenia etykiet: wyposażenie IT obejmuje sprzęt informatyczny, a odebranie
dostępów oznacza administrację uprawnieniami do systemów. Ostatnia wiadomość
nie wskazywała systemów wprost, co ogranicza jednoznaczność jej etykiety.

### Ograniczenia pomiaru

Dane powstały po wyborze modelu, ze znajomością wcześniejszych wyników.
Nie są losową próbką rzeczywistej poczty. Tematy między zestawami częściowo
się pokrywają, a 150 etykiet nie ma niezależnej kontroli człowieka.
98% oznacza zgodność z tym zestawem, nie skuteczność produkcyjną.
Pozostałych modeli nie oceniano na tych 150 wiadomościach. Wyniki 100%
dotyczą wyłącznie opisanych prób.

Zestawy danych i skrypty pomiarowe nie są częścią publicznego repozytorium.
Raport dokumentuje wykonane pomiary; repozytorium zawiera testy kodu
i skrypt kontroli pojedynczej wysyłki.

## Dokumentacja techniczna

- [Ollama — narzędzia](https://docs.ollama.com/capabilities/tool-calling)
- [LangChain — ChatOllama](https://docs.langchain.com/oss/python/integrations/chat/ollama)
- [Gemma4](https://ollama.com/library/gemma4)
- [Ministral3](https://ollama.com/library/ministral-3)
- [Bielik](https://ollama.com/SpeakLeash/bielik-11b-v3.0-instruct)
- [OWASP — prompt injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)
