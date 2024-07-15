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
SYSTEM = os.getenv("SYSTEM")

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

def uploadToGitHub(datei, zielpfad):

    url = f'https://api.github.com/repos/annhilati/vertretungsplan-stats/contents/{zielpfad}'


    with open(datei, 'rb') as f:
        content = f.read()
    content_base64 = base64.b64encode(content).decode('utf-8')

    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Content-Type': 'application/json'
    }
    data = {
        'message': "Vertretungsplan-Scraper-Upload",
        'content': content_base64
    }
    
    response = requests.put(url, json=data, headers=headers)
    
    if response.status_code == 201:
        log(f"\033[32m[SUCCES] Datei \"{zielpfad}\" erfolgreich hochgeladen\033[0m")
    else:
        log(f'\033[38;2;255;165;0m[WARN] Datei \"{zielpfad}\" konnte nicht hochgeladen werden: {response.status_code}\033[0m')
        if response.status_code == 422:
            log("   [INFO] Die Datei wurde nicht hochgeladen, da sie bereits mit exakt dem selben Inhalt existiert.")
        #print(response.json())

def scrape(date = date.today() - timedelta(days=1)):
    loghead(f"Scrape-Versuch für den {datum(date)} begonnen")

    dateiname = f"{date.strftime("%Y-%m-%d")} ({wochentag[date.weekday()]}).xml"
    datenverzeichnis = f"./data" if SYSTEM == "live" else "./test"
    zieldateipfad = f"{datenverzeichnis}/{dateiname}"

    try:
        tag = vp.fetch(date)
        log(f"\033[32m[SUCCES] Daten vom {datum(date)} erfolgreich abgerufen\033[0m")

        try:
            tag.saveasfile(pfad=zieldateipfad, allowoverwrite=False)
 
            tag.saveasfile(pfad=f"{datenverzeichnis}/latest.xml", allowoverwrite=True)

            log(f"\033[32m[SUCCES] Dateien wurden in {datenverzeichnis}/ angelegt\033[0m")

            uploadToGitHub(datei=zieldateipfad, zielpfad=zieldateipfad)

        except FileExistsError:
            log(f"\033[38;2;255;165;0m[CONFLICT] Datei mit Pfad \"{zieldateipfad}\" existiert bereits \033[0m")
            log(f"  -> Anlegung und Upload neuer Dateien wird übersprungen")

    except VpMobil.FetchingError:
        if wochentag[date.weekday()] not in ["Sa", "So"]:
            global freieTage
            
            if date not in freieTage:
                log(f"\033[31m[ERROR] Daten vom {datum(date)} konnten nicht abgerufen werden \033[0m")
                log(f"  -> Eine Platzhalterdatei wird erstellt und hochgeladen")
                log(f"  -> Versende Benachrichtung an Webhook")

                with open(f"{zieldateipfad}.ERROR", "w") as f: pass
                uploadToGitHub(f"{zieldateipfad}.ERROR")
            
            elif date in freieTage:
                log(f"[INFO] Daten vom {datum(date)} wurden nicht abgerufen (als frei markierter Tag)")
                log(f"  -> Eine Platzhalterdatei wird erstellt und hochgeladen")

                with open(f"{zieldateipfad}.frei", "w") as f: pass
                uploadToGitHub(f"{zieldateipfad}.frei")
        
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