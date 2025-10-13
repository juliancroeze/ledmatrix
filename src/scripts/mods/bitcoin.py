import time
import random
import threading
from rgbmatrix import graphics
from mods.samplebase import SampleBase


class BTCDisplay(SampleBase):
    def __init__(self, matrix):
        threading.Thread.__init__(self)
        self.matrix = matrix
        self.lock = threading.Lock()
        self.fake_prices = [random.uniform(30000, 70000) for _ in range(32)]
        self.running = True
        self.last_price = self.fake_prices[-1]

    def run(self):
        super(BTCDisplay, self).run()

        font = graphics.Font()
        font.LoadFont("../../fonts/7x13.bdf")

        canvas = self.matrix.CreateFrameCanvas()
        text_color = graphics.Color(255, 140, 0)
        green = graphics.Color(0, 255, 0)
        red = graphics.Color(255, 0, 0)
        white = graphics.Color(255, 255, 255)

        while self.running:
            canvas.Clear()

            # --- Simulate some fake BTC data ---
            price = self.fake_prices[-1] + random.uniform(-200, 200)
            self.fake_prices.append(price)
            self.fake_prices = self.fake_prices[-32:]
            price_change = ((price - self.last_price) / self.last_price) * 100
            self.last_price = price

            # --- Title ---
            graphics.DrawText(canvas, font, 5, 12, white, "BTC / USD")

            # --- Price ---
            price_text = f"${price:,.0f}"
            graphics.DrawText(canvas, font, 5, 28, text_color, price_text)

            # --- Change ---
            change_color = green if price_change >= 0 else red
            change_symbol = "▲" if price_change >= 0 else "▼"
            change_text = f"{change_symbol} {price_change:+.2f}%"
            graphics.DrawText(canvas, font, 130, 28, change_color, change_text)

            # --- Improved graph ---
            graph_x = 5
            graph_y = 60         # Bottom of the display
            graph_width = 182
            graph_height = 20    # Make graph taller now

            min_p = min(self.fake_prices)
            max_p = max(self.fake_prices)
            if max_p == min_p:
                max_p += 1

            for i in range(1, len(self.fake_prices)):
                prev = self.fake_prices[i - 1]
                curr = self.fake_prices[i]

                x1 = graph_x + (i - 1) * (graph_width / len(self.fake_prices))
                x2 = graph_x + i * (graph_width / len(self.fake_prices))

                # Smooth graph by scaling to taller height
                y1 = graph_y - int(((prev - min_p) / (max_p - min_p)) * graph_height)
                y2 = graph_y - int(((curr - min_p) / (max_p - min_p)) * graph_height)

                line_color = green if curr >= prev else red
                graphics.DrawLine(canvas, int(x1), y1, int(x2), y2, line_color)

            canvas = self.matrix.SwapOnVSync(canvas)
            time.sleep(0.2)

    def stop(self):
        self.running = False
