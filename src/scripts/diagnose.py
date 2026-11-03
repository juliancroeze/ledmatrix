#!/usr/bin/env python3
"""Runs every matrix mode for a moment without touching the LED panels and
reports which ones crash. Safe to run while the dashboard is running.

    cd ~/rpi-led-matrix/src/scripts && python3 diagnose.py
"""
import os
import sys
import time
import traceback
import platform

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import PIL
from PIL import Image

print(f"Python {platform.python_version()}, Pillow {PIL.__version__}")
for pkg in ('flask', 'flask_socketio', 'psutil', 'requests'):
    try:
        mod = __import__(pkg)
        print(f"  {pkg}: {getattr(mod, '__version__', 'ok')}")
    except Exception as e:
        print(f"  {pkg}: MISSING ({e})")


class FakeMatrix(object):
    width, height, brightness = 192, 64, 100

    def __init__(self):
        self.frames = 0

    def SetImage(self, image, x=0, y=0, unsafe=True):
        self.frames += 1

    def Clear(self):
        pass


tests = [
    ('mods.text', 'TextScroller', dict(text='Hello', color='#ffffff', speed=40, size='medium')),
    ('mods.pong', 'Pong', {}),
    ('mods.flappybird', 'FlappyBird', {}),
    ('mods.snake', 'Snake', {}),
    ('mods.tetris', 'Tetris', {}),
    ('mods.clock', 'Clock', {}),
    ('mods.rain', 'MatrixRain', {}),
    ('mods.starfield', 'Starfield', {}),
    ('mods.life', 'GameOfLife', {}),
    ('mods.test', 'PulsingColors', {}),
    ('mods.dvd', 'Dvd', {}),
    ('mods.imageviewer', 'Gif', {}),
    ('mods.stream', 'Webcam', {}),
]

failed = 0
for module, cls_name, opts in tests:
    try:
        cls = getattr(__import__(module, fromlist=[cls_name]), cls_name)
        m = FakeMatrix()
        mode = cls(m, **opts)
        if hasattr(mode, 'render'):          # FrameMode: call directly so errors surface
            mode.running = True
            mode.setup()
            for _ in range(20):
                mode.render(1 / 30.0)
            if hasattr(mode, 'handle_input'):
                for a in ('A', 'UP', 'DOWN', 'LEFT', 'RIGHT', 'B'):
                    mode.handle_input(a, True)
                mode.render(1 / 30.0)
            mode.running = False
        else:
            mode.process()
            time.sleep(0.5)
            mode.kill()
            if m.frames == 0:
                raise RuntimeError('no frames drawn')
        print(f"OK    {cls_name}")
    except Exception:
        failed += 1
        print(f"FAIL  {cls_name}")
        traceback.print_exc()

print('\nAll modes OK' if not failed else f'\n{failed} mode(s) failed - paste this output to get them fixed')
