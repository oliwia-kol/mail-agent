"""Wysyła przykład z README i sprawdza odebrany mail w Mailpit."""

import argparse
import json
from email import policy
from email.parser import BytesParser
from time import monotonic, sleep
from urllib.request import Request, urlopen


def get_json(url):
    with urlopen(url, timeout=10) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--mailpit", default="http://localhost:8025")
    args = parser.parse_args()
    payload = {
        "email": "ola@example.com",
        "message": "Proszę o zaświadczenie o zatrudnieniu.",
    }
    if get_json(f"{args.api}/health/ready")["status"] != "ready":
        raise SystemExit("API nie jest gotowe")
    with urlopen(f"{args.api}/api/v1/docs", timeout=10) as response:
        if response.status != 200:
            raise SystemExit("Dokumentacja API nie odpowiada")
    request = Request(
        f"{args.api}/api/v1/route",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    start = monotonic()
    # Wysyłamy raz. W razie potrzeby ponawiamy tylko sprawdzanie skrzynki.
    with urlopen(request, timeout=150) as response:
        result = json.load(response)
    if result.get("status") != "smtp_accepted":
        raise SystemExit("API nie potwierdziło przyjęcia maila przez serwer pocztowy")
    if result.get("recipient") != "kadry@example.com":
        raise SystemExit("Model wybrał nieprawidłowy dział")
    deadline = monotonic() + 10
    while monotonic() < deadline:
        matches = []
        for item in get_json(f"{args.mailpit}/api/v1/messages?limit=100")["messages"]:
            if result["request_id"] not in item["Subject"]:
                continue
            with urlopen(f"{args.mailpit}/api/v1/message/{item['ID']}/raw", timeout=10) as raw:
                message = BytesParser(policy=policy.default).parsebytes(raw.read())
            if message["X-Request-ID"] == result["request_id"]:
                matches.append(message)
        if matches:
            if len(matches) != 1:
                raise SystemExit("Jedno zapytanie utworzyło więcej niż jeden mail")
            message = matches[0]
            checks = {
                "recipient": str(message["To"]) == result["recipient"],
                "reply_to": str(message["Reply-To"]) == payload["email"],
                "original_body": message.get_content().replace("\r\n", "\n").rstrip("\n")
                == payload["message"],
            }
            print(
                json.dumps(
                    {
                        "request_id": result["request_id"],
                        "seconds": round(monotonic() - start, 3),
                        "one_message": True,
                        **checks,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            if not all(checks.values()):
                raise SystemExit(1)
            return
        sleep(1)
    raise SystemExit("Nie znaleziono maila w Mailpit. Nie ponawiaj zapytania automatycznie.")


if __name__ == "__main__":
    main()
