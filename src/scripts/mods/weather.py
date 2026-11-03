import math
import random
import threading
import time
import requests
from mods.samplebase import FrameMode
from mods.fonts import get_font, text_size

# WMO weather codes -> (label, icon)
CODES = {
    0: ('Clear', 'sun'), 1: ('Mostly clear', 'sun'), 2: ('Partly cloudy', 'partly'), 3: ('Overcast', 'cloud'),
    45: ('Fog', 'fog'), 48: ('Fog', 'fog'),
    51: ('Drizzle', 'rain'), 53: ('Drizzle', 'rain'), 55: ('Drizzle', 'rain'),
    56: ('Freezing drizzle', 'rain'), 57: ('Freezing drizzle', 'rain'),
    61: ('Light rain', 'rain'), 63: ('Rain', 'rain'), 65: ('Heavy rain', 'rain'),
    66: ('Freezing rain', 'rain'), 67: ('Freezing rain', 'rain'),
    71: ('Light snow', 'snow'), 73: ('Snow', 'snow'), 75: ('Heavy snow', 'snow'), 77: ('Snow grains', 'snow'),
    80: ('Showers', 'rain'), 81: ('Showers', 'rain'), 82: ('Heavy showers', 'rain'),
    85: ('Snow showers', 'snow'), 86: ('Snow showers', 'snow'),
    95: ('Thunderstorm', 'storm'), 96: ('Thunderstorm', 'storm'), 99: ('Thunderstorm', 'storm'),
}


class WeatherApp(FrameMode):
    """Current weather from Open-Meteo (free, no API key)."""

    FPS = 20
    REFRESH = 600

    def setup(self):
        self.city = (self.options.get('city') or 'Amsterdam').strip()
        self.data = None
        self.error = None
        self.t = 0.0
        self.particles = [[random.uniform(4, 56), random.uniform(0, 64)] for _ in range(14)]
        threading.Thread(target=self.fetch_loop, daemon=True).start()

    def fetch_loop(self):
        coords = None
        while self.running:
            try:
                if coords is None:
                    r = requests.get('https://geocoding-api.open-meteo.com/v1/search',
                                     params={'name': self.city, 'count': 1}, timeout=10)
                    results = r.json().get('results') or []
                    if not results:
                        self.error = 'City not found'
                        self.wait(self.REFRESH)
                        continue
                    coords = (results[0]['latitude'], results[0]['longitude'])
                    self.city = results[0].get('name', self.city)
                r = requests.get('https://api.open-meteo.com/v1/forecast', params={
                    'latitude': coords[0], 'longitude': coords[1],
                    'current': 'temperature_2m,weather_code,wind_speed_10m,relative_humidity_2m,is_day',
                    'daily': 'temperature_2m_max,temperature_2m_min',
                    'timezone': 'auto', 'forecast_days': 1,
                }, timeout=10)
                j = r.json()
                cur, daily = j['current'], j['daily']
                self.data = {
                    'temp': cur['temperature_2m'], 'code': cur['weather_code'],
                    'wind': cur['wind_speed_10m'], 'humidity': cur['relative_humidity_2m'],
                    'day': cur.get('is_day', 1), 'hi': daily['temperature_2m_max'][0], 'lo': daily['temperature_2m_min'][0],
                }
                self.error = None
                self.wait(self.REFRESH)
            except Exception as e:
                print(f"Weather fetch failed: {e}")
                self.error = 'No connection'
                self.wait(30)

    # -- icons -------------------------------------------------------------
    def sun(self, cx, cy, r, day=True):
        d = self.draw
        if not day:
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(220, 220, 200))
            d.ellipse((cx - r + 5, cy - r - 2, cx + r + 5, cy + r - 2), fill=(0, 0, 0))
            return
        for i in range(8):
            a = i * math.pi / 4 + self.t * 0.4
            d.line((cx + math.cos(a) * (r + 3), cy + math.sin(a) * (r + 3),
                    cx + math.cos(a) * (r + 7), cy + math.sin(a) * (r + 7)), fill=(255, 170, 0))
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 210, 0))

    def cloud(self, x, y, color=(200, 205, 220)):
        d = self.draw
        d.ellipse((x, y + 8, x + 18, y + 24), fill=color)
        d.ellipse((x + 8, y, x + 30, y + 22), fill=color)
        d.ellipse((x + 22, y + 7, x + 40, y + 24), fill=color)
        d.rectangle((x + 9, y + 15, x + 32, y + 24), fill=color)

    def icon(self, kind, day):
        d = self.draw
        if kind == 'sun':
            self.sun(30, 30, 10, day)
        elif kind == 'partly':
            self.sun(22, 22, 8, day)
            self.cloud(12, 24)
        elif kind == 'cloud':
            self.cloud(10, 16)
        elif kind == 'fog':
            for i, y in enumerate((20, 28, 36, 44)):
                off = int(3 * math.sin(self.t + i))
                d.line((10 + off, y, 50 + off, y), fill=(150, 150, 170), width=2)
        elif kind in ('rain', 'snow', 'storm'):
            for p in self.particles:
                p[1] += (12 if kind == 'snow' else 40) * 0.05
                if kind == 'snow':
                    p[0] += math.sin(self.t * 2 + p[1]) * 0.3
                if p[1] > 63:
                    p[1] = 34
                if p[1] >= 34:
                    if kind == 'snow':
                        d.point((p[0], p[1]), fill=(255, 255, 255))
                    else:
                        d.line((p[0], p[1], p[0] - 1, p[1] + 3), fill=(80, 150, 255))
            self.cloud(10, 10, (150, 155, 175) if kind != 'snow' else (210, 215, 230))
            if kind == 'storm' and int(self.t * 3) % 4 == 0:
                d.line((30, 34, 26, 44, 32, 44, 27, 56), fill=(255, 240, 80), width=2)

    def render(self, dt):
        self.t += dt
        d = self.draw
        d.rectangle((0, 0, 191, 63), fill=(0, 0, 0))
        small = get_font('5x7')
        mid = get_font('6x10')
        big = get_font('texgyre-27')
        if not self.data:
            msg = self.error or f'Loading {self.city}...'
            w, _ = text_size(d, msg, mid)
            d.text(((192 - w) // 2, 27), msg, font=mid, fill=(140, 140, 170))
            return
        label, kind = CODES.get(self.data['code'], ('', 'cloud'))
        self.icon(kind, self.data['day'])
        temp = f"{round(self.data['temp'])}"
        d.text((68, 6), temp, font=big, fill=(255, 255, 255))
        tw, _ = text_size(d, temp, big)
        # degree symbol drawn by hand (not all fonts have one)
        d.ellipse((68 + tw + 2, 9, 68 + tw + 6, 13), outline=(255, 255, 255))
        d.text((68 + tw + 10, 8), self.city[:14], font=mid, fill=(120, 170, 255))
        d.text((68 + tw + 10, 20), label, font=small, fill=(200, 200, 210))
        line = f"H {round(self.data['hi'])}  L {round(self.data['lo'])}"
        d.text((68, 44), line, font=mid, fill=(220, 220, 230))
        extra = f"{round(self.data['humidity'])}% hum  {round(self.data['wind'])} km/h"
        d.text((68, 56), extra, font=small, fill=(120, 120, 150))
