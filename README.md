# LED Matrix

A Raspberry Pi driving a 192×64 LED matrix (6×2 panels of 64×32), with a web dashboard you can open on any phone or computer on your network.

## Deploying to the Pi (automatic, from GitHub)

The Pi runs the dashboard as a service and follows the `main` branch: every 20 seconds it asks GitHub for the latest commit ID of `main` (a few hundred bytes), and only when that changed it downloads the new code and restarts the dashboard. So the workflow is: work on a branch → open a pull request → merge into `main` → the Pi is updated within about 20 seconds.

**One-time setup on the Pi**

```bash
cd ~
mv rpi-led-matrix rpi-led-matrix.old            # only if an old (non-git) copy exists
git clone https://github.com/juliancroeze/ledmatrix.git rpi-led-matrix
cd rpi-led-matrix
sudo bash deploy/install.sh
```

The `rgbmatrix` Python module must already be installed (it's built from the upstream [rpi-rgb-led-matrix](https://github.com/hzeller/rpi-rgb-led-matrix) library); the installer warns if it isn't.

Options for the installer: `LEDMATRIX_BRANCH=main` (branch to follow) and `LEDMATRIX_ARGS="--https"` (arguments for `index.py`; `LEDMATRIX_ARGS=""` for plain http), e.g. `sudo LEDMATRIX_ARGS="" bash deploy/install.sh`.

**Day to day**

| | |
|---|---|
| Dashboard status | `systemctl status ledmatrix` |
| Dashboard output / errors | `journalctl -u ledmatrix -f` |
| What the updater did | `journalctl -u ledmatrix-update` |
| Check for an update right now | `sudo systemctl restart ledmatrix-update` |
| Restart | `sudo systemctl restart ledmatrix` |
| Stop auto-updates | `sudo systemctl disable --now ledmatrix-update` |
| Check less/more often | edit `LEDMATRIX_INTERVAL` in `deploy/ledmatrix-update.service` |

The Pi always mirrors the branch exactly: edits made directly on the Pi are overwritten by the next update, so make changes through GitHub. Settings, uploads and certificates live outside the repo (`/root/ledmatrix`) and are kept.

## Running it by hand

```bash
cd src/scripts
sudo pip3 install -r requirements.txt     # first time only
sudo python3 index.py                     # http://<pi-address>:8000
sudo python3 index.py --https             # https://<pi-address>:8000
```

Options: `--port 8000`, `--host 0.0.0.0`, `--https` (or set `LEDMATRIX_PORT`, `LEDMATRIX_HOST`, `LEDMATRIX_HTTPS=1`).

### Why HTTPS?

Browsers only allow **camera**, **screen sharing** and **installing the app (PWA)** on secure pages. Everything else works over plain HTTP.

With `--https` the server creates a self-signed certificate on first start (stored in `~/ledmatrix/certs`). Your browser will warn about it once; choose *Advanced → Continue*. To get rid of the warning entirely (and to make Android install the app as a real PWA), trust `~/ledmatrix/certs/cert.pem` on your devices, or put the Pi behind something like Tailscale/Caddy that provides a real certificate.

## Dashboard

One page, three parts:

- **Live preview** at the top shows exactly what's on the matrix, rendered as LEDs. The page's glow colour follows what's on screen.
- **Brightness** slider and **Turn off**.
- **Modes**, grouped:
  - *Send from this device*: Camera, Screen share, Draw (live while you draw), Text (scrolling message), Image (photos and animated GIFs)
  - *Games*: Snake, Tetris, Pong (vs computer, or 2 players on two phones), Flappy
  - *Ambient*: Clock, Weather (Open-Meteo, any city), Bitcoin (CoinGecko), Digital rain, Starfield, Game of Life, Rainbow, DVD, Nyan cat

On a phone, starting a game opens a full-screen controller (works sideways too). On a computer, use the keyboard: arrows/WASD, `Space`, `Z`/`Enter` = A, `X` = B.

### Install as an app

- **iPhone/iPad (Safari):** Share → *Add to Home Screen*.
- **Android (Chrome):** menu → *Install app* (needs HTTPS with a trusted certificate; otherwise *Add to Home screen* still creates a shortcut).
- **Desktop Chrome/Edge:** the *Install app* button appears in the header when available.

## Settings and files

Stored in `~/ledmatrix/` (that's `/root/ledmatrix` when run with sudo):

- `config.json` – brightness, last mode (restored after a restart for modes that don't need a browser), weather city
- `uploads/` – the last uploaded image
- `certs/` – the HTTPS certificate

## Adding a mode

1. Create `src/scripts/mods/mymode.py` with a class extending `FrameMode` and implement `render(self, dt)` by drawing into `self.image` / `self.draw` (Pillow). Use `get_font('7x13')` from `mods.fonts` for the BDF pixel fonts.
2. Optional: `handle_input(action, pressed)` for gamepad input (`UP/DOWN/LEFT/RIGHT/A/B`) and `get_state()` for a score on the dashboard.
3. Add an entry to `MODES` in `index.py` (pick an icon name from `templates/_icons.svg`).

## API

`POST /api/mode {mode, options}`, `POST /api/stop`, `POST /api/brightness {value}`, `POST /api/text {text, color, speed, size, rainbow}`, `POST /api/image` (multipart `file`, `fit`), `GET /api/state`, `GET /api/system`. The old `/on`, `/off`, `/snake-*` and `/send-drawing` routes still work.
