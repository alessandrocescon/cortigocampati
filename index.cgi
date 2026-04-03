#!/usr/bin/python3
# -*- coding: utf-8 -*-
# ============================================
#  CORTIGOCAMPATI — TELEMETRY VIEWER (Python CGI)
#  v2.5.1-py
#  Novità v2.5.0:
#  - Vista 7 giorni con tab switcher GIORNO / 7 GIORNI
#  - Grafici multi-giorno con colore per giorno
#  - Stats aggregate 7gg (min/max/media)
#  - Endpoint ?mode=json&date=YYYYMMDD per fetch AJAX
# ============================================

import os
import json
from datetime import datetime, timezone, timedelta
from urllib.parse import parse_qs

RECDIR = "/var/www/cortigocampati/records"

def utc_now():
    return datetime.now(timezone.utc)

query_string = os.environ.get("QUERY_STRING", "")
params = parse_qs(query_string)

# ---- Modalità JSON per fetch AJAX ----
mode = params.get("mode", ["html"])[0]

req_date = None
if "date" in params and params["date"]:
    cand = params["date"][0]
    if len(cand) == 8 and cand.isdigit():
        req_date = cand

now = utc_now()
if not req_date:
    req_date = now.strftime("%Y%m%d")

# ---- Se mode=json restituisce solo i record del giorno richiesto ----
if mode == "json":
    filepath = os.path.join(RECDIR, f"{req_date}.txt")
    records = []
    if os.path.isfile(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(";")
                    if len(parts) < 9:
                        continue
                    try:
                        records.append({
                            "ts":  int(parts[0]),
                            "t1":  float(parts[1]), "t2": float(parts[2]),
                            "u1":  float(parts[3]), "u2": float(parts[4]),
                            "ut":  float(parts[5]), "lu": float(parts[6]),
                            "pr1": float(parts[7]), "pr2": float(parts[8]),
                            "vb":  float(parts[9]) if len(parts) > 9 else 0.0
                        })
                    except ValueError:
                        continue
        except IOError:
            pass
    print("Content-Type: application/json")
    print("")
    print(json.dumps(records, separators=(",", ":")))
    exit()

# ---- Modalità HTML normale ----
filename = f"{req_date}.txt"
display_date = f"{req_date[0:4]}-{req_date[4:6]}-{req_date[6:8]}"
filepath = os.path.join(RECDIR, filename)

records = []
if os.path.isfile(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(";")
                if len(parts) < 9:
                    continue
                try:
                    records.append({
                        "ts":  int(parts[0]),
                        "t1":  float(parts[1]), "t2": float(parts[2]),
                        "u1":  float(parts[3]), "u2": float(parts[4]),
                        "ut":  float(parts[5]), "lu": float(parts[6]),
                        "pr1": float(parts[7]), "pr2": float(parts[8]),
                        "vb":  float(parts[9]) if len(parts) > 9 else 0.0
                    })
                except ValueError:
                    continue
    except IOError:
        pass

json_data = json.dumps(records, separators=(",", ":"))

print("Content-Type: text/html")
print("")

print(f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CORTIGOCAMPATI — TELEMETRY</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@400;700;900&display=swap" rel="stylesheet">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  :root {{
    --bg:#0d1117; --panel:#161b22; --border:#21262d; --grid:#1c2128;
    --text:#c0cdd8; --text-hi:#edf2f7; --accent:#00ff88;
    --t1:#ff6b6b; --t2:#ffa94d; --u1:#4dabf7; --u2:#9775fa;
    --ut:#20c997; --lu:#ffd43b; --pr1:#ff6b9d; --pr2:#c084fc;
    --oidio:#f59e0b; --pero:#3b82f6; --botrite:#ef4444; --frost:#67e8f9;
  }}
  body {{ background:var(--bg); color:var(--text); font-family:'Share Tech Mono',monospace; min-height:100vh; overflow-x:hidden; }}
  .scanline {{ position:fixed; top:0; left:0; right:0; bottom:0; background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,255,136,0.015) 2px,rgba(0,255,136,0.015) 4px); pointer-events:none; z-index:999; }}

  header {{ border-bottom:1px solid var(--border); padding:16px 24px; display:flex; align-items:center; justify-content:space-between; background:linear-gradient(180deg,#0f1419 0%,var(--bg) 100%); }}
  .logo {{ font-family:'Orbitron',sans-serif; font-weight:900; font-size:18px; color:var(--accent); letter-spacing:4px; text-transform:uppercase; text-shadow:0 0 20px rgba(0,255,136,0.3); display:flex; align-items:center; gap:12px; }}
  .logo-img {{ height:36px; width:auto; border-radius:4px; opacity:0.92; flex-shrink:0; }}
  @media (max-width:600px) {{ .logo-img {{ height:28px; }} }}
  .logo span {{ color:#7a8a9a; font-weight:400; font-size:11px; letter-spacing:2px; margin-left:12px; }}
  .header-right {{ display:flex; align-items:center; gap:20px; font-size:12px; }}
  .status-dot {{ width:8px; height:8px; background:var(--accent); border-radius:50%; display:inline-block; animation:pulse 2s infinite; box-shadow:0 0 8px var(--accent); }}
  @keyframes pulse {{ 0%,100%{{opacity:1}} 50%{{opacity:0.4}} }}
  .date-label {{ font-family:'Orbitron',sans-serif; font-size:11px; color:var(--text-hi); letter-spacing:2px; }}


  /* ---- BARRA METEO ---- */
  .meteo-bar {{ background:#060a0f; border-bottom:1px solid var(--border); padding:10px 24px; display:flex; align-items:center; gap:6px; overflow-x:auto; scrollbar-width:none; min-height:72px; }}
  .meteo-bar::-webkit-scrollbar {{ display:none; }}
  .meteo-bar.loading {{ color:#6b7280; font-size:10px; letter-spacing:2px; }}
  .meteo-loc {{ font-family:'Orbitron',sans-serif; font-size:10px; color:#6b7a8a; letter-spacing:2px; margin-right:12px; white-space:nowrap; flex-shrink:0; }}
  .meteo-day {{ display:flex; flex-direction:column; align-items:center; gap:3px; padding:6px 8px; border-radius:4px; border:1px solid transparent; flex-shrink:0; min-width:72px; cursor:pointer; transition:all 0.2s; position:relative; }}
  .meteo-day:hover {{ border-color:var(--border); background:rgba(255,255,255,0.02); }}
  .meteo-day.today {{ border-color:#1a2332; background:rgba(0,255,136,0.04); }}
  .meteo-day.expanded {{ border-color:var(--accent) !important; background:rgba(0,255,136,0.06); }}
  .meteo-day-label {{ font-size:9px; letter-spacing:1px; color:#6b7a8a; text-transform:uppercase; }}
  .meteo-day.today .meteo-day-label {{ color:var(--accent); }}
  .meteo-icon {{ font-size:24px; line-height:1; }}
  .meteo-temps {{ display:flex; gap:4px; font-size:11px; }}
  .meteo-tmax {{ color:#ff6b6b; font-family:'Orbitron',sans-serif; }}
  .meteo-tmin {{ color:#4dabf7; font-family:'Orbitron',sans-serif; }}
  .meteo-rain {{ font-size:9px; color:#6b7a8a; }}
  .meteo-rain.wet {{ color:#67e8f9; }}
  .meteo-agro-badge {{ font-size:8px; padding:2px 5px; border-radius:2px; margin-top:2px; }}
  .meteo-agro-badge.risk-pero  {{ background:rgba(59,130,246,0.25); color:#60a5fa; }}
  .meteo-agro-badge.risk-oidio {{ background:rgba(245,158,11,0.25); color:#fbbf24; }}
  .meteo-agro-badge.risk-bot   {{ background:rgba(239,68,68,0.25);  color:#fca5a5; }}
  .meteo-agro-badge.ok         {{ background:rgba(32,201,151,0.15); color:#20c997; }}

  /* Popup dettaglio giorno */
  .meteo-popup {{ display:none; position:fixed; z-index:1000; background:#0d1117; border:1px solid var(--accent); border-radius:6px; padding:16px; min-width:280px; box-shadow:0 8px 32px rgba(0,0,0,0.6); font-size:10px; }}
  .meteo-popup.visible {{ display:block; }}
  .meteo-popup-header {{ font-family:'Orbitron',sans-serif; font-size:11px; color:var(--accent); letter-spacing:2px; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center; }}
  .meteo-popup-close {{ cursor:pointer; color:#6b7280; font-size:16px; line-height:1; padding:0 4px; }}
  .meteo-popup-close:hover {{ color:var(--text-hi); }}
  .meteo-fascia {{ margin-bottom:10px; }}
  .meteo-fascia-title {{ font-family:'Orbitron',sans-serif; font-size:9px; letter-spacing:2px; color:var(--text); margin-bottom:6px; padding-bottom:4px; border-bottom:1px solid var(--border); }}
  .meteo-fascia-grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:6px; }}
  .meteo-param {{ display:flex; flex-direction:column; gap:2px; }}
  .meteo-param-label {{ font-size:8px; color:#6b7280; letter-spacing:1px; }}
  .meteo-param-value {{ font-family:'Orbitron',sans-serif; font-size:11px; color:var(--text-hi); }}
  .meteo-param-value.warn {{ color:#f59e0b; }}
  .meteo-param-value.alert {{ color:#ef4444; }}
  .meteo-agro-section {{ margin-top:10px; padding-top:8px; border-top:1px solid var(--border); }}
  .meteo-agro-title {{ font-family:'Orbitron',sans-serif; font-size:9px; letter-spacing:2px; color:var(--text); margin-bottom:6px; }}
  .meteo-agro-row {{ display:flex; align-items:center; gap:8px; margin-bottom:4px; font-size:10px; }}
  .meteo-agro-dot {{ width:6px; height:6px; border-radius:50%; flex-shrink:0; }}

  @media (max-width:600px) {{
    .meteo-bar {{ padding:8px 12px; gap:4px; }}
    .meteo-day {{ min-width:62px; padding:5px 6px; }}
    .meteo-icon {{ font-size:20px; }}
    .meteo-loc {{ display:none; }}
    .meteo-popup {{ min-width:260px; padding:12px; left:50% !important; transform:translateX(-50%); }}
    .meteo-fascia-grid {{ grid-template-columns:repeat(3,1fr); }}
  }}

  /* ---- TAB SWITCHER ---- */
  .tab-bar {{ display:flex; align-items:center; gap:4px; padding:12px 24px; border-bottom:1px solid var(--border); background:var(--panel); }}
  .tab-btn {{ background:var(--bg); border:1px solid var(--border); color:var(--text); padding:7px 20px; font-family:'Orbitron',sans-serif; font-size:10px; letter-spacing:3px; cursor:pointer; border-radius:3px; transition:all 0.2s; }}
  .tab-btn:hover {{ border-color:var(--accent); color:var(--accent); }}
  .tab-btn.active {{ background:rgba(0,255,136,0.1); border-color:var(--accent); color:var(--accent); }}
  .tab-sep {{ width:1px; height:24px; background:var(--border); margin:0 8px; }}
  .tab-info {{ font-size:10px; letter-spacing:2px; color:#6b7280; margin-left:8px; }}

  /* ---- ALERT BAR ---- */
  .alert-bar {{ display:none; padding:0 24px; background:var(--panel); border-bottom:1px solid var(--border); }}
  .alert-bar.visible {{ display:block; }}
  .alert-item {{ display:flex; align-items:center; gap:12px; padding:10px 0; border-bottom:1px solid var(--border); font-size:11px; letter-spacing:2px; }}
  .alert-item:last-child {{ border-bottom:none; }}
  .alert-dot {{ width:8px; height:8px; border-radius:50%; flex-shrink:0; animation:pulse 1.5s infinite; }}
  .alert-name {{ font-family:'Orbitron',sans-serif; font-size:10px; font-weight:700; min-width:160px; }}
  .alert-desc {{ color:var(--text); font-size:10px; }}
  .alert-vals {{ color:var(--text-hi); font-size:10px; margin-left:auto; }}

  /* ---- LEGENDA PATOGENI ---- */
  .patogen-legend {{ display:flex; gap:20px; flex-wrap:wrap; padding:10px 24px; border-bottom:1px solid var(--border); background:var(--panel); font-size:10px; letter-spacing:2px; align-items:center; }}
  .pl-item {{ display:flex; align-items:center; gap:8px; }}
  .pl-item.pl-inactive {{ opacity:0.35; }}
  .pl-dot  {{ width:8px; height:8px; border-radius:50%; flex-shrink:0; }}
  .pl-season {{ font-size:9px; padding:2px 6px; border-radius:3px; margin-left:4px; }}
  .pl-season.active {{ background:rgba(0,255,136,0.15); color:var(--accent); }}
  .pl-season.inactive {{ background:rgba(139,148,158,0.15); color:var(--text); }}

  /* ---- DATE NAV ---- */
  .date-nav {{ display:flex; align-items:center; gap:12px; padding:12px 24px; border-bottom:1px solid var(--border); background:var(--panel); }}
  .date-nav label {{ font-size:11px; letter-spacing:2px; color:var(--text); }}
  .date-nav input[type="date"] {{ background:var(--bg); border:1px solid var(--border); color:var(--text-hi); padding:6px 10px; font-family:'Share Tech Mono',monospace; font-size:12px; border-radius:3px; cursor:pointer; }}
  .date-nav input[type="date"]:focus {{ outline:none; border-color:var(--accent); }}
  .btn-nav {{ background:var(--bg); border:1px solid var(--border); color:var(--accent); padding:6px 14px; font-family:'Share Tech Mono',monospace; font-size:11px; letter-spacing:2px; cursor:pointer; border-radius:3px; transition:background 0.2s; }}
  .btn-nav:hover {{ background:var(--border); }}

  /* ---- STATS BAR ---- */
  .stats-bar {{ display:flex; gap:24px; padding:10px 24px; border-bottom:1px solid var(--border); font-size:10px; letter-spacing:2px; color:var(--text); background:var(--panel); flex-wrap:wrap; }}
  .stats-bar span {{ color:var(--accent); }}

  /* ---- CARDS ---- */
  .dashboard {{ padding:20px 24px; max-width:1400px; margin:0 auto; }}
  .cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(155px,1fr)); gap:12px; margin-bottom:20px; }}
  .card {{ background:var(--panel); border:1px solid var(--border); border-radius:4px; padding:14px 16px; position:relative; overflow:hidden; transition:border-color 0.3s, box-shadow 0.3s; }}
  .card:hover {{ border-color:#2a3a52; }}
  .card::before {{ content:''; position:absolute; top:0; left:0; right:0; height:2px; }}
  .card[data-sensor="t1"]::before  {{ background:var(--t1); }}
  .card[data-sensor="t2"]::before  {{ background:var(--t2); }}
  .card[data-sensor="u1"]::before  {{ background:var(--u1); }}
  .card[data-sensor="u2"]::before  {{ background:var(--u2); }}
  .card[data-sensor="ut"]::before  {{ background:var(--ut); }}
  .card[data-sensor="lu"]::before  {{ background:var(--lu); }}
  .card[data-sensor="pr1"]::before {{ background:var(--pr1); }}
  .card[data-sensor="pr2"]::before {{ background:var(--pr2); }}
  .card.ring-oidio   {{ border-color:var(--oidio)   !important; box-shadow:0 0 8px rgba(245,158,11,0.3); }}
  .card.ring-pero    {{ border-color:var(--pero)    !important; box-shadow:0 0 8px rgba(59,130,246,0.3); }}
  .card.ring-botrite {{ border-color:var(--botrite) !important; box-shadow:0 0 8px rgba(239,68,68,0.3); }}
  .card-label    {{ font-size:10px; letter-spacing:3px; text-transform:uppercase; color:var(--text); margin-bottom:6px; }}
  .card-sublabel {{ font-size:9px; letter-spacing:1px; color:#6b7280; margin-bottom:8px; }}
  .card-value    {{ font-family:'Orbitron',sans-serif; font-size:24px; font-weight:700; color:var(--text-hi); line-height:1; }}
  .card-unit     {{ font-size:11px; color:var(--text); margin-left:3px; font-family:'Share Tech Mono',monospace; }}

  /* ---- INDICATORI EPIDEMIOLOGICI ---- */
  .epi-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:12px; }}
  .epi-card {{ background:var(--bg); border:1px solid var(--border); border-radius:4px; padding:14px 16px; transition:border-color 0.3s; }}
  .epi-card.epi-ok    {{ border-color:#20c997; box-shadow:0 0 6px rgba(32,201,151,0.2); }}
  .epi-card.epi-low   {{ border-color:#84cc16; box-shadow:0 0 6px rgba(132,204,22,0.2); }}
  .epi-card.epi-warn  {{ border-color:var(--oidio); box-shadow:0 0 6px rgba(245,158,11,0.25); }}
  .epi-card.epi-alert {{ border-color:var(--botrite); box-shadow:0 0 8px rgba(239,68,68,0.3); animation:epi-pulse 2s infinite; }}
  @keyframes epi-pulse {{ 0%,100%{{box-shadow:0 0 8px rgba(239,68,68,0.3)}} 50%{{box-shadow:0 0 16px rgba(239,68,68,0.6)}} }}
  .epi-icon     {{ font-size:20px; margin-bottom:6px; }}
  .epi-label    {{ font-family:'Orbitron',sans-serif; font-size:10px; letter-spacing:2px; color:var(--text-hi); margin-bottom:4px; }}
  .epi-sublabel {{ font-size:9px; letter-spacing:1px; color:#6b7280; margin-bottom:10px; }}
  .epi-value    {{ font-family:'Orbitron',sans-serif; font-size:22px; font-weight:700; color:var(--text-hi); margin-bottom:8px; }}
  .epi-bar-wrap {{ height:3px; background:var(--border); border-radius:2px; overflow:hidden; margin-bottom:8px; }}
  .epi-bar      {{ height:100%; border-radius:2px; transition:width 0.6s ease, background 0.4s; width:0%; }}
  .epi-status   {{ font-size:10px; letter-spacing:2px; }}
  .epi-status.ok    {{ color:#20c997; }}
  .epi-status.low   {{ color:#84cc16; }}
  .epi-status.warn  {{ color:var(--oidio); }}
  .epi-status.alert {{ color:var(--botrite); }}

  /* ---- CHARTS ---- */
  .chart-panel {{ background:var(--panel); border:1px solid var(--border); border-radius:4px; padding:20px; margin-bottom:16px; }}
  .chart-title {{ font-family:'Orbitron',sans-serif; font-size:11px; letter-spacing:3px; color:var(--text); text-transform:uppercase; margin-bottom:16px; padding-bottom:10px; border-bottom:1px solid var(--border); display:flex; justify-content:space-between; align-items:center; }}
  .chart-container {{ position:relative; height:280px; }}
  .chart-container.tall {{ height:340px; }}

  /* ---- VISTA 7GG ---- */
  #view-7d {{ display:none; }}
  .w7-loading {{ text-align:center; padding:60px; color:var(--text); letter-spacing:3px; font-size:12px; }}
  .w7-loading .spin {{ display:inline-block; width:20px; height:20px; border:2px solid var(--border); border-top-color:var(--accent); border-radius:50%; animation:spin 0.8s linear infinite; margin-right:12px; vertical-align:middle; }}
  @keyframes spin {{ to{{transform:rotate(360deg)}} }}

  /* Tabella stats 7gg */
  .stats7-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:10px; margin-bottom:20px; }}
  .stats7-card {{ background:var(--bg); border:1px solid var(--border); border-radius:4px; padding:12px 14px; }}
  .stats7-label {{ font-family:'Orbitron',sans-serif; font-size:9px; letter-spacing:2px; color:var(--text); margin-bottom:8px; }}
  .stats7-row {{ display:flex; justify-content:space-between; font-size:10px; margin-bottom:3px; }}
  .stats7-key {{ color:#6b7280; }}
  .stats7-val {{ color:var(--text-hi); font-family:'Orbitron',sans-serif; font-size:10px; }}
  .stats7-val.hi {{ color:#ef4444; }}
  .stats7-val.lo {{ color:#3b82f6; }}
  .stats7-val.avg {{ color:var(--accent); }}

  /* Legenda giorni */
  .days-legend {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom:16px; padding:10px 14px; background:var(--bg); border-radius:4px; border:1px solid var(--border); }}
  .day-leg {{ display:flex; align-items:center; gap:6px; font-size:10px; letter-spacing:1px; }}
  .day-leg-dot {{ width:10px; height:3px; border-radius:2px; }}

  .footer-bar {{ padding:12px 24px; font-size:10px; color:var(--text); letter-spacing:2px; text-align:center; border-top:1px solid var(--border); margin-top:20px; }}
  .no-data {{ text-align:center; padding:80px 20px; color:var(--text); font-size:13px; letter-spacing:3px; }}
  .no-data .icon {{ font-size:40px; margin-bottom:16px; opacity:0.2; display:block; }}

  /* ============================================================
     RESPONSIVE MOBILE  (< 600px)
     ============================================================ */
  @media (max-width: 600px) {{
    header {{ padding:10px 12px; flex-wrap:wrap; gap:6px; }}
    .logo {{ font-size:13px; letter-spacing:2px; }}
    .logo span {{ display:none; }}
    .header-right {{ gap:10px; font-size:10px; }}
    .date-label {{ font-size:9px; letter-spacing:1px; }}

    .tab-bar {{ padding:8px 12px; flex-wrap:wrap; gap:6px; }}
    .tab-btn {{ padding:6px 12px; font-size:9px; letter-spacing:1px; }}
    .tab-sep,.tab-info {{ display:none; }}

    .alert-item {{ flex-wrap:wrap; gap:6px; padding:8px 0; }}
    .alert-name {{ min-width:unset; font-size:9px; }}
    .alert-desc {{ display:none; }}
    .alert-vals {{ margin-left:0; font-size:9px; width:100%; }}
    .alert-bar {{ padding:0 12px; }}

    .patogen-legend {{ padding:8px 12px; gap:8px; }}
    .pl-season {{ display:none; }}
    .pl-item span:not([style]) {{ display:none; }}

    .date-nav {{ padding:8px 12px; gap:6px; flex-wrap:wrap; }}
    .date-nav label {{ display:none; }}
    .date-nav input[type="date"] {{ font-size:11px; padding:5px 8px; flex:1; min-width:0; }}
    .btn-nav {{ padding:5px 10px; font-size:10px; letter-spacing:1px; }}

    .stats-bar {{ padding:8px 12px; gap:8px; font-size:9px; letter-spacing:0; }}

    .dashboard {{ padding:10px 10px; }}
    .cards {{ grid-template-columns:repeat(2,1fr); gap:8px; }}
    .card {{ padding:10px 12px; }}
    .card-value {{ font-size:20px; }}
    .card-label {{ font-size:9px; letter-spacing:1px; }}

    .epi-grid {{ grid-template-columns:1fr 1fr; gap:8px; }}
    .epi-card {{ padding:10px 12px; }}
    .epi-value {{ font-size:18px; }}
    .epi-label {{ font-size:9px; letter-spacing:1px; }}
    .epi-sublabel {{ display:none; }}

    .chart-title {{ font-size:9px; letter-spacing:0; flex-direction:column; align-items:flex-start; gap:4px; line-height:1.4; }}
    .chart-panel {{ padding:12px 10px; }}
    .chart-container {{ height:200px; }}
    .chart-container.tall {{ height:240px; }}

    .stats7-grid {{ grid-template-columns:repeat(2,1fr); gap:8px; }}
    .stats7-card {{ padding:10px 10px; }}
    .days-legend {{ gap:6px; padding:8px 10px; font-size:9px; }}
    .day-leg {{ font-size:9px; }}

    .footer-bar {{ font-size:9px; padding:10px 12px; }}
  }}

  @media (min-width:601px) and (max-width:900px) {{
    .dashboard {{ padding:14px 16px; }}
    .alert-bar,.patogen-legend,.date-nav,.stats-bar,.tab-bar {{ padding-left:16px; padding-right:16px; }}
    .cards {{ grid-template-columns:repeat(4,1fr); gap:10px; }}
    .chart-title {{ flex-wrap:wrap; gap:4px; font-size:10px; }}
    .epi-grid {{ grid-template-columns:repeat(3,1fr); }}
    .stats7-grid {{ grid-template-columns:repeat(4,1fr); }}
  }}
</style>
</head>
<body>
<div class="scanline"></div>

<header>
  <div class="logo"><img class="logo-img" src="https://cortigocampati.ddns.net/files/cortigo_campati.jpg" alt="Cortigo Campati" onerror="this.style.display='none'">CORTIGOCAMPATI <span>TELEMETRY SYS (PY) v2.5.1</span></div>
  <div class="header-right">
    <span class="status-dot"></span>
    <span class="date-label">{display_date} UTC</span>
    <span id="clock" class="date-label"></span>
  </div>
</header>

<!-- Barra previsioni meteo 7gg — Open-Meteo, no API key -->
<div class="meteo-bar loading" id="meteoBar">
  <span style="color:#6b7280;font-size:10px;letter-spacing:2px">⟳ CARICAMENTO PREVISIONI...</span>
</div>

<!-- Tab switcher -->
<div class="tab-bar">
  <button class="tab-btn active" id="tab-1d" onclick="switchView('1d')">▸ GIORNO</button>
  <button class="tab-btn" id="tab-7d" onclick="switchView('7d')">▸ 7 GIORNI</button>
  <div class="tab-sep"></div>
  <span class="tab-info" id="tab-info">Vista giornaliera — {display_date}</span>
</div>

<!-- Alert bar patogeni -->
<div class="alert-bar" id="alertBar">
  <div class="alert-item" id="alert-oidio" style="display:none">
    <div class="alert-dot" style="background:var(--oidio);box-shadow:0 0 8px var(--oidio)"></div>
    <div class="alert-name" style="color:var(--oidio)">⚠ RISCHIO OIDIO</div>
    <div class="alert-desc">Erysiphe necator · T 20-30°C · UR 40-70%</div>
    <div class="alert-vals" id="vals-oidio"></div>
  </div>
  <div class="alert-item" id="alert-pero" style="display:none">
    <div class="alert-dot" style="background:var(--pero);box-shadow:0 0 8px var(--pero)"></div>
    <div class="alert-name" style="color:var(--pero)">⚠ RISCHIO PERONOSPORA</div>
    <div class="alert-desc">Plasmopara viticola · T ≥10°C · UR ≥90%</div>
    <div class="alert-vals" id="vals-pero"></div>
  </div>
  <div class="alert-item" id="alert-botrite" style="display:none">
    <div class="alert-dot" style="background:var(--botrite);box-shadow:0 0 8px var(--botrite)"></div>
    <div class="alert-name" style="color:var(--botrite)">⚠ RISCHIO BOTRITE</div>
    <div class="alert-desc">Botrytis cinerea · T 15-25°C · UR ≥90% · Glera sensibile</div>
    <div class="alert-vals" id="vals-botrite"></div>
  </div>
  <div class="alert-item" id="alert-frost" style="display:none">
    <div class="alert-dot" style="background:#67e8f9;box-shadow:0 0 8px #67e8f9"></div>
    <div class="alert-name" style="color:#67e8f9">❄️ RISCHIO BRINA/GELO</div>
    <div class="alert-desc">T ≤2°C · UR ≥80% · germogli in pericolo</div>
    <div class="alert-vals" id="vals-frost"></div>
  </div>
</div>

<!-- Legenda patogeni -->
<div class="patogen-legend">
  <span style="color:var(--text)">SOGLIE:</span>
  <div class="pl-item" id="pl-oidio">
    <div class="pl-dot" style="background:var(--oidio)"></div>
    <span style="color:var(--oidio);font-weight:700">OIDIO</span>
    <span>T 20-30°C · UR 40-70%</span>
    <span class="pl-season" id="pl-season-oidio"></span>
  </div>
  <div class="pl-item" id="pl-pero">
    <div class="pl-dot" style="background:var(--pero)"></div>
    <span style="color:var(--pero);font-weight:700">PERONOSPORA</span>
    <span>T ≥10°C · UR ≥90%</span>
    <span class="pl-season" id="pl-season-pero"></span>
  </div>
  <div class="pl-item" id="pl-botrite">
    <div class="pl-dot" style="background:var(--botrite)"></div>
    <span style="color:var(--botrite);font-weight:700">BOTRITE</span>
    <span>T 15-25°C · UR ≥90%</span>
    <span class="pl-season" id="pl-season-botrite"></span>
  </div>
  <div class="pl-item">
    <div class="pl-dot" style="background:#67e8f9"></div>
    <span style="color:#67e8f9;font-weight:700">PIOGGIA</span>
    <span>UT in aumento</span>
  </div>
</div>

<!-- Date nav (solo vista 1d) -->
<div class="date-nav" id="nav-1d">
  <label>DATA:</label>
  <input type="date" id="datePicker">
  <button class="btn-nav" onclick="goDate(-1)">◀ PREC</button>
  <button class="btn-nav" onclick="goToday()">OGGI</button>
  <button class="btn-nav" onclick="goDate(+1)">SUCC ▶</button>
</div>

<!-- Stats bar (solo vista 1d) -->
<div class="stats-bar" id="statsbar-1d">
  RECORDS: <span id="statRecords">--</span> &nbsp;|&nbsp;
  PRIMA: <span id="statFirst">--</span> &nbsp;|&nbsp;
  ULTIMA: <span id="statLast">--</span> &nbsp;|&nbsp;
  T1 MIN: <span id="statT1min">--</span> &nbsp;|&nbsp;
  T1 MAX: <span id="statT1max">--</span> &nbsp;|&nbsp;
  U1 MIN: <span id="statU1min">--</span> &nbsp;|&nbsp;
  U1 MAX: <span id="statU1max">--</span>
</div>

<!-- ===================== VISTA 1 GIORNO ===================== -->
<div id="view-1d">
  <div class="dashboard">
    <div class="cards">
      <div class="card" data-sensor="t1" id="card-t1"><div class="card-label">Temperatura 1</div><div class="card-sublabel">DHT22</div><div class="card-value" id="v-t1">--<span class="card-unit">°C</span></div></div>
      <div class="card" data-sensor="t2" id="card-t2"><div class="card-label">Temperatura 2</div><div class="card-sublabel">HTU21</div><div class="card-value" id="v-t2">--<span class="card-unit">°C</span></div></div>
      <div class="card" data-sensor="u1" id="card-u1"><div class="card-label">Umidità 1</div><div class="card-sublabel">DHT22</div><div class="card-value" id="v-u1">--<span class="card-unit">%</span></div></div>
      <div class="card" data-sensor="u2" id="card-u2"><div class="card-label">Umidità 2</div><div class="card-sublabel">HTU21</div><div class="card-value" id="v-u2">--<span class="card-unit">%</span></div></div>
      <div class="card" data-sensor="ut" id="card-ut"><div class="card-label">Umid. Terreno</div><div class="card-sublabel">Soil v1.2</div><div class="card-value" id="v-ut">--<span class="card-unit">%</span></div></div>
      <div class="card" data-sensor="lu" id="card-lu"><div class="card-label">Luminosità</div><div class="card-sublabel">BH1750</div><div class="card-value" id="v-lu">--<span class="card-unit">lux</span></div></div>
      <div class="card" data-sensor="pr1" id="card-pr1"><div class="card-label">Pressione 1</div><div class="card-sublabel">BMP180 #1</div><div class="card-value" id="v-pr1">--<span class="card-unit">hPa</span></div></div>
      <div class="card" data-sensor="pr2" id="card-pr2"><div class="card-label">Pressione 2</div><div class="card-sublabel">BMP180 #2</div><div class="card-value" id="v-pr2">--<span class="card-unit">hPa</span></div></div>
    </div>

    <div class="chart-panel">
      <div class="chart-title">▸ Indicatori Epidemiologici — Analisi Giornaliera</div>
      <div class="epi-grid">
        <div class="epi-card" id="epi-ore-pero"><div class="epi-icon">💧</div><div class="epi-label">Ore UR≥90%</div><div class="epi-sublabel">Soglia peronospora: ≥2h consecutive</div><div class="epi-value" id="epi-val-ore-pero">--</div><div class="epi-bar-wrap"><div class="epi-bar" id="epi-bar-ore-pero"></div></div><div class="epi-status" id="epi-status-ore-pero"></div></div>
        <div class="epi-card" id="epi-ore-oidio"><div class="epi-icon">🌡</div><div class="epi-label">Ore T 20-30°C</div><div class="epi-sublabel">Range termico favorevole oidio</div><div class="epi-value" id="epi-val-ore-oidio">--</div><div class="epi-bar-wrap"><div class="epi-bar" id="epi-bar-ore-oidio"></div></div><div class="epi-status" id="epi-status-ore-oidio"></div></div>
        <div class="epi-card" id="epi-delta-p"><div class="epi-icon">🌀</div><div class="epi-label">Delta Pressione</div><div class="epi-sublabel">Variazione PR1 prima↔ultima lettura</div><div class="epi-value" id="epi-val-delta-p">--</div><div class="epi-bar-wrap"><div class="epi-bar" id="epi-bar-delta-p"></div></div><div class="epi-status" id="epi-status-delta-p"></div></div>
        <div class="epi-card" id="epi-escursione"><div class="epi-icon">↕</div><div class="epi-label">Escursione Termica</div><div class="epi-sublabel">T_max - T_min giornaliera</div><div class="epi-value" id="epi-val-escursione">--</div><div class="epi-bar-wrap"><div class="epi-bar" id="epi-bar-escursione"></div></div><div class="epi-status" id="epi-status-escursione"></div></div>
        <div class="epi-card" id="epi-risk"><div class="epi-icon">⚠</div><div class="epi-label">Risk Score</div><div class="epi-sublabel">Indice composito 0-100</div><div class="epi-value" id="epi-val-risk">--</div><div class="epi-bar-wrap"><div class="epi-bar" id="epi-bar-risk"></div></div><div class="epi-status" id="epi-status-risk"></div></div>
        <div class="epi-card" id="epi-frost"><div class="epi-icon">❄️</div><div class="epi-label">Rischio Brina/Gelo</div><div class="epi-sublabel">T≤2°C · UR≥80% · durata critica</div><div class="epi-value" id="epi-val-frost">--</div><div class="epi-bar-wrap"><div class="epi-bar" id="epi-bar-frost"></div></div><div class="epi-status" id="epi-status-frost"></div></div>
      </div>
    </div>

    <div class="chart-panel">
      <div class="chart-title">▸ Temperature [<span style="color:var(--oidio)">■ oidio</span> <span style="color:var(--botrite)">■ botrite</span> <span style="color:var(--pero)">■ peronospora</span> <span style="color:#67e8f9">■ brina/gelo</span>] — pallini = rischio attivo</div>
      <div class="chart-container"><canvas id="chartTemp"></canvas></div>
    </div>
    <div class="chart-panel">
      <div class="chart-title">▸ Umidità [<span style="color:var(--oidio)">■ oidio</span> <span style="color:var(--botrite)">■ botrite</span> <span style="color:var(--pero)">■ peronospora</span>] — <span style="color:#fbbf24">● pioggia >2%</span> <span style="color:#67e8f9">❄ brina su UT</span></div>
      <div class="chart-container"><canvas id="chartHum"></canvas></div>
    </div>
    <div class="chart-panel">
      <div class="chart-title">▸ Luminosità — Timeline (scala logaritmica)</div>
      <div class="chart-container"><canvas id="chartLux"></canvas></div>
    </div>
    <div class="chart-panel">
      <div class="chart-title">▸ Pressione Atmosferica — Timeline</div>
      <div class="chart-container"><canvas id="chartPres"></canvas></div>
    </div>
  </div>
</div>

<!-- ===================== VISTA 7 GIORNI ===================== -->
<div id="view-7d">
  <div class="dashboard">
    <div id="w7-loading" class="w7-loading">
      <span class="spin"></span>CARICAMENTO DATI 7 GIORNI...
    </div>
    <div id="w7-content" style="display:none">

      <!-- Stats aggregate -->
      <div class="chart-panel">
        <div class="chart-title">▸ Statistiche Aggregate — Ultimi 7 Giorni</div>
        <div class="stats7-grid" id="stats7-grid"></div>
      </div>

      <!-- Legenda giorni -->
      <div class="days-legend" id="days-legend"></div>

      <!-- Grafici 7gg -->
      <div class="chart-panel">
        <div class="chart-title">▸ Temperatura T1 — 7 Giorni</div>
        <div class="chart-container tall"><canvas id="chart7Temp"></canvas></div>
      </div>
      <div class="chart-panel">
        <div class="chart-title">▸ Umidità U1 — 7 Giorni</div>
        <div class="chart-container tall"><canvas id="chart7Hum"></canvas></div>
      </div>
      <div class="chart-panel">
        <div class="chart-title">▸ Umidità Terreno — 7 Giorni</div>
        <div class="chart-container tall"><canvas id="chart7Soil"></canvas></div>
      </div>
      <div class="chart-panel">
        <div class="chart-title">▸ Pressione PR1 — 7 Giorni</div>
        <div class="chart-container tall"><canvas id="chart7Pres"></canvas></div>
      </div>
      <div class="chart-panel">
        <div class="chart-title">▸ Luminosità — 7 Giorni (scala log)</div>
        <div class="chart-container tall"><canvas id="chart7Lux"></canvas></div>
      </div>

    </div>
  </div>
</div>

<div class="footer-bar">CORTIGO CAMPATI — FONTANELLE (TV) — PRECISION AGRICULTURE MONITORING — PY v2.5.1</div>

<script>
const rawData  = {json_data};
const pageDate = "{display_date}";
const CGI_URL  = window.location.pathname;  // stesso script


// ============================================================
//  BARRA METEO — Open-Meteo API (gratuita, no key)
//  Fontanelle TV: 45.8410N 12.4451E
//  Parametri orari aggiuntivi per agricoltura
// ============================================================
const METEO_LAT = 45.834996;
const METEO_LON = 12.444629;

// API con variabili giornaliere + orarie per le 3 fasce
const METEO_URL = [
  'https://api.open-meteo.com/v1/forecast',
  '?latitude=' + METEO_LAT + '&longitude=' + METEO_LON,
  '&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum,',
  'et0_fao_evapotranspiration,windspeed_10m_max,precipitation_probability_max',
  '&hourly=temperature_2m,relativehumidity_2m,dewpoint_2m,precipitation,',
  'windspeed_10m,weathercode,precipitation_probability',
  '&timezone=Europe%2FRome&forecast_days=7'
].join('');

function wmoToIcon(code) {{
  if (code === 0)  return {{ icon:'☀️',  desc:'Sereno' }};
  if (code <= 2)   return {{ icon:'🌤️',  desc:'Poco nuvoloso' }};
  if (code === 3)  return {{ icon:'☁️',  desc:'Nuvoloso' }};
  if (code <= 49)  return {{ icon:'🌫️',  desc:'Nebbia' }};
  if (code <= 55)  return {{ icon:'🌦️',  desc:'Pioggerella' }};
  if (code <= 65)  return {{ icon:'🌧️',  desc:'Pioggia' }};
  if (code <= 75)  return {{ icon:'❄️',  desc:'Neve' }};
  if (code <= 82)  return {{ icon:'🌧️',  desc:'Rovesci' }};
  if (code <= 86)  return {{ icon:'🌨️',  desc:'Rovesci neve' }};
  if (code <= 99)  return {{ icon:'⛈️',  desc:'Temporale' }};
  return {{ icon:'🌡️', desc:'--' }};
}}

const GIORNI_SHORT = ['Dom','Lun','Mar','Mer','Gio','Ven','Sab'];

// Estrae la media oraria di una variabile per una fascia
function fasciaAvg(hourly, field, dateStr, hStart, hEnd) {{
  const vals = [];
  hourly.time.forEach((t, i) => {{
    if (!t.startsWith(dateStr)) return;
    const h = parseInt(t.slice(11, 13));
    if (h >= hStart && h < hEnd) {{
      const v = hourly[field][i];
      if (v !== null && v !== undefined) vals.push(v);
    }}
  }});
  if (!vals.length) return null;
  return vals.reduce((a, b) => a + b, 0) / vals.length;
}}

function fasciaMax(hourly, field, dateStr, hStart, hEnd) {{
  const vals = [];
  hourly.time.forEach((t, i) => {{
    if (!t.startsWith(dateStr)) return;
    const h = parseInt(t.slice(11, 13));
    if (h >= hStart && h < hEnd) {{
      const v = hourly[field][i];
      if (v !== null && v !== undefined) vals.push(v);
    }}
  }});
  return vals.length ? Math.max(...vals) : null;
}}

function fasciaSum(hourly, field, dateStr, hStart, hEnd) {{
  let sum = 0;
  hourly.time.forEach((t, i) => {{
    if (!t.startsWith(dateStr)) return;
    const h = parseInt(t.slice(11, 13));
    if (h >= hStart && h < hEnd) {{
      const v = hourly[field][i];
      if (v !== null && v !== undefined) sum += v;
    }}
  }});
  return sum;
}}

// Valuta rischio patogeni da dati previsionali di una fascia
function fasciaRischio(t, ur, dp) {{
  const risks = [];
  if (t >= 10 && ur >= 90)           risks.push({{ label:'PERO', cls:'risk-pero', color:'#3b82f6' }});
  if (t >= 20 && t <= 30 && ur >= 40 && ur <= 70) risks.push({{ label:'OIDIO', cls:'risk-oidio', color:'#f59e0b' }});
  if (t >= 15 && t <= 25 && ur >= 90) risks.push({{ label:'BOTRITE', cls:'risk-bot', color:'#ef4444' }});
  return risks;
}}

// Badge rischio aggregato per la card (prende il giorno intero)
function dayRischioBadge(hourly, dateStr) {{
  const t   = fasciaAvg(hourly, 'temperature_2m',      dateStr, 0, 24) ?? 15;
  const ur  = fasciaMax(hourly, 'relativehumidity_2m',  dateStr, 0, 24) ?? 0;
  const risks = fasciaRischio(t, ur, 0);
  if (!risks.length) return '<div class="meteo-agro-badge ok">✓ OK</div>';
  return risks.map(r => `<div class="meteo-agro-badge ${{r.cls}}">${{r.label}}</div>`).join('');
}}

// Popup globale (unico, riposizionato al click)
let meteoData = null;
const popup = document.createElement('div');
popup.className = 'meteo-popup';
popup.id = 'meteoPopup';
document.body.appendChild(popup);
document.addEventListener('click', e => {{
  if (!e.target.closest('.meteo-day') && !e.target.closest('.meteo-popup')) {{
    popup.classList.remove('visible');
    document.querySelectorAll('.meteo-day').forEach(d => d.classList.remove('expanded'));
  }}
}});

function showDayPopup(dayEl, dateStr, dayLabel) {{
  if (!meteoData) return;
  const daily  = meteoData.daily;
  const hourly = meteoData.hourly;
  const di = daily.time.indexOf(dateStr);

  // Fasce: mattina 06-12, mezzogiorno 12-16, sera 16-22
  const fasce = [
    {{ name:'🌅 MATTINA',      h0:6,  h1:12 }},
    {{ name:'☀️ MEZZOGIORNO', h0:12, h1:16 }},
    {{ name:'🌆 SERA',         h0:16, h1:22 }},
  ];

  let html = `<div class="meteo-popup-header">
    <span>${{wmoToIcon(daily.weathercode[di]).icon}} ${{dayLabel}} — ${{dateStr}}</span>
    <span class="meteo-popup-close" onclick="document.getElementById('meteoPopup').classList.remove('visible');document.querySelectorAll('.meteo-day').forEach(d=>d.classList.remove('expanded'))">✕</span>
  </div>`;

  // Riepilogo giornaliero
  const et0  = daily.et0_fao_evapotranspiration?.[di]?.toFixed(1) ?? '--';
  const wmax = Math.round(daily.windspeed_10m_max?.[di] ?? 0);
  const rain = (daily.precipitation_sum[di] ?? 0).toFixed(1);
  const pmax = daily.precipitation_probability_max?.[di] ?? '--';
  html += `<div class="meteo-fascia">
    <div class="meteo-fascia-title">RIEPILOGO GIORNALIERO</div>
    <div class="meteo-fascia-grid">
      <div class="meteo-param"><div class="meteo-param-label">T MAX</div><div class="meteo-param-value" style="color:#ff6b6b">${{Math.round(daily.temperature_2m_max[di])}}°C</div></div>
      <div class="meteo-param"><div class="meteo-param-label">T MIN</div><div class="meteo-param-value" style="color:#4dabf7">${{Math.round(daily.temperature_2m_min[di])}}°C</div></div>
      <div class="meteo-param"><div class="meteo-param-label">PIOGGIA</div><div class="meteo-param-value ${{parseFloat(rain)>5?'warn':''}}">${{rain}} mm</div></div>
      <div class="meteo-param"><div class="meteo-param-label">PROB PIOG</div><div class="meteo-param-value ${{pmax>70?'warn':''}}">${{pmax}}%</div></div>
      <div class="meteo-param"><div class="meteo-param-label">VENTO MAX</div><div class="meteo-param-value ${{wmax>40?'warn':''}}">${{wmax}} km/h</div></div>
      <div class="meteo-param"><div class="meteo-param-label">ET₀</div><div class="meteo-param-value" style="color:#20c997">${{et0}} mm</div></div>
    </div>
  </div>`;

  // Fasce orarie
  fasce.forEach(f => {{
    const t   = fasciaAvg(hourly, 'temperature_2m',       dateStr, f.h0, f.h1);
    const ur  = fasciaAvg(hourly, 'relativehumidity_2m',  dateStr, f.h0, f.h1);
    const dp  = fasciaAvg(hourly, 'dewpoint_2m',          dateStr, f.h0, f.h1);
    const w   = fasciaAvg(hourly, 'windspeed_10m',        dateStr, f.h0, f.h1);
    const r   = fasciaSum(hourly, 'precipitation',        dateStr, f.h0, f.h1);
    const pp  = fasciaMax(hourly, 'precipitation_probability', dateStr, f.h0, f.h1);
    if (t === null) return;

    const tR  = t.toFixed(1);
    const urR = Math.round(ur ?? 0);
    const dpR = dp?.toFixed(1) ?? '--';
    const wR  = Math.round(w ?? 0);
    const rR  = r.toFixed(1);
    const ppR = Math.round(pp ?? 0);
    const risks = fasciaRischio(parseFloat(tR), urR, parseFloat(dpR));

    html += `<div class="meteo-fascia">
      <div class="meteo-fascia-title">${{f.name}} (${{f.h0}}:00–${{f.h1}}:00)</div>
      <div class="meteo-fascia-grid">
        <div class="meteo-param"><div class="meteo-param-label">TEMP</div><div class="meteo-param-value">${{tR}}°C</div></div>
        <div class="meteo-param"><div class="meteo-param-label">UR</div><div class="meteo-param-value ${{urR>=90?'alert':urR>=70?'warn':''}}">${{urR}}%</div></div>
        <div class="meteo-param"><div class="meteo-param-label">DEW PT</div><div class="meteo-param-value">${{dpR}}°C</div></div>
        <div class="meteo-param"><div class="meteo-param-label">VENTO</div><div class="meteo-param-value ${{wR>40?'warn':''}}">${{wR}} km/h</div></div>
        <div class="meteo-param"><div class="meteo-param-label">PIOGGIA</div><div class="meteo-param-value ${{parseFloat(rR)>3?'warn':''}}">${{rR}} mm</div></div>
        <div class="meteo-param"><div class="meteo-param-label">PROB</div><div class="meteo-param-value ${{ppR>70?'warn':''}}">${{ppR}}%</div></div>
      </div>
      ${{risks.length ? `<div style="display:flex;gap:4px;margin-top:6px">${{risks.map(r=>`<div class="meteo-agro-badge ${{r.cls}}">⚠ RISCHIO ${{r.label}}</div>`).join('')}}</div>` : '<div class="meteo-agro-badge ok" style="margin-top:4px">✓ CONDIZIONI OK</div>'}}
    </div>`;
  }});

  // ET0 e nota irrigazione
  const et0f = parseFloat(et0);
  const rainf = parseFloat(rain);
  const deficit = (et0f - rainf).toFixed(1);
  html += `<div class="meteo-agro-section">
    <div class="meteo-agro-title">🌱 NOTE AGRONOMICHE</div>
    <div class="meteo-agro-row">
      <div class="meteo-agro-dot" style="background:#20c997"></div>
      <span>ET₀ giornaliera: <strong style="color:#20c997">${{et0}} mm</strong></span>
    </div>
    <div class="meteo-agro-row">
      <div class="meteo-agro-dot" style="background:#4dabf7"></div>
      <span>Pioggia prevista: <strong style="color:#4dabf7">${{rain}} mm</strong></span>
    </div>
    <div class="meteo-agro-row">
      <div class="meteo-agro-dot" style="background:${{parseFloat(deficit)>2?'#f59e0b':'#20c997'}}"></div>
      <span>Deficit idrico: <strong style="color:${{parseFloat(deficit)>2?'#f59e0b':'#20c997'}}">${{deficit}} mm</strong>
      ${{parseFloat(deficit)>2?' ⚠ valutare irrigazione':''}}</span>
    </div>
  </div>`;

  popup.innerHTML = html;
  popup.classList.add('visible');

  // Posizionamento popup
  const rect = dayEl.getBoundingClientRect();
  const pw = 290;
  let left = rect.left + window.scrollX;
  if (left + pw > window.innerWidth - 10) left = window.innerWidth - pw - 10;
  if (left < 5) left = 5;
  const top = rect.bottom + window.scrollY + 6;
  popup.style.left = left + 'px';
  popup.style.top  = top + 'px';
  popup.style.width = pw + 'px';
}}

async function loadMeteo() {{
  const bar = document.getElementById('meteoBar');
  try {{
    const resp = await fetch(METEO_URL);
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    meteoData = await resp.json();
    const daily  = meteoData.daily;
    const hourly = meteoData.hourly;

    bar.className = 'meteo-bar';
    bar.innerHTML = '<div class="meteo-loc">📍 FONTANELLE TV</div>';

    const todayStr = new Date().toISOString().slice(0, 10);

    daily.time.forEach((dateStr, i) => {{
      const d      = new Date(dateStr + 'T12:00:00');
      const label  = i === 0 ? 'OGGI' : GIORNI_SHORT[d.getDay()];
      const wmo    = daily.weathercode[i];
      const tmax   = Math.round(daily.temperature_2m_max[i]);
      const tmin   = Math.round(daily.temperature_2m_min[i]);
      const rain   = (daily.precipitation_sum[i] ?? 0).toFixed(1);
      const wet    = parseFloat(rain) >= 1;
      const info   = wmoToIcon(wmo);
      const isToday = (dateStr === todayStr);
      const badge  = dayRischioBadge(hourly, dateStr);

      const div = document.createElement('div');
      div.className = 'meteo-day' + (isToday ? ' today' : '');
      div.title = info.desc + ' — clicca per dettagli';
      div.innerHTML = `
        <div class="meteo-day-label">${{label}}</div>
        <div class="meteo-icon">${{info.icon}}</div>
        <div class="meteo-temps">
          <span class="meteo-tmax">${{tmax}}°</span>
          <span class="meteo-tmin">${{tmin}}°</span>
        </div>
        <div class="meteo-rain${{wet ? ' wet' : ''}}">💧${{rain}}mm</div>
        ${{badge}}`;

      div.addEventListener('click', e => {{
        e.stopPropagation();
        const wasExpanded = div.classList.contains('expanded');
        document.querySelectorAll('.meteo-day').forEach(d => d.classList.remove('expanded'));
        popup.classList.remove('visible');
        if (!wasExpanded) {{
          div.classList.add('expanded');
          showDayPopup(div, dateStr, label);
        }}
      }});

      bar.appendChild(div);
    }});

  }} catch(e) {{
    bar.innerHTML = '<span style="color:#6b7280;font-size:10px;letter-spacing:2px">⚠ METEO NON DISPONIBILE</span>';
    console.warn('[Meteo]', e);
  }}
}}

loadMeteo();

// ============================================================
//  UTILITIES
// ============================================================
function updateClock() {{
  const now = new Date();
  document.getElementById('clock').textContent = now.toUTCString().split(' ')[4] + ' UTC';
}}
updateClock(); setInterval(updateClock, 1000);

(function() {{ document.getElementById('datePicker').value = pageDate; }})();
function goDate(n) {{
  const d = new Date(document.getElementById('datePicker').value);
  d.setDate(d.getDate() + n);
  window.location.href = '?date=' + d.toISOString().slice(0,10).replace(/-/g,'');
}}
function goToday() {{ window.location.href = '?'; }}
document.getElementById('datePicker').addEventListener('change', function() {{
  window.location.href = '?date=' + this.value.replace(/-/g,'');
}});

// Converte timestamp UTC in HH:MM ora di Roma (gestisce CEST/CET automaticamente)
const _romeHMFmt = new Intl.DateTimeFormat('it-IT', {{
  timeZone: 'Europe/Rome', hour: '2-digit', minute: '2-digit', hour12: false
}});
function toHM(ts) {{
  return _romeHMFmt.format(new Date(ts * 1000));
}}
function luPayloadToLux(lu) {{
  const v = parseFloat(lu);
  if (isNaN(v) || v <= 0) return 0;
  return Math.pow(10, v / 200.0) - 1.0;
}}

// ============================================================
//  TAB SWITCHER
// ============================================================
let charts7loaded = false;
function switchView(v) {{
  document.getElementById('view-1d').style.display = v==='1d' ? 'block' : 'none';
  document.getElementById('view-7d').style.display = v==='7d' ? 'block' : 'none';
  document.getElementById('nav-1d').style.display  = v==='1d' ? '' : 'none';
  document.getElementById('statsbar-1d').style.display = v==='1d' ? '' : 'none';
  document.getElementById('alertBar').style.display = v==='1d' && document.getElementById('alertBar').classList.contains('visible') ? '' : 'none';
  document.getElementById('tab-1d').classList.toggle('active', v==='1d');
  document.getElementById('tab-7d').classList.toggle('active', v==='7d');
  document.getElementById('tab-info').textContent =
    v==='1d' ? 'Vista giornaliera — ' + pageDate
             : 'Ultimi 7 giorni fino al ' + pageDate;
  if (v==='7d' && !charts7loaded) {{ load7Days(); }}
}}

// ============================================================
//  FENOLOGIA + PATOGENI
// ============================================================
const FENOLOGIA = {{
  germogliamento: {{ start:'04-01', end:'04-30' }},
  fioritura:      {{ start:'05-15', end:'06-15' }},
  invaiatura:     {{ start:'07-15', end:'08-31' }}
}};
function inSeasonFor(patogen) {{
  const today = pageDate.slice(5);
  switch(patogen) {{
    case 'oidio':   return today >= '04-01' && today <= '08-31';
    case 'pero':    return today >= '04-01' && today <= '06-15';
    case 'botrite': return today >= '07-15' && today <= '10-31';
    default: return false;
  }}
}}
const PATOGEN = {{
  oidio:   {{ check: (t,u) => inSeasonFor('oidio')   && t>=20 && t<=30 && u>=40 && u<=70 }},
  pero:    {{ check: (t,u) => inSeasonFor('pero')    && t>=10 && u>=90 }},
  botrite: {{ check: (t,u) => inSeasonFor('botrite') && t>=15 && t<=25 && u>=90 }},
}};

// Valuta il rischio giornaliero per un array di record
// Restituisce oggetto con score e dettaglio per ogni patogeno
function calcDayRisk(data) {{
  if (!data || !data.length) return null;

  // Intervallo medio tra campioni in ore
  const avgInt = data.length > 1
    ? (data[data.length-1].ts - data[0].ts) / (data.length - 1) / 3600
    : 1/6;

  // ---- PERONOSPORA ----
  // Ore consecutive UR>=90% + T>=10°C (condizione di Mills)
  let peroStreak=0, peroMax=0;
  let peroOreUR=0;
  data.forEach(d => {{
    const t=parseFloat(d.t1), u=parseFloat(d.u1);
    if (u>=90 && t>=10) {{ peroStreak++; peroMax=Math.max(peroMax,peroStreak); }}
    else peroStreak=0;
    if (u>=90) peroOreUR++;
  }});
  const peroOreConsec = peroMax * avgInt;
  const peroOreTot    = peroOreUR * avgInt;
  const peroScore = Math.min(100,
    (peroOreConsec>=6?60:peroOreConsec>=4?40:peroOreConsec>=2?20:0) +
    (peroOreTot>=10?40:peroOreTot>=6?25:peroOreTot>=3?10:0)
  );
  const peroLevel = peroScore>=60?'alert':peroScore>=30?'warn':peroScore>0?'low':'ok';

  // ---- OIDIO ----
  // Ore in range T 20-30°C + UR 40-70% (ottimale per conidi)
  let oidioOre=0, oidioOreOttimale=0;
  data.forEach(d => {{
    const t=parseFloat(d.t1), u=parseFloat(d.u1);
    if (t>=20 && t<=30) {{
      oidioOre++;
      if (u>=40 && u<=70) oidioOreOttimale++;
    }}
  }});
  const oidioH     = oidioOre * avgInt;
  const oidioHOtt  = oidioOreOttimale * avgInt;
  const oidioScore = Math.min(100,
    (oidioH>=10?40:oidioH>=6?25:oidioH>=3?10:0) +
    (oidioHOtt>=6?60:oidioHOtt>=3?35:oidioHOtt>=1?15:0)
  );
  const oidioLevel = oidioScore>=60?'alert':oidioScore>=30?'warn':oidioScore>0?'low':'ok';

  // ---- BOTRITE ----
  // Ore T 15-25°C + UR>=90% (Glera particolarmente sensibile)
  // Fattore aggravante: pioggia (aumento UT)
  let botOre=0, botStreakMax=0, botStreak=0;
  let rainEvents=0;
  data.forEach((d,i) => {{
    const t=parseFloat(d.t1), u=parseFloat(d.u1), ut=parseFloat(d.ut);
    if (t>=15 && t<=25 && u>=90) {{ botOre++; botStreak++; botStreakMax=Math.max(botStreakMax,botStreak); }}
    else botStreak=0;
    if (i>0 && ut > parseFloat(data[i-1].ut)+5) rainEvents++;
  }});
  const botH      = botOre * avgInt;
  const botHStreak= botStreakMax * avgInt;
  const botScore  = Math.min(100,
    (botH>=8?40:botH>=4?25:botH>=2?10:0) +
    (botHStreak>=4?40:botHStreak>=2?20:botHStreak>=1?10:0) +
    (rainEvents>=3?20:rainEvents>=1?10:0)
  );
  const botLevel = botScore>=60?'alert':botScore>=30?'warn':botScore>0?'low':'ok';

  // Score globale
  const globalScore = Math.round((peroScore*0.4 + oidioScore*0.3 + botScore*0.3));
  const globalLevel = globalScore>=60?'alert':globalScore>=30?'warn':globalScore>0?'low':'ok';

  // ---- BRINA/GELO — rischio germogli ----
  // Soglie agronomiche Glera:
  //   T ≤ 2°C + UR ≥ 80%  → brina possibile (punto di rugiada basso)
  //   T ≤ 0°C              → gelo certo
  //   durata critica: ≥ 30 min a T≤2 già danneggia gemme aperte
  // In fase di germogliamento (mar-mag) la sensibilità è massima
  const FROST_T_WARN  = 2.0;   // °C soglia brina
  const FROST_T_ALERT = 0.0;   // °C soglia gelo
  const FROST_UR_MIN  = 80.0;  // % umidità favorevole alla brina
  const FROST_DUR_WARN  = 3;   // campioni consecutivi (≈30min) → warn
  const FROST_DUR_ALERT = 6;   // campioni consecutivi (≈60min) → alert

  let frostStreak=0, frostStreakMax=0;
  let frostOreWarn=0, frostOreAlert=0;
  let tMinObs = 999;
  data.forEach(d => {{
    const t=parseFloat(d.t1), u=parseFloat(d.u1);
    tMinObs = Math.min(tMinObs, t);
    if (t <= FROST_T_WARN && u >= FROST_UR_MIN) {{
      frostStreak++;
      frostStreakMax = Math.max(frostStreakMax, frostStreak);
      frostOreWarn++;
      if (t <= FROST_T_ALERT) frostOreAlert++;
    }} else {{
      frostStreak = 0;
    }}
  }});
  const frostH      = frostOreWarn * avgInt;
  const frostHAlert = frostOreAlert * avgInt;
  const frostScore  = Math.min(100,
    (frostStreakMax >= FROST_DUR_ALERT ? 60 : frostStreakMax >= FROST_DUR_WARN ? 30 : frostStreakMax > 0 ? 10 : 0) +
    (frostHAlert >= 1 ? 40 : frostH >= 1 ? 20 : frostH > 0 ? 10 : 0)
  );
  // Attivo tutto l'anno — la gelata tardiva è il rischio principale a marzo-maggio
  const frostLevel = frostScore >= 60 ? 'alert' : frostScore >= 30 ? 'warn' : frostScore > 0 ? 'low' : 'ok';

  return {{
    pero:   {{ score:Math.round(peroScore),  level:peroLevel,  oreConsec:peroOreConsec.toFixed(1),  oreTot:peroOreTot.toFixed(1) }},
    oidio:  {{ score:Math.round(oidioScore), level:oidioLevel, ore:oidioH.toFixed(1), oreOtt:oidioHOtt.toFixed(1) }},
    bot:    {{ score:Math.round(botScore),   level:botLevel,   ore:botH.toFixed(1),   rain:rainEvents }},
    frost:  {{ score:Math.round(frostScore), level:frostLevel, ore:frostH.toFixed(1), oreAlert:frostHAlert.toFixed(1), tMin:tMinObs.toFixed(1), streak:frostStreakMax }},
    global: {{ score:globalScore, level:globalLevel }},
    inSeason: {{
      pero:   inSeasonFor('pero'),
      oidio:  inSeasonFor('oidio'),
      botrite:inSeasonFor('botrite'),
    }}
  }};
}}

// Badge HTML compatto per una card giorno (vista 7gg)
function riskBadgeHTML(risk) {{
  if (!risk) return '<span style="color:#6b7280;font-size:9px">NO DATA</span>';
  const badges = [];
  const lvlColor = {{ ok:'#20c997', low:'#84cc16', warn:'#f59e0b', alert:'#ef4444' }};
  const lvlLabel = {{ ok:'OK', low:'BASSO', warn:'MED', alert:'ALTO' }};
  if (risk.inSeason.pero && risk.pero.level !== 'ok')
    badges.push(`<span style="background:rgba(59,130,246,0.2);color:#60a5fa;font-size:8px;padding:1px 4px;border-radius:2px">PERO ${{lvlLabel[risk.pero.level]}}</span>`);
  if (risk.inSeason.oidio && risk.oidio.level !== 'ok')
    badges.push(`<span style="background:rgba(245,158,11,0.2);color:#fbbf24;font-size:8px;padding:1px 4px;border-radius:2px">OIDIO ${{lvlLabel[risk.oidio.level]}}</span>`);
  if (risk.inSeason.botrite && risk.bot.level !== 'ok')
    badges.push(`<span style="background:rgba(239,68,68,0.2);color:#fca5a5;font-size:8px;padding:1px 4px;border-radius:2px">BOT ${{lvlLabel[risk.bot.level]}}</span>`);
  if (!badges.length)
    return `<span style="color:#20c997;font-size:9px">✓ OK</span>`;
  return badges.join(' ');
}}




(function updateSeasonIndicators() {{
  const periods = {{ oidio:'apr-ago', pero:'apr-giu', botrite:'lug-ott' }};
  ['oidio','pero','botrite'].forEach(p => {{
    const active = inSeasonFor(p);
    const el = document.getElementById('pl-season-'+p);
    const item = document.getElementById('pl-'+p);
    if (el) {{
      el.textContent = active ? '● ATTIVO ('+periods[p]+')' : '○ FUORI STAGIONE ('+periods[p]+')';
      el.className = 'pl-season ' + (active ? 'active' : 'inactive');
    }}
    if (item && !active) item.classList.add('pl-inactive');
  }});
}})();

// ============================================================
//  PLUGIN BANDE
// ============================================================
const bandPlugin = {{
  id:'bandPlugin',
  beforeDraw(chart, args, opts) {{
    if (!opts || !opts.bands || !opts.bands.length) return;
    const {{ ctx, chartArea, scales }} = chart;
    const yScale = scales['y'];
    if (!yScale || !chartArea) return;
    ctx.save();
    opts.bands.forEach(b => {{
      const yTop    = yScale.getPixelForValue(Math.min(b.yMax, yScale.max));
      const yBottom = yScale.getPixelForValue(Math.max(b.yMin, yScale.min));
      const top = Math.min(yTop, yBottom);
      const height = Math.abs(yBottom - yTop);
      if (height < 1) return;
      ctx.fillStyle = b.fill;
      ctx.fillRect(chartArea.left, top, chartArea.width, height);
      ctx.strokeStyle = b.stroke;
      ctx.lineWidth = 1; ctx.setLineDash([5,5]);
      ctx.beginPath(); ctx.moveTo(chartArea.left, top); ctx.lineTo(chartArea.right, top); ctx.stroke();
      ctx.setLineDash([]);
    }});
    ctx.restore();
  }}
}};
Chart.register(bandPlugin);

// ============================================================
//  BASE OPTS 1D
// ============================================================
function baseOpts(bands) {{
  return {{
    responsive:true, maintainAspectRatio:false,
    animation:{{ duration:600, easing:'easeOutQuart' }},
    plugins:{{
      legend:{{ labels:{{ color:'#b0bec5', font:{{family:'Share Tech Mono',size:11}}, boxWidth:12, padding:20 }} }},
      tooltip:{{ backgroundColor:'#0d1117', borderColor:'#1a2332', borderWidth:1, titleColor:'#c9d1d9', bodyColor:'#b0bec5', titleFont:{{family:'Share Tech Mono'}}, bodyFont:{{family:'Share Tech Mono'}} }},
      bandPlugin:{{ bands: bands||[] }}
    }},
    scales:{{
      x:{{ grid:{{color:'#131b27'}}, ticks:{{color:'#aab4be', font:{{family:'Share Tech Mono',size:10}}, maxTicksLimit:24}} }},
      y:{{ grid:{{color:'#131b27'}}, ticks:{{color:'#aab4be', font:{{family:'Share Tech Mono',size:10}}}} }}
    }},
    elements:{{ point:{{radius:2, hoverRadius:5}}, line:{{tension:0.3, borderWidth:2}} }}
  }};
}}
// Controllo brina/gelo inline — usato da lineWithRisk e lineUT
function isFrost(t, u) {{
  return t <= 2.0 && u >= 80.0;
}}

function lineWithRisk(label, data, field, color) {{
  const vals = data.map(d => parseFloat(d[field]));
  const ptBg = data.map(d => {{
    const t=parseFloat(d.t1), u=parseFloat(d.u1);
    if (isFrost(t,u))               return '#67e8f9';  // ❄ gelo/brina — priorità massima
    if (PATOGEN.botrite.check(t,u)) return '#ef4444';
    if (PATOGEN.pero.check(t,u))    return '#3b82f6';
    if (PATOGEN.oidio.check(t,u))   return '#f59e0b';
    return color;
  }});
  const ptBorder = data.map(d => {{
    const t=parseFloat(d.t1), u=parseFloat(d.u1);
    if (isFrost(t,u))               return '#ffffff';
    if (PATOGEN.botrite.check(t,u)) return '#ff6b6b';
    if (PATOGEN.pero.check(t,u))    return '#60a5fa';
    if (PATOGEN.oidio.check(t,u))   return '#fbbf24';
    return color;
  }});
  const ptR = data.map(d => {{
    const t=parseFloat(d.t1), u=parseFloat(d.u1);
    return (isFrost(t,u)||PATOGEN.botrite.check(t,u)||PATOGEN.pero.check(t,u)||PATOGEN.oidio.check(t,u)) ? 7 : 2;
  }});
  return {{ label, data:vals, borderColor:color, backgroundColor:color+'18', fill:false,
    pointBackgroundColor:ptBg, pointBorderColor:ptBorder,
    pointBorderWidth:ptR.map(r=>r>2?2:1), pointRadius:ptR, pointHoverRadius:ptR.map(r=>r+3),
    tension:0.3, borderWidth:2 }};
}}
function lineUT(data) {{
  const vals = data.map(d => parseFloat(d.ut));
  // Pioggia = aumento UT > 2% rispetto al campione precedente
  const isRain = (i) => i > 0 && (vals[i] - vals[i-1]) > 2.0;
  return {{ label:'UT Terreno (\u25cf pioggia >2% · ❄ brina)', data:vals,
    borderColor:'#20c997', backgroundColor:'#20c99718', fill:false,
    pointBackgroundColor: vals.map((v,i) => {{
      const t=parseFloat(data[i].t1), u=parseFloat(data[i].u1);
      if (isFrost(t,u)) return '#67e8f9';  // ❄ brina — ciano (stesso colore frost)
      if (isRain(i))    return '#fbbf24';  // 💧 pioggia — giallo ambra
      return '#20c997';
    }}),
    pointBorderColor: vals.map((v,i) => {{
      const t=parseFloat(data[i].t1), u=parseFloat(data[i].u1);
      if (isFrost(t,u)) return '#ffffff';
      if (isRain(i))    return '#ffffff';
      return '#20c997';
    }}),
    pointBorderWidth: vals.map((v,i) => {{
      const t=parseFloat(data[i].t1), u=parseFloat(data[i].u1);
      return (isFrost(t,u) || isRain(i)) ? 2 : 1;
    }}),
    pointRadius: vals.map((v,i) => {{
      const t=parseFloat(data[i].t1), u=parseFloat(data[i].u1);
      return (isFrost(t,u) || isRain(i)) ? 8 : 2;
    }}),
    pointHoverRadius: vals.map((v,i) => {{
      const t=parseFloat(data[i].t1), u=parseFloat(data[i].u1);
      return (isFrost(t,u) || isRain(i)) ? 11 : 5;
    }}),
    tension:0.3, borderWidth:2 }};
}}

// ============================================================
//  INDICATORI EPI
// ============================================================
function calcOreUR90(data) {{
  let maxStreak=0, cur=0, avgInt=1/12;
  if (data.length>1) avgInt=(data[data.length-1].ts-data[0].ts)/(data.length-1)/3600;
  data.forEach(d=>{{ if(parseFloat(d.u1)>=90){{cur++;maxStreak=Math.max(maxStreak,cur);}}else cur=0; }});
  return {{ ore:(maxStreak*avgInt).toFixed(1) }};
}}
function calcOreOidio(data) {{
  let count=0, avgInt=1/12;
  if (data.length>1) avgInt=(data[data.length-1].ts-data[0].ts)/(data.length-1)/3600;
  data.forEach(d=>{{ const t=parseFloat(d.t1); if(t>=20&&t<=30) count++; }});
  return {{ ore:(count*avgInt).toFixed(1) }};
}}
function calcDeltaP(data) {{
  const v=data.filter(d=>parseFloat(d.pr1)>100);
  if(v.length<2) return {{delta:'0'}};
  return {{ delta:(parseFloat(v[v.length-1].pr1)-parseFloat(v[0].pr1)).toFixed(1) }};
}}
function calcEsc(data) {{
  const temps=data.map(d=>parseFloat(d.t1)).filter(v=>!isNaN(v));
  if(!temps.length) return {{esc:'0',tmax:'0',tmin:'0'}};
  const tmax=Math.max(...temps), tmin=Math.min(...temps);
  return {{esc:(tmax-tmin).toFixed(1),tmax:tmax.toFixed(1),tmin:tmin.toFixed(1)}};
}}
function calcRisk(oreP,oreO,dp,esc) {{
  return Math.round(
    Math.min(30,(parseFloat(oreP.ore)/6)*30) +
    Math.min(25,(parseFloat(oreO.ore)/12)*25) +
    Math.min(25,(Math.max(0,-parseFloat(dp.delta))/6)*25) +
    Math.min(20,(parseFloat(esc.esc)/20)*20)
  );
}}
function renderEpiCard(cardId,barId,statusId,valId,value,unit,barPct,level,statusText) {{
  document.getElementById(valId).textContent = value+unit;
  const bar=document.getElementById(barId);
  bar.style.width=Math.min(100,barPct)+'%';
  bar.style.background=level==='ok'?'#20c997':level==='low'?'#84cc16':level==='warn'?'#f59e0b':'#ef4444';
  document.getElementById(cardId).classList.add('epi-'+level);
  const st=document.getElementById(statusId);
  st.textContent=statusText; st.className='epi-status '+level;
}}

// ============================================================
//  COLORI 7 GIORNI (dal più vecchio al più recente)
// ============================================================
const DAY_COLORS = [
  '#6b7280',  // -6 giorni: grigio scuro
  '#2d6a8a',  // -5: blu scuro
  '#3b82f6',  // -4: blu
  '#8b5cf6',  // -3: viola
  '#f59e0b',  // -2: arancio
  '#10b981',  // -1: verde
  '#00ff88',  // oggi: accent verde
];

// ============================================================
//  CARICAMENTO E RENDERING 7 GIORNI
// ============================================================
async function load7Days() {{
  // Calcola le date degli ultimi 7 giorni
  const dates = [];
  const [py, pm, pd] = pageDate.split('-').map(Number);
  for (let i = 6; i >= 0; i--) {{
    const d = new Date(Date.UTC(py, pm - 1, pd - i));
    const y  = d.getUTCFullYear();
    const m  = String(d.getUTCMonth() + 1).padStart(2, '0');
    const dd = String(d.getUTCDate()).padStart(2, '0');
    dates.push({{ key: `${{y}}${{m}}${{dd}}`, label: `${{m}}/${{dd}}` }});
  }}

  // Fetch parallelo di tutti i giorni
  const fetches = dates.map(d =>
    fetch(`${{CGI_URL}}?mode=json&date=${{d.key}}`)
      .then(r => r.ok ? r.json() : [])
      .catch(() => [])
  );
  const allData = await Promise.all(fetches);

  document.getElementById('w7-loading').style.display = 'none';
  document.getElementById('w7-content').style.display = '';
  charts7loaded = true;

  await new Promise(r => setTimeout(r, 50));

  // Legenda giorni
  const legEl = document.getElementById('days-legend');
  legEl.innerHTML = '<span style="color:var(--text);font-size:10px;letter-spacing:2px;margin-right:8px">GIORNI:</span>';
  dates.forEach((d,i) => {{
    const hasData = allData[i].length > 0;
    legEl.innerHTML += `
      <div class="day-leg" style="opacity:${{hasData?1:0.3}}">
        <div class="day-leg-dot" style="background:${{DAY_COLORS[i]}}"></div>
        <span style="color:${{DAY_COLORS[i]}}">${{d.label}}${{i===6?' ★':''}}</span>
        <span style="color:#6b7280">(${{allData[i].length}})</span>
      </div>`;
  }});

  // Stats aggregate per ogni giorno
  const statsGrid = document.getElementById('stats7-grid');
  statsGrid.innerHTML = '';
  const aggT1min=[], aggT1max=[], aggT1avg=[], aggU1max=[], aggPr1=[], aggSoil=[];

  dates.forEach((d,i) => {{
    const data = allData[i];
    if (!data.length) return;
    const t1v = data.map(r=>parseFloat(r.t1));
    const u1v = data.map(r=>parseFloat(r.u1));
    const pr1v = data.filter(r=>parseFloat(r.pr1)>100).map(r=>parseFloat(r.pr1));
    const soilv = data.map(r=>parseFloat(r.ut));
    const tmin = Math.min(...t1v).toFixed(1);
    const tmax = Math.max(...t1v).toFixed(1);
    const tavg = (t1v.reduce((a,b)=>a+b,0)/t1v.length).toFixed(1);
    const umax = Math.max(...u1v).toFixed(1);
    const pravg = pr1v.length ? (pr1v.reduce((a,b)=>a+b,0)/pr1v.length).toFixed(0) : '--';
    const soilavg = (soilv.reduce((a,b)=>a+b,0)/soilv.length).toFixed(0);
    aggT1min.push(parseFloat(tmin)); aggT1max.push(parseFloat(tmax));
    aggT1avg.push(parseFloat(tavg)); aggU1max.push(parseFloat(umax));
    if (pravg!=='--') aggPr1.push(parseFloat(pravg));
    aggSoil.push(parseFloat(soilavg));

    // Calcola risk per questo giorno
    const dayR = calcDayRisk(data);
    const riskBorder = dayR ? (
      dayR.global.level==='alert' ? 'rgba(239,68,68,0.5)' :
      dayR.global.level==='warn'  ? 'rgba(245,158,11,0.4)' :
      dayR.global.level==='low'   ? 'rgba(132,204,22,0.3)' :
      DAY_COLORS[i]+'33'
    ) : DAY_COLORS[i]+'33';

    statsGrid.innerHTML += `
      <div class="stats7-card" style="border-color:${{riskBorder}}">
        <div class="stats7-label" style="color:${{DAY_COLORS[i]}}">${{d.label}} ${{i===6?'★ OGGI':''}}</div>
        <div class="stats7-row"><span class="stats7-key">T min</span><span class="stats7-val lo">${{tmin}}°C</span></div>
        <div class="stats7-row"><span class="stats7-key">T max</span><span class="stats7-val hi">${{tmax}}°C</span></div>
        <div class="stats7-row"><span class="stats7-key">T avg</span><span class="stats7-val avg">${{tavg}}°C</span></div>
        <div class="stats7-row"><span class="stats7-key">UR max</span><span class="stats7-val">${{umax}}%</span></div>
        <div class="stats7-row"><span class="stats7-key">Press.</span><span class="stats7-val">${{pravg}} hPa</span></div>
        <div class="stats7-row"><span class="stats7-key">Soil avg</span><span class="stats7-val">${{soilavg}}%</span></div>
        <div style="margin-top:8px;padding-top:6px;border-top:1px solid var(--border);display:flex;flex-wrap:wrap;gap:3px">
          ${{riskBadgeHTML(dayR)}}
          ${{dayR ? `<span style="color:#6b7280;font-size:8px;margin-left:auto">score:${{dayR.global.score}}</span>` : ''}}
        </div>
      </div>`;
  }});

  // ---- Opzioni base 7gg ----
  function base7Opts(bands, yMin, yMax) {{
    return {{
      responsive:true, maintainAspectRatio:false,
      animation:{{ duration:800, easing:'easeOutQuart' }},
      plugins:{{
        legend:{{ labels:{{ color:'#b0bec5', font:{{family:'Share Tech Mono',size:10}}, boxWidth:10, padding:14 }} }},
        tooltip:{{
          backgroundColor:'#0d1117', borderColor:'#1a2332', borderWidth:1,
          titleColor:'#c9d1d9', bodyColor:'#aab8c8',
          titleFont:{{family:'Share Tech Mono'}}, bodyFont:{{family:'Share Tech Mono'}},
          callbacks:{{
            title: items => {{
              const d = items[0];
              return d.dataset.label + ' — ' + d.label;
            }}
          }}
        }},
        bandPlugin:{{ bands: bands||[] }}
      }},
      scales:{{
        x:{{ grid:{{color:'#0f1820'}}, ticks:{{color:'#6b7280', font:{{family:'Share Tech Mono',size:9}}, maxTicksLimit:24}} }},
        y:{{
          min: yMin, max: yMax,
          grid:{{color:'#131b27'}},
          ticks:{{color:'#aab8c8', font:{{family:'Share Tech Mono',size:10}}}}
        }}
      }},
      elements:{{ point:{{radius:1, hoverRadius:4}}, line:{{tension:0.3, borderWidth:1.5}} }}
    }};
  }}

  // Costruisce dataset per un campo su tutti i giorni
  function buildDatasets7(field, luxMode=false) {{
    return dates.map((d,i) => {{
      const data = allData[i];
      const labels = data.map(r => toHM(r.ts));
      const vals = luxMode
        ? data.map(r => Math.max(luPayloadToLux(r[field]),1))
        : data.map(r => parseFloat(r[field]));
      return {{
        label: d.label + (i===6?' ★':''),
        data: vals,
        borderColor: DAY_COLORS[i],
        backgroundColor: DAY_COLORS[i]+'18',
        fill: false,
        pointRadius: 0,
        pointHoverRadius: 4,
        tension: 0.3,
        borderWidth: i===6 ? 2.5 : 1.5,
        // Etichette x personalizzate per giorno
        parsing: false,
      }};
    }});
  }}

  // Asse X comune: 24 slot orari (00:00 … 23:00)
  // Ogni slot = media di tutti i campioni caduti in quell'ora
  // Con campionamento ogni 10min → ~6 campioni/ora → nessun buco
  function buildLabels7() {{
    const all = [];
    for (let h = 0; h < 24; h++)
      all.push(String(h).padStart(2,'0') + ':00');
    return all;
  }}

  // Raggruppa i record per ora Rome e calcola la media del campo
  // Riusa toHM che già converte in ora Rome
  function mapToHourlyAxis(data, field, luxMode=false) {{
    const buckets = Array.from({{length:24}}, () => []);
    data.forEach(r => {{
      const h   = parseInt(toHM(r.ts).split(':')[0]);
      const val = luxMode ? Math.max(luPayloadToLux(r[field]), 1) : parseFloat(r[field]);
      if (!isNaN(val) && h >= 0 && h < 24) buckets[h].push(val);
    }});
    return buckets.map(b => b.length ? b.reduce((a,c) => a+c, 0) / b.length : null);
  }}

  const commonLabels = buildLabels7();

  function buildDatasets7Mapped(field, luxMode=false) {{
    return dates.map((d,i) => {{
      const data = allData[i];
      return {{
        label: d.label + (i===6?' ★':''),
        data: mapToHourlyAxis(data, field, luxMode),
        borderColor: DAY_COLORS[i],
        backgroundColor: DAY_COLORS[i]+'15',
        fill: false,
        pointRadius: i===6 ? 2 : 0,
        pointHoverRadius: 4,
        tension: 0.4,
        borderWidth: i===6 ? 2.5 : 1.5,
        spanGaps: true,
      }};
    }});
  }}

  const tempBands = [
    {{ yMin:10,yMax:15,fill:'rgba(59,130,246,0.05)',stroke:'rgba(59,130,246,0.2)' }},
    {{ yMin:15,yMax:20,fill:'rgba(239,68,68,0.04)',stroke:'rgba(239,68,68,0.2)'  }},
    {{ yMin:20,yMax:25,fill:'rgba(245,158,11,0.04)',stroke:'rgba(245,158,11,0.2)' }},
    {{ yMin:25,yMax:30,fill:'rgba(245,158,11,0.06)',stroke:'rgba(245,158,11,0.3)' }},
  ];
  const humBands = [
    {{ yMin:40,yMax:70,fill:'rgba(245,158,11,0.05)',stroke:'rgba(245,158,11,0.2)' }},
    {{ yMin:90,yMax:100,fill:'rgba(59,130,246,0.07)',stroke:'rgba(59,130,246,0.3)' }},
  ];

  // Grafico Temperatura 7gg
  new Chart(document.getElementById('chart7Temp'), {{
    type:'line',
    data:{{ labels:commonLabels, datasets:buildDatasets7Mapped('t1') }},
    options: base7Opts(tempBands, 0, 35)
  }});

  // Grafico Umidità 7gg
  new Chart(document.getElementById('chart7Hum'), {{
    type:'line',
    data:{{ labels:commonLabels, datasets:buildDatasets7Mapped('u1') }},
    options: base7Opts(humBands, 0, 100)
  }});

  // Grafico Soil 7gg
  new Chart(document.getElementById('chart7Soil'), {{
    type:'line',
    data:{{ labels:commonLabels, datasets:buildDatasets7Mapped('ut') }},
    options: base7Opts([], 0, 100)
  }});

  // Grafico Pressione 7gg
  new Chart(document.getElementById('chart7Pres'), {{
    type:'line',
    data:{{ labels:commonLabels, datasets:buildDatasets7Mapped('pr1') }},
    options: base7Opts([], null, null)
  }});

  // Grafico Lux 7gg (log)
  const luxOpts7 = base7Opts([], null, null);
  luxOpts7.scales.y = {{
    type:'logarithmic', min:1,
    grid:{{color:'#131b27'}},
    ticks:{{ color:'#aab4be', font:{{family:'Share Tech Mono',size:10}},
      callback: v => [1,10,100,1000,10000,65535].includes(v)
        ? (v>=1000?(v/1000).toFixed(0)+'k lux':v+' lux') : ''
    }}
  }};
  new Chart(document.getElementById('chart7Lux'), {{
    type:'line',
    data:{{ labels:commonLabels, datasets:buildDatasets7Mapped('lu', true) }},
    options: luxOpts7
  }});
}}

// ============================================================
//  RENDER VISTA 1 GIORNO
// ============================================================
if (rawData.length === 0) {{
  document.getElementById('view-1d').querySelector('.dashboard').innerHTML =
    '<div class="no-data"><span class="icon">◇</span>WAITING FOR TELEMETRY DATA...<br><br><small style="opacity:0.5">'+pageDate+'</small></div>';
}} else {{
  const labels = rawData.map(d => toHM(d.ts));
  const last   = rawData[rawData.length-1];
  const lastT  = parseFloat(last.t1);
  const lastU  = parseFloat(last.u1);

  document.getElementById('v-t1').innerHTML  = last.t1  + '<span class="card-unit">°C</span>';
  document.getElementById('v-t2').innerHTML  = last.t2  + '<span class="card-unit">°C</span>';
  document.getElementById('v-u1').innerHTML  = last.u1  + '<span class="card-unit">%</span>';
  document.getElementById('v-u2').innerHTML  = last.u2  + '<span class="card-unit">%</span>';
  document.getElementById('v-ut').innerHTML  = last.ut  + '<span class="card-unit">%</span>';
  document.getElementById('v-lu').innerHTML  = luPayloadToLux(last.lu).toFixed(0) + '<span class="card-unit">lux</span>';
  document.getElementById('v-pr1').innerHTML = last.pr1 + '<span class="card-unit">hPa</span>';
  document.getElementById('v-pr2').innerHTML = last.pr2 + '<span class="card-unit">hPa</span>';

  const t1v=rawData.map(d=>parseFloat(d.t1));
  const u1v=rawData.map(d=>parseFloat(d.u1));
  document.getElementById('statRecords').textContent = rawData.length;
  document.getElementById('statFirst').textContent   = toHM(rawData[0].ts);
  document.getElementById('statLast').textContent    = toHM(last.ts);
  document.getElementById('statT1min').textContent   = Math.min(...t1v).toFixed(1)+'°C';
  document.getElementById('statT1max').textContent   = Math.max(...t1v).toFixed(1)+'°C';
  document.getElementById('statU1min').textContent   = Math.min(...u1v).toFixed(1)+'%';
  document.getElementById('statU1max').textContent   = Math.max(...u1v).toFixed(1)+'%';

  const countRisk = fn => rawData.filter(d=>fn(parseFloat(d.t1),parseFloat(d.u1))).length;
  let anyAlert = false;
  function showAlert(id,valsId,cond,cnt) {{
    if (!cond) return;
    anyAlert=true;
    document.getElementById(id).style.display='flex';
    document.getElementById(valsId).textContent='T='+lastT.toFixed(1)+'°C  UR='+lastU.toFixed(1)+'%  ('+cnt+' rilevazioni oggi)';
  }}
  showAlert('alert-oidio',  'vals-oidio',   PATOGEN.oidio.check(lastT,lastU),   countRisk(PATOGEN.oidio.check));
  showAlert('alert-pero',   'vals-pero',    PATOGEN.pero.check(lastT,lastU),    countRisk(PATOGEN.pero.check));
  showAlert('alert-botrite','vals-botrite', PATOGEN.botrite.check(lastT,lastU), countRisk(PATOGEN.botrite.check));
  if (anyAlert) document.getElementById('alertBar').classList.add('visible');

  const ring=(id,cls)=>document.getElementById(id).classList.add(cls);
  if (PATOGEN.oidio.check(lastT,lastU))   {{ ring('card-t1','ring-oidio');   ring('card-u1','ring-oidio');   }}
  if (PATOGEN.pero.check(lastT,lastU))    {{ ring('card-t1','ring-pero');    ring('card-u1','ring-pero');    }}
  if (PATOGEN.botrite.check(lastT,lastU)) {{ ring('card-t1','ring-botrite'); ring('card-u1','ring-botrite'); }}

  const epiOreP=calcOreUR90(rawData), epiOreO=calcOreOidio(rawData);
  const epiDp=calcDeltaP(rawData), epiEsc=calcEsc(rawData);

  // Calcolo avanzato con calcDayRisk
  const dayRisk = calcDayRisk(rawData);

  // Peronospora — ore consecutive condizioni Mills
  const dr_pero = dayRisk?.pero;
  const oreConsP = dr_pero ? parseFloat(dr_pero.oreConsec) : parseFloat(epiOreP.ore);
  renderEpiCard('epi-ore-pero','epi-bar-ore-pero','epi-status-ore-pero','epi-val-ore-pero',
    dr_pero ? dr_pero.oreConsec : epiOreP.ore, 'h consec',
    (oreConsP/6)*100,
    dr_pero ? dr_pero.level : (oreConsP>=4?'alert':oreConsP>=2?'warn':'ok'),
    dr_pero
      ? (dr_pero.level==='alert'?'✗ ALLERTA — TRATTARE':dr_pero.level==='warn'?'⚠ ATTENZIONE':dr_pero.level==='low'?'↗ RISCHIO INIZIALE':'✓ NELLA NORMA')
        + ' (tot '+dr_pero.oreTot+'h UR≥90%)'
      : (oreConsP>=4?'✗ ALLERTA PERONOSPORA':oreConsP>=2?'⚠ ATTENZIONE':'✓ NELLA NORMA'));

  // Oidio — ore range ottimale T+UR
  const dr_oidio = dayRisk?.oidio;
  const oreOidio = dr_oidio ? parseFloat(dr_oidio.oreOtt) : parseFloat(epiOreO.ore);
  renderEpiCard('epi-ore-oidio','epi-bar-ore-oidio','epi-status-ore-oidio','epi-val-ore-oidio',
    dr_oidio ? dr_oidio.oreOtt : epiOreO.ore, 'h ottim',
    (oreOidio/6)*100,
    dr_oidio ? dr_oidio.level : (oreOidio>=8?'alert':oreOidio>=4?'warn':'ok'),
    dr_oidio
      ? (dr_oidio.level==='alert'?'✗ ALLERTA — TRATTARE':dr_oidio.level==='warn'?'⚠ ATTENZIONE':dr_oidio.level==='low'?'↗ RISCHIO INIZIALE':'✓ NELLA NORMA')
        + ' ('+dr_oidio.ore+'h T 20-30°C)'
      : (oreOidio>=8?'✗ ALLERTA OIDIO':oreOidio>=4?'⚠ ATTENZIONE':'✓ NELLA NORMA'));

  // Delta pressione
  const dp=parseFloat(epiDp.delta);
  renderEpiCard('epi-delta-p','epi-bar-delta-p','epi-status-delta-p','epi-val-delta-p',
    (dp>=0?'+':'')+dp,' hPa',Math.min(100,(Math.abs(dp)/8)*100),
    dp<-6?'alert':dp<-3?'warn':'ok',
    dp<-6?'✗ FRONTE INTENSO IN ARRIVO':dp<-3?'⚠ FRONTE PERTURBATO':'✓ PRESSIONE STABILE');

  // Escursione termica
  const esc=parseFloat(epiEsc.esc);
  renderEpiCard('epi-escursione','epi-bar-escursione','epi-status-escursione','epi-val-escursione',
    epiEsc.esc,'°C',(esc/20)*100, esc>=20?'alert':esc>=15?'warn':'ok',
    (esc>=20?'✗ ESCURSIONE SEVERA':esc>=15?'⚠ ESCURSIONE ELEVATA':'✓ NELLA NORMA')+
    ' (min '+epiEsc.tmin+'° / max '+epiEsc.tmax+'°)');

  // Risk score globale con dettaglio per patogeno
  const globalScore = dayRisk?.global.score ?? 0;
  const botScore    = dayRisk?.bot.score ?? 0;
  const riskDetail  = dayRisk
    ? ` P:${{dayRisk.pero.score}} O:${{dayRisk.oidio.score}} B:${{botScore}}`
    : '';
  renderEpiCard('epi-risk','epi-bar-risk','epi-status-risk','epi-val-risk',
    globalScore,'/100', globalScore,
    globalScore>=60?'alert':globalScore>=30?'warn':globalScore>0?'ok':'ok',
    (globalScore>=60?'✗ ALLERTA — INTERVENIRE':globalScore>=30?'⚠ MONITORARE':globalScore>0?'↗ RISCHIO BASSO':'✓ NESSUN RISCHIO')
    + riskDetail);

  // Brina/Gelo
  const dr_frost = dayRisk?.frost;
  if (dr_frost) {{
    const fScore = dr_frost.score;
    renderEpiCard('epi-frost','epi-bar-frost','epi-status-frost','epi-val-frost',
      dr_frost.tMin,'°C min',
      fScore,
      dr_frost.level,
      (dr_frost.level==='alert' ? '✗ GELO — GERMOGLI IN PERICOLO' :
       dr_frost.level==='warn'  ? '⚠ BRINA POSSIBILE — MONITORARE' :
       dr_frost.level==='low'   ? '↗ TEMPERATURE CRITICHE' :
                                  '✓ NESSUN RISCHIO GELO')
      + ` (${{dr_frost.ore}}h ≤2°C · ${{dr_frost.oreAlert}}h ≤0°C)`
    );
    // Mostra alert bar se frost in warn o alert
    if (dr_frost.level === 'warn' || dr_frost.level === 'alert') {{
      anyAlert = true;
      document.getElementById('alert-frost').style.display = 'flex';
      document.getElementById('vals-frost').textContent =
        `T min=${{dr_frost.tMin}}°C  ${{dr_frost.ore}}h ≤2°C  ${{dr_frost.oreAlert}}h ≤0°C`;
      document.getElementById('alertBar').classList.add('visible');
    }}
  }}

  const tempBands=[
    {{yMin:10,yMax:15,fill:'rgba(59,130,246,0.07)',stroke:'rgba(59,130,246,0.35)'}},
    {{yMin:15,yMax:20,fill:'rgba(239,68,68,0.06)',stroke:'rgba(239,68,68,0.30)'}},
    {{yMin:20,yMax:25,fill:'rgba(245,158,11,0.06)',stroke:'rgba(245,158,11,0.30)'}},
    {{yMin:25,yMax:30,fill:'rgba(245,158,11,0.08)',stroke:'rgba(245,158,11,0.40)'}},
  ];
  const humBands=[
    {{yMin:40,yMax:70,fill:'rgba(245,158,11,0.07)',stroke:'rgba(245,158,11,0.35)'}},
    {{yMin:90,yMax:100,fill:'rgba(59,130,246,0.09)',stroke:'rgba(59,130,246,0.40)'}},
  ];

  const tempOpts=baseOpts(tempBands);
  tempOpts.scales.y={{min:0,max:35,grid:{{color:'#131b27'}},ticks:{{color:'#aab8c8',font:{{family:'Share Tech Mono',size:10}}}}}};
  new Chart(document.getElementById('chartTemp'),{{type:'line',data:{{labels,datasets:[
    lineWithRisk('T1 DHT22',rawData,'t1','#ff6b6b'),
    lineWithRisk('T2 HTU21',rawData,'t2','#ffa94d')
  ]}},options:tempOpts}});

  const humOpts=baseOpts(humBands);
  humOpts.scales.y={{min:0,max:100,grid:{{color:'#131b27'}},ticks:{{color:'#aab8c8',font:{{family:'Share Tech Mono',size:10}}}}}};
  new Chart(document.getElementById('chartHum'),{{type:'line',data:{{labels,datasets:[
    lineWithRisk('U1 DHT22',rawData,'u1','#4dabf7'),
    lineWithRisk('U2 HTU21',rawData,'u2','#9775fa'),
    lineUT(rawData)
  ]}},options:humOpts}});

  const luxArr=rawData.map(d=>Math.max(luPayloadToLux(d.lu),1));
  const luxOpts=baseOpts([]);
  luxOpts.scales.y={{type:'logarithmic',min:1,grid:{{color:'#131b27'}},ticks:{{color:'#aab8c8',font:{{family:'Share Tech Mono',size:10}},callback:v=>[1,10,100,1000,10000,65535].includes(v)?(v>=1000?(v/1000).toFixed(0)+'k lux':v+' lux'):''}}}};
  new Chart(document.getElementById('chartLux'),{{type:'line',data:{{labels,datasets:[{{label:'Lux',data:luxArr,borderColor:'#ffd43b',backgroundColor:'#ffd43b18',fill:false,pointBackgroundColor:'#ffd43b',tension:0.3,borderWidth:2}}]}},options:luxOpts}});

  const presOpts=baseOpts([]);
  presOpts.scales.y1={{position:'right',grid:{{display:false}},ticks:{{color:'#c084fc',font:{{family:'Share Tech Mono',size:10}}}}}};
  new Chart(document.getElementById('chartPres'),{{type:'line',data:{{labels,datasets:[
    {{label:'PR1 BMP180#1',data:rawData.map(d=>parseFloat(d.pr1)),borderColor:'#ff6b9d',backgroundColor:'#ff6b9d18',fill:false,pointBackgroundColor:'#ff6b9d',tension:0.3,borderWidth:2}},
    {{label:'PR2 BMP180#2',data:rawData.map(d=>parseFloat(d.pr2)),borderColor:'#c084fc',backgroundColor:'#c084fc18',fill:false,pointBackgroundColor:'#c084fc',tension:0.3,borderWidth:2,yAxisID:'y1'}}
  ]}},options:presOpts}});
}}
</script>
</body>
</html>""")