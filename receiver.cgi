#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import re
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

RECDIR   = "/var/www/cortigocampati/records"
ERRLOG   = "/var/www/cortigocampati/receiver_errors.log"

def log_error(reason, raw_qs=""):
    """Scrive una riga nel log errori con timestamp UTC e dettaglio."""
    try:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        remote = os.environ.get("REMOTE_ADDR", "-")
        with open(ERRLOG, "a") as f:
            f.write(f"{now} | {remote} | {reason} | qs={raw_qs[:120]}\n")
    except Exception:
        pass  # non bloccare mai il receiver per un errore di log

print("Content-Type: text/plain")
print("")

query_string = os.environ.get("QUERY_STRING", "")

# ---- Controllo 1: parametro data presente ----
match = re.search(r'data=(\d+)', query_string)
if not match:
    log_error("ERR:no_data", query_string)
    print("ERR:no_data")
    raise SystemExit(1)

data = match.group(1)

# ---- Controllo 2: lunghezza esatta 26 cifre ----
if len(data) != 26:
    log_error(f"ERR:len={len(data)} expected=26", query_string)
    print(f"ERR:len={len(data)}")
    raise SystemExit(1)

# ---- Controllo 3: parsing valori ----
try:
    T1  = int(data[0:3])  / 10.0
    T2  = int(data[3:6])  / 10.0
    U1  = int(data[6:9])  / 10.0
    U2  = int(data[9:12]) / 10.0
    UT  = int(data[12:15])/ 10.0
    LU  = int(data[15:18])   # payload logaritmico, non /10
    PR1 = int(data[18:22])
    PR2 = int(data[22:26])
except ValueError as e:
    log_error(f"ERR:parse:{e}", query_string)
    print(f"ERR:parse:{e}")
    raise SystemExit(1)

# ---- Controllo 4: range valori fisici plausibili ----
errors = []
if not (-40 <= T1 <= 85):   errors.append(f"T1={T1} fuori range")
if not (-40 <= T2 <= 85):   errors.append(f"T2={T2} fuori range")
if not (0   <= U1 <= 100):  errors.append(f"U1={U1} fuori range")
if not (0   <= U2 <= 100):  errors.append(f"U2={U2} fuori range")
if not (0   <= UT <= 100):  errors.append(f"UT={UT} fuori range")
if not (0   <= LU <= 999):  errors.append(f"LU={LU} fuori range")
if not (300 <= PR1 <= 1200): errors.append(f"PR1={PR1} fuori range")
if not (300 <= PR2 <= 1200): errors.append(f"PR2={PR2} fuori range")

if errors:
    reason = "ERR:range:" + "|".join(errors)
    log_error(reason, query_string)
    print(reason)
    raise SystemExit(1)

# ---- Timestamp UTC — invariato, riferimento assoluto ----
now_utc = datetime.now(timezone.utc)
TS = int(now_utc.timestamp())

# ---- Nome file basato su ora di Roma ----
try:
    rome_tz  = ZoneInfo("Europe/Rome")
    now_rome = now_utc.astimezone(rome_tz)
except Exception:
    month    = now_utc.month
    if 4 <= month <= 9:
        offset = 2
    elif month in (3, 10):
        import calendar
        last_day = calendar.monthrange(now_utc.year, month)[1]
        last_sun = last_day - (datetime(now_utc.year, month, last_day).weekday() + 1) % 7
        if month == 3:
            offset = 2 if now_utc.day > last_sun or (now_utc.day == last_sun and now_utc.hour >= 1) else 1
        else:
            offset = 1 if now_utc.day > last_sun or (now_utc.day == last_sun and now_utc.hour >= 1) else 2
    else:
        offset = 1
    now_rome = now_utc + timedelta(hours=offset)

filename = now_rome.strftime("%Y%m%d") + ".txt"
filepath = f"{RECDIR}/{filename}"
line     = f"{TS};{T1:.1f};{T2:.1f};{U1:.1f};{U2:.1f};{UT:.1f};{LU};{PR1};{PR2}\n"

# ---- Scrittura file ----
try:
    with open(filepath, "a") as f:
        f.write(line)
except IOError as e:
    log_error(f"ERR:write:{e}", query_string)
    print(f"ERR:write:{e}")
    raise SystemExit(1)

print(f"OK|{TS}|T1={T1:.1f}|T2={T2:.1f}|U1={U1:.1f}|U2={U2:.1f}|UT={UT:.1f}|LU={LU}|PR1={PR1}|PR2={PR2}")
