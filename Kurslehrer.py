from vpmobil import Vertretungsplan, VpDay
from datetime import datetime, timedelta

vp = Vertretungsplan(schulnummer=10126582,
                     benutzername="schueler",
                     passwort="s361o97")

daten: list[VpDay] = []
for tag in range(20241112, 20241122):
    fetch = vp.fetch(datei=f"10126582/mobil/mobdaten/PlanKl{tag}.xml")
    daten.append(fetch)

for tag in daten:
    for klasse in tag.klassen():
        if klasse.kürzel == 11 or 12:
            for kurs in klasse.alleKurse():
                print(f"{kurs.fach} | {kurs.lehrer}")