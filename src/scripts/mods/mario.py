"""World 1-1 of New Super Mario Bros. (Nintendo DS, 2006) on the 192x64 matrix.

Every 16px tile of the original is drawn as 4x4 LEDs, so the matrix shows a
window of 48x16 tiles (the DS showed 16x12). The level layout follows the
Mario Wiki map of 1-1: the first ? blocks with a Goomba under them, the coin
arcs over the raised ground, the 10-coin brick, the first pit and pipe, the
Mega Mushroom after the first pit, the 1-Up vine into the sky, Star Coin 1
next to the second pipe, the vine to the Red Coin ring, the pipe to the
underground room (Star Coin 2, needs a wall jump), the midway flag, the hidden
Star, Star Coin 3 sealed under bricks (ground-pound them as Super Mario), the
two red Koopas on brick ledges, and the staircase to the goal pole and fort.

Controls: LEFT/RIGHT walk, B (hold) run, A jump (hold for higher),
DOWN in the air = ground pound, DOWN on a green pipe = enter it,
UP/DOWN on a vine = climb, B with a Fire Flower = fireball,
A while sliding down a wall = wall jump.
"""
import math
import random

from PIL import Image, ImageOps

from mods.samplebase import FrameMode
from mods.fonts import get_font, text_size

W, H = 192, 64
T = 4                       # LEDs per tile
VIEW_W, VIEW_H = W // T, H // T
STEP = 1.0 / 60.0           # fixed physics step
EPS = 1e-4

# Movement, in tiles per second (one tile = 16px on the DS). The run speed
# is the measured 3 px/frame (TASVideos); the rest is tuned to feel like it.
WALK, RUN = 5.5, 11.0
ACCEL_GROUND, ACCEL_AIR = 22.0, 14.0
FRICTION, SKID = 20.0, 40.0
GRAV_HOLD, GRAV = 38.0, 95.0
MAX_FALL = 18.0
JUMP_V, JUMP_RUN_BONUS = 17.5, 0.35
STOMP_V, STOMP_V_HOLD = 11.0, 17.0
TIME_TICK = 0.6             # seconds per timer unit
COMBO = [100, 200, 400, 800, 1000, 2000, 4000, 8000]

# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------
C = dict(
    red=(230, 30, 20), skin=(255, 190, 130), blue=(40, 70, 230), brown=(110, 55, 15),
    white=(245, 245, 245), black=(0, 0, 0), yellow=(255, 210, 0), orange=(240, 130, 20),
    green=(40, 180, 40), dgreen=(10, 100, 25), lgreen=(150, 245, 110),
)
PAL = {
    'R': C['red'], 'S': C['skin'], 'B': C['blue'], 'N': C['brown'], 'W': C['white'],
    'K': C['black'], 'Y': C['yellow'], 'O': C['orange'], 'G': C['green'], 'g': C['dgreen'],
    'L': C['lgreen'], 'H': (60, 30, 8), 'n': (160, 85, 30), 'y': (250, 225, 130),
}

# ---------------------------------------------------------------------------
# Sprites (facing right; mirrored when needed)
# ---------------------------------------------------------------------------
SMALL = {
    'stand': [".RRR", ".NSS", "RBBR", "N..N"],
    'walk':  [".RRR", ".NSS", "RBBR", ".NN."],
    'jump':  [".RRR", ".NSS", "RBBS", "N..."],
    'dead':  [".RR.", "SSSS", "RBBR", "N..N"],
}
BIG = {
    'stand': [".RRR", ".NSS", ".SSS", "RRBR", "RBBR", ".BB.", "B..B", "N..N"],
    'walk':  [".RRR", ".NSS", ".SSS", "RRBR", "RBBR", ".BB.", ".BB.", ".NN."],
    'jump':  [".RRR", ".NSS", ".SSS", "RRBS", "RBBR", ".BB.", "B...", "N..."],
    'pound': ["....", ".RRR", ".NSS", "RSSS", "RBBR", "SBBS", "BBBB", "N..N"],
}
GOOMBA = [[".nn.", "WnnW", "nnnn", "HH.H"], [".nn.", "WnnW", "nnnn", "H.HH"]]
GOOMBA_FLAT = ["nnnn", "HHHH"]
KOOPA = [["..yy", "..yK", ".GG.", "GLGy", "GGG.", "y..y"],
         ["..yy", "..yK", ".GG.", "GLGy", "GGG.", ".yy."]]
SHELL = [".GG.", "GLLG", "WWWW"]
MUSHROOM = [".RR.", "RWRR", "RRRW", ".yy."]
FLOWER = [".OO.", "OYYO", ".OO.", "GLLG"]
STARMAN = [".YY.", "YYYY", ".YY.", "Y..Y"]
FIREBALL = ["OY", "YO"]
STARCOIN = [".YY.", "YWWY", "YWWY", ".YY."]
COIN = ["YO", "WO", "YO", "YO"]
REDCOIN = ["RN", "WN", "RN", "RN"]
RING = [".RRRR.", "R....R", "R....R", "R....R", "R....R", ".RRRR."]


def make_sprite(rows, pal=None):
    pal = dict(PAL, **(pal or {}))
    img = Image.new('RGBA', (len(rows[0]), len(rows)), (0, 0, 0, 0))
    px = img.load()
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != '.':
                px[x, y] = pal[ch] + (255,)
    return img


class Sprites(object):
    def __init__(self):
        self.cache = {}

    def get(self, key, rows, pal=None, flip=False, scale=1):
        k = (key, flip, scale)
        img = self.cache.get(k)
        if img is None:
            img = make_sprite(rows, pal)
            if scale != 1:
                img = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
            if flip:
                img = ImageOps.mirror(img)
            self.cache[k] = img
        return img


FIRE_PAL = {'R': C['white'], 'B': C['red']}
STAR_PALS = [{'R': C['yellow'], 'B': C['green']}, {'R': C['white'], 'B': C['red']},
             {}, {'R': (60, 220, 255), 'B': C['orange']}]
RED_KOOPA = {'G': (220, 40, 30), 'L': (255, 160, 140)}

# ---------------------------------------------------------------------------
# Tiles
# ---------------------------------------------------------------------------
SOLID = set("GR#BCYUWS?MXuq{}[]")
SEMI = set("=")
HIDDEN = set("hHV")
CONTENT_BLOCKS = set("?MXCYUWSBhHV")
MEGA_BREAK = set("#BCYUWS?MXuq{}[]")
DECOR = set("FTDv")


def build_main():
    LW, LH = 264, 30
    g = [['.'] * LW for _ in range(LH)]
    vines = {}

    def put(x, y, c):
        if 0 <= x < LW and 0 <= y < LH:
            g[y][x] = c

    def ground(x0, x1, top=26):
        for x in range(x0, x1 + 1):
            for y in range(top, LH):
                g[y][x] = 'G'

    def pipe(x, top, bottom=25):
        put(x, top, '{'); put(x + 1, top, '}')
        for y in range(top + 1, bottom + 1):
            put(x, y, '['); put(x + 1, y, ']')

    def row(x0, x1, y, c):
        for x in range(x0, x1 + 1):
            put(x, y, c)

    # -- terrain (pits at 73-74, 103-104, 166-168, 216-218)
    ground(0, 72); ground(75, 102); ground(105, 165); ground(169, 215); ground(219, 263)
    ground(27, 31, 25); ground(32, 37, 23); ground(50, 56, 25)
    # Star Coin 3 pocket: three bricks flush with the ground, a 2-high hole below
    for x in (180, 181, 182):
        for y in range(26, 29):
            put(x, y, '.')
        put(x, 26, 'B')

    # -- opening: ? blocks with a Goomba under them
    put(15, 22, '?'); put(19, 22, 'M'); put(20, 22, '?')
    put(35, 19, '?')
    # coin arcs over the raised ground
    for x, y in [(26, 23), (27, 22), (28, 22), (31, 21), (32, 20), (33, 20),
                 (51, 21), (52, 20), (53, 20), (54, 21),
                 (72, 22), (73, 21), (74, 21), (75, 22)]:
        put(x, y, 'o')
    # brick / ? / brick with the 10-coin brick above
    put(42, 22, 'B'); put(43, 22, '?'); put(44, 22, 'B'); put(43, 18, 'Y')
    pipe(61, 24)
    # Mega Mushroom block right after the first pit
    put(84, 22, 'X')
    put(91, 22, 'B'); put(92, 22, '?'); put(93, 22, 'B')
    put(97, 22, '?'); put(98, 22, '?')
    # hidden vine block -> sky platforms with the 1-Up brick at the top
    put(98, 19, 'V'); vines[(98, 19)] = 8
    put(98, 7, 'U')
    row(100, 104, 12, '#'); row(107, 113, 11, '#')
    row(107, 113, 9, 'o'); row(107, 113, 10, 'o')
    for y in (10, 11, 12):
        put(115, y, 'o')
    for x, y in [(102, 22), (103, 21), (104, 21), (105, 22)]:
        put(x, y, 'o')
    pipe(110, 23)
    for x, y in [(112, 19), (113, 18), (114, 18)]:
        put(x, y, 'o')
    put(114, 20, '?'); put(115, 20, 'M'); put(116, 20, '?'); put(117, 20, 'B'); put(118, 20, 'B')

    # red Koopa on a brick ledge, three hidden coin blocks, vine to the sky
    row(126, 129, 22, 'B')
    put(131, 21, 'h'); put(132, 21, 'h'); put(133, 21, 'h')
    put(136, 22, 'W'); vines[(136, 22)] = 3
    row(133, 186, 6, '=')
    for x in range(176, 186, 2):
        put(x, 4, 'o')
    # pipe down to the underground room, midway flag at 150
    pipe(144, 24)
    # three coin bricks, hidden Star above the middle one
    put(158, 22, 'C'); put(159, 22, 'C'); put(160, 22, 'C'); put(159, 18, 'H')
    put(171, 22, 'M')
    pipe(175, 23)
    # exit pipe of the underground room, four bricks
    pipe(204, 24)
    put(208, 22, 'B'); put(209, 22, 'M'); put(210, 22, 'B'); put(211, 22, 'B')
    for x, y in [(215, 22), (216, 21), (217, 21), (218, 22)]:
        put(x, y, 'o')
    # red Koopa on three bricks
    row(222, 224, 22, 'B')
    # staircase to the goal
    for i in range(8):
        for y in range(25 - i, 26):
            put(232 + i, y, '#')
    for y in range(18, 26):
        put(240, y, '#')
    put(247, 25, '#')       # goal pole base
    # fort
    for x in range(254, 263):
        for y in range(21, 26):
            put(x, y, 'F')
        if x % 2 == 0:
            put(x, 20, 'T')
    for x in range(256, 261):
        for y in range(17, 21):
            put(x, y, 'F')
        if x % 2 == 0:
            put(x, 16, 'T')
    put(258, 24, 'D'); put(259, 24, 'D'); put(258, 25, 'D'); put(259, 25, 'D')
    put(258, 18, 'D')

    def walker(kind, x, row_):
        return (kind, x, row_)

    enemies = [walker('goomba', x, 25) for x in (21, 59, 70, 94, 122, 140, 155, 157, 171, 190, 192, 226, 228)]
    enemies += [walker('koopa', 112, 25), walker('koopa', 198, 25),
                walker('redkoopa', 128, 21), walker('redkoopa', 223, 21)]
    return dict(grid=g, vines=vines, enemies=enemies, kind='over',
                starcoins=[(0, 120, 17), (2, 181, 27)],
                ring=(141, 4), redcoins=[(146 + i * 4, 5 if i % 2 else 4) for i in range(8)],
                pipes={(144, 24): ('under', 4.0, 5.0)},
                goal=247, door=258.5, midway=150)


def build_under():
    LW, LH = 34, 16
    g = [['.'] * LW for _ in range(LH)]
    for x in range(LW):
        for y in (0, 1, 14, 15):
            g[y][x] = 'R'
    for y in range(LH):
        g[y][0] = 'R'; g[y][LW - 1] = 'R'
    # entry pipe hanging from the ceiling
    for y in (2, 3):
        g[y][3] = '['; g[y][4] = ']'
    g[4][3] = 'q'; g[4][4] = 'q'
    for x in range(6, 24):
        g[13][x] = 'o'
        if x % 2 == 0:
            g[12][x] = 'o'
    for x in range(9, 18):
        g[9][x] = 'B'
        g[8][x] = 'o'
    g[9][13] = '?'
    # pillar to wall-jump between
    for y in range(5, 11):
        g[y][27] = 'R'
    # exit pipe
    g[11][29] = '{'; g[11][30] = '}'
    for y in (12, 13):
        g[y][29] = '['; g[y][30] = ']'
    return dict(grid=g, vines={}, enemies=[], kind='under', starcoins=[(1, 31, 4)],
                ring=None, redcoins=[], pipes={(29, 11): ('main', 205.0, 24.0)},
                goal=None, door=None, midway=None)


# ---------------------------------------------------------------------------
# Game objects
# ---------------------------------------------------------------------------
class Body(object):
    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.vx = self.vy = 0.0
        self.on_ground = False
        self.hit_wall = 0

    @property
    def cx(self):
        return self.x + self.w / 2

    def overlaps(self, o, shrink=0.0):
        return (self.x + shrink < o.x + o.w and o.x + shrink < self.x + self.w and
                self.y + shrink < o.y + o.h and o.y + shrink < self.y + self.h)


class Enemy(Body):
    def __init__(self, kind, x, row):
        h = 0.9 if kind == 'goomba' else 1.4
        Body.__init__(self, x + 0.05, row + 1 - h, 0.9, h)
        self.kind = kind
        self.vx = -1.9
        self.active = False
        self.state = 'walk'     # walk, flat, dead
        self.timer = 0.0
        self.grace = 0.0
        self.red = kind == 'redkoopa'


class Item(Body):
    def __init__(self, kind, x, y):
        Body.__init__(self, x + 0.1, y, 0.8, 0.8)
        self.kind = kind        # mushroom, flower, star, oneup, mega
        self.rise = 1.0 if y == int(y) else 0.0
        self.vx = 0.0 if kind == 'flower' else 3.5
        self.base_y = y


class Area(object):
    def __init__(self, spec):
        self.grid = [list(r) for r in spec['grid']]
        self.h = len(self.grid)
        self.w = len(self.grid[0])
        self.kind = spec['kind']
        self.spec = spec
        self.multi = {}

    def get(self, x, y):
        if x < 0 or x >= self.w:
            return '#'
        if y < 0 or y >= self.h:
            return '.'
        return self.grid[y][x]


# ---------------------------------------------------------------------------
# The mode
# ---------------------------------------------------------------------------
class SuperMario(FrameMode):
    FPS = 60

    def __init__(self, matrix, **options):
        super(SuperMario, self).__init__(matrix, **options)
        self.held = set()
        self.pressed = set()
        self.state = 'loading'

    def setup(self):
        self.font = get_font('tom-thumb')
        self.big_font = get_font('7x13')
        self.sp = Sprites()
        self.best = 0
        self.bg_over = self.make_bg_over()
        self.bg_under = self.make_bg_under()
        self.new_game()

    # -- game state ---------------------------------------------------------
    def new_game(self):
        self.score = 0
        self.coins = 0
        self.lives = 5
        self.state = 'title'
        self.state_t = 0.0
        self.checkpoint = False
        self.star_coins = [False, False, False]
        self.load_level()

    def load_level(self):
        self.areas = {'main': Area(build_main()), 'under': Area(build_under())}
        self.layers = {k: self.paint_area(a) for k, a in self.areas.items()}
        self.objects = {}
        for k, a in self.areas.items():
            s = a.spec
            self.objects[k] = dict(
                enemies=[Enemy(*e) for e in s['enemies']],
                starcoins=[[i, x, y, False] for i, x, y in s['starcoins'] if not self.star_coins[i]],
            )
        self.ring_used = False
        self.redcoins = []
        self.red_timer = 0.0
        self.red_got = 0
        self.flag_y = 13.5
        self.timer = 400
        self.time_acc = 0.0
        self.spawn_mario()

    def spawn_mario(self):
        self.area_id = 'main'
        x = 151.0 if self.checkpoint else 3.0
        m = Body(x, 26 - 0.9, 0.75, 0.9)
        m.facing = 1
        m.power = 0         # 0 small, 1 super, 2 fire
        m.mega = 0.0
        m.star = 0.0
        m.invuln = 0.0
        m.climb = False
        m.pound = None      # None, 'spin', 'fall'
        m.pound_t = 0.0
        m.lock = 0.0
        m.combo = 0
        m.anim = 0.0
        m.jump_buf = 0.0
        m.coyote = 0.0
        m.jump_held = False
        m.prev_bottom = m.y + m.h
        m.pipe = None
        self.mario = m
        self.items, self.fireballs, self.debris, self.popups, self.bumps, self.coinfx = [], [], [], [], [], []
        self.growing_vines = []
        self.camx = max(0.0, x - VIEW_W * 0.4)
        self.camy = 12.0
        self.flag_y = 13.5

    @property
    def area(self):
        return self.areas[self.area_id]

    # -- input ----------------------------------------------------------------
    def handle_input(self, action, pressed=True, **_):
        with self.lock:
            if pressed:
                if action not in self.held:
                    self.pressed.add(action)
                self.held.add(action)
            else:
                self.held.discard(action)

    def get_state(self):
        if not hasattr(self, 'score'):
            return {'score': 0}
        return {'score': self.score, 'best': self.best, 'coins': self.coins, 'lives': self.lives,
                'star_coins': sum(self.star_coins), 'game_over': self.state == 'gameover'}

    # -- main loop -------------------------------------------------------------
    def render(self, dt):
        # Advance by exactly the time that passed since the last frame (in
        # sub-steps of at most 1/60 s), so motion stays even when frames
        # don't arrive at a perfectly steady rate.
        dt = min(dt, 4 * STEP)
        n = max(1, int(math.ceil(dt / STEP - 1e-6)))
        for i in range(n):
            self.tick(dt / n)
            self.pressed.clear()
        self.draw_frame()

    def tick(self, dt):
        self.state_t += dt
        st = self.state
        if st == 'title':
            if self.pressed & {'A', 'B'}:
                self.state, self.state_t = 'intro', 0.0
        elif st == 'intro':
            if self.state_t > 2.0:
                self.state, self.state_t = 'play', 0.0
        elif st == 'play':
            self.update_play(dt)
        elif st == 'dying':
            m = self.mario
            if self.state_t > 0.5:
                m.vy = min(m.vy + GRAV * 0.5 * dt, MAX_FALL)
                m.y += m.vy * dt
            if self.state_t > 3.0:
                self.lives -= 1
                if self.lives <= 0:
                    self.best = max(self.best, self.score)
                    self.state, self.state_t = 'gameover', 0.0
                else:
                    self.load_level()
                    self.state, self.state_t = 'intro', 0.0
        elif st == 'gameover':
            if self.state_t > 1.0 and self.pressed & {'A', 'B'}:
                self.new_game()
        elif st in ('goal', 'walkout', 'clear'):
            self.update_goal(dt)
        self.update_effects(dt)

    # -- play ------------------------------------------------------------------
    def update_play(self, dt):
        m = self.mario
        self.time_acc += dt
        if self.time_acc >= TIME_TICK:
            self.time_acc -= TIME_TICK
            self.timer -= 1
            if self.timer <= 0:
                self.die()
                return
        if m.pipe:
            self.update_pipe(dt)
            return
        self.update_mario(dt)
        if self.state != 'play':
            return
        self.update_enemies(dt)
        self.update_items(dt)
        self.update_fireballs(dt)
        self.update_vines(dt)
        self.update_redcoins(dt)
        self.update_camera(dt)

    def update_mario(self, dt):
        m, held, pressed = self.mario, self.held, self.pressed
        m.anim += dt
        for t in ('mega', 'star', 'invuln', 'lock'):
            setattr(m, t, max(0.0, getattr(m, t) - dt))
        if m.mega <= 0 and m.w > 1:
            self.set_size(m, 'big')
        if 'A' in pressed:
            m.jump_buf = 0.12
        m.jump_buf = max(0.0, m.jump_buf - dt)
        m.coyote = 0.1 if m.on_ground else max(0.0, m.coyote - dt)
        m.prev_bottom = m.y + m.h
        dirx = (1 if 'RIGHT' in held else 0) - (1 if 'LEFT' in held else 0)

        # vines
        on_vine = self.touching(m, 'v')
        if not m.climb and on_vine and ({'UP', 'DOWN'} & held) and m.mega <= 0:
            m.climb, m.pound = True, None
        if m.climb:
            if not on_vine:
                m.climb = False
            else:
                m.vx = dirx * 3.0
                m.vy = (-4.5 if 'UP' in held else 0) + (4.5 if 'DOWN' in held else 0)
                if m.jump_buf > 0:
                    m.climb = False
                    m.jump_buf = 0
                    m.vy = -13.0
                    m.vx = dirx * WALK
                    m.jump_held = True
                if dirx:
                    m.facing = dirx
                self.move(m, dt, mario=True)
                self.after_mario_move(m)
                return

        # pipes
        if 'DOWN' in held and m.on_ground and m.mega <= 0:
            for (px, py), dest in self.area.spec['pipes'].items():
                if abs(m.y + m.h - py) < 0.05 and px + 0.2 < m.cx < px + 1.8:
                    m.pipe = dict(phase='in', t=0.0, dest=dest, x=px + 1 - m.w / 2, top=py)
                    m.x, m.vx, m.vy = px + 1 - m.w / 2, 0.0, 0.0
                    return

        # ground pound
        if 'DOWN' in pressed and not m.on_ground and m.pound is None:
            m.pound, m.pound_t, m.vx, m.vy = 'spin', 0.18, 0.0, 0.0
        if m.pound == 'spin':
            m.pound_t -= dt
            if m.pound_t <= 0:
                m.pound, m.vy = 'fall', 20.0
        if m.pound:
            if m.pound == 'fall':
                self.move(m, dt, mario=True)
                if m.on_ground:
                    m.pound = None
                    m.combo = 0
            self.after_mario_move(m)
            return

        # horizontal
        if m.lock > 0:
            dirx = 0
        top = (RUN if 'B' in held else WALK)
        if m.mega > 0:
            top = WALK
        accel = ACCEL_GROUND if m.on_ground else ACCEL_AIR
        if dirx:
            m.facing = dirx if (m.on_ground or m.lock <= 0) else m.facing
            if m.vx * dirx < 0 and m.on_ground:
                m.vx += dirx * SKID * dt
            elif abs(m.vx) < top or m.vx * dirx < 0:
                m.vx += dirx * accel * dt
                if abs(m.vx) > top and m.vx * dirx > 0:
                    m.vx = dirx * top
            elif m.on_ground:
                m.vx -= math.copysign(min(abs(m.vx) - top, FRICTION * dt), m.vx)
        elif m.on_ground:
            m.vx -= math.copysign(min(abs(m.vx), FRICTION * dt), m.vx) if m.vx else 0.0

        # wall slide / wall jump
        wall = 0
        if not m.on_ground and m.vy > 0 and dirx and m.mega <= 0:
            probe = m.x + m.w + 0.05 if dirx > 0 else m.x - 0.05
            if self.solid(self.area.get(int(math.floor(probe)), int(math.floor(m.y + m.h * 0.5)))):
                wall = dirx
                m.vy = min(m.vy, 4.0)
        if wall and m.jump_buf > 0:
            m.jump_buf = 0
            m.vx, m.vy = -wall * 8.0, -16.0
            m.facing, m.lock, m.jump_held = -wall, 0.2, True

        # jump
        if m.jump_buf > 0 and m.coyote > 0:
            m.jump_buf = m.coyote = 0
            m.vy = -(JUMP_V + JUMP_RUN_BONUS * abs(m.vx))
            m.on_ground = False
            m.jump_held = True
        if 'A' not in held:
            m.jump_held = False
        g = GRAV_HOLD if (m.vy < 0 and m.jump_held) else GRAV
        m.vy = min(m.vy + g * dt, MAX_FALL)

        # fire
        if 'B' in pressed and m.power == 2 and m.mega <= 0 and len(self.fireballs) < 2:
            fb = Body(m.cx + m.facing * 0.4 - 0.25, m.y + 0.4, 0.5, 0.5)
            fb.vx, fb.vy, fb.life = 12.0 * m.facing, 4.0, 2.5
            self.fireballs.append(fb)

        self.move(m, dt, mario=True)
        if m.on_ground:
            m.combo = 0
        self.after_mario_move(m)

    def after_mario_move(self, m):
        a = self.area
        # coins in tiles
        for ty in range(int(math.floor(m.y)), int(math.floor(m.y + m.h - EPS)) + 1):
            for tx in range(int(math.floor(m.x)), int(math.floor(m.x + m.w - EPS)) + 1):
                if a.get(tx, ty) == 'o':
                    self.set_tile(tx, ty, '.')
                    self.add_coin()
        objs = self.objects[self.area_id]
        for sc in objs['starcoins']:
            if not sc[3] and m.overlaps(Body(sc[1], sc[2], 1, 1)):
                sc[3] = True
                self.star_coins[sc[0]] = True
                self.add_score(4000, sc[1], sc[2])
        if self.area_id == 'main':
            spec = a.spec
            if not self.checkpoint and m.x > spec['midway']:
                self.checkpoint = True
            rx, ry = spec['ring']
            if not self.ring_used and m.overlaps(Body(rx, ry, 1.5, 1.5)):
                self.ring_used = True
                self.redcoins = [[x, y, False] for x, y in spec['redcoins']]
                self.red_timer, self.red_got = 8.0, 0
            for rc in self.redcoins:
                if not rc[2] and m.overlaps(Body(rc[0], rc[1], 1, 1)):
                    rc[2] = True
                    self.red_got += 1
                    self.add_score(200 * self.red_got, rc[0], rc[1])
                    if self.red_got == 8:
                        kind = ['mushroom', 'flower', 'oneup'][min(m.power, 2)]
                        self.items.append(Item(kind, rc[0], rc[1] - 1.5))
                        self.redcoins = []
            if m.x + m.w >= spec['goal'] - 0.05 and self.state == 'play':
                self.start_goal()
                return
        if m.y > a.h + 1:
            self.die()

    def update_pipe(self, dt):
        m = self.mario
        p = m.pipe
        p['t'] += dt
        if p['phase'] == 'in':
            m.y += 2.5 * dt
            if p['t'] > 0.7:
                area, x, y = p['dest']
                self.area_id = area
                m.x = x - m.w / 2
                if area == 'under':
                    # come out of the pipe hanging from the ceiling (mouth at y)
                    p.update(phase='down', t=0.0, top=None, bottom=y)
                    m.y = y - m.h
                else:
                    # rise out of the pipe whose top is at y
                    p.update(phase='up', t=0.0, top=y)
                    m.y = y
                self.camx = max(0.0, min(self.area.w - VIEW_W, m.x - VIEW_W * 0.4))
                self.camy = 0.0 if area == 'under' else 12.0
                if self.area.w < VIEW_W:
                    self.camx = -(VIEW_W - self.area.w) / 2.0
        elif p['phase'] == 'down':
            m.y += 2.5 * dt
            if m.y >= p['bottom']:
                m.pipe = None
        elif p['phase'] == 'up':
            m.y -= 2.5 * dt
            if m.y + m.h <= p['top']:
                m.y = p['top'] - m.h
                m.pipe = None
                m.vy = 0

    # -- physics -----------------------------------------------------------------
    def solid(self, t):
        return t in SOLID

    def touching(self, b, code):
        a = self.area
        for ty in range(int(math.floor(b.y)), int(math.floor(b.y + b.h - EPS)) + 1):
            for tx in range(int(math.floor(b.x + 0.2)), int(math.floor(b.x + b.w - 0.2)) + 1):
                if a.get(tx, ty) == code:
                    return True
        return False

    def move(self, b, dt, mario=False):
        a = self.area
        smash = mario and self.mario.mega > 0
        b.hit_wall = 0
        # horizontal
        b.x += b.vx * dt
        if b.vx:
            col = int(math.floor(b.x + b.w - EPS)) if b.vx > 0 else int(math.floor(b.x + EPS))
            for row in range(int(math.floor(b.y + EPS)), int(math.floor(b.y + b.h - EPS)) + 1):
                t = a.get(col, row)
                if smash and t in MEGA_BREAK and 0 <= col < a.w:
                    self.smash(col, row)
                    continue
                if t in SOLID:
                    if b.vx > 0:
                        b.x = col - b.w
                        b.hit_wall = 1
                    else:
                        b.x = col + 1
                        b.hit_wall = -1
                    b.vx = 0.0 if mario else b.vx
                    break
        # vertical
        prev_bottom = b.y + b.h
        prev_top = b.y
        b.y += b.vy * dt
        b.on_ground = False
        cols = range(int(math.floor(b.x + EPS)), int(math.floor(b.x + b.w - EPS)) + 1)
        if b.vy > 0:
            row = int(math.floor(b.y + b.h - EPS))
            under = []
            for col in cols:
                t = a.get(col, row)
                if smash and t in MEGA_BREAK and 0 <= col < a.w and row < a.h:
                    self.smash(col, row)
                    continue
                if t in SOLID or (t in SEMI and prev_bottom <= row + 0.05):
                    under.append((col, t))
            if under:
                if mario and self.mario.pound == 'fall':
                    m = self.mario
                    broke = False
                    for col, t in under:
                        if t == 'B' and m.power > 0:
                            self.break_block(col, row)
                            broke = True
                        elif t in CONTENT_BLOCKS and t != 'B':
                            self.hit_block(col, row, from_above=True)
                    if broke:
                        return
                b.y = row - b.h
                b.vy = 0.0
                b.on_ground = True
        elif b.vy < 0:
            row = int(math.floor(b.y + EPS))
            hits = []
            for col in cols:
                t = a.get(col, row)
                if smash and t in MEGA_BREAK and 0 <= col < a.w:
                    self.smash(col, row)
                    continue
                if t in SOLID or (mario and t in HIDDEN and prev_top >= row + 1 - 0.05):
                    hits.append(col)
            if hits:
                b.y = row + 1
                b.vy = 0.0
                if mario:
                    col = min(hits, key=lambda c: abs(c + 0.5 - b.cx))
                    self.hit_block(col, row)

    # -- blocks -------------------------------------------------------------------
    def set_tile(self, x, y, c):
        a = self.area
        if 0 <= x < a.w and 0 <= y < a.h:
            a.grid[y][x] = c
            self.paint_tile(self.layers[self.area_id], a, x, y)

    def hit_block(self, x, y, from_above=False):
        a, m = self.area, self.mario
        t = a.get(x, y)
        if t not in CONTENT_BLOCKS:
            return
        after = 'u'
        if t == 'B':
            if m.power > 0 and not from_above:
                self.break_block(x, y)
                return
            after = 'B'
        elif t in '?ChY':
            self.coin_fx(x, y)
            if t == 'Y':
                n = a.multi.get((x, y), 10) - 1
                a.multi[(x, y)] = n
                if n > 0:
                    after = 'Y'
        elif t == 'M':
            self.items.append(Item('mushroom' if m.power == 0 else 'flower', x, y))
        elif t == 'X':
            self.items.append(Item('mega', x, y))
        elif t == 'U':
            self.items.append(Item('oneup', x, y))
        elif t in 'SH':
            self.items.append(Item('star', x, y))
        elif t in 'WV':
            self.growing_vines.append([x, y - 1, a.spec['vines'].get((x, y), y - 8), 0.0])
        self.set_tile(x, y, '.')
        self.bumps.append([x, y, 0.0, after])
        # knock out enemies standing on the block
        for e in self.objects[self.area_id]['enemies']:
            if e.state == 'walk' and abs(e.y + e.h - y) < 0.2 and e.x < x + 1 and e.x + e.w > x:
                self.kill_enemy(e, 1 if e.cx > x + 0.5 else -1)
        for it in self.items:
            if abs(it.y + it.h - y) < 0.2 and it.x < x + 1 and it.x + it.w > x:
                it.vy = -8.0

    def break_block(self, x, y):
        self.set_tile(x, y, '.')
        for dx, dy in ((-3, -10), (3, -10), (-2, -6), (2, -6)):
            d = Body(x + 0.5, y + 0.5, 0.25, 0.25)
            d.vx, d.vy, d.life = dx, dy, 1.2
            self.debris.append(d)
        self.add_score(50)
        for e in self.objects[self.area_id]['enemies']:
            if e.state == 'walk' and abs(e.y + e.h - y) < 0.2 and e.x < x + 1 and e.x + e.w > x:
                self.kill_enemy(e, 1)

    def smash(self, x, y):
        t = self.area.get(x, y)
        if t in CONTENT_BLOCKS and t != 'B':
            self.hit_block(x, y)
            self.bumps = [b for b in self.bumps if (b[0], b[1]) != (x, y)]
        self.break_block(x, y)

    def coin_fx(self, x, y):
        self.coinfx.append([x, y - 1, 0.0])
        self.add_coin(silent=True)
        self.add_score(200, x, y - 1)

    def add_coin(self, silent=False):
        self.coins += 1
        if not silent:
            self.score += 200
        if self.coins >= 100:
            self.coins -= 100
            self.lives += 1

    def add_score(self, n, x=None, y=None, text=None):
        self.score += n
        if x is not None:
            self.popups.append([x, y, 0.0, text or str(n)])

    def update_vines(self, dt):
        for v in self.growing_vines:
            v[3] += dt
            while v[3] > 0.06 and v[1] >= v[2]:
                v[3] -= 0.06
                if self.area.get(v[0], v[1]) in '.=o':
                    self.set_tile(v[0], v[1], 'v')
                v[1] -= 1
        self.growing_vines = [v for v in self.growing_vines if v[1] >= v[2]]

    def update_redcoins(self, dt):
        if self.redcoins:
            self.red_timer -= dt
            if self.red_timer <= 0:
                self.redcoins = []

    # -- enemies -----------------------------------------------------------------
    def update_enemies(self, dt):
        m = self.mario
        enemies = self.objects[self.area_id]['enemies']
        for e in enemies:
            if not e.active:
                if e.x < self.camx + VIEW_W + 2:
                    e.active = True
                else:
                    continue
            if e.state == 'flat':
                e.timer -= dt
                continue
            if e.state == 'dead':
                e.vy = min(e.vy + GRAV * 0.5 * dt, MAX_FALL)
                e.x += e.vx * dt
                e.y += e.vy * dt
                continue
            e.grace = max(0.0, e.grace - dt)
            e.vy = min(e.vy + GRAV * 0.6 * dt, MAX_FALL)
            vx_before = e.vx
            self.move(e, dt)
            if e.hit_wall:
                e.vx = -vx_before
            if e.kind == 'redkoopa' and e.on_ground:
                ahead = e.x + e.w + 0.05 if e.vx > 0 else e.x - 0.05
                below = self.area.get(int(math.floor(ahead)), int(math.floor(e.y + e.h + 0.1)))
                if not (below in SOLID or below in SEMI):
                    e.vx = -e.vx
            if e.y > self.area.h + 2:
                e.state = 'gone'
        # enemies bumping into each other / shells
        walkers = [e for e in enemies if e.active and e.state == 'walk']
        for i, a in enumerate(walkers):
            for b in walkers[i + 1:]:
                if not a.overlaps(b):
                    continue
                ashell = a.kind == 'shell' and abs(a.vx) > 5
                bshell = b.kind == 'shell' and abs(b.vx) > 5
                if ashell and not bshell:
                    self.kill_enemy(b, 1 if a.vx > 0 else -1)
                elif bshell and not ashell:
                    self.kill_enemy(a, 1 if b.vx > 0 else -1)
                elif ashell and bshell:
                    self.kill_enemy(a, -1); self.kill_enemy(b, 1)
                else:
                    if a.cx < b.cx:
                        a.vx, b.vx = -abs(a.vx), abs(b.vx)
                    else:
                        a.vx, b.vx = abs(a.vx), -abs(b.vx)
        # Mario vs enemies
        for e in walkers:
            if e.state != 'walk' or not m.overlaps(e, 0.05):
                continue
            if m.star > 0 or m.mega > 0:
                self.kill_enemy(e, m.facing)
                continue
            stomp = m.vy > 0 and m.prev_bottom <= e.y + 0.45
            if e.kind == 'shell' and abs(e.vx) < 0.1:
                e.vx = 10.0 if m.cx < e.cx else -10.0
                e.grace = 0.25
                self.add_score(400, e.x, e.y - 1)
                if stomp:
                    m.vy = -STOMP_V
                continue
            if stomp or m.pound:
                self.stomp(e)
                if m.pound:
                    continue
                m.vy = -(STOMP_V_HOLD if 'A' in self.held else STOMP_V)
                m.jump_held = 'A' in self.held
                continue
            if e.kind == 'shell' and e.grace > 0:
                continue
            self.hurt()
        self.objects[self.area_id]['enemies'] = [
            e for e in enemies if e.state not in ('gone',) and not (e.state == 'flat' and e.timer <= 0)
            and not (e.state == 'dead' and e.y > self.area.h + 2)]

    def stomp(self, e):
        m = self.mario
        pts = COMBO[min(m.combo, len(COMBO) - 1)]
        if m.combo >= len(COMBO):
            self.lives += 1
            self.add_score(0, e.x, e.y - 1, '1UP')
        else:
            self.add_score(pts, e.x, e.y - 1)
        m.combo += 1
        if e.kind == 'goomba':
            e.state, e.timer = 'flat', 0.5
        elif e.kind in ('koopa', 'redkoopa'):
            bottom = e.y + e.h
            e.kind, e.h, e.vx = 'shell', 0.75, 0.0
            e.y = bottom - e.h
        elif e.kind == 'shell':
            e.vx = 0.0

    def kill_enemy(self, e, direction):
        if e.state in ('dead', 'gone'):
            return
        e.state = 'dead'
        e.vy = -9.0
        e.vx = 2.0 * direction
        self.add_score(200, e.x, e.y - 1)

    def hurt(self):
        m = self.mario
        if m.invuln > 0 or m.star > 0 or m.mega > 0:
            return
        if m.power == 0:
            self.die()
            return
        if m.power == 2:
            m.power = 1
        else:
            self.set_size(m, 'small')
            m.power = 0
        m.invuln = 2.0

    def die(self):
        m = self.mario
        self.best = max(self.best, self.score)
        if m.power > 0 or m.mega > 0:
            self.set_size(m, 'small')
        m.power, m.mega, m.star, m.vx = 0, 0.0, 0.0, 0.0
        m.vy = -12.0
        m.pipe = None
        self.state, self.state_t = 'dying', 0.0

    def set_size(self, m, size):
        w, h = {'small': (0.75, 0.9), 'big': (0.75, 1.8), 'mega': (2.6, 5.8)}[size]
        bottom, cx = m.y + m.h, m.cx
        m.w, m.h = w, h
        m.y = bottom - h
        m.x = cx - w / 2

    # -- items ---------------------------------------------------------------------
    def update_items(self, dt):
        m = self.mario
        keep = []
        for it in self.items:
            if it.rise > 0:
                it.rise -= dt * 2.0
                it.y = it.base_y - (1.0 - max(0.0, it.rise)) * it.h
                if it.rise <= 0:
                    it.y = it.base_y - it.h - 0.01
                    if it.kind == 'star':
                        it.vx, it.vy = 4.0, -8.0
                keep.append(it)
                continue
            if it.kind != 'flower':
                it.vy = min(it.vy + GRAV * 0.4 * dt, MAX_FALL)
                vx = it.vx
                self.move(it, dt)
                if it.hit_wall:
                    it.vx = -vx
                if it.kind == 'star' and it.on_ground:
                    it.vy = -10.0
            if m.overlaps(it):
                self.collect(it)
                continue
            if it.y < self.area.h + 2:
                keep.append(it)
        self.items = keep

    def collect(self, it):
        m = self.mario
        k = it.kind
        if k == 'mushroom':
            if m.power == 0:
                self.set_size(m, 'big')
                m.power = 1
            self.add_score(1000, it.x, it.y - 1)
        elif k == 'flower':
            if m.power == 0:
                self.set_size(m, 'big')
            m.power = 2
            self.add_score(1000, it.x, it.y - 1)
        elif k == 'oneup':
            self.lives += 1
            self.add_score(0, it.x, it.y - 1, '1UP')
        elif k == 'star':
            m.star = 10.0
            self.add_score(1000, it.x, it.y - 1)
        elif k == 'mega':
            if m.power == 0:
                m.power = 1
            self.set_size(m, 'mega')
            m.mega = 10.0
            m.climb = False
            self.add_score(1000, it.x, it.y - 1)

    def update_fireballs(self, dt):
        keep = []
        for fb in self.fireballs:
            fb.life -= dt
            fb.vy = min(fb.vy + 60.0 * dt, 12.0)
            vx = fb.vx
            self.move(fb, dt)
            if fb.on_ground:
                fb.vy = -7.0
            if fb.hit_wall or fb.life <= 0 or fb.y > self.area.h:
                continue
            fb.vx = vx
            hit = False
            for e in self.objects[self.area_id]['enemies']:
                if e.state == 'walk' and e.active and fb.overlaps(e):
                    self.kill_enemy(e, 1 if vx > 0 else -1)
                    hit = True
                    break
            if not hit and self.camx - 2 < fb.x < self.camx + VIEW_W + 2:
                keep.append(fb)
        self.fireballs = keep

    def update_effects(self, dt):
        for d in self.debris:
            d.life -= dt
            d.vy += GRAV * 0.5 * dt
            d.x += d.vx * dt
            d.y += d.vy * dt
        self.debris = [d for d in self.debris if d.life > 0]
        for p in self.popups:
            p[2] += dt
        self.popups = [p for p in self.popups if p[2] < 0.8]
        for c in self.coinfx:
            c[2] += dt
        self.coinfx = [c for c in self.coinfx if c[2] < 0.45]
        for b in self.bumps:
            b[2] += dt
        done = [b for b in self.bumps if b[2] >= 0.15]
        self.bumps = [b for b in self.bumps if b[2] < 0.15]
        for x, y, _, after in done:
            if self.area.get(x, y) == '.':
                self.set_tile(x, y, after)

    # -- camera --------------------------------------------------------------------
    def update_camera(self, dt):
        m, a = self.mario, self.area
        if a.w <= VIEW_W:
            self.camx = -(VIEW_W - a.w) / 2.0
        else:
            # follow Mario 1:1, snapped to whole LEDs so he never wobbles
            px = int(round(m.cx * T)) - int(W * 0.42)
            px = max(0, min((a.w - VIEW_W) * T, px))
            self.camx = px / float(T)
        if a.h <= VIEW_H:
            self.camy = 0.0
            return
        bottom = m.y + m.h
        maxy = a.h - VIEW_H
        if m.on_ground or m.climb:
            target = max(0.0, min(maxy, bottom - 14))
            self.camy += (target - self.camy) * min(1.0, dt * 4.0)
            if abs(target - self.camy) < 0.25 / T:
                self.camy = target
        if m.y < self.camy + 2:
            self.camy = m.y - 2
        if bottom > self.camy + VIEW_H - 1:
            self.camy = bottom - VIEW_H + 1
        self.camy = max(0.0, min(maxy, self.camy))

    # -- goal ----------------------------------------------------------------------
    def start_goal(self):
        m = self.mario
        spec = self.area.spec
        height = 25 - (m.y + m.h)
        if m.y <= self.flag_y:
            self.lives += 1
            self.add_score(0, spec['goal'] - 1, m.y, '1UP')
        else:
            pts = [100, 400, 800, 2000, 4000, 5000][max(0, min(5, int(height / 2)))]
            self.add_score(pts, spec['goal'] - 2, m.y)
        if m.mega > 0:
            m.mega = 0.0
            self.set_size(m, 'big')
        m.x = spec['goal'] + 0.5 - m.w
        m.vx = m.vy = 0.0
        m.star = 0.0
        m.facing = 1
        self.state, self.state_t = 'goal', 0.0

    def update_goal(self, dt):
        m = self.mario
        spec = self.areas['main'].spec
        m.anim += dt
        if self.state == 'goal':
            if m.y + m.h < 25:
                m.y = min(25 - m.h, m.y + 9 * dt)
            self.flag_y = min(23.5, self.flag_y + 9 * dt)
            if self.state_t > 1.4:
                self.state, self.state_t = 'walkout', 0.0
                m.x = spec['goal'] + 0.6
        elif self.state == 'walkout':
            m.vx = 3.5
            m.vy = min(m.vy + GRAV * dt, MAX_FALL)
            self.move(m, dt)
            self.update_camera(dt)
            if m.x >= spec['door']:
                self.state, self.state_t = 'clear', 0.0
                m.hidden = True
        elif self.state == 'clear':
            if self.timer > 0:
                n = min(self.timer, 4)
                self.timer -= n
                self.score += 50 * n
            elif self.state_t > 5.0:
                self.best = max(self.best, self.score)
                lives, score = self.lives, self.score
                self.new_game()
                self.lives, self.score = lives, score

    # =============================================================================
    # Drawing
    # =============================================================================
    def paint_area(self, a):
        layer = Image.new('RGBA', (a.w * T, a.h * T), (0, 0, 0, 0))
        for y in range(a.h):
            for x in range(a.w):
                if a.grid[y][x] != '.':
                    self.paint_tile(layer, a, x, y)
        return layer

    def paint_tile(self, layer, a, x, y):
        px = layer.load()
        t = a.grid[y][x]
        ox, oy = x * T, y * T
        for j in range(T):
            for i in range(T):
                px[ox + i, oy + j] = (0, 0, 0, 0)
        if t == '.' or t in HIDDEN:
            return
        for j, i, col in self.tile_pixels(a, t, x, y):
            px[ox + i, oy + j] = col + (255,)

    def tile_pixels(self, a, t, x, y):
        out = []

        def fill(rows, pal):
            for j, r in enumerate(rows):
                for i, ch in enumerate(r):
                    if ch != '.':
                        out.append((j, i, pal[ch]))

        if t == 'G':
            top = a.get(x, y - 1) != 'G'
            for j in range(T):
                for i in range(T):
                    wx, wy = x * T + i, y * T + j
                    if top and j == 0:
                        col = (120, 230, 70)
                    elif top and j == 1:
                        col = (50, 170, 40) if (wx % 3) else (120, 230, 70)
                    else:
                        wave = (wy + int(1.5 * math.sin(wx * 0.8))) % 5
                        col = (205, 95, 45) if wave == 0 else (245, 150, 85)
                    out.append((j, i, col))
        elif t == 'R':
            for j in range(T):
                for i in range(T):
                    h = (x * 7 + y * 13 + i * 3 + j * 5) % 7
                    out.append((j, i, (60, 70, 110) if h else (95, 105, 150)))
        elif t == 'B':
            fill(["lbbd", "bbbd", "dddd", "bdbb"], {'l': (230, 140, 80), 'b': (190, 95, 45), 'd': (100, 45, 15)})
        elif t in 'CYUWS':
            fill(["lbbd", "bbbd", "dddd", "bdbb"], {'l': (230, 140, 80), 'b': (190, 95, 45), 'd': (100, 45, 15)})
        elif t in '?MX':
            fill(["lyyo", "ywwo", "yywo", "oooo"], {'l': (255, 240, 150), 'y': (245, 185, 0), 'o': (170, 95, 0),
                                                   'w': (255, 255, 255)})
        elif t == 'u':
            fill(["mmmd", "mkmd", "mmmd", "dddd"], {'m': (170, 110, 60), 'd': (95, 55, 25), 'k': (130, 80, 40)})
        elif t == '#':
            fill(["hhhd", "hmmd", "hmmd", "dddd"], {'h': (215, 150, 90), 'm': (165, 100, 50), 'd': (90, 50, 20)})
        elif t in '{}[]q':
            shade = [(10, 90, 20), (170, 250, 130), (110, 220, 80), (50, 180, 45),
                     (50, 180, 45), (40, 160, 40), (20, 120, 30), (10, 80, 15)]
            base = 0 if t in '{[q' else 4
            for j in range(T):
                for i in range(T):
                    col = shade[base + i]
                    if t in '{}' and j in (0, 3):
                        col = (10, 90, 20) if j == 3 else tuple(min(255, c + 30) for c in col)
                    if t == 'q' and j == 3:
                        col = (10, 90, 20)
                    out.append((j, i, col))
        elif t == 'o':
            fill([".YO.", ".WO.", ".YO.", ".YO."], {'Y': (255, 215, 0), 'O': (210, 130, 0), 'W': (255, 250, 200)})
        elif t == '=':
            fill(["WWWW", "WWWW", "cccc", "...."], {'W': (250, 252, 255), 'c': (185, 205, 235)})
        elif t == 'v':
            leaf = 'L.' if y % 2 else '.L'
            fill([".gg.", leaf[0] + "gg" + leaf[1], ".gg.", ".gg."], {'g': (40, 170, 40), 'L': (120, 230, 80)})
        elif t == 'F':
            fill(["sssm", "mmmm", "smss", "mmmm"], {'s': (200, 190, 175), 'm': (130, 120, 110)})
        elif t == 'T':
            fill(["sss.", "sssm", "smss", "mmmm"], {'s': (200, 190, 175), 'm': (130, 120, 110)})
        elif t == 'D':
            fill(["kkkk", "kkkk", "kkkk", "kkkk"], {'k': (25, 15, 10)})
        return out

    def tile_image(self, a, t, x, y):
        img = Image.new('RGBA', (T, T), (0, 0, 0, 0))
        px = img.load()
        for j, i, col in self.tile_pixels(a, t, x, y):
            px[i, j] = col + (255,)
        return img

    def make_bg_over(self):
        rnd = random.Random(11)
        main_w = 264 * T
        bw = int((main_w - W) * 0.5) + W + 4
        bh = 112
        img = Image.new('RGB', (bw, bh))
        px = img.load()
        for y in range(bh):
            f = min(1.0, max(0.0, (y - 20) / 92.0))
            col = (int(70 + 110 * f), int(150 + 80 * f), 255)
            for x in range(bw):
                px[x, y] = col
        from PIL import ImageDraw
        d = ImageDraw.Draw(img)
        ground_y = 48 + 56   # bg row that lines up with the level ground
        # clouds
        for _ in range(bw // 40):
            cx, cy = rnd.randrange(bw), rnd.randrange(30, 80)
            wdt = rnd.randrange(10, 22)
            d.ellipse((cx, cy, cx + wdt, cy + 4), fill=(250, 252, 255))
            d.line((cx + 2, cy + 4, cx + wdt - 2, cy + 4), fill=(200, 220, 245))
        # distant pink domes
        x = 0
        while x < bw:
            wdt = rnd.randrange(12, 20)
            hgt = rnd.randrange(14, 22)
            d.ellipse((x, ground_y - hgt, x + wdt, ground_y + hgt), fill=(245, 200, 205))
            x += wdt + rnd.randrange(2, 12)
        # Peach's castle near the start
        cx = 14
        d.rectangle((cx, ground_y - 12, cx + 22, ground_y), fill=(205, 205, 215))
        d.rectangle((cx + 8, ground_y - 22, cx + 14, ground_y - 12), fill=(215, 215, 225))
        for tx, tw, top in ((cx - 2, 5, 16), (cx + 19, 5, 16), (cx + 8, 6, 22)):
            d.polygon([(tx, ground_y - top), (tx + tw, ground_y - top), (tx + tw / 2.0, ground_y - top - 6)],
                      fill=(220, 50, 60))
        d.rectangle((cx + 10, ground_y - 5, cx + 12, ground_y), fill=(90, 60, 40))
        # striped yellow domes (the 1-1 hills)
        x = 50
        while x < bw:
            wdt = rnd.randrange(10, 16)
            hgt = rnd.randrange(14, 24)
            top = ground_y - hgt
            d.ellipse((x, top, x + wdt, ground_y + hgt), fill=(235, 205, 120))
            for sy in range(top + 3, ground_y, 3):
                for sx in range(x, x + wdt + 1):
                    if img.getpixel((sx, sy)) == (235, 205, 120) and (sx + sy) % 2 == 0:
                        px[sx, sy] = (215, 160, 95)
            x += wdt + rnd.randrange(8, 30)
        # bushes
        x = 0
        while x < bw:
            wdt = rnd.randrange(8, 16)
            d.ellipse((x, ground_y - 7, x + wdt, ground_y + 6), fill=(40, 160, 50))
            d.ellipse((x + 2, ground_y - 6, x + wdt - 3, ground_y - 2), fill=(90, 210, 80))
            x += wdt + rnd.randrange(0, 18)
        # below the ground line: what you see down a pit
        for y in range(ground_y, bh):
            f = (y - ground_y) / float(bh - ground_y)
            col = (int(25 - 20 * f), int(80 - 60 * f), int(35 - 25 * f))
            for x in range(bw):
                px[x, y] = col
        # keep the backdrop a bit darker than the playfield so it reads on LEDs
        return img.point(lambda v: int(v * 0.6))

    def make_bg_under(self):
        img = Image.new('RGB', (W, H), (8, 8, 24))
        px = img.load()
        rnd = random.Random(3)
        for _ in range(140):
            px[rnd.randrange(W), rnd.randrange(H)] = (25, 25, 60)
        return img

    def draw_frame(self):
        img = self.image
        st = self.state
        if st == 'intro':
            self.draw.rectangle((0, 0, W, H), fill=(0, 0, 0))
            self.center_text('WORLD 1-1', 14, self.big_font, (255, 255, 255))
            spr = self.sp.get('m_stand', SMALL['stand'], scale=2)
            img.paste(spr, (78, 38), spr)
            self.draw.text((90, 40), 'x %d' % self.lives, font=self.big_font, fill=(255, 255, 255))
            return
        if st == 'gameover':
            self.draw.rectangle((0, 0, W, H), fill=(0, 0, 0))
            self.center_text('GAME OVER', 18, self.big_font, (255, 60, 60))
            self.center_text('Score %d  -  A = again' % self.score, 42, self.font, (200, 200, 220))
            return

        a = self.area
        camx_px = int(round(self.camx * T))
        camy_px = int(round(self.camy * T))
        if a.kind == 'over':
            bx = int(max(0, camx_px) * 0.5)
            by = int(48 + (camy_px - 48) * 0.25)
            img.paste(self.bg_over.crop((bx, by, bx + W, by + H)), (0, 0))
        else:
            img.paste(self.bg_under, (0, 0))
        layer = self.layers[self.area_id]
        crop = layer.crop((camx_px, camy_px, camx_px + W, camy_px + H))
        img.paste(crop, (0, 0), crop)

        def at(x, y):
            return int(round(x * T)) - camx_px, int(round(y * T)) - camy_px

        def put(spr, x, y):
            img.paste(spr, (x, y), spr)

        t = self.state_t
        # bumped blocks
        for x, y, bt, after in self.bumps:
            sx, sy = at(x, y)
            put(self.tile_image(a, after if after != '.' else 'u', x, y), sx, sy - (1 if bt < 0.1 else 0))
        # goal pole and flag
        spec = a.spec
        if spec.get('goal'):
            gx, gy = at(spec['goal'] + 0.5, 13)
            self.draw.line((gx, gy, gx, gy + 12 * T), fill=(200, 230, 200))
            self.draw.rectangle((gx - 1, gy - 2, gx, gy - 1), fill=(60, 200, 60))
            fx, fy = at(spec['goal'] + 0.5, self.flag_y)
            self.draw.rectangle((fx - 4, fy, fx - 1, fy + 3), fill=(20, 20, 20))
            self.draw.point((fx - 3, fy + 1), fill=(255, 255, 255))
            mx, my = at(spec['midway'] + 0.5, 22)
            self.draw.line((mx, my, mx, my + 4 * T - 1), fill=(200, 200, 200))
            self.draw.rectangle((mx + 1, my, mx + 3, my + 2), fill=(230, 40, 30) if self.checkpoint else (20, 20, 20))
            if not self.ring_used and spec.get('ring'):
                rx, ry = at(*spec['ring'])
                put(self.sp.get('ring', RING), rx, ry)
        objs = self.objects[self.area_id]
        blink = int(t * 6) % 2
        for sc in objs['starcoins']:
            if not sc[3]:
                sx, sy = at(sc[1], sc[2])
                put(self.sp.get('sc', STARCOIN), sx, sy)
        if self.redcoins and (self.red_timer > 2 or blink):
            for rx, ry, got in self.redcoins:
                if not got:
                    sx, sy = at(rx, ry)
                    put(self.sp.get('rc', REDCOIN), sx + 1, sy)
        for c in self.coinfx:
            sx, sy = at(c[0], c[1] - math.sin(c[2] / 0.45 * math.pi) * 1.5)
            put(self.sp.get('coin', COIN), sx + 1, sy)
        # items
        for it in self.items:
            rows, pal = {'mushroom': (MUSHROOM, None), 'oneup': (MUSHROOM, {'R': C['green']}),
                         'mega': (MUSHROOM, {'R': C['yellow'], 'W': C['red']}),
                         'flower': (FLOWER, None), 'star': (STARMAN, None)}[it.kind]
            sx, sy = at(it.x - 0.1, it.y - 0.2)
            spr = self.sp.get('it_' + it.kind, rows, pal)
            if it.rise > 0:
                # still coming out of the block: clip at the block's top edge
                _, top = at(0, it.base_y)
                visible = top - sy
                if visible <= 0:
                    continue
                spr = spr.crop((0, 0, 4, min(4, visible)))
            put(spr, sx, sy)
        # enemies
        for e in objs['enemies']:
            if not e.active:
                continue
            sx, sy = at(e.x - 0.05, e.y)
            flip = e.vx > 0
            red = e.red
            if e.kind == 'goomba':
                if e.state == 'flat':
                    spr = self.sp.get('gflat', GOOMBA_FLAT)
                    put(spr, sx, sy + 2)
                    continue
                spr = self.sp.get('g%d' % (int(t * 6) % 2), GOOMBA[int(t * 6) % 2])
                if e.state == 'dead':
                    spr = spr.transpose(Image.FLIP_TOP_BOTTOM)
                put(spr, sx, sy)
            elif e.kind in ('koopa', 'redkoopa'):
                f = int(t * 6) % 2
                spr = self.sp.get('k%d%s' % (f, 'r' if red else ''), KOOPA[f], RED_KOOPA if red else None,
                                  flip=not flip)
                if e.state == 'dead':
                    spr = spr.transpose(Image.FLIP_TOP_BOTTOM)
                put(spr, sx, sy)
            else:
                spr = self.sp.get('shell%s' % ('r' if red else ''), SHELL, RED_KOOPA if red else None)
                if e.state == 'dead':
                    spr = spr.transpose(Image.FLIP_TOP_BOTTOM)
                put(spr, sx, sy)
        for fb in self.fireballs:
            sx, sy = at(fb.x, fb.y)
            put(self.sp.get('fb', FIREBALL), sx, sy)
        for d in self.debris:
            sx, sy = at(d.x, d.y)
            self.draw.point((sx, sy), fill=(190, 95, 45))
        self.draw_mario(at)
        for x, y, pt, text in self.popups:
            sx, sy = at(x, y - pt * 1.5)
            self.draw.text((sx, sy), text, font=self.font, fill=(255, 255, 255))
        self.draw_hud()
        if st == 'title':
            self.draw.rectangle((44, 14, 148, 50), fill=(0, 0, 0))
            self.draw.rectangle((44, 14, 148, 50), outline=(230, 40, 30))
            self.center_text('NEW SUPER', 17, self.font, (255, 210, 0))
            self.center_text('MARIO 1-1', 24, self.big_font, (255, 255, 255))
            if int(t * 2) % 2 == 0:
                self.center_text('Press A', 41, self.font, (200, 200, 220))
        elif st == 'clear':
            self.center_text('COURSE CLEAR!', 22, self.big_font, (255, 230, 80))

    def draw_mario(self, at):
        m = self.mario
        if getattr(m, 'hidden', False) and self.state == 'clear':
            return
        if m.invuln > 0 and int(m.invuln * 20) % 2:
            return
        pal = dict(FIRE_PAL) if m.power == 2 else {}
        key = 'f' if m.power == 2 else 'n'
        if m.star > 0:
            i = int(m.star * 15) % 4
            pal, key = STAR_PALS[i], 's%d' % i
        if self.state == 'dying':
            rows, frame = SMALL['dead'], 'dead'
        else:
            moving = abs(m.vx) > 0.3
            if m.pound:
                frame = 'pound'
            elif not m.on_ground and not m.climb:
                frame = 'jump'
            elif m.climb:
                frame = 'walk' if int(m.y * 2) % 2 else 'stand'
            elif moving and int(m.anim * (6 + abs(m.vx))) % 2:
                frame = 'walk'
            else:
                frame = 'stand'
            if m.h > 1 or m.mega > 0:
                rows = BIG.get(frame, BIG['stand'])
            else:
                rows = SMALL.get(frame, SMALL['stand'])
        big = len(rows) == 8
        scale = 3 if m.mega > 0 else 1
        spr = self.sp.get('m%s%s%d%d' % (key, frame, big, scale), rows, pal, flip=m.facing < 0, scale=scale)
        sx, sy = at(m.cx, m.y + m.h)
        sx -= spr.width // 2
        sy -= spr.height
        if m.pipe:
            # sink into / rise out of a pipe: hide the part inside it
            p = m.pipe
            if p['phase'] in ('in', 'up'):
                clip = at(0, p['top'])[1]
                h = clip - sy
                if h <= 0:
                    return
                spr = spr.crop((0, 0, spr.width, min(spr.height, h)))
            elif p['phase'] == 'down':
                clip = at(0, p['bottom'])[1]
                cut = clip - sy
                if cut >= spr.height:
                    return
                if cut > 0:
                    spr = spr.crop((0, cut, spr.width, spr.height))
                    sy += cut
        self.image.paste(spr, (sx, sy), spr)

    def draw_hud(self):
        d = self.draw
        f = self.font

        def txt(x, y, s, col=(255, 255, 255)):
            d.text((x + 1, y + 1), s, font=f, fill=(0, 0, 0))
            d.text((x, y), s, font=f, fill=col)

        head = self.sp.get('hud_m', SMALL['stand'])
        self.image.paste(head, (1, 1), head)
        txt(6, 0, 'x%d' % self.lives)
        coin = self.sp.get('coin', COIN)
        self.image.paste(coin, (22, 1), coin)
        txt(26, 0, 'x%02d' % self.coins)
        for i, got in enumerate(self.star_coins):
            x = 44 + i * 5
            if got:
                spr = self.sp.get('sc', STARCOIN)
                self.image.paste(spr, (x, 1), spr)
            else:
                d.rectangle((x, 1, x + 3, 4), outline=(90, 90, 90))
        s = '%07d' % self.score
        txt(150 - text_size(d, s, f)[0], 0, s)
        txt(160, 0, 'T%03d' % max(0, self.timer), (255, 90, 90) if self.timer < 100 else (255, 255, 255))

    def center_text(self, s, y, font, col):
        w, _ = text_size(self.draw, s, font)
        self.draw.text((W // 2 - w // 2, y), s, font=font, fill=col)
