import argparse
import io
import json
import os
import shlex
import socket
import subprocess
import threading
import time
import traceback

import psutil
from PIL import Image
from flask import (Flask, render_template, request, make_response, jsonify,
                   redirect, send_from_directory)
from flask_socketio import SocketIO, emit
from rgbmatrix import RGBMatrix, RGBMatrixOptions

from mods.clock import Clock
from mods.dvd import Dvd
from mods.drawing import Drawing
from mods.snake import Snake
from mods.stream import Webcam, ScreenShare, VideoStream
from mods.weather import WeatherApp
from mods.bitcoin import BTCDisplay
from mods.flappybird import FlappyBird
from mods.text import TextScroller
from mods.imageviewer import ImageViewer
from mods.tetris import Tetris
from mods.pong import Pong
from mods.life import GameOfLife
from mods.rain import MatrixRain
from mods.starfield import Starfield

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.expanduser('~/ledmatrix')
UPLOAD_DIR = os.path.join(DATA_DIR, 'uploads')
CONFIG_PATH = os.path.join(DATA_DIR, 'config.json')
APP_VERSION = '2.0.3'

# ---------------------------------------------------------------------------
# Mode registry. `group` decides where the tile shows up on the dashboard,
# `panel` which control panel opens, `resume` whether the mode is restored
# after a restart (only modes that don't need a browser feeding them).
# ---------------------------------------------------------------------------
MODES = [
    # live: you send something from your device
    dict(id='webcam', label='Camera', icon='camera', group='live', cls=Webcam, panel='webcam'),
    dict(id='screen', label='Screen', icon='monitor', group='live', cls=ScreenShare, panel='screen'),
    dict(id='draw', label='Draw', icon='paintbrush', group='live', cls=Drawing, panel='draw', resume=True),
    dict(id='text', label='Text', icon='type', group='live', cls=TextScroller, panel='text', resume=True),
    dict(id='image', label='Image', icon='image', group='live', cls=ImageViewer, panel='image', resume=True),
    # games
    dict(id='snake', label='Snake', icon='worm', group='games', cls=Snake, panel='gamepad',
         controls=dict(dpad=True, a='Restart', hint='Arrow keys to steer')),
    dict(id='tetris', label='Tetris', icon='blocks', group='games', cls=Tetris, panel='gamepad',
         controls=dict(dpad=True, a='Rotate', b='Drop', repeat=['LEFT', 'RIGHT', 'DOWN'],
                       hint='Arrows move, up rotates, space drops')),
    dict(id='pong', label='Pong', icon='circle-dot', group='games', cls=Pong, panel='gamepad',
         controls=dict(dpad=False, a='Restart', slider=True, players=True, hint='Drag the bar, or use the up/down keys')),
    dict(id='flappybird', label='Flappy', icon='bird', group='games', cls=FlappyBird, panel='gamepad',
         controls=dict(dpad=False, a='Flap', big=True, hint='Space or tap to flap')),
    # ambient
    dict(id='clock', label='Clock', icon='clock', group='ambient', cls=Clock, resume=True),
    dict(id='weather', label='Weather', icon='cloud-sun', group='ambient', cls=WeatherApp, panel='weather', resume=True),
    dict(id='bitcoin', label='Bitcoin', icon='bitcoin', group='ambient', cls=BTCDisplay, resume=True),
    dict(id='rain', label='Rain', icon='binary', group='ambient', cls=MatrixRain, resume=True),
    dict(id='stars', label='Stars', icon='sparkles', group='ambient', cls=Starfield, resume=True),
    dict(id='life', label='Life', icon='sprout', group='ambient', cls=GameOfLife, resume=True),
    dict(id='dvd', label='DVD', icon='disc-3', group='ambient', cls=Dvd, resume=True),
]
MODES_BY_ID = {m['id']: m for m in MODES}
MODES_BY_CLASS = {m['cls']: m['id'] for m in MODES}


def load_config():
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(cfg):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(CONFIG_PATH, 'w') as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"Could not save config: {e}")


class MatrixProxy(object):
    """Wraps RGBMatrix so the game controller can show a live preview: while
    `capture` is on (only during games), every SetImage() call is mirrored
    into `self.frame`. Everything else is passed straight through."""

    def __init__(self, matrix, width=192, height=64):
        object.__setattr__(self, '_m', matrix)
        object.__setattr__(self, 'frame', Image.new('RGB', (width, height)))
        object.__setattr__(self, 'frame_id', 0)
        object.__setattr__(self, 'capture', False)
        object.__setattr__(self, '_lock', threading.Lock())

    def SetImage(self, image, offset_x=0, offset_y=0, unsafe=True):
        self._m.SetImage(image, offset_x, offset_y, unsafe)
        if self.capture:
            with self._lock:
                if offset_x == 0 and offset_y == 0 and image.size == self.frame.size and image.mode == 'RGB':
                    object.__setattr__(self, 'frame', image.copy())
                else:
                    frame = self.frame.copy()
                    frame.paste(image.convert('RGB'), (offset_x, offset_y))
                    object.__setattr__(self, 'frame', frame)
                object.__setattr__(self, 'frame_id', self.frame_id + 1)

    def Clear(self):
        self._m.Clear()
        with self._lock:
            object.__setattr__(self, 'frame', Image.new('RGB', self.frame.size))
            object.__setattr__(self, 'frame_id', self.frame_id + 1)

    def __getattr__(self, name):
        return getattr(self._m, name)

    def __setattr__(self, name, value):
        if name in ('capture',):
            object.__setattr__(self, name, value)
        else:
            setattr(self._m, name, value)


class Matrix(object):
    def __init__(self):
        options = RGBMatrixOptions()
        options.rows = 32
        options.cols = 64
        options.chain_length = 6
        options.parallel = 2
        options.pixel_mapper_config = "U-mapper"
        options.show_refresh_rate = 0
        options.gpio_slowdown = 4
        options.led_rgb_sequence = "RBG"
        options.pwm_lsb_nanoseconds = 500
        options.pwm_bits = 8
        # The library normally switches from root to the 'daemon' user after
        # start-up. The dashboard needs to keep writing its settings, uploads
        # and font cache (and read the HTTPS certificate), so stay as root.
        options.drop_privileges = False
        self.config = load_config()
        self.toggled = False
        self.mode = None
        self.mode_id = None
        self.mode_options = {}
        self.lock = threading.RLock()
        self.matrix = MatrixProxy(RGBMatrix(options=options))
        self.set_brightness(self.config.get('brightness', 100), save=False)

    # -- modes ---------------------------------------------------------------
    def start_mode(self, mode_id, **options):
        info = MODES_BY_ID.get(mode_id)
        if info is None:
            raise ValueError(f"Unknown mode '{mode_id}'")
        with self.lock:
            self._stop_current()
            self.mode = info['cls'](self.matrix, **options)
            self.mode_id = mode_id
            self.mode_options = options
            self.toggled = True
            self.matrix.capture = info['group'] == 'games'
            self.mode.process()
            self.config.update(last_mode=mode_id, last_options=options if info.get('resume') else {}, was_on=True)
            save_config(self.config)
        broadcast_state()
        return self.mode

    def stop(self):
        with self.lock:
            self._stop_current()
            self.matrix.capture = False
            self.toggled = False
            self.mode_id = None
            self.matrix.Clear()
            self.config['was_on'] = False
            save_config(self.config)
        broadcast_state()

    def _stop_current(self):
        if self.mode is not None:
            try:
                self.mode.kill()
            except Exception:
                traceback.print_exc()
            self.mode = None

    def ensure_mode(self, cls, mode_id, **options):
        """Return the running mode if it is of `cls`, otherwise start it."""
        if isinstance(self.mode, cls) and self.toggled:
            return self.mode
        return self.start_mode(mode_id, **options)

    def resume(self):
        mode_id = self.config.get('last_mode')
        info = MODES_BY_ID.get(mode_id)
        if self.config.get('was_on') and info and info.get('resume'):
            print(f"Resuming last mode: {mode_id}")
            try:
                self.start_mode(mode_id, **(self.config.get('last_options') or {}))
            except Exception:
                traceback.print_exc()

    # Backwards compatibility with the old toggle/run API
    def run(self):
        if not self.toggled:
            self.stop()

    # -- brightness ------------------------------------------------------------
    def set_brightness(self, value, save=True):
        value = int(max(5, min(100, int(value))))
        try:
            self.matrix.brightness = value
        except Exception as e:
            print(f"Could not set brightness: {e}")
        self.brightness = value
        if save:
            self.config['brightness'] = value
            save_config(self.config)

    def state(self):
        game = None
        if self.mode is not None and hasattr(self.mode, 'get_state'):
            try:
                game = self.mode.get_state()
            except Exception:
                game = None
        return {
            'on': self.toggled and self.mode is not None,
            'mode': self.mode_id if self.toggled else None,
            'brightness': self.brightness,
            'game': game,
            'options': self.mode_options if self.toggled else {},
            'weather_city': self.config.get('weather_city', 'Amsterdam'),
        }


app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024
socketio = SocketIO(app, cors_allowed_origins="*", max_http_buffer_size=5 * 1024 * 1024)
matrix = None
viewers = set()


def broadcast_state():
    if matrix is not None:
        socketio.emit('state', matrix.state())


def ok(**data):
    data.setdefault('ok', True)
    return jsonify(data)


def fail(message, code=400):
    return make_response(jsonify({'ok': False, 'message': message}), code)


# ---------------------------------------------------------------------------
# Pages & PWA
# ---------------------------------------------------------------------------
@app.route('/', methods=['GET', 'POST'])
def index():
    modes = [{k: v for k, v in m.items() if k != 'cls'} for m in MODES]
    return render_template('index.html', modes=modes, state=matrix.state(),
                           system=system_info_data(), version=APP_VERSION)


@app.route('/manifest.webmanifest')
def manifest():
    resp = send_from_directory(os.path.join(HERE, 'static'), 'manifest.webmanifest',
                               mimetype='application/manifest+json')
    return resp


@app.route('/sw.js')
def service_worker():
    resp = send_from_directory(os.path.join(HERE, 'static', 'js'), 'sw.js', mimetype='application/javascript')
    resp.headers['Cache-Control'] = 'no-cache'
    resp.headers['Service-Worker-Allowed'] = '/'
    return resp


# ---------------------------------------------------------------------------
# JSON API used by the dashboard
# ---------------------------------------------------------------------------
@app.route('/api/state')
def api_state():
    return ok(state=matrix.state())


@app.route('/api/mode', methods=['POST'])
def api_mode():
    body = request.get_json(silent=True) or {}
    mode_id = body.get('mode')
    options = body.get('options') or {}
    if mode_id == 'weather':
        city = (options.get('city') or matrix.config.get('weather_city') or 'Amsterdam').strip()[:60]
        matrix.config['weather_city'] = city
        options = {'city': city}
    if mode_id == 'image' and not options.get('path'):
        current = current_upload()
        if not current:
            return fail('Upload an image first')
        options = {'path': current, 'fit': matrix.config.get('image_fit', 'cover')}
    try:
        matrix.start_mode(mode_id, **options)
    except ValueError as e:
        return fail(str(e))
    except Exception as e:
        traceback.print_exc()
        return fail(f'Could not start {mode_id}: {e}', 500)
    return ok(state=matrix.state())


@app.route('/api/stop', methods=['POST'])
def api_stop():
    matrix.stop()
    return ok(state=matrix.state())


@app.route('/api/brightness', methods=['POST'])
def api_brightness():
    body = request.get_json(silent=True) or {}
    matrix.set_brightness(body.get('value', 100))
    broadcast_state()
    return ok(brightness=matrix.brightness)


@app.route('/api/text', methods=['POST'])
def api_text():
    body = request.get_json(silent=True) or {}
    text = (body.get('text') or '').strip()
    if not text:
        return fail('Type a message first')
    options = {k: body.get(k) for k in ('text', 'color', 'speed', 'size', 'rainbow')}
    matrix.start_mode('text', **options)
    return ok(state=matrix.state())


def current_upload():
    try:
        files = [os.path.join(UPLOAD_DIR, f) for f in os.listdir(UPLOAD_DIR) if f.startswith('current.')]
        return files[0] if files else None
    except FileNotFoundError:
        return None


@app.route('/api/image', methods=['POST'])
def api_image():
    f = request.files.get('file')
    fit = request.form.get('fit', 'cover')
    if fit not in ('cover', 'contain', 'stretch'):
        fit = 'cover'
    if f is None or not f.filename:
        path = current_upload()
        if not path:
            return fail('Choose an image first')
    else:
        try:
            data = f.read()
            img = Image.open(io.BytesIO(data))
            fmt = (img.format or 'png').lower()
        except Exception:
            return fail("That file isn't an image Pillow can read")
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        old = current_upload()
        if old:
            os.remove(old)
        path = os.path.join(UPLOAD_DIR, 'current.' + fmt)
        with open(path, 'wb') as out:
            out.write(data)
    matrix.config['image_fit'] = fit
    matrix.start_mode('image', path=path, fit=fit)
    return ok(state=matrix.state())


@app.route('/api/system')
def api_system():
    return ok(system=system_info_data())


# ---------------------------------------------------------------------------
# Old routes (kept so existing bookmarks/scripts keep working)
# ---------------------------------------------------------------------------
@app.route('/on', methods=['GET', 'POST'])
def on():
    selected = request.form.get('comp_select') or request.args.get('mode')
    if selected in MODES_BY_ID:
        matrix.start_mode(selected)
    return redirect('/')


@app.route('/off', methods=['GET', 'POST'])
def off():
    matrix.stop()
    return make_response(jsonify({'message': 'Done', 'code': 'SUCCESS'}), 201)


@app.route('/start-snake', methods=['POST'])
def start_snake():
    matrix.start_mode('snake')
    return make_response(jsonify({"message": "Snake game started"}), 200)


@app.route('/snake-control', methods=['POST'])
def snake_control():
    direction = request.form.get('direction')
    if direction not in ['UP', 'DOWN', 'LEFT', 'RIGHT']:
        return make_response(jsonify({"message": "Invalid direction"}), 400)
    if not isinstance(matrix.mode, Snake):
        return make_response(jsonify({"message": "Snake game is not running"}), 400)
    success = matrix.mode.change_direction(direction)
    return make_response(jsonify({"message": f"Direction changed to {direction}", "success": success}), 200)


@app.route('/snake-reset', methods=['POST'])
def snake_reset():
    if not isinstance(matrix.mode, Snake):
        return make_response(jsonify({"message": "Snake game is not running"}), 400)
    matrix.mode.reset_game()
    return make_response(jsonify({"message": "Game reset successfully"}), 200)


@app.route('/snake-status', methods=['GET'])
def snake_status():
    if not isinstance(matrix.mode, Snake):
        return make_response(jsonify({"message": "Snake game is not running"}), 400)
    return make_response(jsonify(matrix.mode.get_game_state()), 200)


@app.route('/send-drawing', methods=['POST'])
def send_drawing():
    image_data = request.form.get('image_data')
    if not image_data and request.is_json:
        image_data = (request.get_json(silent=True) or {}).get('image_data')
    if not image_data:
        return make_response(jsonify({'message': 'No image data'}), 400)
    mode = matrix.ensure_mode(Drawing, 'draw')
    if mode.update_from_data_url(image_data):
        return make_response(jsonify({'message': 'Drawing updated successfully'}), 200)
    return make_response(jsonify({'message': 'Failed to update drawing'}), 400)


@app.route('/system-info', methods=['GET'])
def system_info():
    s = system_info_data()
    return jsonify({'storage': s['storage'], 'uptime': s['uptime']})


# ---------------------------------------------------------------------------
# Socket.IO: streaming, game input, live preview
# ---------------------------------------------------------------------------
@socketio.on('connect')
def on_connect():
    viewers.add(request.sid)
    emit('state', matrix.state())


@socketio.on('disconnect')
def on_disconnect(*args):
    viewers.discard(request.sid)


@socketio.on('stream-frame')
def stream_frame(data):
    """Binary JPEG frame from webcam / screen share. Returns an ack so the
    browser only sends the next frame when the previous one arrived."""
    if isinstance(matrix.mode, VideoStream):
        if isinstance(data, dict):
            data = data.get('frame')
        return matrix.mode.update_frame(data)
    return False


@socketio.on('webcam-frame')
def webcam_frame(data):
    if isinstance(matrix.mode, VideoStream):
        image_data = data.get('frame')
        if image_data:
            matrix.mode.update_frame(image_data)


@socketio.on('game-input')
def game_input(data):
    mode = matrix.mode
    if mode is None or not hasattr(mode, 'handle_input'):
        return
    action = str(data.get('action', '')).upper()
    pressed = bool(data.get('pressed', True))
    try:
        if isinstance(mode, Pong):
            mode.handle_input(action, pressed, player=int(data.get('player', 1)))
        else:
            mode.handle_input(action, pressed)
    except Exception:
        traceback.print_exc()


@socketio.on('paddle')
def paddle(data):
    if isinstance(matrix.mode, Pong):
        matrix.mode.set_paddle(int(data.get('player', 1)), data.get('pos', 0.5))


@socketio.on('flappybird_jump')
def handle_flappybird_jump():
    if isinstance(matrix.mode, FlappyBird):
        matrix.mode.flap()
        emit('jumped', {'message': 'Jumped!'})


def preview_loop():
    """Push game state to connected browsers, plus the current frame (as PNG)
    for the game controller's preview while a game is running."""
    last_id = -1
    last_state = None
    tick = 0
    while True:
        socketio.sleep(0.1)
        tick += 1
        if not viewers:
            continue
        try:
            proxy = matrix.matrix
            if proxy.capture and proxy.frame_id != last_id:
                last_id = proxy.frame_id
                buf = io.BytesIO()
                proxy.frame.save(buf, format='PNG', optimize=False, compress_level=1)
                socketio.emit('preview', buf.getvalue())
            if tick % 4 == 0:
                state = matrix.state()
                if state != last_state:
                    last_state = state
                    socketio.emit('state', state)
        except Exception:
            traceback.print_exc()


# ---------------------------------------------------------------------------
# System info
# ---------------------------------------------------------------------------
def detect_model():
    try:
        with open('/proc/device-tree/model') as f:
            return f.read().strip('\x00').strip()
    except Exception:
        return "Unknown model"


def cpu_temp():
    try:
        with open('/sys/class/thermal/thermal_zone0/temp') as f:
            return round(int(f.read()) / 1000.0, 1)
    except Exception:
        return None


def local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'
    finally:
        s.close()


def getStorage():
    disk = psutil.disk_usage('/')
    free = round(disk.free / 1024.0 ** 3, 1)
    total = round(disk.total / 1024.0 ** 3, 1)
    return f"{free} GB free of {total} GB"


def getUptime():
    try:
        p = subprocess.Popen(shlex.split("uptime -p"), stdout=subprocess.PIPE)
        return p.communicate()[0].decode("utf-8").strip().split(' ', 1)[1]
    except Exception:
        return "Unknown"


def system_info_data():
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    return {
        'model': detect_model(),
        'ip': local_ip(),
        'cpu': psutil.cpu_percent(),
        'temp': cpu_temp(),
        'memory': mem.percent,
        'disk': disk.percent,
        'storage': getStorage(),
        'uptime': getUptime(),
    }


# ---------------------------------------------------------------------------
# HTTPS (needed by browsers for camera, screen share and installing the PWA)
# ---------------------------------------------------------------------------
def ensure_certificate(cert_dir):
    cert = os.path.join(cert_dir, 'cert.pem')
    key = os.path.join(cert_dir, 'key.pem')
    if not (os.path.exists(cert) and os.path.exists(key)):
        os.makedirs(cert_dir, exist_ok=True)
        ip = local_ip()
        host = socket.gethostname()
        print(f"Creating self-signed certificate for {ip} / {host}.local")
        subprocess.check_call([
            'openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-sha256',
            '-keyout', key, '-out', cert, '-days', '3650', '-subj', '/CN=LED Matrix',
            '-addext', f'subjectAltName=IP:{ip},IP:127.0.0.1,DNS:{host}.local,DNS:localhost',
        ])
    return cert, key


def run_server(host, port, https=False):
    kwargs = dict(host=host, port=port, debug=False)
    mode = socketio.async_mode
    if https:
        cert, key = ensure_certificate(os.path.join(DATA_DIR, 'certs'))
        if mode in ('eventlet', 'gevent', 'gevent_uwsgi'):
            kwargs.update(certfile=cert, keyfile=key)
        else:
            kwargs.update(ssl_context=(cert, key))
    scheme = 'https' if https else 'http'
    print(f"LED matrix dashboard: {scheme}://{local_ip()}:{port}  (async mode: {mode})")
    if mode == 'threading':
        # Newer Flask-SocketIO refuses the built-in server unless told it's fine
        # (it is, for a LAN gadget); older versions don't know the flag.
        try:
            socketio.run(app, allow_unsafe_werkzeug=True, **kwargs)
            return
        except TypeError as e:
            if 'allow_unsafe_werkzeug' not in str(e):
                raise
    socketio.run(app, **kwargs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='LED matrix dashboard')
    parser.add_argument('--host', default=os.environ.get('LEDMATRIX_HOST', '0.0.0.0'))
    parser.add_argument('--port', type=int, default=int(os.environ.get('LEDMATRIX_PORT', 8000)))
    parser.add_argument('--https', action='store_true', default=os.environ.get('LEDMATRIX_HTTPS') == '1',
                        help='Serve over HTTPS with a self-signed certificate (enables camera, '
                             'screen share and PWA install on other devices)')
    args = parser.parse_args()

    def warm_fonts():
        from mods.fonts import get_font
        for name in ('10x20', '7x13', '6x10', '5x7', 'texgyre-27', 'tom-thumb'):
            get_font(name)
    threading.Thread(target=warm_fonts, daemon=True).start()

    matrix = Matrix()
    socketio.start_background_task(preview_loop)
    matrix.resume()
    run_server(args.host, args.port, args.https)
