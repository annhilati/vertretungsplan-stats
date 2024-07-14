import os
from dotenv import load_dotenv
from vpmobil import Vertretungsplan

# Lade die .env-Datei
load_dotenv()

# Zugriff auf die Umgebungsvariablen
SCHULNUMMER = os.getenv('VP_SCHULNUMMER')
BENUTZERNAME = os.getenv('BENUTZERNAME')
PASSWORT = os.getenv('PASSWORT')

