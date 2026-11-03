import random
import threading
import time
import requests
from mods.samplebase import FrameMode
from mods.fonts import get_font, text_size

GREEN, RED, ORANGE = (0, 230, 110), (255, 60, 70), (255, 150, 0)


class BTCDisplay(FrameMode):
    """Bitcoin price + 24h chart from CoinGecko. Falls back to simulated
    prices (marked SIM) when there's no internet."""

    FPS = 10

    def setup(self):
        self.prices = []
        self.price = None
        self.change = 0.0
        self.live = False
        threading.Thread(target=self.fetch_loop, daemon=True).start()

    def fetch_loop(self):
        while self.running:
            try:
                r = requests.get('https://api.coingecko.com/api/v3/coins/bitcoin/market_chart',
                                 params={'vs_currency': 'usd', 'days': 1}, timeout=10)
                points = [p[1] for p in r.json()['prices']]
                step = max(1, len(points) // 90)
                self.prices = points[::step]
                self.price = points[-1]
                self.change = (points[-1] - points[0]) / points[0] * 100
                self.live = True
                self.wait(120)
            except Exception as e:
                print(f"BTC fetch failed, simulating: {e}")
                self.live = False
                if not self.prices:
                    self.prices = [random.uniform(60000, 64000)]
                for _ in range(10):
                    if not self.running:
                        return
                    p = self.prices[-1] + random.uniform(-150, 150)
                    self.prices = (self.prices + [p])[-90:]
                    self.price = p
                    self.change = (p - self.prices[0]) / self.prices[0] * 100
                    self.wait(3)

    def render(self, dt):
        d = self.draw
        d.rectangle((0, 0, 191, 63), fill=(0, 0, 0))
        small = get_font('5x7')
        mid = get_font('7x13')
        big = get_font('10x20')
        d.text((5, 3), 'BTC / USD', font=mid, fill=ORANGE)
        if not self.live and self.prices:
            d.text((80, 5), 'SIM', font=small, fill=(110, 110, 130))
        if self.price is None:
            d.text((5, 22), 'Loading...', font=mid, fill=(150, 150, 170))
            return
        d.text((5, 18), f"${self.price:,.0f}", font=big, fill=(255, 255, 255))
        up = self.change >= 0
        ch = f"{'+' if up else ''}{self.change:.2f}%  24h"
        w, _ = text_size(d, ch, mid)
        d.text((187 - w, 22), ch, font=mid, fill=GREEN if up else RED)
        pts = self.prices
        if len(pts) > 1:
            lo, hi = min(pts), max(pts)
            hi = hi if hi > lo else lo + 1
            x0, y0, gw, gh = 4, 61, 184, 18
            coords = [(x0 + i * gw / (len(pts) - 1), y0 - (p - lo) / (hi - lo) * gh) for i, p in enumerate(pts)]
            color = GREEN if up else RED
            fill = tuple(c // 6 for c in color)
            for (x1, y1), (x2, y2) in zip(coords, coords[1:]):
                d.polygon([(x1, y1), (x2, y2), (x2, y0), (x1, y0)], fill=fill)
            d.line(coords, fill=color)

    def stop(self):
        self.running = False
