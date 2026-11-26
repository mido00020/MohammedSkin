# -*- coding: utf-8 -*-
# Football in the guide: finds "team A against team B" (and the competition) in a programme title and
# draws a card for it with the club badges, the club colours and the competition logo.
from __future__ import print_function
import hashlib
import json
import os
import re
import threading
import time
import zlib
from Components import MohammedSkinUtils as U

BASE = os.path.join(U.SKIN_DIR, 'football')
_K = b'M0h@mmedSk1n'
_TASHKEEL = re.compile(u'[ً-ْـٰ]')
_ARABIC = re.compile(u'[؀-ۿ]')
_SPORT_CH = re.compile(u'sport|ssc|bein|ad sport|alkass|al kass|dubai sport|abu dhabi sport|sky sport|sharjah sport|ksa sport|رياض|رياضي', re.I)
_OTHER_SPORT = re.compile(u'تنس|كره السله|لكره السله|الكره الطائره|كره الطائره|الطائره الشاطئيه|كره اليد|كره الصالات|الهوكي|الرغبي|'
                          u'كره الماء|كره القدم الامريكيه|الدوري الاميركي لكره|الدوري الامريكي لكره|\\btennis\\b|basketball|volleyball|'
                          u'handball|futsal|\\bnba\\b|\\bnfl\\b|hockey|rugby|snooker|darts|boxing|\\bufc\\b|\\bmma\\b|padel|golf|cricket|\\bwwe\\b|formula|motogp|'
                          u'سنوكر|السهام|ملاكمه|المصارعه|مصارعه|بادل|جولف|الغولف|كريكيت|فورمولا|الفنون القتاليه', re.I)
_VERSUS = re.compile(u'(?:\\s|^)(?:vs?\\.?|x|×|ضد|-|–|—|:)(?:\\s|$)|مباراه|مواجهه|مباراة|\\blive\\b|مباشر|\\bmatch\\b|ديربي|كلاسيكو|derby|clasico', re.I)
_LIVE = re.compile(u'^(?:مباشر|انتهت|live|ft)\\b[^:]{0,24}:\\s*', re.I)
_SCORE = re.compile(u'\\s+\\d{1,2}\\s*[-–]\\s*\\d{1,2}\\s+')
_db = {}
_dlock = threading.RLock()


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
    with _dlock:
        return _data()


def _data():
    if _db:
        return _db
    try:
        blob = bytearray(open(os.path.join(BASE, 'data.bin'), 'rb').read())
        kb = bytearray(_K)
        for i in range(len(blob)):
            blob[i] ^= kb[i % len(kb)]
        d = json.loads(zlib.decompress(bytes(blob)).decode('utf-8'))
    except Exception as e:
        print('[MohammedSkin] football data: %s' % e)
        _db['bad'] = True
        return _db
    db = {}
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
    db['teams'] = d['teams']
    db['comps'] = d['comps']
    db['alias'] = alias
    db['csalias'] = cs
    db['calias'] = calias
    db['tre'] = re.compile(u'(?<!\\w)(?:و(?=ال))?(%s)(?!\\w)' % _alt(alias.keys()), re.I | re.U)
    db['csre'] = re.compile(u'(?<!\\w)(%s)(?!\\w)' % _alt(cs.keys()), re.U) if cs else None
    db['cre'] = re.compile(u'(?<!\\w)(%s)(?!\\w)' % _alt(calias.keys()), re.I | re.U)
    _db.update(db)  # all at once: another thread never sees half of it
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
    live = _LIVE.match(title)       # a match followed live in the guide: 'مباشر 67': A 2 - 0 B' / 'انتهت: A 2 - 1 B'
    if live:
        title = title[live.end():]
    title = _SCORE.sub(u' × ', title)
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
    if _OTHER_SPORT.search(t):  # tennis, basketball, volleyball ... between two countries is no football match
        return None
    sport = genre == 4 or bool(live) or bool(_SPORT_CH.search(_u(chname))) or comp is not None
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
    if sport:
        pair = _unknown_pair(title, t, comp, found)
        if pair:
            return {'a': pair[0], 'b': pair[1], 'comp': comp, 'ar': ar}
    if comp is not None and (genre == 4 or _SPORT_CH.search(_u(chname)) or _VERSUS.search(t)):
        return {'comp': comp, 'ar': ar}
    return None


_SEG = re.compile(u'\\s*(?:·|•|\\||،|\\s[-–—]\\s|:)\\s*')
_PAIR = re.compile(u'^(.{2,40}?)\\s+(?:vs\\.?|v|x|×|ضد)\\s+(.{2,40}?)$', re.I)
_FOOT = re.compile(u'دوري|كاس|بطوله|تصفيات|كره القدم|league|liga|ligue|\\bcup\\b|copa|coppa|pokal|football|soccer|'
                   u'premier|serie a|bundesliga|eredivisie|championship|uefa|fifa|\\bcaf\\b|\\bafc\\b', re.I)
_LEAD = re.compile(u'^(?:مباشر|حصري|مباراه|مباراة|live|en vivo|direct)\\s*', re.I)
_NOT_NAME = re.compile(u'\\d{3,}|الحلقه|episode|season|\\bs\\d|\\be\\d|موسم|برنامج|ملخص|استوديو|studio|highlights', re.I)
_PALETTE = ('1e5fbf', 'b8202f', '1f8a4c', '6a2ca0', 'd07a12', '0f7f8c', '8c1f5a', '3d4a63', 'a3912a', '2a6f3a')


def _unknown_pair(title, t, comp, found):
    """'X × Y' on a sports channel, X or Y not in the pack: a card with their names (first letters
    in a circle of a colour of their own). Only for football: other sports are left out before."""
    if not (comp is not None or found or _FOOT.search(t)):
        return None
    for seg in _SEG.split(_TASHKEEL.sub(u'', title)):
        seg = _LEAD.sub(u'', seg.strip())
        m = _PAIR.match(seg)
        if not m:
            continue
        sides = []
        for raw in (m.group(1).strip(), m.group(2).strip()):
            if _NOT_NAME.search(raw) or len(raw.split()) > 4:
                return None
            n = _norm(raw)
            k = None
            for hit in _db['tre'].finditer(n):  # a known club on this side
                k = _db['alias'].get(hit.group(1)) or _db['alias'].get(hit.group(1).lower())
                if isinstance(k, (list, tuple)):  # one name, several clubs: the one of this competition
                    k = ([x for x in k if comp and _db['teams'][x].get('lg') == comp] or list(k))[0] if k else None
                if k:
                    break
            if not k:
                k = u'x:' + raw
                if k not in _db['teams']:
                    if len(_db['teams']) > 2000:
                        return None
                    h = sum(ord(c) for c in raw)
                    _db['teams'][k] = {'name': raw, 'ar': [], 'en': [], 'cs': [], 'c1': _PALETTE[h % len(_PALETTE)],
                                       'c2': None, 'b': False, 'lg': 'x'}
            sides.append(k)
        if sides[0] != sides[1]:
            return sides
    return None


_fe = {}


def preload():
    """read the football data in the background at start: the first match is no longer waited for"""
    try:
        if U.settings().get('matches', True):
            U.in_background(data, lambda r: None)
    except Exception:
        pass


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
    # the same programme is asked for again and again (every redraw of the list): answered once
    ck = (name, desc[:240], genre, chname, begin, bool(U.settings().get('matches', True)))
    if ck in _fe:
        m = _fe[ck]
        return dict(m) if m else None
    m = find(name, desc, genre, chname)
    if m:
        m['begin'], m['length'] = begin or 0, length or 0
    if len(_fe) > 600:
        _fe.clear()
    _fe[ck] = m
    return dict(m) if m else None


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
        nm = re.sub(u'^(Al|Al-|FC|SC|AS)\\s+', u'', t['name'])
        if _ARABIC.search(nm):
            nm = re.sub(u'^ال', u'', nm.split()[0]) or nm
            _text(d, (size / 2, size / 2), nm[0], _arfont(int(size * .44)), (255, 255, 255))
        else:
            ini = u''.join(w[0] for w in nm.split()[:2]).upper()
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


_FORMS = {
    u'\u0621': (0xFE80,), u'\u0622': (0xFE81, 0xFE82), u'\u0623': (0xFE83, 0xFE84), u'\u0624': (0xFE85, 0xFE86),
    u'\u0625': (0xFE87, 0xFE88), u'\u0626': (0xFE89, 0xFE8A, 0xFE8B, 0xFE8C), u'\u0627': (0xFE8D, 0xFE8E),
    u'\u0628': (0xFE8F, 0xFE90, 0xFE91, 0xFE92), u'\u0629': (0xFE93, 0xFE94), u'\u062A': (0xFE95, 0xFE96, 0xFE97, 0xFE98),
    u'\u062B': (0xFE99, 0xFE9A, 0xFE9B, 0xFE9C), u'\u062C': (0xFE9D, 0xFE9E, 0xFE9F, 0xFEA0), u'\u062D': (0xFEA1, 0xFEA2, 0xFEA3, 0xFEA4),
    u'\u062E': (0xFEA5, 0xFEA6, 0xFEA7, 0xFEA8), u'\u062F': (0xFEA9, 0xFEAA), u'\u0630': (0xFEAB, 0xFEAC), u'\u0631': (0xFEAD, 0xFEAE),
    u'\u0632': (0xFEAF, 0xFEB0), u'\u0633': (0xFEB1, 0xFEB2, 0xFEB3, 0xFEB4), u'\u0634': (0xFEB5, 0xFEB6, 0xFEB7, 0xFEB8),
    u'\u0635': (0xFEB9, 0xFEBA, 0xFEBB, 0xFEBC), u'\u0636': (0xFEBD, 0xFEBE, 0xFEBF, 0xFEC0), u'\u0637': (0xFEC1, 0xFEC2, 0xFEC3, 0xFEC4),
    u'\u0638': (0xFEC5, 0xFEC6, 0xFEC7, 0xFEC8), u'\u0639': (0xFEC9, 0xFECA, 0xFECB, 0xFECC), u'\u063A': (0xFECD, 0xFECE, 0xFECF, 0xFED0),
    u'\u0641': (0xFED1, 0xFED2, 0xFED3, 0xFED4), u'\u0642': (0xFED5, 0xFED6, 0xFED7, 0xFED8), u'\u0643': (0xFED9, 0xFEDA, 0xFEDB, 0xFEDC),
    u'\u0644': (0xFEDD, 0xFEDE, 0xFEDF, 0xFEE0), u'\u0645': (0xFEE1, 0xFEE2, 0xFEE3, 0xFEE4), u'\u0646': (0xFEE5, 0xFEE6, 0xFEE7, 0xFEE8),
    u'\u0647': (0xFEE9, 0xFEEA, 0xFEEB, 0xFEEC), u'\u0648': (0xFEED, 0xFEEE), u'\u0649': (0xFEEF, 0xFEF0),
    u'\u064A': (0xFEF1, 0xFEF2, 0xFEF3, 0xFEF4)}
_LAMALEF = {u'\u0622': (0xFEF5, 0xFEF6), u'\u0623': (0xFEF7, 0xFEF8), u'\u0625': (0xFEF9, 0xFEFA), u'\u0627': (0xFEFB, 0xFEFC)}


def _shape(s):
    """Arabic letters joined by hand (for a picture library without text shaping), in display order"""
    s = _TASHKEEL.sub(u'', _u(s))
    out = []
    i = 0
    joins = lambda c: c in _FORMS and len(_FORMS[c]) == 4
    while i < len(s):
        c = s[i]
        prev = s[i - 1] if i else u''
        after = joins(prev)
        if c == u'\u0644' and i + 1 < len(s) and s[i + 1] in _LAMALEF:
            out.append(unichr_(_LAMALEF[s[i + 1]][1 if after else 0]))
            i += 2
            continue
        f = _FORMS.get(c)
        if not f:
            out.append(c)
            i += 1
            continue
        nxt = s[i + 1] if i + 1 < len(s) else u''
        before = len(f) == 4 and nxt in _FORMS
        if len(f) == 1:
            g = f[0]
        elif after and before:
            g = f[3]
        elif after:
            g = f[1]
        elif before:
            g = f[2]
        else:
            g = f[0]
        out.append(unichr_(g))
        i += 1
    return u''.join(reversed(out))


def unichr_(n):
    try:
        return unichr(n)
    except NameError:
        return chr(n)


def _arfont(n):
    from PIL import ImageFont
    for f in ('moh-arabic.ttf', 'ar-title.ttf'):
        p = os.path.join(U.SKIN_DIR, 'fonts', f)
        if os.path.isfile(p):
            try:
                return ImageFont.truetype(p, n)
            except Exception:
                pass
    return _font(n)


def _ar_label(text, height, maxw):
    from PIL import Image, ImageDraw
    try:
        raqm = U._raqm()
    except Exception:
        raqm = False
    shown = text if raqm else _shape(text)
    n = height
    while True:
        f = _arfont(n)
        d = ImageDraw.Draw(Image.new('L', (4, 4)))
        try:
            bb = d.textbbox((0, 0), shown, font=f, direction='rtl') if raqm else d.textbbox((0, 0), shown, font=f)
        except Exception:
            w0, h0 = d.textsize(shown, font=f)
            bb = (0, 0, w0, h0)
        if bb[2] - bb[0] <= maxw or n <= 12:
            break
        n -= 2
    im = Image.new('RGBA', (bb[2] - bb[0] + 8, bb[3] - bb[1] + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if raqm:
        d.text((4 - bb[0], 4 - bb[1]), shown, font=f, fill=(255, 255, 255), direction='rtl')
    else:
        d.text((4 - bb[0], 4 - bb[1]), shown, font=f, fill=(255, 255, 255))
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
    if _ARABIC.search(text_en):
        return _ar_label(text_en, height, maxw)
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

# ---- players (only with the user's own key, after the pledge; nothing is built in) ----
_AF_FILE = '/etc/enigma2/MohammedSkin.af.json'
_AF_HOST = 'https://v3.football.api-sports.io'
_af = {}


def _af_key():
    try:
        return U.user_key('apifootball')
    except Exception:
        return ''


def players_on():
    return bool(_af_key())


def _af_load():
    if not _af:
        try:
            with open(_AF_FILE) as f:
                _af.update(json.load(f))
        except Exception:
            pass
        if _af.get('v') != 2:  # clubs looked up by an older version: look them up again
            _af.clear()
            _af['v'] = 2
        _af.setdefault('ids', {})
        _af.setdefault('sq', {})
    return _af


def _af_save():
    try:
        tmp = _AF_FILE + '.part'
        with open(tmp, 'w') as f:
            json.dump(_af, f, separators=(',', ':'))
        os.rename(tmp, _AF_FILE)
    except Exception as e:
        print('[MohammedSkin] players file: %s' % e)


_af_last = [0.0]


def _af_get(path):
    k = _af_key()
    if not k:
        return None
    with _af_lock:
        for _ in range(3):
            wait = 6.5 - (time.time() - _af_last[0])  # the free plan takes 10 questions a minute
            if wait > 0:
                time.sleep(wait)
            _af_last[0] = time.time()
            d = U.get_json(_AF_HOST + path, {'x-apisports-key': k}, 12)
            if not isinstance(d, dict):
                return None
            err = d.get('errors')
            if err and 'rateLimit' in (err if isinstance(err, dict) else {}):
                time.sleep(20)
                continue
            if err:
                print('[MohammedSkin] players: %s' % (err,))
                return None
            return d.get('response')
    return None


try:
    import threading as _th
    _af_lock = _th.Lock()
except Exception:
    _af_lock = None


_YOUTH = re.compile(r'\b(?:U\d\d|W|II|B|Reserves?|Youth|Women)\b', re.I)


def _af_team(key):
    """the id of a club on the players service (looked up once, then kept)"""
    st = _af_load()
    hit = st['ids'].get(key)
    if hit is not None and (hit or time.time() - st.get('miss_' + key, 0) < 3 * 86400):
        return hit
    t = _db['teams'][key]

    def ascii_name(n):
        try:
            import unicodedata
            n = unicodedata.normalize('NFKD', _u(n)).encode('ascii', 'ignore').decode('ascii')
        except Exception:
            pass
        return re.sub(r'\s+', ' ', re.sub(r'[^0-9A-Za-z ]+', ' ', n)).strip()
    name = ascii_name(t['name'])
    nat = t.get('lg') == 'nat'
    co = (t.get('co') or '').lower().replace('-', ' ')
    qs = [name]
    for alt in [ascii_name(x) for x in t.get('en') or []]:
        if alt and alt.lower() not in [q.lower() for q in qs] and len(qs) < 3:
            qs.append(alt)
    words = [x for x in name.split() if x.lower() not in ('al', 'fc', 'sc', 'cf', 'club', 'de', 'ac', 'as', 'cd')]
    if words and max(words, key=len).lower() not in [q.lower() for q in qs]:
        qs.append(max(words, key=len))
    best, score, asked = 0, -1, False
    for q in qs:
        if len(q) < 3:
            continue
        res = _af_get('/teams?search=' + q.replace(' ', '%20'))
        if res is None:  # no network or the day is used up: try again later, keep nothing
            return 0
        asked = True
        for r in res:
            tm = r.get('team') or {}
            n = tm.get('name') or ''
            if _YOUTH.search(n):
                continue
            if co:
                if tm.get('national') or (tm.get('country') or '').lower().replace('-', ' ') != co:
                    continue
            elif nat and not tm.get('national'):
                continue
            sc = 2 if bool(tm.get('national')) == nat else 1
            nn, tn = n.lower().replace('-', ' '), t['name'].lower().replace('-', ' ')
            if nn == tn:
                sc += 5
            elif nn in [x.lower().replace('-', ' ') for x in t.get('en') or []]:
                sc += 4
            elif nn in tn or tn in nn:
                sc += 3
            if sc > score:
                best, score = tm.get('id') or 0, sc
        if best:
            break
    if not asked:
        return 0
    st['ids'][key] = best
    if not best:
        st['miss_' + key] = time.time()
    _af_save()
    return best


_STAR = (10, 9, 7, 11, 8, 19, 17, 14, 20, 21, 22, 6)


def _af_star(tid):
    """the club's best known attacking player (from the current squad, kept a week)"""
    st = _af_load()
    c = st['sq'].get(str(tid))
    if c and time.time() - c.get('t', 0) < 7 * 86400:
        return c.get('p')
    res = _af_get('/players/squads?team=%d' % tid)
    if res is None:
        return c.get('p') if c else None
    pl = (res[0].get('players') if res else None) or []
    pos = {'Attacker': 0, 'Midfielder': 1}
    cands = [x for x in pl if x.get('position') in pos and x.get('photo') and (x.get('age') or 30) >= 19]
    def rank(x):
        n = x.get('number') or 99
        return (_STAR.index(n) if n in _STAR else 50, pos[x['position']], x.get('id') or 0)
    cands.sort(key=rank)
    p = cands[0] if cands else None
    best = {'id': p['id'], 'name': p.get('name') or '', 'photo': p['photo']} if p else None
    st['sq'][str(tid)] = {'t': time.time(), 'p': best}
    _af_save()
    return best


def _cutout(path):
    """the head and shoulders without the white studio background"""
    from PIL import Image, ImageFilter, ImageDraw, ImageEnhance
    im = Image.open(path).convert('RGB')
    w, h = im.size
    px = im.load()
    a = Image.new('L', (w, h), 255)
    ap = a.load()
    corners = [px[x, y][:3] for x, y in ((1, 1), (w - 2, 1), (1, h // 3), (w - 2, h // 3))]
    bg = tuple(sorted(c[i] for c in corners)[len(corners) // 2] for i in range(3))  # the studio colour
    lim = int(h * .6)  # lower down the shirt can touch the edges: only the plain studio colour goes there

    def near(c, tol):
        return (c[0] - bg[0]) ** 2 + (c[1] - bg[1]) ** 2 + (c[2] - bg[2]) ** 2 <= tol * tol
    seen = set()
    stack = [(x, 0) for x in range(w)] + [(0, y) for y in range(h)] + [(w - 1, y) for y in range(h)]
    while stack:
        x, y = stack.pop()
        if (x, y) in seen or x < 0 or y < 0 or x >= w or y >= h:
            continue
        seen.add((x, y))
        if not near(px[x, y][:3], 30 if y < lim else 12):
            continue
        ap[x, y] = 0
        stack.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    a = a.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.2))
    fade = Image.new('L', (1, h))
    for y in range(h):
        t = y / float(h - 1)
        fade.putpixel((0, y), 255 if t < .8 else int(255 * (1 - (t - .8) / .2)))
    a = Image.composite(a, Image.new('L', (w, h), 0), fade.resize((w, h)))
    im = ImageEnhance.Sharpness(im).enhance(1.4)
    out = im.convert('RGBA')
    out.putalpha(a)
    return out


def _player(key, net=True):
    """(picture, name) of the star of a club, or None. net=False: only what is kept already."""
    if not players_on():
        return None
    try:
        if net:
            tid = _af_team(key)
            p = _af_star(tid) if tid else None
        else:
            st = _af_load()
            tid = st['ids'].get(key)
            p = (st['sq'].get(str(tid)) or {}).get('p') if tid else None
        if not p:
            return None
        path = os.path.join(U.CACHE_DIR, 'pl_%d.png' % p['id'])
        if not os.path.isfile(path):
            if not net or not U.download(p['photo'], path):
                return None
        cut = os.path.join(U.CACHE_DIR, 'plc_%d.png' % p['id'])
        from PIL import Image
        if os.path.isfile(cut):
            try:
                return Image.open(cut).convert('RGBA'), p.get('name') or ''
            except Exception:
                pass
        im = _cutout(path)  # made once: the next cards take it ready
        try:
            im.save(cut + '.part', 'PNG')
            os.rename(cut + '.part', cut)
        except Exception:
            pass
        return im, p.get('name') or ''
    except Exception as e:
        print('[MohammedSkin] player %s: %s' % (key, e))
        return None


_fetching = set()


def _prefetch(keys):
    """look the stars up in the background; the card shows them the next time it is drawn"""
    keys = [k for k in keys if k not in _fetching]
    if not keys:
        return
    _fetching.update(keys)

    def run():
        for k in keys:
            try:
                _player(k, True)
            finally:
                _fetching.discard(k)
    try:
        import threading
        th = threading.Thread(target=run, name='MohammedSkinPlayers')
        th.daemon = True
        th.start()
    except Exception:
        _fetching.difference_update(keys)


def _wants_players(m, shape):
    return shape != 'row' and 'a' in m and players_on() and not (u'%s%s' % (m['a'], m['b'])).count(u'x:')


def _out(m, shape, w, h, pf):
    live, hm = _when(m)
    sig = json.dumps([m.get('a'), m.get('b'), m.get('comp'), m.get('ar'), shape, w, h, live, hm, 3] + (['p'] if pf else []))
    return os.path.join(U.CACHE_DIR, 'mc_%s.png' % hashlib.md5(sig.encode('utf-8')).hexdigest()[:16])


def make(m, shape, w, h, fetch=True):
    """draw the card: shape = poster (tall), wide or row. Returns the picture path."""
    from PIL import Image
    data()
    pf = _wants_players(m, shape)
    out = _out(m, shape, w, h, pf)
    if os.path.isfile(out):
        return out
    pls = {}
    if pf:
        for side in ('a', 'b'):
            pls[m[side]] = _player(m[side], False)
        need = [m[side] for side in ('a', 'b') if not pls[m[side]]]
        if need and fetch:
            _prefetch(need)
        if not all(pls.values()):  # not here yet (or no network, day used up): the card without them for now
            pls = {}
            pf = False
            out = _out(m, shape, w, h, False)
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
            xs = (.28, .72) if wide else (.25, .75)
            nh = int(h * (.075 if wide else .058))
            if pls:  # the star of each club above its badge
                ph = int(min(h * (.6 if wide else .42), w * (.34 if wide else .62)))
                ptop = h * (.12 if wide else .115)
                for side, x in ((left, xs[0]), (right, xs[1])):
                    got = pls.get(side)
                    if not got:
                        continue
                    pim = got[0].resize((ph, ph), Image.LANCZOS)
                    _put(im, pim, w * x, ptop + ph / 2.0, True)
                cy = ptop + ph * (.97 if wide else .98)
                bs = int(min(w * (.15 if wide else .22), h * (.22 if wide else .16)))
                _put(im, _vs(int(h * (.17 if wide else .1))), w / 2, ptop + ph * .45, False)
                ny = cy + bs * .42 + nh * .75
            else:
                cy = h * (.42 if wide else .47)
                bs = int(min(w * (.24 if wide else .36), h * (.38 if wide else .26)))
                _put(im, _vs(int(bs * .62)), w / 2, cy, False)
                ny = cy + bs * .5 + nh * 1.15
            _put(im, _badge(left, bs), w * xs[0], cy, False)
            _put(im, _badge(right, bs), w * xs[1], cy, False)
            for side, x in ((left, xs[0]), (right, xs[1])):
                t = _db['teams'][side]
                lab = _label(side, t['name'], ar, nh, int(w * (.4 if wide else .46)))
                _put(im, lab, w * x, ny)
            pill = _pill(m, ar, int(h * (.085 if wide else .062)))
            if pill:
                _put(im, pill, w / 2, h * ((.945 if pls else .87) if wide else .9), False)
        if shape != 'row':
            im = _round(im, max(8, min(w, h) // 30))
    tmp = out + '.part'
    im.save(tmp, 'PNG')
    os.rename(tmp, out)
    return out


_busy = {}
_tried = {}


def final_path(m, shape, w, h):
    """the card that is wanted now: with the players when there is a key, else with the logos"""
    data()
    return _out(m, shape, w, h, _wants_players(m, shape))


def busy(path):
    return path in _busy


def make_async(m, shape, w, h, callback):
    """the picture if it is made already, else None and callback(path) when it is ready"""
    data()
    out = _out(m, shape, w, h, _wants_players(m, shape))
    if os.path.isfile(out):
        return out
    if out in _busy:
        _busy[out].append(callback)
        return None
    _busy[out] = [callback]

    def tell(path):
        for cb in list(_busy.get(out, [])):
            try:
                cb(path)
            except Exception:
                pass

    def work():
        try:
            with U.CPU:
                path = make(m, shape, w, h, False)
            if path and path != out and _wants_players(m, shape):
                # the logos now, the players as soon as they are here
                try:
                    from twisted.internet import reactor
                    reactor.callFromThread(tell, path)
                except Exception:
                    pass
                for side in ('a', 'b'):
                    k = m.get(side)
                    if not k:
                        continue
                    for _ in range(240):  # another card is getting this club already: wait for it
                        if k not in _fetching:
                            break
                        time.sleep(.5)
                    if time.time() - _tried.get(k, 0) < 90 and _player(k, False) is None:
                        continue  # asked a moment ago and nothing came: not again so soon
                    _tried[k] = time.time()
                    _fetching.add(k)
                    try:
                        _player(k, True)
                    finally:
                        _fetching.discard(k)
                with U.CPU:
                    path = make(m, shape, w, h, False) or path
            return path
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
