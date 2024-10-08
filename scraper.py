import os
import schedule
import time
import requests
import yaml
import xml.etree.ElementTree as XML
from acemeta import Discord, GitHub, FancyConsole as FC, Time
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
from vpmobil import Vertretungsplan, VpMobil

load_dotenv()
with open(".env.yaml") as file:
    config = yaml.safe_load(file)

# ╭──────────────────────────────────────────────────────────────────────────────────────────╮
# │                                      Bibliothek                                          │ 
# ╰──────────────────────────────────────────────────────────────────────────────────────────╯

zeitdiff: int = config["schedule"]["shift"]

wochentag = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

def uhrzeit(dt) -> str:
    return (dt - timedelta(hours=zeitdiff)).strftime("%H:%M")

def datum(dt) -> str:
    return (dt - timedelta(hours=zeitdiff)).strftime("%d.%m.%Y")

# ╭──────────────────────────────────────────────────────────────────────────────────────────╮
# │                                    Initialisierung                                       │ 
# ╰──────────────────────────────────────────────────────────────────────────────────────────╯

SCHULNUMMER = int(os.getenv('VP_SCHULNUMMER'))
BENUTZERNAME = os.getenv('VP_BENUTZERNAME')
PASSWORT = os.getenv('VP_PASSWORT')
WEBHOOK_URL = os.getenv("DC_WEBHOOK_URL")
GITHUB_TOKEN = os.getenv("GH_TOKEN")

SYSTEM = config["system"]
if SYSTEM not in ["dev", "live"]: raise SyntaxError("Systemstatus unklar")
uploaddir = "data" if SYSTEM == "live" else "test"
localdir = f"./tmp" 

vp = Vertretungsplan(SCHULNUMMER, BENUTZERNAME, PASSWORT)

# ╭──────────────────────────────────────────────────────────────────────────────────────────╮
# │                                     Unterprogramme                                       │ 
# ╰──────────────────────────────────────────────────────────────────────────────────────────╯

def postToWebhook(msg: str):
    webhook = Discord.Webhook(WEBHOOK_URL)
    try:
        webhook.send(msg)
        FC.print(f"      [SUCCES] Nachricht wurde an Webhook versendet", color="green")
    except requests.exceptions.HTTPError as e:
        FC.print(f"      [FATAL] Nachricht konnte nicht an Webhook versendet werden: {e.response.status_code}", color="red")

def uploadToGitHub(datei, zielpfad):
    repo = GitHub.Repository("annhilati/vertretungsplan-stats", GITHUB_TOKEN)
    try:
        repo.upload(datei, zielpfad, "Vertretungsplan-Scraper-Upload")
        FC.print(f"[SUCCES] Datei \"{zielpfad}\" erfolgreich hochgeladen", color="green")
    except FileExistsError as e:
        FC.print(f'[WARN] Datei \"{zielpfad}\" konnte nicht hochgeladen werden', color="orange")
        FC.print(f"  -> (\033[32mOK\033[0m) Die Datei wurde nicht hochgeladen, da sie bereits mit exakt dem selben Inhalt existiert.")
    except Exception as e:
        FC.print(f'\033[38;2;255;165;0m[WARN] Datei \"{zielpfad}\" konnte nicht hochgeladen werden: {e.response.status_code}\033[0m')
        FC.print(f"  -> (\033[31m??\033[0m) Versende Benachrichtung an Webhook")
        postToWebhook(msg=f"""
# Vertretungsplan-Scraper
```[WARN] Datei \"{zielpfad}\" konnte nicht hochgeladen werden```
### excepted response.status_code `{e.response.status_code}`
Beim Fehler handelt es sich nicht um einen `422`. Die zum Upload angefragte Datei existierte also noch nicht

<@720992368110862407>
-# Dieser Fall sollte überprüft werden ・ [Karlo-Hosting](https://karlo-hosting.com/dash/servers)""")

def scrape(scrape_date = None):
    if scrape_date is None:
        scrape_date = date.today() - timedelta(days=1)
        
    current_time = uhrzeit(datetime.now())
    current_date = datum(datetime.now())
    scrape_date_str = datum(scrape_date)

    FC.printhead(f"Scrape-Versuch für den {scrape_date_str} begonnen", first=False)
    FC.print(f"Aktuelle Uhrzeit: {current_time} am {current_date}")
    FC.print("")

    dateiname = f"{scrape_date.strftime('%Y-%m-%d')} ({wochentag[scrape_date.weekday()]}).xml"
    dateipfad = f"{localdir}/{dateiname}"

    try:
        tag = vp.fetch(scrape_date)
        FC.print(f"[SUCCES] Daten vom {scrape_date_str} erfolgreich abgerufen", color="green")

        try:
            tag.saveasfile(pfad=dateipfad, overwrite=False)
            tag.saveasfile(pfad=f"{localdir}/latest.xml", overwrite=True)
            FC.print(f"[SUCCES] Dateien wurden in {localdir}/ angelegt", color="green")
            uploadToGitHub(datei=dateipfad, zielpfad=f"{uploaddir}/{dateiname}")
        except FileExistsError:
            FC.print(f"[CONFLICT] Datei mit Pfad \"{dateipfad}\" existiert bereits", color="orange")
            FC.print(f"  -> Anlegung und Upload neuer Dateien wird übersprungen")

        global freieTage
        if os.path.exists(f"{localdir}/latest.xml"):
            freieTage = VpMobil.parsefromfile(f"{localdir}/latest.xml").freieTage()
        FC.print(f"[INFO] FreieTage aus neuer Quelldatei aktualisiert")

    except VpMobil.FetchingError:
        if wochentag[scrape_date.weekday()] not in ["Sa", "So"]:
            if scrape_date not in freieTage:
                FC.print(f"[ERROR] Daten vom {scrape_date_str} konnten nicht abgerufen werden", color="red")
                FC.print(f"  -> Eine Platzhalterdatei wird erstellt und hochgeladen")
                FC.print(f"  -> Versende Benachrichtung an Webhook")
                postToWebhook(msg=f"""
# Vertretungsplan-Scraper
```[ERROR] Daten vom {scrape_date_str} konnten nicht abgerufen werden```
### excepted `VpMobil.FetchingError`
Der Tag war weder Wochenende noch ein als frei markierter Tag

-> Eine Platzhalterdatei wurde erstellt und hochgeladen

<@720992368110862407>
-# Dieser Fall sollte überprüft werden ・ [Karlo-Hosting](https://karlo-hosting.com/dash/servers)
""")
                with open(f"{dateipfad}.err", "w") as f: pass
                uploadToGitHub(datei=f"{dateipfad}.err", zielpfad=f"{uploaddir}/{dateiname}.ERROR")
            elif scrape_date in freieTage:
                FC.print(f"[INFO] Daten vom {scrape_date_str} wurden nicht abgerufen (als frei markierter Tag)")
                FC.print(f"  -> Eine Platzhalterdatei wird erstellt und hochgeladen")
                with open(f"{dateipfad}.frei", "w") as f: pass
                uploadToGitHub(datei=f"{dateipfad}.frei", zielpfad=f"{uploaddir}/{dateiname}.frei")
        elif wochentag[scrape_date.weekday()] in ["Sa", "So"]:
            FC.print(f"[INFO] Daten vom {scrape_date_str} wurden nicht abgerufen (Wochenende)")

    FC.print(f"[INFO] Scraping abgeschlossen. Warten auf nächsten Scrape-Versuch ({schedule.next_run()})")
    FC.print("")

# ╭──────────────────────────────────────────────────────────────────────────────────────────╮
# │                                     Hauptprogramm                                        │ 
# ╰──────────────────────────────────────────────────────────────────────────────────────────╯
# Planungszeiten
h = config["schedule"]["hour"] - zeitdiff
m = config["schedule"]["minute"]
schedule_time = datetime.now().replace(hour=h, minute=m, second=0, microsecond=0)
schedule.every().day.at(schedule_time.strftime("%H:%M")).do(scrape)

print(f"╔════════════════════════════════════════════════════════════════════╗")
print(f"║ Vertretungsplan-Scraper by Annhilati & Joshi                       ║")
print(f"╚═╦══════════════════════════════════════════════════════════════════╝")
freieTage = []
if os.path.exists(f"{localdir}/latest.xml"):
    freieTage = VpMobil.parsefromfile(f"{localdir}/latest.xml").freieTage()
    FC.print(f"[INFO] FreieTage erfolgreich aus \"{localdir}/latest.xml\" ausgelesen")
FC.print(f"[INFO] Aktuelle Zeit: {datum(datetime.now())}:{uhrzeit(datetime.now())} (UTC+{zeitdiff})")
FC.print(f"[INFO] System-Status: {SYSTEM}")
FC.print(f"[INFO] Warten auf nächsten Scrape-Versuch ({schedule.next_run()})")

if SYSTEM == "dev":
    scrape(date(2024, 8, 5)) # Debug-Test pos
    scrape(date(2024, 7, 19)) # Debug-Test frei
    scrape(date(2024, 8, 15)) # Debug-Test Err

while True:
    try:
        schedule.run_pending()
    except Exception as e:
        try:
            postToWebhook(msg=f"""
# Vertretungsplan-Scraper
```{e}```
Es ist ein Fehler aufgetreten, der absolut unerwartet war!
Es ist unbedingt nötig, dieses unerwartete Fehlverhalten zu überprüfen, oder es können Datenlöcher entstehen!

<@720992368110862407>
-# Dieser Fall sollte überprüft werden ・ [Karlo-Hosting](https://karlo-hosting.com/dash/servers)""")
        except: continue
    time.sleep(10)
