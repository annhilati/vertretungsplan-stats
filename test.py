import yaml

with open("config.yaml") as file:
    CFG = yaml.safe_load(file)

from datetime import datetime
import pytz

def print_current_time_and_timezone():
    # Holen der aktuellen Zeit in UTC
    utc_now = datetime.now(pytz.utc)
    
    # Bestimmen der lokalen Zeitzone
    local_timezone = pytz.timezone('Europe/Berlin')  # Hier kannst du deine lokale Zeitzone angeben
    local_time = utc_now.astimezone(local_timezone)
    
    # Ausgabe der aktuellen Zeit und Zeitzone
    print(f"Aktuelle Zeit: {local_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Zeitzone: {local_time.tzname()}")

if __name__ == "__main__":
    print_current_time_and_timezone()


print(CFG["config"]["system"])