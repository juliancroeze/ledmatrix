"""Load the BDF pixel fonts from the repo's fonts/ folder as Pillow fonts.

Pillow can't read .bdf directly, so the first time a font is used it is
converted to Pillow's .pil/.pbm format and cached in ~/.cache/ledmatrix-fonts.
"""
import os
import threading
from PIL import ImageFont, BdfFontFile

FONT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'fonts'))
CACHE_DIR = os.path.expanduser('~/.cache/ledmatrix-fonts')

_cache = {}
_lock = threading.Lock()


def font_path(name):
    return os.path.join(FONT_DIR, name + '.bdf')


def get_font(name='7x13'):
    font = _cache.get(name)
    if font is not None:
        return font
    with _lock:
        if name not in _cache:
            _cache[name] = _load(name)
    return _cache[name]


def _load(name):
    font = None
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        pil_path = os.path.join(CACHE_DIR, name + '.pil')
        if not os.path.exists(pil_path):
            with open(font_path(name), 'rb') as fp:
                BdfFontFile.BdfFontFile(fp).save(pil_path)
        font = ImageFont.load(pil_path)
    except Exception as e:
        print(f"Could not load font {name}: {e}")
        font = ImageFont.load_default()
    return font


def text_bbox(draw, text, font):
    """Bounding box of `text`. Works on old Pillow (no textbbox, < 8.0)
    and new Pillow (no textsize, >= 10)."""
    if hasattr(draw, 'textbbox'):
        try:
            return draw.textbbox((0, 0), text, font=font)
        except Exception:
            pass
    w, h = draw.textsize(text, font=font)
    return (0, 0, w, h)


def text_size(draw, text, font):
    box = text_bbox(draw, text, font)
    return box[2] - box[0], box[3] - box[1]
