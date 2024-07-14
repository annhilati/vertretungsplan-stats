from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()
TIME_DIFF = int(os.getenv("TIME_DIFF"))

wochentag = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

def uhrzeit(datetime: datetime = datetime.now()) -> str:
    return (datetime - timedelta(hours=TIME_DIFF)).strftime("%H:%M")

def loghead(msg: str):
    print(f"╔════════════════════════════════════════════════════════════════════")
    print(f"║ {msg}")
    print(f"╚═╦══════════════════════════════════════════════════════════════════")
    print(f"  ║ Aktuelle Uhrzeit: {uhrzeit()}")
    print(f"  ║ ")

def log(msg: str):
    print("  ║ " + msg)