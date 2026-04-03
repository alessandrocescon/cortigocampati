"""
CORTIGOCAMPATI — ESP32 VIGNETO FIRMWARE
main.py — MicroPython v2.x
Sensori: DHT22 · HTU21 · BH1750 · BMP180x2 · Soil ADC
Invio:   HTTPS GET -> receiver.cgi
Stabilita':
  - Deep sleep tra le misure (~10uA vs ~50mA idle)
  - WDT hardware 90s (>WiFi timeout totale)
  - feed_wdt() dentro il loop di attesa WiFi
  - IP statico reimpostato ad ogni tentativo
  - Rilevamento cold boot vs wake-from-deepsleep
  - Warm-up DHT22 (2s) solo al cold boot
  - I2C scan solo al cold boot
  - Retry DHT22 (3 tentativi)
  - Tutti i sensori opzionali (payload = 0 se fail)
  - Validazione range su ogni lettura
Alessandro Cescon — 2025
"""

import time
import math
import network
import machine
from machine import Pin, I2C, ADC, WDT, reset_cause, DEEPSLEEP_RESET
import dht

try:
    import urequests as requests
except ImportError:
    import requests

# ============================================================
#  BOOT TYPE
# ============================================================
COLD_BOOT = (reset_cause() != DEEPSLEEP_RESET)

# ============================================================
#  CPU FREQUENCY
# ============================================================
machine.freq(240000000)

# ============================================================
#  WATCHDOG
#  DEVE essere > WIFI_TIMEOUT_S * WIFI_RETRY_N
#  20s * 3 retry = 60s + margine = 90s
# ============================================================
WDT_ENABLE  = True
WDT_TIMEOUT = 90000   # ms — era 60000, troppo poco per 3 retry da 30s

# ============================================================
#  WIFI
# ============================================================
NETWORKS = [
    ("tp_campagna",    "***",  "IP"),
    ("ACWIFI",         "***",       "DHCP"),
    ("acesconwifi24",  "***", "DHCP"),
]
WIFI_TIMEOUT_S = 15   # era 30 — ridotto, 3 retry * 20s = 60s < WDT 90s
WIFI_RETRY_N   = 2

# IP statici in rotazione — ogni tentativo usa un IP diverso
# Tutti e 3 devono essere fuori dal pool DHCP del router
STATIC_IPS  = ["192.168.1.87", "192.168.1.88", "192.168.1.89"]
STATIC_MASK = "255.255.255.0"
STATIC_GW   = "192.168.1.1"
STATIC_DNS1 = "192.168.1.1"
STATIC_DNS2 = "8.8.8.8"

SERVER_URL   = "https://cortigocampati.ddns.net/cgi-bin/receiver.cgi?data="
HTTP_TIMEOUT = 15

# ============================================================
#  TIMING
# ============================================================
SLEEP_S      = 600
DHT_RETRIES  = 3
DHT_RETRY_MS = 2500

# ============================================================
#  PINOUT
# ============================================================
I2C0_SDA = 21
I2C0_SCL = 22
I2C1_SDA = 18
I2C1_SCL = 19
DHT_PIN  = 4
SOIL_PIN = 34

# ============================================================
#  SOIL CALIBRATION
# ============================================================
SOIL_DRY      = 2530
SOIL_WET      = 940
SOIL_SAMPLES  = 8
SOIL_DELAY_MS = 15
SOIL_FLOAT    = 3900

# ============================================================
#  I2C ADDRESSES
# ============================================================
HTU21_ADDR  = 0x40
BH1750_ADDR = 0x23
BMP180_ADDR = 0x77

# ============================================================
#  DRIVER BH1750
# ============================================================
class BH1750:
    CONT_HIRES = 0x10

    def __init__(self, i2c, addr=BH1750_ADDR):
        self.i2c  = i2c
        self.addr = addr
        self.ok   = False

    def begin(self):
        try:
            self.i2c.writeto(self.addr, bytes([0x01]))
            time.sleep_ms(10)
            self.i2c.writeto(self.addr, bytes([self.CONT_HIRES]))
            time.sleep_ms(180)
            self.ok = True
        except OSError as e:
            print("[BH1750] begin error:", e)
            self.ok = False
        return self.ok

    def read_lux(self):
        if not self.ok:
            return None
        try:
            data = self.i2c.readfrom(self.addr, 2)
            raw  = (data[0] << 8) | data[1]
            lux  = raw / 1.2
            return lux if 0 <= lux <= 100000 else None
        except OSError as e:
            print("[BH1750] read error:", e)
            return None

# ============================================================
#  DRIVER HTU21D
# ============================================================
class HTU21:
    CMD_TEMP  = 0xE3
    CMD_HUM   = 0xE5
    CMD_RESET = 0xFE

    def __init__(self, i2c, addr=HTU21_ADDR):
        self.i2c  = i2c
        self.addr = addr
        self.ok   = False

    def begin(self):
        try:
            self.i2c.writeto(self.addr, bytes([self.CMD_RESET]))
            time.sleep_ms(20)
            self.ok = True
        except OSError as e:
            print("[HTU21] begin error:", e)
            self.ok = False
        return self.ok

    def _read(self, cmd, delay_ms):
        self.i2c.writeto(self.addr, bytes([cmd]))
        time.sleep_ms(delay_ms)
        d = self.i2c.readfrom(self.addr, 3)
        raw = (d[0] << 8) | d[1]
        raw &= 0xFFFC
        return raw

    def read_temperature(self):
        if not self.ok:
            return None
        try:
            raw = self._read(self.CMD_TEMP, 60)
            t   = -46.85 + (175.72 * raw / 65536.0)
            return t if -40 < t < 125 else None
        except OSError as e:
            print("[HTU21] temp error:", e)
            return None

    def read_humidity(self):
        if not self.ok:
            return None
        try:
            raw = self._read(self.CMD_HUM, 20)
            h   = -6.0 + (125.0 * raw / 65536.0)
            return max(0.0, min(100.0, h))
        except OSError as e:
            print("[HTU21] hum error:", e)
            return None

# ============================================================
#  DRIVER BMP180
# ============================================================
class BMP180:
    REG_CALIB = 0xAA
    REG_CTRL  = 0xF4
    REG_DATA  = 0xF6
    CMD_TEMP  = 0x2E
    CMD_PRES  = 0x34
    OSS       = 0

    def __init__(self, i2c, addr=BMP180_ADDR):
        self.i2c  = i2c
        self.addr = addr
        self.cal  = None
        self.B5   = None
        self.ok   = False

    def begin(self):
        try:
            chip_id = self.i2c.readfrom_mem(self.addr, 0xD0, 1)[0]
            if chip_id != 0x55:
                print("[BMP180] unexpected chip_id:", hex(chip_id))
            buf = self.i2c.readfrom_mem(self.addr, self.REG_CALIB, 22)
            self._parse_cal(buf)
            self.ok = True
        except OSError as e:
            print("[BMP180]", hex(self.addr), "begin error:", e)
            self.ok = False
        return self.ok

    def _parse_cal(self, buf):
        def s16(h, l): v = (h << 8) | l; return v - 65536 if v & 0x8000 else v
        def u16(h, l): return (h << 8) | l
        self.cal = (
            s16(buf[0],buf[1]),   s16(buf[2],buf[3]),   s16(buf[4],buf[5]),
            u16(buf[6],buf[7]),   u16(buf[8],buf[9]),   u16(buf[10],buf[11]),
            s16(buf[12],buf[13]), s16(buf[14],buf[15]), s16(buf[16],buf[17]),
            s16(buf[18],buf[19]), s16(buf[20],buf[21]),
        )

    def _read_ut(self):
        self.i2c.writeto_mem(self.addr, self.REG_CTRL, bytes([self.CMD_TEMP]))
        time.sleep_ms(6)
        d = self.i2c.readfrom_mem(self.addr, self.REG_DATA, 2)
        return (d[0] << 8) | d[1]

    def _read_up(self):
        cmd = self.CMD_PRES | (self.OSS << 6)
        self.i2c.writeto_mem(self.addr, self.REG_CTRL, bytes([cmd]))
        time.sleep_ms(6)
        d = self.i2c.readfrom_mem(self.addr, self.REG_DATA, 3)
        return ((d[0] << 16) | (d[1] << 8) | d[2]) >> (8 - self.OSS)

    def read_both(self):
        if not self.ok or not self.cal:
            return None, None
        try:
            AC1,AC2,AC3,AC4,AC5,AC6,B1,B2,MB,MC,MD = self.cal
            UT = self._read_ut()
            X1 = ((UT - AC6) * AC5) >> 15
            X2 = (MC << 11) // (X1 + MD)
            self.B5 = X1 + X2
            T  = (self.B5 + 8) >> 4
            temp = T / 10.0
            UP = self._read_up()
            B6 = self.B5 - 4000
            X1 = (B2 * ((B6 * B6) >> 12)) >> 11
            X2 = (AC2 * B6) >> 11
            X3 = X1 + X2
            B3 = (((AC1 * 4 + X3) << self.OSS) + 2) >> 2
            X1 = (AC3 * B6) >> 13
            X2 = (B1 * ((B6 * B6) >> 12)) >> 16
            X3 = ((X1 + X2) + 2) >> 2
            B4 = (AC4 * (X3 + 32768)) >> 15
            if B4 == 0:
                return temp, None
            B7 = (UP - B3) * (50000 >> self.OSS)
            p  = (B7 * 2) // B4 if B7 < 0x80000000 else (B7 // B4) * 2
            X1 = (p >> 8) * (p >> 8)
            X1 = (X1 * 3038) >> 16
            X2 = (-7357 * p) >> 16
            p  = p + ((X1 + X2 + 3791) >> 4)
            press = p / 100.0
            if not (-40 < temp < 85): temp = None
            if press is not None and not (300 < press < 1200): press = None
            return temp, press
        except (OSError, ZeroDivisionError, TypeError) as e:
            print("[BMP180]", hex(self.addr), "read error:", e)
            return None, None

# ============================================================
#  WIFI
#  Fix principali rispetto alla versione precedente:
#  1. feed_wdt() dentro il loop di attesa connessione
#  2. IP statico reimpostato ad ogni tentativo (si perde dopo disconnect)
#  3. WIFI_TIMEOUT_S ridotto a 20s, WDT alzato a 90s
#     → 3 retry * 20s = 60s < WDT 90s (non scatta mai durante WiFi)
#  4. _wlan.active(False/True) per reset hardware stack WiFi
#     in caso di blocco prolungato
# ============================================================
_wlan = None

def connect_wifi():
    global _wlan
    if _wlan is None:
        _wlan = network.WLAN(network.STA_IF)

    # Reset stack completo una volta sola all'inizio —
    # evita stati residui da cicli precedenti o da deep sleep
    _wlan.active(False)
    time.sleep_ms(300)
    _wlan.active(True)
    _wlan.config(txpower=20)
    time.sleep_ms(300)

    for ssid, pw, mode in NETWORKS:
        use_static = (mode.upper() == "IP")

        for attempt in range(WIFI_RETRY_N):
            feed_wdt()
            print(f"[WiFi] {ssid} tentativo {attempt+1}/{WIFI_RETRY_N} ({'IP statico' if use_static else 'DHCP'})")
            try:
                _wlan.disconnect()
                time.sleep_ms(300)

                if use_static:
                    # IP ruotato ad ogni tentativo — aumenta probabilità
                    # di evitare conflitti ARP con lease residui sul router
                    ip = STATIC_IPS[attempt % len(STATIC_IPS)]
                    print(f"[WiFi] IP statico: {ip}")
                    _wlan.ifconfig((ip, STATIC_MASK, STATIC_GW, STATIC_DNS1))
                else:
                    # Forza DHCP esplicitamente — MicroPython persiste
                    # l'ultimo ifconfig in NVS flash e riusa l'IP statico
                    # precedente se non viene azzerato esplicitamente
                    _wlan.ifconfig('dhcp')

                _wlan.connect(ssid, pw)
                t0 = time.time()
                while not _wlan.isconnected():
                    if time.time() - t0 > WIFI_TIMEOUT_S:
                        print(f"[WiFi] timeout dopo {WIFI_TIMEOUT_S}s")
                        break
                    feed_wdt()  # <-- critico: evita WDT durante attesa
                    time.sleep_ms(300)

                if _wlan.isconnected():
                    ip, mask, gw, dns = _wlan.ifconfig()
                    print(f"[WiFi] OK {'IP statico' if use_static else 'DHCP'} — IP:{ip} GW:{gw}")
                    return True

            except Exception as e:
                print(f"[WiFi] errore tentativo {attempt+1}:", e)

            # Pausa breve tra retry con feed WDT
            feed_wdt()
            time.sleep_ms(500)

    # Tutti i tentativi falliti — reset hardware stack WiFi
    # per evitare stato corrotto al prossimo wake
    print("[WiFi] FAIL — reset stack WiFi")
    try:
        _wlan.active(False)
        time.sleep_ms(200)
        _wlan.active(True)
    except Exception:
        pass

    return False

def ensure_wifi():
    if _wlan and _wlan.isconnected():
        return True
    print("[WiFi] riconnessione...")
    return connect_wifi()

def disconnect_wifi():
    """Disconnessione pulita con notifica all'AP.
    Libera il MAC sul router prima del deep sleep evitando
    che rimanga appeso tra un ciclo e il successivo.
    """
    global _wlan
    if _wlan is None or not _wlan.isconnected():
        if _wlan:
            _wlan.active(False)
        return
    try:
        print("[WiFi] disconnessione pulita...")
        _wlan.disconnect()
        time.sleep_ms(200)
        _wlan.active(False)
        print("[WiFi] disconnesso")
    except Exception as e:
        print("[WiFi] errore disconnessione:", e)

# ============================================================
#  PAYLOAD HELPERS
# ============================================================
def lux_to_payload(lux):
    if lux is None or lux <= 0:
        return 0
    v = int(math.log10(lux + 1.0) * 200.0)
    return max(0, min(999, v))

def read_soil(adc):
    samples = []
    for _ in range(SOIL_SAMPLES):
        try:
            v = adc.read()
            if 0 <= v <= 4095:
                samples.append(v)
        except Exception:
            pass
        time.sleep_ms(SOIL_DELAY_MS)
    if not samples:
        return None
    avg = sum(samples) // len(samples)
    if avg > SOIL_FLOAT:
        return None
    if SOIL_DRY == SOIL_WET:
        return None
    pct = (SOIL_DRY - avg) * 100.0 / (SOIL_DRY - SOIL_WET)
    return int(max(0.0, min(100.0, pct)))

def read_dht(sensor):
    for attempt in range(DHT_RETRIES):
        try:
            sensor.measure()
            t = sensor.temperature()
            u = sensor.humidity()
            if -40 < t < 80 and 0 <= u <= 100:
                return t, u
            print(f"[DHT22] fuori range T={t} U={u}")
        except Exception as e:
            print(f"[DHT22] tentativo {attempt+1} errore: {e}")
        if attempt < DHT_RETRIES - 1:
            time.sleep_ms(DHT_RETRY_MS)
    return None, None

def build_payload(t1, t2, u1, u2, soil, lu, pr1, pr2):
    def ci(v): return int(v * 10) if v is not None else 0
    def cp(v): return int(v)      if v is not None else 0
    def cl(v, lo, hi): return max(lo, min(hi, v))
    return "{:03d}{:03d}{:03d}{:03d}{:03d}{:03d}{:04d}{:04d}".format(
        cl(ci(t1),  0, 999), cl(ci(t2),  0, 999),
        cl(ci(u1),  0, 999), cl(ci(u2),  0, 999),
        cl(ci(soil),0, 999), cl(lu,       0, 999),
        cl(cp(pr1), 0,9999), cl(cp(pr2),  0,9999),
    )

def send_payload(payload):
    url = SERVER_URL + payload
    try:
        r  = requests.get(url, timeout=HTTP_TIMEOUT)
        ok = (r.status_code == 200)
        print(f"[HTTP] {r.status_code} — {'OK' if ok else 'FAIL'} — {r.text[:80]}")
        r.close()
        return ok
    except Exception as e:
        print("[HTTP] errore:", e)
        return False

# ============================================================
#  INIT HARDWARE
# ============================================================
print(f"\n=== CORTIGOCAMPATI BOOT ({'COLD' if COLD_BOOT else 'WAKE'}) ===")
print(f"[CPU] {machine.freq()//1000000} MHz")

# WDT — inizializzato PRIMA di qualsiasi operazione lunga
wdt = None
if WDT_ENABLE:
    try:
        wdt = WDT(timeout=WDT_TIMEOUT)
        print(f"[WDT] abilitato ({WDT_TIMEOUT//1000}s)")
    except Exception as e:
        print("[WDT] non disponibile:", e)

def feed_wdt():
    if wdt:
        wdt.feed()

# I2C buses
i2c0 = I2C(0, scl=Pin(I2C0_SCL), sda=Pin(I2C0_SDA), freq=100000)
i2c1 = I2C(1, scl=Pin(I2C1_SCL), sda=Pin(I2C1_SDA), freq=100000)

if COLD_BOOT:
    for idx, bus in [(0, i2c0), (1, i2c1)]:
        devs = bus.scan()
        print(f"[I2C{idx}] scan: {[hex(d) for d in devs]}")

bh   = BH1750(i2c0, BH1750_ADDR)
htu  = HTU21 (i2c1, HTU21_ADDR)
bmp2 = BMP180(i2c0, BMP180_ADDR)
bmp1 = BMP180(i2c1, BMP180_ADDR)

print("[BH1750]", "OK" if bh.begin()   else "FAIL")
print("[HTU21 ]", "OK" if htu.begin()  else "FAIL")
print("[BMP2  ]", "OK" if bmp2.begin() else "FAIL", "(I2C0 21/22)")
print("[BMP1  ]", "OK" if bmp1.begin() else "FAIL", "(I2C1 18/19)")

dht22 = dht.DHT22(Pin(DHT_PIN))
if COLD_BOOT:
    print("[DHT22] cold boot — warm-up 2s...")
    time.sleep_ms(2000)

adc = ADC(Pin(SOIL_PIN))
adc.atten(ADC.ATTN_11DB)
adc.width(ADC.WIDTH_12BIT)

feed_wdt()
connect_wifi()
feed_wdt()

# ============================================================
#  MISURA + INVIO
# ============================================================
try:
    feed_wdt()

    t1, u1 = read_dht(dht22)
    feed_wdt()

    t2 = htu.read_temperature()
    u2 = htu.read_humidity()

    lux    = bh.read_lux()
    lu_pay = lux_to_payload(lux)
    feed_wdt()

    _, pr1 = bmp1.read_both()
    _, pr2 = bmp2.read_both()
    feed_wdt()

    soil = read_soil(adc)

    print(f"[T1={t1}C U1={u1}%] [T2={t2}C U2={u2}%] "
          f"[Soil={soil}%] [Lux={lux}->{lu_pay}] "
          f"[PR1={pr1}hPa] [PR2={pr2}hPa]")

    payload = build_payload(t1, t2, u1, u2, soil, lu_pay, pr1, pr2)
    print("[Payload]", payload, f"({len(payload)} chr)")
    feed_wdt()

    if ensure_wifi():
        # Retry invio: reti con NAT o DNS lenti possono fallire al primo tentativo
        sent = False
        for send_attempt in range(2):
            if send_payload(payload):
                sent = True
                break
            print(f"[HTTP] retry {send_attempt+1}...")
            feed_wdt()
            time.sleep_ms(2000)
        if not sent:
            print("[HTTP] invio fallito dopo retry")
    else:
        print("[Main] WiFi non disponibile, payload saltato")

    feed_wdt()
    disconnect_wifi()  # libera MAC sul router prima del deep sleep
    feed_wdt()

except MemoryError as e:
    print("[Main] MemoryError:", e, "— reset via WDT")
    time.sleep(WDT_TIMEOUT // 1000 + 1)

except Exception as e:
    print("[Main] errore:", e)

# ============================================================
#  DEEP SLEEP
# ============================================================
print(f"[Sleep] deep sleep {SLEEP_S}s...")
machine.deepsleep(SLEEP_S * 1000)
