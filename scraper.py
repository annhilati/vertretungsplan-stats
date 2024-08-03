import os
import schedule
import time
import requests
import xml.etree.ElementTree as XML
from acemeta import Discord, GitHub, FancyConsole as FC, Time
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

# ╭──────────────────────────────────────────────────────────────────────────────────────────╮
# │                                    Initialisierung                                       │ 
# ╰──────────────────────────────────────────────────────────────────────────────────────────╯

SCHULNUMMER = int(os.getenv('VP_SCHULNUMMER'))
BENUTZERNAME = os.getenv('VP_BENUTZERNAME')
PASSWORT = os.getenv('VP_PASSWORT')
WEBHOOK_URL = os.getenv("DC_WEBHOOK_URL")
GITHUB_TOKEN = os.getenv("GH_TOKEN")

SYSTEM = os.getenv("SYSTEM")
if SYSTEM not in ["dev", "live"]: raise SyntaxError("Systemstatus unklar")
uploaddir = "data" if SYSTEM == "live" else "test"

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


def scrape(date = date.today() - timedelta(days=1)):
    FC.printhead(f"Scrape-Versuch für den {datum(date)} begonnen", first=False)
    FC.print(f"Aktuelle Uhrzeit: {uhrzeit()} am {datum()}")
    FC.print("")

    dateiname = f"{date.strftime('%Y-%m-%d')} ({wochentag[date.weekday()]}).xml"
    localdir = f"./tmp" 
    
    dateipfad = f"{localdir}/{dateiname}"

    try:
        tag = vp.fetch(date)
        FC.print(f"[SUCCES] Daten vom {datum(date)} erfolgreich abgerufen", color="green")

        try:
            tag.saveasfile(pfad=dateipfad, overwrite=False)
 
            tag.saveasfile(pfad=f"{localdir}/latest.xml", overwrite=True)

            FC.print(f"[SUCCES] Dateien wurden in {localdir}/ angelegt", color="green")

            uploadToGitHub(datei=dateipfad, zielpfad=f"{uploaddir}/{dateiname}")

        except FileExistsError:
            FC.print(f"[CONFLICT] Datei mit Pfad \"{dateipfad}\" existiert bereits", color="orange")
            FC.print(f"  -> Anlegung und Upload neuer Dateien wird übersprungen")

    except VpMobil.FetchingError:
        if wochentag[date.weekday()] not in ["Sa", "So"]:
            global freieTage
            
            if date not in freieTage:
                FC.print(f"[ERROR] Daten vom {datum(date)} konnten nicht abgerufen werden", color="red")
                FC.print(f"  -> Eine Platzhalterdatei wird erstellt und hochgeladen")
                FC.print(f"  -> Versende Benachrichtung an Webhook")
                postToWebhook(msg=f"""
# Vertretungsplan-Scraper
```[ERROR] Daten vom {datum(date)} konnten nicht abgerufen werden```
### excepted `VpMobil.FetchingError`
Der Tag war weder Wochenende noch ein als frei markierter Tag

-> Eine Platzhalterdatei wurde erstellt und hochgeladen

<@720992368110862407>
-# Dieser Fall sollte überprüft werden ・ [Karlo-Hosting](https://karlo-hosting.com/dash/servers)
""")

                with open(f"{dateipfad}.err", "w") as f: pass
                uploadToGitHub(datei=f"{dateipfad}.err", zielpfad=f"{uploaddir}/{dateiname}.ERROR")
            
            elif date in freieTage:
                FC.print(f"[INFO] Daten vom {datum(date)} wurden nicht abgerufen (als frei markierter Tag)")
                FC.print(f"  -> Eine Platzhalterdatei wird erstellt und hochgeladen")

                with open(f"{dateipfad}.frei", "w") as f: pass
                uploadToGitHub(datei=f"{dateipfad}.frei", zielpfad=f"{uploaddir}/{dateiname}.frei")
        
        elif wochentag[date.weekday()] in ["Sa", "So"]:
            FC.print(f"[INFO] Daten vom {datum(date)} wurden nicht abgerufen (Wochenende)")

    if os.path.exists(f"./tmp/latest.xml"):
        freieTage = VpMobil.parsefromfile(f"{localdir}/latest.xml").freieTage()
        FC.print(f"[INFO] FreieTage aktualisiert")
    FC.print(f"[INFO] Scraping abgeschlossen. Warten auf nächsten Scrape-Versuch ...")
    FC.print(f"")

# ╭──────────────────────────────────────────────────────────────────────────────────────────╮
# │                                     Hauptprogramm                                        │ 
# ╰──────────────────────────────────────────────────────────────────────────────────────────╯

print(f"╔════════════════════════════════════════════════════════════════════╗")
print(f"║ Vertretungsplan-Scraper by Annhilati & Joshi                       ║")
print(f"╚═╦══════════════════════════════════════════════════════════════════╝")
freieTage = []
if os.path.exists(f"./tmp/latest.xml"):
    freieTage = VpMobil.parsefromfile("./tmp/latest.xml").freieTage()
    FC.print(f"[INFO] FreieTage erfolgreich aus \"./tmp/latest.xml\" ausgelesen")
FC.print(f"[INFO] System-Status: {SYSTEM}")
FC.print(f"[INFO] Warten auf nächsten Scrape-Versuch ...")

# Planungszeiten
schedule.every().day.at(uhrzeit(datetime.now().replace(hour=10, minute=32))).do(scrape, date = date.today() - timedelta(days=1))
# Beachtet Time-DIFF

if SYSTEM == "dev":
    scrape(date(2024, 8, 5)) # Debug-Test pos
    scrape(date(2024, 7, 19)) # Debug-Test frei
    scrape(date(2024, 8, 15)) # Debug-Test Err

while True:
    break
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
        
            ...
        except: continue # Falls das Senden des Webhooks fehlschlägt, wird continuet, um das Programm nicht abstürzen zu lassen
    
    time.sleep(10)

while True:
    schedule.run_pending()
    time.sleep(10)