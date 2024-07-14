import os
import schedule
import time
import requests
import base64
import xml.etree.ElementTree as XML
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
from vpmobil import Vertretungsplan, VpMobil, VpDay

load_dotenv()

# ╭──────────────────────────────────────────────────────────────────────────────────────────╮
# │                                      Bibliothek                                          │ 
# ╰──────────────────────────────────────────────────────────────────────────────────────────╯

zeitdiff = int(os.getenv("TIME_DIFF"))

wochentag = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

def uhrzeit(datetime: datetime = datetime.now()) -> str:
    return (datetime - timedelta(hours=zeitdiff)).strftime("%H:%M")

def datum(datetime: datetime = datetime.now()) -> str:
    return (datetime - timedelta(hours=zeitdiff)).strftime("%d.%m.%Y")

c = {
    "warn":"\033[38;2;255;165;0m",
    "error":"\033[31m",
    "succes":"\033[32m",
    "reset":"\033[0m"
    }

def loghead(msg: str):
    print(f"╔═╩══════════════════════════════════════════════════════════════════")
    print(f"║ {msg}")
    print(f"╚═╦══════════════════════════════════════════════════════════════════")
    print(f"  ║ Aktuelle Uhrzeit: {uhrzeit()} am {datum()}")
    print(f"  ║ ")

def log(msg: str):
    print("  ║ " + msg)

# ╭──────────────────────────────────────────────────────────────────────────────────────────╮
# │                                    Initialisierung                                       │ 
# ╰──────────────────────────────────────────────────────────────────────────────────────────╯

SCHULNUMMER = int(os.getenv('VP_SCHULNUMMER'))
BENUTZERNAME = os.getenv('VP_BENUTZERNAME')
PASSWORT = os.getenv('VP_PASSWORT')
WEBHOOK_URL = os.getenv("DC_WEBHOOK_URL")
GITHUB_TOKEN = os.getenv("GH_TOKEN")

vp = Vertretungsplan(SCHULNUMMER, BENUTZERNAME, PASSWORT)
if os.path.exists("./data/latest.xml"):
    freieTage = VpDay(xmldata=XML.parse("./data/latest.xml"), datum=date).freieTage()

# ╭──────────────────────────────────────────────────────────────────────────────────────────╮
# │                                     Unterprogramme                                       │ 
# ╰──────────────────────────────────────────────────────────────────────────────────────────╯

# def postToWebhook(msg: str):
#     payload = {"content": msg}

#     response = requests.post(WEBHOOK_URL, json=payload)
#     try:
#         response.raise_for_status()
#         #print(f"Nachricht erfolgreich gesendet: {response.status_code}")
#         ...
#     except requests.exceptions.HTTPError as err:
#         #print(f"Fehler beim Senden der Nachricht: {err}")
#         ...

def uploadToGitHub(dateipfad):

    dateiname = os.path.basename(dateipfad)
    url = f'https://api.github.com/repos/annhilati/vertretungsplan-stats/contents/data/{dateiname}'


    with open(dateipfad, 'rb') as datei:
        inhalt = datei.read()
    base64_content = base64.b64encode(inhalt).decode('utf-8')

    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Content-Type': 'application/json'
    }
    data = {
        'message': "Vertretungsplan-Scraper-Upload",
        'content': base64_content
    }
    
    response = requests.put(url, json=data, headers=headers)
    
    if response.status_code == 201:
        log(f"\033[32m[SUCCES] Datei \"{dateiname}\" erfolgreich hochgeladen\033[0m")
    else:
        log(f'\033[31m[ERROR] Datei \"{dateiname}\" konnte nicht hochgeladen werden: {response.status_code}\033[0m')
        print(response.json())

def scrape(date = date.today() - timedelta(days=1)):
    loghead(f"Scrape-Versuch für den {datum(date)} begonnen")
    try:
        tag = vp.fetch(date)
        log(f"\033[32m[SUCCES] Daten vom {datum(date)} erfolgreich abgerufen\033[0m")

        try:
            dateipfad = f"./data/{tag.datum.strftime("%d.%m.%Y")} ({wochentag[tag.datum.weekday()]}).xml"
            tag.saveasfile(pfad=dateipfad, allowoverwrite=False)
 
            tag.saveasfile(pfad=f"./data/latest.xml", allowoverwrite=True)

            log(f"\033[32m[SUCCES] Dateien wurden in data/ angelegt\033[0m")

            uploadToGitHub(dateipfad)

        except FileExistsError:
            log(f"\033[38;2;255;165;0m[CONFLICT] Datei mit Pfad \"{dateipfad}\" existiert bereits \033[0m")
            log(f"-> Anlegung und Upload neuer Dateien wird übersprungen")

    except VpMobil.FetchingError:
        if wochentag[date.weekday()] not in ["Sa", "So"]:
            global freieTage
            
            if date not in freieTage:
                log(f"\033[31m[ERROR] Daten vom {datum(date)} konnten nicht abgerufen werden \033[0m")
                log(f"-> Versende Benachrichtung an Webhook")
            
            elif date in freieTage:
                log(f"[INFO] Daten vom {datum(date)} wurden nicht abgerufen (als frei markierter Tag)")
        
        elif wochentag[date.weekday()] in ["Sa", "So"]:
            log(f"[INFO] Daten vom {datum(date)} wurden nicht abgerufen (Wochenende)")

    freieTage = VpDay(xmldata=XML.parse("./data/latest.xml"), datum=date).freieTage()
    log(f"[INFO] Scraping abgeschlossen. Warten auf nächsten Scrape-Versuch ...")
    log(f"")

# ╭──────────────────────────────────────────────────────────────────────────────────────────╮
# │                                     Hauptprogramm                                        │ 
# ╰──────────────────────────────────────────────────────────────────────────────────────────╯

print(f"╔════════════════════════════════════════════════════════════════════╗")
print(f"║ Vertretungsplan-Scraper by Annhilati & Joshi                       ║")
print(f"╚═╦══════════════════════════════════════════════════════════════════╝")
print(f"  ║ [INFO] Warten auf nächsten Scrape-Versuch ...")

# Planungszeiten
schedule.every().day.at(uhrzeit(datetime.now().replace(hour=8, minute=0))).do(scrape, date = date.today() - timedelta(days=1))

scrape(date(2024, 6, 19)) # Debug-Test

while True:
    schedule.run_pending()
    time.sleep(1)