import os
import schedule
import time
import requests
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
from vpmobil import Vertretungsplan, VpMobil

from lib.lib import loghead, wochentag, uhrzeit

load_dotenv()

SCHULNUMMER = int(os.getenv('VP_SCHULNUMMER'))
BENUTZERNAME = os.getenv('VP_BENUTZERNAME')
PASSWORT = os.getenv('VP_PASSWORT')
WEBHOOK_URL = os.getenv("DC_WEBHOOK_URL")
GITHUB_TOKEN = os.getenv("GH_TOKEN")

vp = Vertretungsplan(SCHULNUMMER, BENUTZERNAME, PASSWORT)

def postToWebhook(msg: str):
    payload = {"content": msg}

    response = requests.post(WEBHOOK_URL, json=payload)
    try:
        response.raise_for_status()
        #print(f"Nachricht erfolgreich gesendet: {response.status_code}")
        ...
    except requests.exceptions.HTTPError as err:
        #print(f"Fehler beim Senden der Nachricht: {err}")
        ...

def scrape(datum = date.today() - timedelta(days=1)):
    loghead(f"Scrape-Versuch für den {datum.strftime("%d.%m.%Y")} begonnen")
    try:
        gestern = vp.fetch(datum)

        try:
            dateipfad = f"./data/{gestern.datum.strftime("%d.%m.%Y")} ({wochentag[gestern.datum.weekday()]})"
            gestern.saveasfile(pfad=dateipfad, allowoverwrite=False)
        except FileExistsError:
            ...

    except VpMobil.FetchingError:
        ...

# ╭──────────────────────────────────────────────────────────────────────────────────────────╮
# │                                     Hauptprogramm                                        │ 
# ╰──────────────────────────────────────────────────────────────────────────────────────────╯

# ZEITEN SIND -2H
schedule.every().day.at(uhrzeit(datetime.now().replace(hour=8, minute=0))).do(scrape)

scrape(date(2024, 6, 19)) # Debug

while True:
    schedule.run_pending()
    time.sleep(1)