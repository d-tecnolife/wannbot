import base64
import re
from datetime import datetime

from cogs.flight_alerts.auth_gmail import authenticate_gmail
from config import GMAIL_QUERY

# gmail = authenticate_gmail()


def get_unread_flight_alerts(gmail):
    try:
        result = gmail.users().messages().list(userId="me", q=GMAIL_QUERY).execute()
        id_list = result.get("messages", [])
    except Exception as e:
        print(f"[{datetime.now()}] Error: {e}\nMaybe token expired?")
    # returns list of msg ids in inbox
    return id_list


def get_email_content(gmail, id):
    msg = gmail.users().messages().get(userId="me", id=id["id"]).execute()
    return msg


def mark_as_read(gmail, id):
    gmail.users().messages().modify(
        userId="me", id=id, body={"removeLabelIds": ["UNREAD"]}
    ).execute()


def parse_flight_email(msg):
    flights = []
    AIRPORT_CODES = {"YYZ": "Toronto", "YWG": "Winnipeg"}
    if "parts" in msg["payload"]:
        for part in msg["payload"]["parts"]:
            if part["mimeType"] == "text/plain":
                data = part["body"]["data"]
                data = base64.urlsafe_b64decode(data).decode("utf-8")

    # Day, Mon DD – Day, Mon DD
    date_pattern = (
        r"([A-Z][a-z]{2}, [A-Z][a-z]{2} \d+ [–-] [A-Z][a-z]{2}, [A-Z][a-z]{2} \d+)"
    )

    # SAVE XX%
    savings_pattern = r"SAVE (\d+)%"

    # From CA$XXX
    price_pattern = r"From (CA\$\d+)"

    airline_pattern = r"([A-Z][a-z]+ [A-Z][a-z]+) · Nonstop"

    link_pattern = r"\((https://[^\)]+)\)"
    route_pattern = r"([A-Z]{3}[–-][A-Z]{3})"

    dates = re.findall(date_pattern, data)
    savings = re.findall(savings_pattern, data)
    prices = re.findall(price_pattern, data)
    airlines = re.findall(airline_pattern, data)
    links = re.findall(link_pattern, data)
    routes = re.findall(route_pattern, data)
    # delete last two links, they are unrelated
    links = links[:-2]
    match_count = len(dates)

    if not (len(routes) == len(prices) == len(airlines) == len(links) == match_count):
        return []

    for i in range(match_count):
        origin, destination = routes[i].split("–")

        route = f"{AIRPORT_CODES.get(origin, origin)} to {AIRPORT_CODES.get(destination, destination)}"

        flights.append(
            {
                "dates": dates[i],
                "savings": savings[i] if i < len(savings) else "N/A",
                "price": prices[i],
                "airline": airlines[i],
                "link": links[i],
                "routes": route,
            }
        )
    return flights


def check_flights():
    flight_data = []
    print(f"[{datetime.now()}] Authenticating Gmail..")

    try:
        gmail = authenticate_gmail()
        print(f"[{datetime.now()}] Gmail successfully authenticated")
    except Exception as e:
        print(f"[{datetime.now()}] Error authenticating Gmail: {e}")
        return None
    id_list = get_unread_flight_alerts(gmail)
    for id in reversed(id_list):
        msg = get_email_content(gmail, id)
        flight_info = parse_flight_email(msg)
        for flight in flight_info:
            flight_data.append({"email_id": id, "flight": flight})
    return gmail, flight_data


# id_list = get_unread_flight_alerts(gmail)
# if id_list:
#     for id in id_list:
#         msg = get_email_content(gmail, id)
#         flight_info = parse_flight_email(msg)
#         for flight in flight_info:
#             print(f"\nPrice update:\n{flight["airline"]}\n{flight["dates"]}\n{flight["routes"]}\n{flight["price"]} ({flight["savings"]}% lower)\n{flight["link"]}")
