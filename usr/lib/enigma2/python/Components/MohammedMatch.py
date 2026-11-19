# -*- coding: utf-8 -*-
# Football in the guide: finds "team A against team B" (and the competition) in a programme title and
# draws a card for it with the club badges, the club colours and the competition logo.
from __future__ import print_function
import hashlib
import json
import os
import re
import time
import zlib
from Components import MohammedSkinUtils as U

BASE = os.path.join(U.SKIN_DIR, 'football')
_K = b'M0h@mmedSk1n'
_TASHKEEL = re.compile(u'[ً-ْـٰ]')
_ARABIC = re.compile(u'[؀-ۿ]')
_SPORT_CH = re.compile(u'sport|ssc|bein|ad sport|alkass|al kass|dubai sport|abu dhabi sport|sky sport|sharjah sport|ksa sport|رياض|رياضي', re.I)
_VERSUS = re.compile(u'(?:\\s|^)(?:vs?\\.?|x|×|ضد|-|–|—|:)(?:\\s|$)|مباراه|مواجهه|مباراة|\\blive\\b|مباشر|\\bmatch\\b|ديربي|كلاسيكو|derby|clasico', re.I)
_db = {}


def _norm(s):
    s = _TASHKEEL.sub(u'', s)
    for a, b in ((u'أ', u'ا'), (u'إ', u'ا'), (u'آ', u'ا'), (u'ٱ', u'ا'), (u'ة', u'ه'), (u'ى', u'ي')):
        s = s.replace(a, b)
    return re.sub(u'\\s+', u' ', s).strip()


def _u(s):
    if s is None:
        return u''
    try:
        return s.decode('utf-8', 'ignore')
    except AttributeError:
        return s


def _alt(names):
    return u'|'.join(re.escape(n) for n in sorted(set(names), key=len, reverse=True) if n)


def data():
    if _db:
        return _db
    try:
        blob = bytearray(open(os.path.join(BASE, 'data.bin'), 'rb').read())
        for i in range(len(blob)):
            blob[i] ^= bytearray(_K)[i % len(_K)]
        d = json.loads(zlib.decompress(bytes(blob)).decode('utf-8'))
    except Exception as e:
        print('[MohammedSkin] football data: %s' % e)
        _db['bad'] = True
        return _db
    alias, cs = {}, {}
    for key, t in d['teams'].items():
        for n in t['ar'] + t['en']:
            alias.setdefault(n, []).append(key)
        for n in t.get('cs') or []:
            cs.setdefault(n, []).append(key)
    calias = {}
    for code, c in d['comps'].items():
        for n in c['ar'] + c['en']:
            calias.setdefault(n, code)
    # Arabic names may carry a joined "و" (and): "الهلال والنصر"
    _db['teams'] = d['teams']
    _db['comps'] = d['comps']
    _db['alias'] = alias
    _db['csalias'] = cs
    _db['calias'] = calias
    _db['tre'] = re.compile(u'(?<!\\w)(?:و(?=ال))?(%s)(?!\\w)' % _alt(alias.keys()), re.I | re.U)
    _db['csre'] = re.compile(u'(?<!\\w)(%s)(?!\\w)' % _alt(cs.keys()), re.U) if cs else None
    _db['cre'] = re.compile(u'(?<!\\w)(%s)(?!\\w)' % _alt(calias.keys()), re.I | re.U)
    return _db


def _pick(cands_a, cands_b):
    # "الأهلي" or "الوحدة" can be more than one club: take the pair that plays in the same league
    teams = _db['teams']
    best = None
    for a in cands_a:
        for b in cands_b:
            if a == b:
                continue
            score = 2 if teams[a]['lg'] == teams[b]['lg'] else 0
            if best is None or score > best[0]:
                best = (score, a, b)
    return best and best[1:]


def find(title, desc=u'', genre=None, chname=u''):
    """{'a': key, 'b': key, 'comp': code or None, 'ar': bool} for a football match, {'comp': code} for a
    competition programme without the two clubs, or None."""
    if not U.settings().get('matches', True):
        return None
    db = data()
    if db.get('bad'):
        return None
    title = _u(title)
    if not title:
        return None
    t = _norm(title)
    comp = None
    m = db['cre'].search(t)
    if m:
        comp = db['calias'].get(m.group(1).lower()) or db['calias'].get(m.group(1))
        t = t[:m.start()] + u' | ' + t[m.end():]  # "كأس الاتحاد الإنجليزي" is no club called الاتحاد
    elif desc:
        dm = db['cre'].search(_norm(_u(desc))[:240])
        if dm:
            comp = db['calias'].get(dm.group(1).lower()) or db['calias'].get(dm.group(1))
    found = []
    spans = []
    for m in db['tre'].finditer(t):
        k = db['alias'].get(m.group(1)) or db['alias'].get(m.group(1).lower())
        if k:
            found.append((m.start(), k))
            spans.append((m.start(), m.end()))
    if db.get('csre') is not None:
        for m in db['csre'].finditer(_TASHKEEL.sub(u'', title)):
            k = db['csalias'].get(m.group(1))
            if k and not any(s <= m.start() < e for s, e in spans):
                found.append((m.start(), k))
    found.sort()
    sport = genre == 4 or bool(_SPORT_CH.search(_u(chname))) or comp is not None
    ar = bool(_ARABIC.search(title))
    if len(found) >= 2:
        if not (sport or _VERSUS.search(t)):
            return None
        pair = _pick(found[0][1], found[1][1])
        if pair:
            a, b = pair
            if comp is None:
                la, lb = db['teams'][a]['lg'], db['teams'][b]['lg']
                if la == lb and la in db['comps']:
                    comp = la
            return {'a': a, 'b': b, 'comp': comp, 'ar': ar}
    if comp is not None and (genre == 4 or _SPORT_CH.search(_u(chname)) or _VERSUS.search(t)):
        return {'comp': comp, 'ar': ar}
    return None


def find_event(event, chname=u''):
    if event is None:
        return None
    try:
        name = event.getEventName() or ''
        desc = event.getShortDescription() or ''
        begin, length = event.getBeginTime(), event.getDuration()
    except Exception:
        return None
    try:
        genre = U.event_genre(event)
    except Exception:
        genre = None
    m = find(name, desc, genre, chname)
    if m:
        m['begin'], m['length'] = begin or 0, length or 0
    return m

# ------------------------------------------------------------------ the card


def _text(d, xy, s, font, fill, anchor='mm'):
    try:
        d.text(xy, s, font=font, fill=fill, anchor=anchor)
    except Exception:  # an old picture library without anchors
        try:
            w, h = d.textsize(s, font=font)
        except Exception:
            w, h = len(s) * 10, 20
        x, y = xy
        if anchor[0] == 'm':
            x -= w / 2
        if anchor[1] == 'm':
            y -= h / 2
        d.text((x, y), s, font=font, fill=fill)


def _tlen(s, font):
    from PIL import Image, ImageDraw
    d = ImageDraw.Draw(Image.new('L', (4, 4)))
    try:
        return d.textlength(s, font=font)
    except Exception:
        return d.textsize(s, font=font)[0]


def _rgb(h, fb=(40, 44, 60)):
    try:
        h = (h or '').lstrip('#')
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:
        return fb


def _mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _font(n, bold=True):
    from PIL import ImageFont
    for f in (('moh-semibold.otf', 'moh-title.otf') if bold else ('moh-regular.otf',)):
        p = os.path.join(U.SKIN_DIR, 'fonts', f)
        if os.path.isfile(p):
            try:
                return ImageFont.truetype(p, n)
            except Exception:
                pass
    return ImageFont.load_default()


def _team_color(t):
    c = _rgb(t.get('c1'))
    if max(c) < 60:  # a black club colour: lift it so the half still reads as a colour
        c = _mix(c, (90, 96, 110), .5)
    return c


def _badge(key, size):
    from PIL import Image, ImageDraw, ImageFilter
    t = _db['teams'][key]
    p = os.path.join(BASE, 't', '%s.png' % key)
    out = Image.new('RGBA', (size + 40, size + 40), (0, 0, 0, 0))
    if t.get('b') and os.path.isfile(p):
        im = Image.open(p).convert('RGBA')
        im.thumbnail((size, size), Image.LANCZOS)
    else:  # no badge in the pack: the club's colour with its initials
        im = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        c = _team_color(t)
        d.ellipse((2, 2, size - 3, size - 3), fill=c + (255,), outline=(255, 255, 255, 230), width=max(2, size // 30))
        ini = u''.join(w[0] for w in re.sub(u'^(Al|Al-|FC|SC|AS)\\s+', u'', t['name']).split()[:2]).upper()
        _text(d, (size / 2, size / 2), ini, _font(int(size * .36)), (255, 255, 255))
    # a soft light behind, so dark badges (black, navy) still stand out
    glow = Image.new('RGBA', out.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    cx, cy = out.size[0] // 2, out.size[1] // 2
    r = int(size * .46)
    gd.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255, 70))
    out.alpha_composite(glow.filter(ImageFilter.GaussianBlur(max(4, size // 7))))
    sh = Image.new('RGBA', out.size, (0, 0, 0, 0))
    sh.paste((0, 0, 0, 150), ((out.size[0] - im.size[0]) // 2, (out.size[1] - im.size[1]) // 2 + 4), im.getchannel('A'))
    out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(5)))
    out.alpha_composite(im, ((out.size[0] - im.size[0]) // 2, (out.size[1] - im.size[1]) // 2))
    return out


def _vs(s):
    from PIL import Image, ImageDraw, ImageFilter
    im = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    g = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse((s * .1, s * .1, s * .9, s * .9), fill=(255, 255, 255, 110))
    im.alpha_composite(g.filter(ImageFilter.GaussianBlur(max(2, s // 10))))
    d = ImageDraw.Draw(im)
    d.ellipse((s * .16, s * .16, s * .84, s * .84), fill=(10, 10, 14, 240), outline=(255, 255, 255, 235), width=max(2, s // 28))
    _text(d, (s * .5, s * .5), 'VS', _font(int(s * .27)), (255, 255, 255))
    return im


def _label(img_key, text_en, ar, height, maxw):
    """the picture of a name: Arabic ones come ready made (this receiver's picture library may not join
    Arabic letters), English ones are written here."""
    from PIL import Image, ImageDraw
    if ar:
        p = os.path.join(BASE, 'n', '%s.png' % img_key)
        if os.path.isfile(p):
            im = Image.open(p).convert('RGBA')
            s = min(float(height) / im.size[1], float(maxw) / im.size[0])
            return im.resize((max(1, int(im.size[0] * s)), max(1, int(im.size[1] * s))), Image.LANCZOS)
    f = _font(height)
    n = height
    while n > 10:
        f = _font(n)
        if _tlen(text_en, f) <= maxw:
            break
        n -= 2
    w = int(_tlen(text_en, f)) + 4
    im = Image.new('RGBA', (max(4, w), int(n * 1.35)), (0, 0, 0, 0))
    _text(ImageDraw.Draw(im), (2, im.size[1] // 2), text_en, f, (255, 255, 255), 'lm')
    return im


def _put(base, im, cx, cy, shadow=True):
    from PIL import Image, ImageFilter
    x, y = int(cx - im.size[0] / 2), int(cy - im.size[1] / 2)
    if shadow:
        sh = Image.new('RGBA', base.size, (0, 0, 0, 0))
        sh.paste((0, 0, 0, 200), (x + 2, y + 3), im.getchannel('A'))
        base.alpha_composite(sh.filter(ImageFilter.GaussianBlur(4)))
    base.alpha_composite(im, (x, y))


def _when(m):
    b, ln = m.get('begin') or 0, m.get('length') or 0
    if not b:
        return False, u''
    now = time.time()
    return (b <= now < b + max(ln, 60)), time.strftime('%H:%M', time.localtime(b))


def _pill(m, ar, h):
    from PIL import Image, ImageDraw
    live, hm = _when(m)
    if not hm:
        return None
    f = _font(int(h * .5))
    parts = []
    if live:
        parts.append(_label('live', 'LIVE', ar, int(h * .5), 400))
    parts.append(_label('', hm, False, int(h * .5), 400))
    w = sum(p.size[0] for p in parts) + int(h * .35) * (len(parts) - 1) + int(h * 1.0)
    try:
        acc = U._theme_rgb('accent', '#D3162E')
    except Exception:
        acc = (211, 22, 46)
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, w - 1, h - 1), h // 2, fill=(acc if live else (20, 20, 26)) + (240,), outline=(255, 255, 255, 90 if live else 70), width=1)
    x = int(h * .5)
    seq = list(reversed(parts)) if ar else parts
    for p in seq:
        im.alpha_composite(p, (x, (h - p.size[1]) // 2))
        x += p.size[0] + int(h * .35)
    return im


def _split(w, h, ca, cb, slope):
    from PIL import Image, ImageDraw, ImageFilter
    a = U._vgrad(w, h, _mix(ca, (0, 0, 0), .25) + (255,), _mix(ca, (0, 0, 0), .82) + (255,))
    b = U._vgrad(w, h, _mix(cb, (0, 0, 0), .25) + (255,), _mix(cb, (0, 0, 0), .82) + (255,))
    m = Image.new('L', (w, h), 0)
    ImageDraw.Draw(m).polygon([(w * (.5 + slope), 0), (w, 0), (w, h), (w * (.5 - slope), h)], fill=255)
    a.paste(b, (0, 0), m)
    seam = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(seam).line([(w * (.5 + slope), 0), (w * (.5 - slope), h)], fill=(255, 255, 255, 190), width=max(2, w // 220))
    a.alpha_composite(seam.filter(ImageFilter.GaussianBlur(max(2, w // 120))))
    a.alpha_composite(seam)
    return a


def _shade(im, top=0.0, bottom=.92, start=.55):
    from PIL import Image
    w, h = im.size
    a = Image.new('L', (1, h))
    for y in range(h):
        t = y / float(max(1, h - 1))
        v = 0 if t < start else (t - start) / (1 - start)
        a.putpixel((0, y), int(255 * bottom * v ** .9))
    lay = Image.new('RGBA', (w, h), (0, 0, 0, 255))
    lay.putalpha(a.resize((w, h)))
    im.alpha_composite(lay)


def _watermark(im, comp, size, alpha, cy=None):
    from PIL import Image
    if not comp or not _db['comps'].get(comp, {}).get('logo'):
        return
    p = os.path.join(BASE, 'c', '%s.png' % comp)
    if not os.path.isfile(p):
        return
    lg = Image.open(p).convert('RGBA')
    lg.thumbnail((size, size), Image.LANCZOS)
    lg.putalpha(lg.getchannel('A').point(lambda v: int(v * alpha)))
    im.alpha_composite(lg, ((im.size[0] - lg.size[0]) // 2, int((cy if cy is not None else im.size[1] / 2) - lg.size[1] / 2)))


def _comp_line(comp, ar, h, maxw):
    """small competition logo + its name"""
    from PIL import Image
    if not comp:
        return None
    c = _db['comps'].get(comp) or {}
    name = _label('c_' + comp, c.get('name', ''), ar, int(h * .62), maxw - h - 12)
    logo = None
    p = os.path.join(BASE, 'c', '%s.png' % comp)
    if c.get('logo') and os.path.isfile(p):
        logo = Image.open(p).convert('RGBA')
        logo.thumbnail((h, h), Image.LANCZOS)
    w = name.size[0] + ((logo.size[0] + 12) if logo else 0)
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    parts = [logo, name] if not ar else [name, logo]
    x = 0
    for p in parts:
        if p is None:
            continue
        im.alpha_composite(p, (x, (h - p.size[1]) // 2))
        x += p.size[0] + 12
    return im


def _round(im, r):
    from PIL import Image, ImageDraw
    m = Image.new('L', im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, im.size[0] - 1, im.size[1] - 1), r, fill=255)
    out = Image.new('RGBA', im.size, (0, 0, 0, 0))
    out.paste(im, (0, 0), m)
    return out


def _names(m, side):
    t = _db['teams'][m[side]]
    return m[side], t['name']


def make(m, shape, w, h):
    """draw the card: shape = poster (tall), wide or row. Returns the picture path."""
    from PIL import Image
    data()
    live, hm = _when(m)
    sig = json.dumps([m.get('a'), m.get('b'), m.get('comp'), m.get('ar'), shape, w, h, live, hm, 3])
    out = os.path.join(U.CACHE_DIR, 'mc_%s.png' % hashlib.md5(sig.encode('utf-8')).hexdigest()[:16])
    if os.path.isfile(out):
        return out
    ar = m.get('ar')
    comp = m.get('comp')
    if 'a' not in m:  # a competition without the two clubs: its logo, big
        im = U._vgrad(w, h, (26, 28, 36, 255), (6, 6, 9, 255))
        if shape == 'row':
            _watermark(im, comp, int(h * .8), .9, h / 2)
        else:
            _watermark(im, comp, int(min(w, h) * .62), .95, h * (.42 if shape == 'poster' else .44))
            line = _label('c_' + comp, (_db['comps'].get(comp) or {}).get('name', ''), ar, int(h * (.06 if shape == 'poster' else .075)), int(w * .9))
            _put(im, line, w / 2, h * (.8 if shape == 'poster' else .82))
            pill = _pill(m, ar, int(h * (.075 if shape == 'poster' else .085)))
            if pill:
                _put(im, pill, w / 2, h * .91, False)
    else:
        ta, tb = _db['teams'][m['a']], _db['teams'][m['b']]
        ca, cb = _team_color(ta), _team_color(tb)
        if ar:  # Arabic reads right to left: the first club on the right
            ca, cb = cb, ca
            left, right = m['b'], m['a']
        else:
            left, right = m['a'], m['b']
        if shape == 'row':
            im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
            free = 150  # the list draws the programme progress bar at the right end
            band = _split(int(w * .52), h, ca, cb, .08)
            fade = Image.new('L', band.size)
            bw = band.size[0]
            for x in range(bw):
                fade.paste(int(235 * min(1.0, x / (bw * .45), (bw - x) / (bw * .2))), (x, 0, x + 1, h))
            band.putalpha(fade)
            bx = w - bw - free
            im.alpha_composite(band, (bx, 0))
            bs = int(h * .78)
            _put(im, _badge(left, bs), bx + bw * .36, h / 2, False)
            _put(im, _badge(right, bs), bx + bw * .64, h / 2, False)
            _put(im, _vs(int(h * .5)), bx + bw * .5, h / 2, False)
        else:
            wide = shape == 'wide'
            im = _split(w, h, ca, cb, .07 if wide else .12)
            _watermark(im, comp, int(min(w, h) * (.78 if wide else .7)), .16, h * .44)
            _shade(im, bottom=.95, start=.5)
            top = Image.new('RGBA', (w, int(h * (.11 if wide else .1))), (0, 0, 0, 110))
            im.alpha_composite(top)
            line = _comp_line(comp, ar, int(top.size[1] * .76), int(w * .9))
            if line:
                _put(im, line, w / 2, top.size[1] / 2, False)
            cy = h * (.42 if wide else .47)
            bs = int(min(w * (.24 if wide else .36), h * (.38 if wide else .26)))
            xs = (.28, .72) if wide else (.25, .75)
            _put(im, _badge(left, bs), w * xs[0], cy, False)
            _put(im, _badge(right, bs), w * xs[1], cy, False)
            _put(im, _vs(int(bs * .62)), w / 2, cy, False)
            nh = int(h * (.075 if wide else .058))
            for side, x in ((left, xs[0]), (right, xs[1])):
                t = _db['teams'][side]
                lab = _label(side, t['name'], ar, nh, int(w * (.4 if wide else .46)))
                _put(im, lab, w * x, cy + bs * .5 + nh * 1.15)
            pill = _pill(m, ar, int(h * (.085 if wide else .062)))
            if pill:
                _put(im, pill, w / 2, h * (.87 if wide else .9), False)
        if shape != 'row':
            im = _round(im, max(8, min(w, h) // 30))
    tmp = out + '.part'
    im.save(tmp, 'PNG')
    os.rename(tmp, out)
    return out


_busy = {}


def make_async(m, shape, w, h, callback):
    """the picture if it is made already, else None and callback(path) when it is ready"""
    data()
    live, hm = _when(m)
    sig = json.dumps([m.get('a'), m.get('b'), m.get('comp'), m.get('ar'), shape, w, h, live, hm, 3])
    out = os.path.join(U.CACHE_DIR, 'mc_%s.png' % hashlib.md5(sig.encode('utf-8')).hexdigest()[:16])
    if os.path.isfile(out):
        return out
    if out in _busy:
        _busy[out].append(callback)
        return None
    _busy[out] = [callback]

    def work():
        try:
            return make(m, shape, w, h)
        except Exception as e:
            print('[MohammedSkin] match card: %s' % e)
            return None

    def done(path):
        for cb in _busy.pop(out, []):
            try:
                cb(path)
            except Exception:
                pass
    U.in_background(work, done)
    return None
