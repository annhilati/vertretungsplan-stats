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

def log(msg: str):
    print("  ║ " + msg)

GITHUB_TOKEN = os.getenv("GH_TOKEN")

def uploadToGitHub(dateiname: str, dateipfad, nachricht: str):
    url = f'https://api.github.com/repos/annhilati/vertretungsplan-stats/contents/data/{dateiname}'

    with open(dateipfad, 'rb') as datei:
        inhalt = datei.read()
    base64_content = base64.b64encode(inhalt).decode('utf-8')

    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Content-Type': 'application/json'
    }
    data = {
        'message': nachricht,
        'content': base64_content
    }
    
    response = requests.put(url, json=data, headers=headers)
    
    if response.status_code == 201:
        log(f"Datei {dateiname} erfolgreich hochgeladen")
    else:
        log(f'\033[31m[ERROR] Datei {dateiname} konnte nicht hochgeladen werden: {response.status_code}')
        print(response.json())

uploadToGitHub("test.xml", "./data/latest.xml", "Test")