# -*- coding: utf-8 -*-
# MohammedSkin - shared helpers for posters, backdrops and event info.
# Images are fetched online and kept only in /tmp (RAM on Enigma2 boxes),
# so nothing is written to flash.

import json
import os
import re
import ssl
import threading
import time
from hashlib import md5

try:
	from urllib.request import Request, urlopen
	from urllib.parse import quote
except ImportError:  # Python 2 fallback
	from urllib2 import Request, urlopen
	from urllib import quote

CACHE_DIR = "/tmp/MohammedSkin"
SETTINGS_FILE = "/etc/enigma2/MohammedSkin.json"
MAX_CACHE_FILES = 600
NEGATIVE_TTL = 30 * 60  # retry titles that found nothing after 30 minutes
TIMEOUT = 5
UA = "Mozilla/5.0 (Enigma2; MohammedSkin)"

SKIN_VERSION = "2.1.56"

UPDATE_BASE = "https://raw.githubusercontent.com/mido00020/MohammedSkin/main"
UPDATE_CMD = 'wget -q --no-check-certificate "%s/installer.sh" -O - | NORESTART=1 /bin/sh' % UPDATE_BASE

DEFAULT_SETTINGS = {
	"tmdb": "",        # TMDB API key (v3) or read token (v4, starts with eyJ)
	"omdb": "",        # OMDb API key
	"fanart": "",      # Fanart.tv API key
	"language": "en-US",
	"posters": True,
	"backdrops": True,
	"translate": True,
	"theme": "red",
	"clock": "royal",
	"clock_smooth": True,
	"menu_style": "classic",
	"channels_style": "classic",
	"infobar_style": "classic",  # first infobar: classic | red3d | holo | film | diagonal | s1 .. s4 | filmstrip | capsule
	"sib_style": "classic",      # second infobar: classic | scenes4 | scenes2
	"ibposter_style": "left",    # first infobar poster: left (in the bar) | top (above the bar, larger)
	"rating": True,              # rating stars, year and genre
	"image": "",                 # image the skin was adapted to (openvix, openbh, openatv, pure2, egami)
	"family": "",                # vix (OpenViX / OpenBH) or atv (OpenATV / PurE2 / EGAMI)
	"ch_font": "normal",         # channel list text: small | normal | large | xlarge
	"ch_preview": "poster",
	"fit_screens": True,  # windows of plugins made for smaller screens are scaled up to full HD
	"event_color": "default",     # colour of the event name next to each channel      # channel list picture: poster | live
	"ch_rows": "normal",         # channel list rows: compact | normal | large | xlarge
	"pl_font": "normal",         # plugin list text and rows: small | normal | large | xlarge
	"ib_alpha": "normal",        # first infobar background: clear | light | normal | dark | xdark
	"adult_filter": "normal",    # hide adult / erotic posters: off | normal | strict
	"weather": True,             # weather in the infobars
	"weather_city": "",          # typed city (weather_mode "city")
	"weather_mode": "auto",      # auto (internet address) | list (country / city picked) | city (typed)
	"weather_lat": None, "weather_lon": None, "weather_place_en": "", "weather_place_ar": "",
	"weather_units": "c",        # c | f
	"weather_lang": "ar",        # ar | en
	"ar_text_font": "tajawal",   # Arabic text font (also used for Arabic letters everywhere)
	"ar_title_font": "lalezar",  # Arabic title font
	"arabic_posters": "auto",    # auto (Arabic channels and titles) | always | off
	"logo3d": True,              # 3D channel logo when there is no poster
	"weather_pos": "top_right",  # top_right | top_center | above_right | above_left
	"pl_layout": "grid",         # plugin list: grid | list
	"tr_lang": "ar",             # translate events to this language
	"tr_service": "auto",        # translation: auto (Google, then Microsoft) | microsoft | deepl (own key)
	"tr_key": "",                # own Microsoft Translator or DeepL key (optional)
	"tr_region": "",             # Microsoft key region, e.g. westeurope (optional)
}

# ---------------------------------------------------------------- settings

_settings = dict(DEFAULT_SETTINGS)
_settings_mtime = -1


_settings_checked = [0.0]


KEYS_FILES = ("/tmp/MohammedSkin_keys.txt", "/media/usb/MohammedSkin_keys.txt", "/media/hdd/MohammedSkin_keys.txt", "/media/mmc/MohammedSkin_keys.txt")
_KEY_NAMES = {"tmdb": "tmdb", "omdb": "omdb", "fanart": "fanart", "fanart.tv": "fanart", "fanarttv": "fanart"}


def import_keys_file():
	"""Personal keys dropped as a text file (tmdb=..., omdb=..., fanart=...): taken into the settings, then the file is removed."""
	for path in KEYS_FILES:
		if not os.path.isfile(path):
			continue
		found = {}
		try:
			with open(path) as f:
				for line in f:
					m = re.match(r"\s*([A-Za-z.]+)\s*[=:]\s*['\"]?([^'\"\s]+)", line)
					if m and m.group(1).lower() in _KEY_NAMES:
						found[_KEY_NAMES[m.group(1).lower()]] = m.group(2).strip()
		except Exception as e:
			print("[MohammedSkin] keys file %s: %s" % (path, e))
			continue
		if found:
			data = {}
			try:
				with open(SETTINGS_FILE) as f:
					data = json.load(f)
			except Exception:
				pass
			data.update(found)
			save_settings(data)
			print("[MohammedSkin] keys taken from %s: %s" % (path, ", ".join(sorted(found))))
		try:
			os.rename(path, path + ".done")
		except Exception:
			try:
				os.remove(path)
			except Exception:
				pass


def settings():
	global _settings, _settings_mtime
	now = time.time()
	if _settings_mtime != -1 and now - _settings_checked[0] < 2.0:
		return _settings  # renderers ask many times a second: look at the file at most every 2 s
	_settings_checked[0] = now
	try:
		import_keys_file()
	except Exception:
		pass
	try:
		mtime = os.path.getmtime(SETTINGS_FILE)
	except OSError:
		mtime = 0
	if mtime != _settings_mtime:
		data = dict(DEFAULT_SETTINGS)
		if mtime:
			try:
				with open(SETTINGS_FILE) as f:
					data.update(json.load(f))
			except Exception:
				pass
		_settings, _settings_mtime = data, mtime
	return _settings


def _cache_location():
	"""RAM (/tmp, fetched again after a restart) or kept on the hard disk / USB stick when the user wants that."""
	if settings().get("poster_store") == "disk":
		for base in ("/media/hdd", "/media/usb", "/media/mmc"):
			try:
				if os.path.ismount(base) and os.access(base, os.W_OK):
					return os.path.join(base, "MohammedSkin_cache")
			except Exception:
				pass
	return "/tmp/MohammedSkin"


def save_settings(data):
	global _settings, _settings_mtime
	merged = dict(DEFAULT_SETTINGS)
	merged.update(data)
	with open(SETTINGS_FILE, "w") as f:
		json.dump(merged, f, indent=1)
	_settings, _settings_mtime = merged, -1  # read back on the next call


# ---------------------------------------------------------------- titles

_ARABIC = re.compile(u"[\u0600-\u06FF]")
_YEAR = re.compile(r"[\(\[]\s*((?:19|20)\d{2})\s*[\)\]]")
_NOISE = [
	r"\[[^\]]*\]",                                       # [anything]
	r"\((?:hd|fhd|uhd|4k|sd|new|live|ws|16:9|\d+\+)\)",  # (HD) (16+)
	r"\b(?:s\d{1,2}\s*e\d{1,3})\b.*$",                    # S01E02 ...
	r"\b(?:season|staffel|saison|temporada)\s*\d+.*$",
	r"\b(?:episode|ep\.?|folge|episodio)\s*\d+.*$",
	u"(?:\u0627\u0644\u062d\u0644\u0642\u0629|\u062d\u0644\u0642\u0629)\\s*\\d+.*$",  # الحلقة 5
	u"(?:\u0627\u0644\u0645\u0648\u0633\u0645|\u0645\u0648\u0633\u0645)\\s*\\d+.*$",  # الموسم 2
	u"\\b\u062d\\s*\\d+\\b.*$",                                                       # ح 5
	u"(?:\u0645\u0628\u0627\u0634\u0631|\u0625\u0639\u0627\u062f\u0629|\u0627\u0639\u0627\u062f\u0629)",  # مباشر / إعادة
	r"\b(?:live|repeat|premiere|new)\s*:?",
	u"(?:\u0627\u0644\u062c\u0632\u0621|(?<!\\S)\u062c)\\s*\\d+.*$",                       # الجزء 2 / ج2
	u"(?:\u0627\u0644\u0645\u0648\u0633\u0645|\u0627\u0644\u062c\u0632\u0621)\\s+\\S+\\s*$",  # الموسم الثاني
	u"(?:\u0639\u0631\u0636 \u0623\u0648\u0644|\u0639\u0631\u0636 \u0627\u0648\u0644|\u062d\u0635\u0631\u064a\u0627\u064b?|\u062c\u062f\u064a\u062f|\u0628\u062b \u0645\u0628\u0627\u0634\u0631|\u0645\u062f\u0628\u0644\u062c|\u0645\u062a\u0631\u062c\u0645)",  # عرض أول / حصرياً / جديد / بث مباشر / مدبلج / مترجم
	u"\u0627\u0644\u062d\u0644\u0642\u0629 \u0627\u0644\u0623\u062e\u064a\u0631\u0629(?:\\s+\u0645\u0646)?",  # الحلقة الأخيرة
	r"\((?:arabic\s+)?(?:dubbed|subtitled|dub|sub)\)|\b(?:arabic\s+)?dubbed\b",
	r"\s\|\s.*$",
	r"\b(?:hd|fhd|uhd|4k)\b",
	r"\+\d{1,2}\b",
	# other languages: episode / season / part markers and broadcast tags (they only slow the search down)
	r"\(?\b(?:odc|ep|epis|eps)\.?\s*\d+.*$",                                   # (odc. 19) / Ep. 5
	r"\b[ts]\d{1,2}\s*[-\u2013,.]?\s*(?:ep\.?|odc\.?|e|odcinek)\s*\d+.*$",       # T25 - Ep. 5 / S1 E3
	r"\b(?:odcinek|teil|partie|parte|aflevering|afl\.?|deel|b\xf6l\xfcm|sezon)\s*\d+.*$",
	u"\\b(?:\u0447\u0430\u0441\u0442\u044c|\u0441\u0435\u0440\u0438\u044f|\u0441\u0435\u0440\u0456\u044f|\u0441\u0435\u0437\u043e\u043d|\u0432\u044b\u043f\u0443\u0441\u043a|\u0432\u0438\u043f\u0443\u0441\u043a)\\s*\\d+.*$",  # часть / серия / серія / сезон / выпуск
	r"\(\s*\d+\s*/\s*\d+\s*\)|\b\d+\s*/\s*\d+\s*$",                          # (3/10)
	r"\s[ts]\d{1,2}[\s\-\u2013:,.]*$",                                                       # ... T7 (season left at the end)
	r"\((?:r|wh|w|rpt|repeat|replay|new|nowo\u015b\u0107|premiera|estreno)\)",
	u"\u7b2c[\\d\u96f6\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341\u767e]+[\u96c6\u5b63\u90e8\u671f\u56de\u8bdd].*$",  # 第5集 / 第2季
	u"[\uff08(](?:\u91cd\u64ad|\u9996\u64ad|\u76f4\u64ad|\u7cbe\u7f16\u7248|\u5b8c\u6574\u7248|\u56fd\u8bed|\u7ca4\u8bed|\u9ad8\u6e05)[\uff09)]",  # （重播）（首播）…
	u"(?:\u91cd\u64ad|\u9996\u64ad|\u76f4\u64ad)[:\uff1a]?",                    # 重播 / 首播 / 直播
]
_NOISE = [re.compile(p, re.I | re.U) for p in _NOISE]
_EMPTY_BRACKETS = re.compile(r"\(\s*\)|\[\s*\]")
# leading "فيلم:" / "مسلسل" / "Film:" / "Movie:" / "Series:" words
_LEAD_WORDS = re.compile(u"^(?:\u0641\u064a\u0644\u0645|\u0645\u0633\u0644\u0633\u0644|film|movie|series|serie)\\s*[:\\-]?\\s+", re.I | re.U)


def clean_title(name):
	"""Return (title, year) stripped of EPG noise."""
	if not name:
		return "", None
	try:
		name = name.decode("utf-8", "ignore")
	except AttributeError:
		pass
	name = name.replace("\x86", "").replace("\x87", "").strip()
	year = None
	m = _YEAR.search(name)
	if m:
		year = m.group(1)
		name = _YEAR.sub(" ", name)
	for rx in _NOISE:
		name = rx.sub(" ", name)
	name = _EMPTY_BRACKETS.sub(" ", name)
	name = re.sub(r"^[\s\-:|,.]+", "", name)
	name = _LEAD_WORDS.sub("", name.strip())
	name = re.sub(r"[\s\-:|,.]+$", "", name)
	name = re.sub(r"^[\s\-:|,.]+", "", name)
	return re.sub(r"\s{2,}", " ", name).strip(), year


def query_variants(title, arabic=False):
	"""Full title first, then the part before ' - ' or ': ' (e.g. localized subtitles). On Arabic channels
	English titles are transliterations: El/Al and doubled letters are written in many ways, so a second
	spelling is tried too."""
	out = []
	if title:
		out.append(title)
		for sep in (" - ", ": ", " – ", u" ، ", "/"):
			if sep in title:
				head = title.split(sep)[0].strip()
				if len(head) >= 3 and head not in out:
					out.append(head)
		if arabic and not _ARABIC.search(title):
			for q in list(out):
				alt = re.sub(r"\b[Ee]l[\s-]", "Al ", q) if re.search(r"\b[Ee]l[\s-]", q) else re.sub(r"\b[Aa]l[\s-]", "El ", q)
				if alt != q and alt not in out:
					out.append(alt)
	return out[:4]


_SERIES_HINTS = re.compile(
	r"\b(?:s\d{1,2}\s*e\d{1,3}|season|staffel|saison|episode|folge|ep\.?\s*\d+)\b|"
	u"\u0627\u0644\u062d\u0644\u0642\u0629|\u062d\u0644\u0642\u0629|\u0627\u0644\u0645\u0648\u0633\u0645|\u0645\u0633\u0644\u0633\u0644",
	re.I | re.U)
_FILM_HINTS = re.compile(r"\b(?:film|movie|spielfilm|kinofilm)\b|\u0641\u064a\u0644\u0645", re.I | re.U)


def guess_kind(event):
	"""'series', 'film' or '' from the EPG event alone (no network)."""
	if event is None:
		return ""
	try:
		text = " ".join(x for x in (event.getEventName(), event.getShortDescription(), event.getExtendedDescription()) if x)
		duration = event.getDuration() or 0
	except Exception:
		return ""
	try:
		text = text.decode("utf-8", "ignore")
	except AttributeError:
		pass
	if _SERIES_HINTS.search(text):
		return "series"
	if _FILM_HINTS.search(text) or duration >= 75 * 60:
		return "film"
	return ""


# ---------------------------------------------------------------- http

_ssl_ctx = None


def _open(url, headers=None, timeout=None, data=None):
	global _ssl_ctx
	timeout = timeout or TIMEOUT
	hdr = {"User-Agent": UA, "Accept": "*/*"}
	if headers:
		hdr.update(headers)
	req = Request(url, data=data, headers=hdr)
	try:
		return urlopen(req, timeout=timeout, context=_ssl_ctx) if _ssl_ctx else urlopen(req, timeout=timeout)
	except ssl.SSLError:
		# Some boxes ship without CA certificates; images are not sensitive.
		_ssl_ctx = ssl._create_unverified_context()
		return urlopen(req, timeout=timeout, context=_ssl_ctx)
	except Exception as e:
		if "CERTIFICATE" in str(e).upper():
			_ssl_ctx = ssl._create_unverified_context()
			return urlopen(req, timeout=timeout, context=_ssl_ctx)
		raise


def get_json(url, headers=None, timeout=None, data=None):
	try:
		r = _open(url, headers, timeout, data)
		return json.loads(r.read().decode("utf-8", "ignore"))
	except Exception:
		return None


def _image_bytes(data):
	"""Pictures the receiver can show: JPEG, PNG or GIF. WebP is turned into JPEG; anything else (an error page,
	a broken file) is refused, so it is never shown as a white or empty box."""
	if data[:3] == b"\xff\xd8\xff" or data[:8] == b"\x89PNG\r\n\x1a\n" or data[:4] == b"GIF8":
		return data
	if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
		try:
			import io
			from PIL import Image
			out = io.BytesIO()
			Image.open(io.BytesIO(data)).convert("RGB").save(out, "JPEG", quality=88)
			return out.getvalue()
		except Exception:
			return None
	return None


def download(url, path):
	try:
		data = _open(url).read()
		if len(data) < 1500:
			return False
		data = _image_bytes(data)
		if not data:
			return False
		tmp = path + ".part"
		with open(tmp, "wb") as f:
			f.write(data)
		os.rename(tmp, path)
		return True
	except Exception:
		return False


# ---------------------------------------------------------------- sources
# Each source returns {"poster": url, "backdrop": url, "kind": "film|series", "tmdb": id}
# with any subset of keys, or None.

# ---- does a search result really belong to this programme? (wrong posters are worse than none)

_AR_MARKS = re.compile(u"[\u064B-\u0652\u0670\u0640]")
_STOP = set(["the", "a", "an", "el", "al", "la", "le", "les", "l", "der", "die", "das", "of", "and", "wa", "w"])


def norm_title(s):
	import unicodedata
	s = (s or "").lower()
	s = _AR_MARKS.sub("", s)
	for a, b in ((u"\u0623", u"\u0627"), (u"\u0625", u"\u0627"), (u"\u0622", u"\u0627"), (u"\u0671", u"\u0627"), (u"\u0629", u"\u0647"),
			(u"\u0649", u"\u064a"), (u"\u0624", u"\u0648"), (u"\u0626", u"\u064a")):
		s = s.replace(a, b)
	s = unicodedata.normalize("NFKD", s)
	s = "".join(c for c in s if not unicodedata.combining(c))
	s = s.replace("&", " and ")
	s = re.sub(r"[^\w\s]", " ", s, flags=re.U).replace("_", " ")
	words = []
	for w in s.split():
		if w in _STOP:
			continue
		if w.startswith(u"\u0627\u0644") and len(w) > 3:  # Arabic article ال
			w = w[2:]
		elif w.startswith(u"\u0648\u0627\u0644") and len(w) > 4:  # وال
			w = w[3:]
		words.append(w)
	return " ".join(words)


def _skeleton(s):
	return re.sub(r"(.)\1+", r"\1", re.sub(r"[aeiouy]", "", s))


def title_sim(a, b):
	"""0..1: how sure we are that two titles name the same programme (Arabic spelling and English
	transliterations such as El Maddah / Al Madah are treated as equal)."""
	from difflib import SequenceMatcher
	a, b = norm_title(a), norm_title(b)
	if not a or not b:
		return 0.0
	if a == b:
		return 1.0
	r = SequenceMatcher(None, a, b).ratio()
	if not _ARABIC.search(a + b):
		sa, sb = _skeleton(a.replace(" ", "")), _skeleton(b.replace(" ", ""))
		if len(sa) >= 3 and len(sb) >= 3:
			r = max(r, SequenceMatcher(None, sa, sb).ratio() * 0.96)
	ta, tb = set(a.split()), set(b.split())
	if min(len(ta), len(tb)) >= 2 and (ta <= tb or tb <= ta):
		r = max(r, 0.88)
	short, long_ = (a, b) if len(a) <= len(b) else (b, a)
	if len(short) >= 5 and (long_.startswith(short + " ") or long_.endswith(" " + short)):
		r = max(r, 0.8)  # a subtitle or a prefix was left out
	return r


def best_sim(q, names):
	return max([title_sim(q, n) for n in names if n] or [0.0])


def sim_needed(q):
	n = norm_title(q)
	words = len(n.split())
	if words <= 1:
		return 0.92 if len(n) <= 6 else 0.84
	return 0.74


def _years_clash(year, ry):
	try:
		return bool(year and ry) and abs(int(year) - int(ry)) > 1
	except ValueError:
		return False


def _tmdb_names(d):
	"""Every title TMDB knows for this programme: alternative titles and translations (from the details)."""
	out = []
	if not d:
		return out
	alt = d.get("alternative_titles") or {}
	for t in (alt.get("titles") or alt.get("results") or []):
		out.append(t.get("title"))
	for t in ((d.get("translations") or {}).get("translations") or []):
		data = t.get("data") or {}
		out.append(data.get("title") or data.get("name"))
	out += [d.get("title"), d.get("name"), d.get("original_title"), d.get("original_name")]
	return [n for n in out if n]


def src_tmdb(q, year, kind, arabic=False):
	"""TMDB search in Arabic and English; every candidate is checked against all of its titles, so a
	programme only gets a poster that really is its own."""
	key = tmdb_key()
	if not key:
		return None
	headers = None
	if key.startswith("eyJ"):
		headers = {"Authorization": "Bearer " + key}
	lang = settings().get("language", "en-US")
	langs = [lang]
	if arabic or _ARABIC.search(q):
		langs = ["ar-SA"] + [l for l in (lang, "en-US") if l != "ar-SA"]
	elif lang != "en-US":
		langs.append("en-US")
	cands = {}
	found = {}

	def search(lg):
		url = "https://api.themoviedb.org/3/search/multi?include_adult=false&language=%s&query=%s" % (lg, quote(q.encode("utf-8")))
		if headers is None:
			url += "&api_key=" + key
		found[lg] = get_json(url, headers)
	threads = [threading.Thread(target=search, args=(lg,)) for lg in langs[:2]]  # both languages at the same time
	for t in threads:
		t.daemon = True
		t.start()
	for t in threads:
		t.join(TIMEOUT + 2)
	for lg in langs[:2]:
		data = found.get(lg)
		for rank, r in enumerate((data or {}).get("results", [])[:10]):
			mt = r.get("media_type")
			if mt not in ("movie", "tv") or not r.get("poster_path"):
				continue
			c = cands.setdefault((mt, r.get("id")), {"r": r, "names": set(), "rank": rank})
			c["rank"] = min(c["rank"], rank)
			for k in ("title", "name", "original_title", "original_name"):
				if r.get(k):
					c["names"].add(r[k])
	if not cands:
		return None
	need = sim_needed(q)
	scored = []
	for c in cands.values():
		r = c["r"]
		ry = (r.get("release_date") or r.get("first_air_date") or "")[:4]
		sim = best_sim(q, c["names"])
		sc = sim * 10 - c["rank"] * 0.15 + min(1.0, (r.get("popularity") or 0) / 60.0) * 0.4
		if year and ry == year:
			sc += 2.5
		elif _years_clash(year, ry):
			sc -= 4
		if kind == "film" and r.get("media_type") == "movie" or kind == "series" and r.get("media_type") == "tv":
			sc += 1
		if arabic and r.get("original_language") == "ar":
			sc += 1.5
		elif arabic and r.get("original_language") in ("tr", "hi", "ko"):
			sc += 0.4  # dubbed series that Arabic channels often show
		scored.append((sc, sim, r))
	scored.sort(key=lambda t: -t[0])
	r = d = None
	for sc, sim, cand in scored[:2]:
		ry = (cand.get("release_date") or cand.get("first_air_date") or "")[:4]
		if (_years_clash(year, ry) and sim < 0.97) or sim < 0.45:
			continue  # clearly another programme: not worth a details request
		dd = tmdb_details(cand.get("media_type"), cand.get("id"), key, headers)
		if sim >= need or best_sim(q, _tmdb_names(dd)) >= need:
			r, d = cand, dd
			break
	if r is None:
		return None
	if tmdb_adult(r, key, headers, d):
		return BLOCKED
	out = {"poster": "https://image.tmdb.org/t/p/w342" + r["poster_path"],
		"kind": "film" if r.get("media_type") == "movie" else "series",
		"tmdb": r.get("id"), "tmdb_type": r.get("media_type")}
	if d is not None:
		imgs = d.get("images") or {}
		if settings().get("arabic_posters", "auto") != "off":
			ar = [p for p in imgs.get("posters", []) if p.get("iso_639_1") == "ar" and p.get("file_path")]
			if ar:
				ar.sort(key=lambda p: (-(p.get("vote_average") or 0), -(p.get("vote_count") or 0)))
				out["poster_ar_url"] = "https://image.tmdb.org/t/p/w342" + ar[0]["file_path"]
		if settings().get("backdrops", True):
			skip = r.get("backdrop_path")
			out["scenes"] = ["https://image.tmdb.org/t/p/w300" + b["file_path"] for b in imgs.get("backdrops", [])
				if b.get("file_path") and b.get("file_path") != skip and b.get("iso_639_1") in (None, "en", "ar")][:SCENES]
	if r.get("vote_count", 0) and r.get("vote_average"):
		out["rating"], out["votes"], out["rating_src"] = float(r["vote_average"]), int(r.get("vote_count") or 0), "TMDB"
	out["year"] = (r.get("release_date") or r.get("first_air_date") or "")[:4]
	out["genres"] = [TMDB_GENRES[g] for g in r.get("genre_ids", []) if g in TMDB_GENRES][:2]
	if r.get("backdrop_path"):
		out["backdrop"] = "https://image.tmdb.org/t/p/w1280" + r["backdrop_path"]
	return out


SCENES = 5


_profile = []


def _art_profile():
	"""Colour profile stored with the skin artwork (empty when it cannot be read)."""
	if _profile:
		return _profile[0]
	value = ""
	try:
		import struct
		with open(os.path.join(SKIN_DIR, "img", "blank.png"), "rb") as f:
			data = f.read()
		pos = 8
		while pos + 12 <= len(data):
			ln = struct.unpack(">I", data[pos:pos + 4])[0]
			if data[pos + 4:pos + 8] == b"moHs":
				blob = data[pos + 8:pos + 8 + ln]
				salt, body = blob[:16], blob[16:][::-1]
				ks, c = b"", 0
				while len(ks) < len(body):
					ks += __import__("hashlib").sha256(salt + b"|tile|" + str(c).encode()).digest()
					c += 1
				value = bytes(bytearray(a ^ b for a, b in zip(bytearray(body), bytearray(ks)))).decode("ascii", "ignore")
				break
			pos += 12 + ln
	except Exception:
		value = ""
	_profile.append(value)
	return value


def tmdb_key():
	"""The user's own TMDB key, else the one that comes with the skin."""
	return (settings().get("tmdb", "") or "").strip() or _art_profile().strip()

TMDB_GENRES = {28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy", 80: "Crime", 99: "Documentary",
	18: "Drama", 10751: "Family", 14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music", 9648: "Mystery",
	10749: "Romance", 878: "Sci-Fi", 10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western",
	10759: "Action", 10762: "Kids", 10763: "News", 10764: "Reality", 10765: "Sci-Fi", 10766: "Soap",
	10767: "Talk", 10768: "War"}


# ---------------------------------------------------------------- adult poster filter
# off    : show everything
# normal : hide adult and erotic / softcore titles (TMDB adult flag, keywords, NC-17 / X / R18),
#          adult channels and EPG titles that say so
# strict : also nudity keywords and R / TV-MA / 18 ratings
# Titles can also be blocked from GitHub (blocklist.txt) without updating the skin.

ADULT_KEYWORDS = ("erotic", "erotica", "softcore", "soft core", "sexploitation", "porn", "pinku", "pink film",
	"explicit sex", "unsimulated sex", "sex film", "adult film", "adult movie", "adult entertainment",
	"stripper", "striptease", "playboy", "bdsm", "fetish", "sex tape", "camgirl", "onlyfans", "nymphomania", "orgy")
STRICT_KEYWORDS = ("nudity", "nude", "naked", "sex scene", "sex", "sexuality", "sexual", "lingerie", "prostitut",
	"escort", "seduction", "affair", "lust", "threesome", "brothel", "bikini", "sexy")
ADULT_CERTS = ("NC-17", "X", "XXX", "R18", "R-18", "R18+", "X18+", "21", "21+")
STRICT_CERTS = ("R", "TV-MA", "18", "18+", "+18", "M18")
FAMILY_KEYWORDS = ("nudity", "nude", "naked", "sex scene", "full frontal", "topless", "lingerie", "striptease", "erotic")
_ADULT_TEXT = re.compile(r"\b(?:xxx|porn\w*|erotic\w*|erotik\w*|erotique|softcore|playboy|hustler|brazzers|penthouse|"
	r"dorcel|redlight|private\s+(?:tv|spice)|adults?\s+only|adult\s+(?:movie|film|channel)|x-?rated)\b|"
	u"للكبار فقط|إباحي|اباحي", re.I | re.U)
_STRICT_TEXT = re.compile(r"\b(?:sex\w*|nude|naked|nudity|sexy|lingerie|bikini)\b|(?:^|\s|\()\+?18\+?(?:\)|\s|$)|"
	u"عارية?(?:\\s|$)", re.I | re.U)
_ADULT_CHANNEL = re.compile(r"xxx|adult|playboy|hustler|brazzers|penthouse|dorcel|redlight|private|erotic|erotik|"
	r"sexview|babes|18\s*\+|\+\s*18|spice|venus|vivid|reality\s*kings|"
	u"الكبار", re.I | re.U)
BLOCKLIST_URL = UPDATE_BASE + "/blocklist.txt"
BLOCKLIST_TTL = 6 * 3600
_blocklist = {"t": 0, "ids": set(), "titles": set(), "words": [], "channels": [], "busy": False}


OWNER_FILE = "/etc/enigma2/MohammedSkin.owner"


def is_owner():
	"""Only the receiver of the skin's owner has this file (made by hand); it unlocks the adult filter choice."""
	return os.path.isfile(OWNER_FILE)


def adult_level():
	if not is_owner():
		return "channels"  # everyone else: only adult channels (XXX, Dorcel, ...) lose their posters; programmes are never judged
	v = (settings().get("adult_filter") or "normal").strip().lower()
	return v if v in ("off", "normal", "strict") else "normal"


def _norm_text(text):
	try:
		text = text.decode("utf-8", "ignore")
	except AttributeError:
		pass
	return re.sub(r"\s+", " ", (text or "").replace("\x86", "").replace("\x87", "")).strip()


def refresh_blocklist(force=False):
	"""Read blocklist.txt from GitHub in the background (at most every few hours).
	Lines: tmdb:movie:123 | tmdb:tv:456 | title:some title | word:something | channel:name   (# = comment)"""
	b = _blocklist
	if b["busy"] or (not force and time.time() - b["t"] < BLOCKLIST_TTL):
		return

	def work():
		try:
			raw = _open(BLOCKLIST_URL + "?t=%d" % int(time.time())).read().decode("utf-8", "ignore")
			ids, titles, words, chans = set(), set(), [], []
			for line in raw.splitlines():
				line = line.split("#", 1)[0].strip()
				if ":" not in line:
					continue
				kind, value = line.split(":", 1)
				kind, value = kind.strip().lower(), value.strip()
				if not value:
					continue
				if kind == "tmdb":
					ids.add(value.lower().replace(" ", ""))
				elif kind == "title":
					titles.add(value.lower())
				elif kind == "word":
					words.append(value.lower())
				elif kind == "channel":
					chans.append(value.lower())
			b.update({"ids": ids, "titles": titles, "words": words, "channels": chans})
			b["t"] = time.time()
		except Exception:
			b["t"] = time.time() - BLOCKLIST_TTL + 15 * 60  # try again in 15 minutes
		b["busy"] = False

	b["busy"] = True
	th = threading.Thread(target=work, name="MohammedSkinBlocklist")
	th.daemon = True
	th.start()


def adult_text(text, level=None):
	"""True when an EPG title / description says it is adult content."""
	level = level or adult_level()
	if level in ("off", "channels") or not text:
		return False
	text = _norm_text(text)
	low = text.lower()
	refresh_blocklist()
	if _ADULT_TEXT.search(text):
		return True
	if any(w in low for w in _blocklist["words"]):
		return True
	return level == "strict" and bool(_STRICT_TEXT.search(text))


def adult_channel(name, level=None):
	level = level or adult_level()
	if level == "off" or not name:
		return False
	name = _norm_text(name)
	refresh_blocklist()
	low = name.lower()
	if any(c in low for c in _blocklist["channels"]):
		return True
	return bool(_ADULT_CHANNEL.search(name))


def adult_event(event, channel_name=""):
	"""Block posters for this EPG event / channel without asking the internet."""
	level = adult_level()
	if level == "off":
		return False
	if channel_name and adult_channel(channel_name, level):
		return True
	if event is None or level == "channels":
		return False
	try:
		name = event.getEventName() or ""
		short = event.getShortDescription() or ""
	except Exception:
		return False
	title = clean_title(name)[0].lower()
	if title and title in _blocklist["titles"]:
		return True
	return adult_text(name + " \n " + short, level)


def _keyword_hit(names, level):
	for n in names:
		n = (n or "").lower()
		if any(k in n for k in ADULT_KEYWORDS):
			return True
		if level == "strict" and any(k == n or n.startswith(k + " ") or n.endswith(" " + k) or k in n for k in STRICT_KEYWORDS):
			return True
		if level == "family" and any(k in n for k in FAMILY_KEYWORDS):
			return True
	return False


def _cert_hit(certs, level):
	certs = set((c or "").strip().upper() for c in certs if c)
	if certs & set(ADULT_CERTS):
		return True
	return level == "strict" and bool(certs & set(STRICT_CERTS))


def tmdb_details(mt, tid, key, headers):
	"""Details of a TMDB title with keywords, age ratings and pictures, in one request (None on failure)."""
	if mt not in ("movie", "tv") or not tid:
		return None
	extra = "keywords,release_dates,images,alternative_titles,translations" if mt == "movie" else "keywords,content_ratings,images,alternative_titles,translations"
	url = "https://api.themoviedb.org/3/%s/%s?append_to_response=%s&include_image_language=ar,en,null" % (mt, tid, extra)
	if not key.startswith("eyJ"):
		url += "&api_key=" + key
	return get_json(url, headers)


def tmdb_adult(r, key, headers, details=False):
	"""Check one TMDB search result with its keywords and age ratings."""
	level = adult_level()
	if level in ("off", "channels"):
		return bool(r.get("adult"))
	refresh_blocklist()
	mt, tid = r.get("media_type"), r.get("id")
	if r.get("adult"):
		return True
	if ("%s:%s" % (mt, tid)) in _blocklist["ids"]:
		return True
	title = (r.get("title") or r.get("name") or "").lower()
	orig = (r.get("original_title") or r.get("original_name") or "").lower()
	if title in _blocklist["titles"] or orig in _blocklist["titles"]:
		return True
	if adult_text(" ".join((r.get("title") or r.get("name") or "", r.get("overview") or "")), level):
		return True
	d = details if details is not False else tmdb_details(mt, tid, key, headers)
	if not d:
		return False  # no answer: do not hide a poster just because the network is slow
	if d.get("adult"):
		return True
	kw = d.get("keywords") or {}
	names = [k.get("name") for k in (kw.get("keywords") or kw.get("results") or [])]
	if _keyword_hit(names, level):
		return True
	certs = []
	if mt == "movie":
		for c in (d.get("release_dates") or {}).get("results", []):
			for rd in c.get("release_dates", []):
				certs.append(rd.get("certification"))
	else:
		for c in (d.get("content_ratings") or {}).get("results", []):
			certs.append(c.get("rating"))
	return _cert_hit(certs, level)


BLOCKED = {"blocked": True}


def add_rating(r, q, year):
	"""Ratings come with the TMDB, TVmaze and OMDb results; nothing else to fetch."""
	return r


def tmdb_scenes(tmdb_id, tmdb_type, skip=None):
	"""Scene stills (backdrops) for a TMDB title, small size."""
	key = tmdb_key()
	if not key or not tmdb_id or tmdb_type not in ("movie", "tv"):
		return []
	url = "https://api.themoviedb.org/3/%s/%s/images?include_image_language=null,en" % (tmdb_type, tmdb_id)
	headers = None
	if key.startswith("eyJ"):
		headers = {"Authorization": "Bearer " + key}
	else:
		url += "&api_key=" + key
	data = get_json(url, headers) or {}
	out = []
	for b in data.get("backdrops", []):
		fp = b.get("file_path")
		if fp and fp != skip:
			out.append("https://image.tmdb.org/t/p/w300" + fp)
		if len(out) >= SCENES:
			break
	return out


def src_tvmaze(q, year, kind):
	data = get_json("https://api.tvmaze.com/singlesearch/shows?q=" + quote(q.encode("utf-8")))
	if not data or not data.get("image") or title_sim(q, data.get("name") or "") < sim_needed(q):
		return None
	level = adult_level()
	if level not in ("off", "channels") and ("Adult" in (data.get("genres") or []) or adult_text(data.get("name") or "", level)
			or (level == "strict" and adult_text(re.sub(r"<[^>]+>", " ", data.get("summary") or ""), level))):
		return BLOCKED
	img = data["image"].get("original") or data["image"].get("medium")
	out = {"poster": img, "kind": "series", "year": (data.get("premiered") or "")[:4], "genres": (data.get("genres") or [])[:2]}
	avg = (data.get("rating") or {}).get("average")
	if avg:
		out["rating"], out["rating_src"] = float(avg), "TVmaze"
	imdb_id = (data.get("externals") or {}).get("imdb")
	if imdb_id:
		out["imdb"] = imdb_id
	if settings().get("backdrops", True) and data.get("id"):
		imgs = get_json("https://api.tvmaze.com/shows/%s/images" % data["id"]) or []
		scenes = []
		for i in imgs:
			if i.get("type") == "background":
				res = i.get("resolutions", {})
				big = (res.get("original") or res.get("medium") or {}).get("url")
				small = (res.get("medium") or res.get("original") or {}).get("url")
				if big and "backdrop" not in out:
					out["backdrop"] = big
				elif small:
					scenes.append(small)
		out["scenes"] = scenes[:SCENES]
	return out


def src_itunes(q, year, kind):
	data = get_json("https://itunes.apple.com/search?media=movie&entity=movie&limit=5&term=" + quote(q.encode("utf-8")))
	if not data:
		return None
	res = data.get("results", [])
	if year:
		res = sorted(res, key=lambda r: (r.get("releaseDate", "")[:4] != year))
	level = adult_level()
	for r in res:
		if title_sim(q, r.get("trackName") or "") < sim_needed(q) or _years_clash(year, (r.get("releaseDate") or "")[:4]):
			continue
		art = r.get("artworkUrl100")
		if level not in ("off", "channels") and (_cert_hit([r.get("contentAdvisoryRating")], level) or adult_text(r.get("trackName") or "", level)
				or r.get("primaryGenreName", "").lower() in ("adult", "erotic", "erotica")):
			return BLOCKED
		if art:
			return {"poster": art.replace("100x100bb", "400x600bb"), "kind": "film"}
	return None


def src_imdb(q, year, kind):
	if adult_level() == "strict":
		return None  # IMDb suggestions carry no age rating; strict mode does not trust them
	first = q[0].lower() if q and q[0].isalnum() and ord(q[0]) < 128 else "x"
	data = get_json("https://v3.sg.media-imdb.com/suggestion/%s/%s.json" % (first, quote(q.encode("utf-8"))))
	if not data:
		return None
	cands = [d for d in data.get("d", []) if d.get("i") and d.get("q") in ("feature", "TV series", "TV mini-series", "TV movie")]
	if year:
		cands.sort(key=lambda d: str(d.get("y", "")) != year)
	for d in cands:
		if title_sim(q, d.get("l") or "") < sim_needed(q) or _years_clash(year, str(d.get("y") or "")):
			continue
		if adult_text(d.get("l") or ""):
			return BLOCKED
		url = d["i"].get("imageUrl")
		if url:
			url = re.sub(r"\._V1_.*?\.jpg$", "._V1_SX400.jpg", url)
			return {"poster": url, "kind": "film" if d.get("q") in ("feature", "TV movie") else "series",
				"imdb": d.get("id"), "year": str(d.get("y") or "")}
	return None


def src_omdb(q, year, kind):
	key = settings().get("omdb", "").strip()
	if not key:
		return None
	url = "https://www.omdbapi.com/?apikey=%s&t=%s" % (key, quote(q.encode("utf-8")))
	if year:
		url += "&y=" + year
	data = get_json(url)
	if not data or data.get("Response") != "True" or not data.get("Poster", "").startswith("http"):
		return None
	if title_sim(q, data.get("Title") or "") < sim_needed(q):
		return None
	level = adult_level()
	if level not in ("off", "channels") and (_cert_hit([data.get("Rated")], level) or "adult" in (data.get("Genre") or "").lower()
			or adult_text(data.get("Title") or "", level)):
		return BLOCKED
	out = {"poster": data["Poster"], "kind": "series" if data.get("Type") == "series" else "film",
		"imdb": data.get("imdbID"), "year": (data.get("Year") or "")[:4],
		"genres": [g.strip() for g in (data.get("Genre") or "").split(",") if g.strip() and g.strip() != "N/A"][:2]}
	try:
		out["rating"], out["rating_src"] = float(data.get("imdbRating")), "IMDb"
	except (TypeError, ValueError):
		pass
	return out


def fanart_backdrop(tmdb_id, tmdb_type):
	key = settings().get("fanart", "").strip()
	if not key or not tmdb_id or tmdb_type != "movie":
		return None
	data = get_json("https://webservice.fanart.tv/v3/movies/%s?api_key=%s" % (tmdb_id, key))
	if data:
		for k in ("moviebackground", "moviethumb"):
			for i in data.get(k, []):
				if i.get("url"):
					return i["url"]
	return None


def lookup(title, year, kind, arabic=False, extra=()):
	"""Ask the sources in a sensible order until a poster that really matches is found."""
	if adult_level() not in ("off", "channels") and (title.lower() in _blocklist["titles"] or adult_text(title)):
		return BLOCKED
	tm = lambda q, y, k: src_tmdb(q, y, k, arabic)
	if _ARABIC.search(title) or (arabic and tmdb_key()):
		order = [tm, src_omdb]  # Arabic channels: TMDB knows the Arabic titles; the others only slow it down
	elif kind == "series":
		order = [tm, src_tvmaze, src_imdb, src_omdb, src_itunes]
	else:
		order = [tm, src_itunes, src_imdb, src_omdb, src_tvmaze]
	queries = query_variants(title, arabic)
	for e in extra or ():  # e.g. the Arabic name an Arabic channel gives in the short description
		if e and e not in queries:
			queries.append(e)
	for q in queries:
		for src in order:
			try:
				r = src(q, year, kind)
			except Exception:
				r = None
			if r and r.get("blocked"):
				return BLOCKED  # same title elsewhere would show the same picture: stop here
			if r and r.get("poster"):
				if not r.get("backdrop") and settings().get("backdrops", True):
					b = fanart_backdrop(r.get("tmdb"), r.get("tmdb_type"))
					if b:
						r["backdrop"] = b
				if "scenes" not in r and r.get("tmdb") and settings().get("backdrops", True):
					skip = (r.get("backdrop") or "").split("/t/p/w1280")[-1] or None
					try:
						r["scenes"] = tmdb_scenes(r.get("tmdb"), r.get("tmdb_type"), skip)
					except Exception:
						r["scenes"] = []
				return add_rating(r, q, year)
	return None


# ---------------------------------------------------------------- cache + workers

_lock = threading.Lock()
_memo = {}        # key -> {"poster": path|None, "backdrop": path|None, "kind": str, "t": time}
_inflight = {}    # key -> [callbacks]


def cache_key(title, year):
	raw = (u"%s|%s" % (title.lower(), year or "")).encode("utf-8")
	return md5(raw).hexdigest()


def _prune():
	try:
		files = [os.path.join(CACHE_DIR, f) for f in os.listdir(CACHE_DIR) if f != "index.json"]
		limit = MAX_CACHE_FILES if CACHE_DIR.startswith("/tmp") else 2000
		if len(files) > limit:
			files.sort(key=lambda p: os.path.getmtime(p))
			for p in files[:len(files) - limit]:
				os.remove(p)
	except Exception:
		pass


def cached(key):
	"""Return a memo entry if it is usable now, else None."""
	with _lock:
		e = _memo.get(key)
	if e is None:
		return None
	if e.get("poster") is None and time.time() - e["t"] > NEGATIVE_TTL:
		return None
	for k in ("poster", "backdrop", "poster_ar"):
		if e.get(k) and not os.path.exists(e[k]):  # cache cleared
			return None
	for sp in e.get("scenes") or []:
		if not os.path.exists(sp):
			return None
	return e


def _work(key, title, year, kind, arabic=False, extra=()):
	entry = {"poster": None, "backdrop": None, "scenes": [], "kind": kind, "t": time.time(),
		"rating": None, "votes": 0, "rating_src": "", "year": year or "", "genres": []}
	try:
		if not os.path.isdir(CACHE_DIR):
			os.makedirs(CACHE_DIR)
		r = lookup(title, year, kind, arabic, extra)
		if r and r.get("blocked"):
			entry["blocked"] = True
			r = None
		if r:
			entry["kind"] = r.get("kind") or kind
			for k in ("rating", "votes", "rating_src", "genres"):
				if r.get(k):
					entry[k] = r[k]
			entry["year"] = r.get("year") or entry["year"]
			# all pictures at the same time: much quicker than one after the other
			jobs = [("poster", r["poster"], os.path.join(CACHE_DIR, key + "_p.jpg"))]
			if r.get("backdrop"):
				jobs.append(("backdrop", r["backdrop"], os.path.join(CACHE_DIR, key + "_b.jpg")))
			if r.get("poster_ar_url"):
				jobs.append(("poster_ar", r["poster_ar_url"], os.path.join(CACHE_DIR, key + "_pa.jpg")))
			for i, url in enumerate((r.get("scenes") or [])[:SCENES]):
				jobs.append(("scene%d" % i, url, os.path.join(CACHE_DIR, "%s_s%d.jpg" % (key, i))))
			done = {}

			def fetch(name, url, path):
				if download(url, path):
					done[name] = path
			threads = [threading.Thread(target=fetch, args=j) for j in jobs]
			for t in threads:
				t.daemon = True
				t.start()
			for t in threads:
				t.join(TIMEOUT + 4)
			for k in ("poster", "backdrop", "poster_ar"):
				if done.get(k):
					entry[k] = done[k]
			entry["scenes"] = [done["scene%d" % i] for i in range(SCENES) if done.get("scene%d" % i)]
		# no blurred "backdrop" made from the poster any more: with no real backdrop the 3D channel logo is shown
		_prune()
	except Exception:
		pass
	with _lock:
		_memo[key] = entry
		cbs = _inflight.pop(key, [])
	for cb in cbs:
		_deliver(cb, entry)
	_save_index()


# ---- posters kept on the disk: the list of what was found is kept with them, so nothing is fetched twice

_index_saved = [0.0]


def _save_index(force=False):
	if CACHE_DIR.startswith("/tmp"):
		return
	now = time.time()
	if not force and now - _index_saved[0] < 20:
		return
	_index_saved[0] = now
	try:
		with _lock:
			data = {"v": SKIN_VERSION, "e": dict((k, v) for k, v in _memo.items() if v.get("poster") or v.get("blocked"))}
		tmp = os.path.join(CACHE_DIR, "index.json.part")
		with open(tmp, "w") as f:
			json.dump(data, f)
		os.rename(tmp, os.path.join(CACHE_DIR, "index.json"))
	except Exception:
		pass


def set_cache_dir():
	"""Use the place chosen in the setup (RAM or disk); posters kept on the disk are known again at once."""
	global CACHE_DIR
	CACHE_DIR = _cache_location()
	with _lock:
		_memo.clear()
	if CACHE_DIR.startswith("/tmp"):
		return CACHE_DIR
	try:
		if not os.path.isdir(CACHE_DIR):
			os.makedirs(CACHE_DIR)
		with open(os.path.join(CACHE_DIR, "index.json")) as f:
			data = json.load(f)
		if data.get("v") == SKIN_VERSION:  # a new version may match titles better: look again
			with _lock:
				_memo.update(data.get("e") or {})
	except Exception:
		pass
	return CACHE_DIR


def _deliver(cb, entry):
	try:
		from twisted.internet import reactor
		reactor.callFromThread(cb, entry)
	except Exception:
		pass


_NO_EVENT = re.compile(u"^(no (event|information|info|data|epg|programme|program)( available)?|information|n/?a|tba|tbd|"
	u"لا توجد معلومات|لا يوجد برنامج|لا توجد بيانات|لا يوجد|غير متوفر|keine informationen|pas d'information|aucune information|bilgi yok)$", re.I)


def arabic_alt_title(event):
	"""Arabic channels often give the English title as the name and the Arabic one in the short description."""
	try:
		desc = (event.getShortDescription() or "").strip()
	except Exception:
		return ""
	try:
		desc = desc.decode("utf-8", "ignore")
	except AttributeError:
		pass
	first = re.split(u"[\n.\u060c،:|-]", desc)[0].strip()
	if not _ARABIC.search(first) or len(first.split()) > 6:
		return ""
	return clean_title(first)[0]


def no_event_title(title):
	"""Guide placeholders such as "No Information" are not a programme: never look a poster up for them."""
	t = (title or "").strip().strip(".:-").strip()
	return len(t) < 2 or bool(_NO_EVENT.match(t))


def request(title, year, kind, callback, arabic=False, extra=()):
	"""Fetch art for title in the background; callback(entry) runs on the GUI thread."""
	key = cache_key(title, year)
	e = cached(key)
	if e is not None:
		return e
	with _lock:
		if key in _inflight:
			_inflight[key].append(callback)
			return None
		_inflight[key] = [callback]
	t = threading.Thread(target=_work, args=(key, title, year, kind, arabic, tuple(extra or ())))
	t.daemon = True
	t.start()
	return None


def blurred_backdrop(poster, out):
	"""Fallback backdrop made from the poster colours (needs python3-pillow)."""
	try:
		from PIL import Image, ImageFilter
		im = Image.open(poster).convert("RGB")
		w, h = im.size
		crop = im.crop((0, int(h * 0.15), w, int(h * 0.15) + int(w * 9 / 16)))
		crop = crop.resize((320, 180)).filter(ImageFilter.GaussianBlur(14)).resize((780, 439))
		crop.save(out, "JPEG", quality=80)
		return out
	except Exception:
		return None


def cover_crop(path, w, h):
	"""Centre-crop a picture to the w:h shape of its widget (so a round or square widget is filled).
	Needs python3-pillow; without it the original picture is returned unchanged."""
	if not path or w <= 0 or h <= 0:
		return path
	out = "%s_c%dx%d.jpg" % (os.path.splitext(path)[0], w, h)
	if os.path.exists(out):
		return out
	try:
		from PIL import Image
		im = Image.open(path).convert("RGB")
		iw, ih = im.size
		want = float(w) / h
		if float(iw) / ih > want:
			nw = int(ih * want)
			im = im.crop(((iw - nw) // 2, 0, (iw - nw) // 2 + nw, ih))
		else:
			nh = int(iw / want)
			top = max(0, int((ih - nh) * 0.35))  # keep faces: a little above the middle
			im = im.crop((0, top, iw, top + nh))
		im = im.resize((w, h), Image.LANCZOS if hasattr(Image, "LANCZOS") else Image.ANTIALIAS)
		im.save(out + ".part", "JPEG", quality=88)
		os.rename(out + ".part", out)
		return out
	except Exception:
		return path


_crop_busy = {}


def cover_crop_async(path, w, h, callback):
	"""Like cover_crop, but the crop is made in the background so the GUI never waits for Pillow
	(weak receivers froze for a moment on OK in the channel list). Returns the picture to show when it
	is ready now; else None and callback(path) runs on the GUI thread later (the original picture when
	the crop cannot be made)."""
	if not path or w <= 0 or h <= 0:
		return path
	out = "%s_c%dx%d.jpg" % (os.path.splitext(path)[0], w, h)
	if os.path.exists(out):
		return out
	with _lock:
		if out in _crop_busy:
			_crop_busy[out].append(callback)
			return None
		_crop_busy[out] = [callback]

	def work():
		try:
			res = cover_crop(path, w, h)
		except Exception:
			res = path
		with _lock:
			cbs = _crop_busy.pop(out, [])
		for cb in cbs:
			try:
				from twisted.internet import reactor
				reactor.callFromThread(cb, res)
			except Exception:
				pass
	th = threading.Thread(target=work, name="MohammedSkinCrop")
	th.daemon = True
	th.start()
	return None


def clear_cache():
	with _lock:
		_memo.clear()
	try:
		for f in os.listdir(CACHE_DIR):
			os.remove(os.path.join(CACHE_DIR, f))
	except Exception:
		pass


# ---------------------------------------------------------------- themes

SKIN_DIR = "/usr/share/enigma2/MohammedSkin"
# skin.xml colour name -> key in themes.json, and the alpha byte to keep
THEME_COLORS = (("crimson", "accent", "00"), ("ember", "accent2", "00"), ("neonred", "neon", "00"),
	("ink", "ink", "00"), ("panel", "ink", "14"), ("line", "line", "00"), ("ivorydim", "ivorydim", "00"))


def selection_colors(theme):
	"""The selection bar and the text on it, readable in every theme: a light theme colour (white, black/silver)
	gets dark text, or its darker selection colour when the theme has one."""
	sel = (theme.get("sel_accent") or theme.get("accent") or "#C8102E").lstrip("#")
	try:
		r, g, b = int(sel[0:2], 16), int(sel[2:4], 16), int(sel[4:6], 16)
		light = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
	except ValueError:
		light = 0.3
	fg = "#00" + (theme.get("ink", "#050506").lstrip("#").upper() if light > 0.62 else "FFFFFF")
	return "#00" + sel.upper(), fg


def load_themes(base=SKIN_DIR):
	try:
		with open(os.path.join(base, "themes", "themes.json")) as f:
			return json.load(f)
	except Exception:
		return {}


def _picture(stem):
	for ext in (".jpg", ".png"):
		if os.path.isfile(stem + ext):
			return stem + ext
	return None


def theme_preview(name, base=SKIN_DIR):
	return (_picture(os.path.join(base, "themes", name, "preview")) or _picture(os.path.join(base, "previews", "theme", name))
		or _picture(os.path.join(base, "themes", "red", "preview")) or "")


# ---- colour themes that are made on the box from the red one (keeps the download small)

RED_ACCENT = "#C8102E"


SHIPPED_THEMES = ("red", "blue", "turquoise", "gold", "black", "white")


def theme_missing(name, base=SKIN_DIR):
	"""True when this colour has to be made on the box first (new colours, or made by an older version)."""
	if name in SHIPPED_THEMES or name not in load_themes(base):
		return False
	try:
		with open(os.path.join(base, "themes", name, ".made")) as f:
			return f.read().strip() != _red_stamp(base)
	except Exception:
		return True


def _red_stamp(base=SKIN_DIR):
	"""Fingerprint of the red pictures and the colour values: a made colour is only made again when one of them
	changed in an update, not after every update."""
	import hashlib
	h = hashlib.md5()
	src = os.path.join(base, "themes", "red")
	for root, dirs, files in os.walk(src):
		dirs.sort()
		for fn in sorted(files):
			p = os.path.join(root, fn)
			try:
				h.update(("%s:%d;" % (os.path.relpath(p, src), os.path.getsize(p))).encode("utf-8"))
			except Exception:
				pass
	h.update(json.dumps(load_themes(base), sort_keys=True).encode("utf-8"))
	return h.hexdigest()


def _hsv255(hexc):
	import colorsys
	h = hexc.lstrip("#")
	r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
	return tuple(int(round(x * 255)) for x in colorsys.rgb_to_hsv(r, g, b))


def recolor_png(src, dst, target):
	"""Copy of a red-theme picture in another accent colour (Pillow)."""
	from PIL import Image, ImageChops
	im = Image.open(src)
	rgba = im.convert("RGBA")
	alpha = rgba.split()[3]
	h, s, v = rgba.convert("RGB").convert("HSV").split()
	rh, rs, rv = _hsv255(RED_ACCENT)
	th, ts, tv = _hsv255(target)
	mask = ImageChops.multiply(h.point(lambda x: 255 if (x > 224 or x < 15) else 0), s.point(lambda x: 255 if x > 25 else 0))
	if not os.path.isdir(os.path.dirname(dst)):
		os.makedirs(os.path.dirname(dst))
	if mask.getbbox() is None:  # nothing red in it: a plain copy is much quicker
		import shutil
		shutil.copyfile(src, dst + ".part")
		os.rename(dst + ".part", dst)
		return
	h = Image.composite(Image.new("L", h.size, th), h, mask)
	s = Image.composite(s.point(lambda x: min(255, int(x * ts / float(max(rs, 1))))), s, mask)
	v = Image.composite(v.point(lambda x: min(255, int(x * (0.55 + 0.45 * tv / float(max(rv, 1)))))), v, mask)
	out = Image.merge("HSV", (h, s, v)).convert("RGB")
	out.putalpha(alpha)
	if not os.path.isdir(os.path.dirname(dst)):
		os.makedirs(os.path.dirname(dst))
	out.save(dst + ".part", "PNG", compress_level=1)
	os.rename(dst + ".part", dst)


def make_theme(name, base=SKIN_DIR, progress=None):
	"""Make themes/<name> and the clocks in that colour from the red theme. Returns True when done."""
	import shutil
	t = load_themes(base).get(name)
	if not t:
		return False
	try:
		from PIL import Image  # noqa
	except ImportError:
		return False
	for d in [os.path.join(base, "themes", name), os.path.join(base, "themes", name + ".part")] + \
			[os.path.join(base, "clocks", c, n) for c in os.listdir(os.path.join(base, "clocks")) for n in (name, name + ".part")]:
		if os.path.isdir(d):
			shutil.rmtree(d)
	jobs = []
	src = os.path.join(base, "themes", "red")
	for root, dirs, files in os.walk(src):
		for fn in files:
			jobs.append((os.path.join(root, fn), os.path.join(base, "themes", name + ".part", os.path.relpath(os.path.join(root, fn), src))))
	clocks = []  # clock frames in this colour are made when that clock is used (clock_frames_ready)
	for d in [os.path.join(base, "themes", name + ".part")] + [os.path.join(base, "clocks", c, name + ".part") for c in clocks]:
		if not os.path.isdir(d):
			os.makedirs(d)
	for i, (sp, dp) in enumerate(jobs):
		fn = os.path.basename(sp)
		if fn.startswith("preview."):
			continue
		if fn.endswith(".png"):
			# light themes keep the selection bars darker so the white text on them stays readable
			recolor_png(sp, dp, t.get("sel_accent", t["accent"]) if "sel" in fn else t["accent"])
		else:
			if not os.path.isdir(os.path.dirname(dp)):
				os.makedirs(os.path.dirname(dp))
			shutil.copyfile(sp, dp)
		if progress and i % 20 == 0:
			progress(i, len(jobs))
	for c in clocks:
		os.rename(os.path.join(base, "clocks", c, name + ".part"), os.path.join(base, "clocks", c, name))
	with open(os.path.join(base, "themes", name + ".part", ".made"), "w") as f:
		f.write(_red_stamp(base))
	os.rename(os.path.join(base, "themes", name + ".part"), os.path.join(base, "themes", name))
	return True


def apply_theme(name, base=SKIN_DIR):
	"""Copy the theme's images into img/ and rewrite the theme colours in skin.xml.
	Returns True on success. A GUI restart is needed to see the change."""
	import shutil
	themes = load_themes(base)
	if name not in themes:
		return False
	t = themes[name]
	if theme_missing(name, base) and not make_theme(name, base):
		return False
	src = os.path.join(base, "themes", name)
	dst = os.path.join(base, "img")
	for root, dirs, files in os.walk(src):
		rel = os.path.relpath(root, src)
		out = os.path.join(dst, rel) if rel != "." else dst
		if not os.path.isdir(out):
			os.makedirs(out)
		for fn in files:
			if fn.startswith("preview."):
				continue
			shutil.copyfile(os.path.join(root, fn), os.path.join(out, fn))
	skin = os.path.join(base, "skin.xml")
	with open(skin) as f:
		xml = f.read()
	for cname, key, alpha in THEME_COLORS:
		value = "#" + alpha + t[key].lstrip("#").upper()
		xml = re.sub(r'(<color name="%s" value=")#[0-9A-Fa-f]{8}(")' % cname, r"\g<1>%s\g<2>" % value, xml)
	sel, fg = selection_colors(t)
	for cname, value in (("selbg", sel), ("selfg", fg)):
		if '<color name="%s"' % cname in xml:
			xml = re.sub(r'(<color name="%s" value=")#[0-9A-Fa-f]{8}(")' % cname, r"\g<1>%s\g<2>" % value, xml)
		else:
			xml = xml.replace("<colors>", '<colors>\n\t\t<color name="%s" value="%s" />' % (cname, value), 1)
	ink = "#00" + t["ink"].lstrip("#").upper()
	xml = re.sub(r'fill="#00[0-9A-Fa-f]{6}"', 'fill="%s"' % ink, xml)
	tmp = skin + ".tmp"
	with open(tmp, "w") as f:
		f.write(xml)
	os.rename(tmp, skin)
	s = dict(settings())
	s["theme"] = name
	save_settings(s)
	clock = s.get("clock", "royal")
	if os.path.isdir(os.path.join(base, "clocks", clock)):
		install_clock_files(clock, name, base)
	try:
		apply_plugin_fonts(base)  # plugin tiles follow the colour
	except Exception:
		pass
	return True


# ---------------------------------------------------------------- translation (Arabic)

_tr_cache = {}
_tr_inflight = {}
_tr_lock = threading.Lock()
TR_MAX = 1800
TR_RETRY = 120  # seconds before a failed translation is tried again
_tr_failed = {}


def is_arabic(text):
	return bool(text) and len(_ARABIC.findall(text)) > len(text) * 0.3


def parse_google(data):
	"""Google gtx returns [[["translated","original",...], ...], ...]."""
	try:
		return "".join(seg[0] for seg in data[0] if seg and seg[0]).strip()
	except Exception:
		return ""


def parse_mymemory(data):
	try:
		txt = data["responseData"]["translatedText"].strip()
		if "MYMEMORY WARNING" in txt.upper() or "QUERY LENGTH LIMIT" in txt.upper():
			return ""
		return txt
	except Exception:
		return ""


TR_TIMEOUT = 12  # translations are slower than pictures; never cut them short


def _chunks(text, size=450):
	"""Split long text at sentence ends so every request stays short (long requests get refused)."""
	text = text[:TR_MAX]
	if len(text) <= size:
		return [text]
	parts, cur = [], ""
	for piece in re.split(r"(?<=[.!?\n])\s+", text):
		while len(piece) > size:  # one very long sentence: cut at a space
			cut = piece.rfind(" ", 0, size)
			cut = cut if cut > size // 2 else size
			if cur:
				parts.append(cur)
				cur = ""
			parts.append(piece[:cut])
			piece = piece[cut:].strip()
		if len(cur) + len(piece) + 1 > size and cur:
			parts.append(cur)
			cur = piece
		else:
			cur = (cur + " " + piece).strip()
	if cur:
		parts.append(cur)
	return parts


def _google_unused(text, target):
	url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=%s&dt=t" % target
	body = ("q=" + quote(text.encode("utf-8"))).encode("ascii")
	out = parse_google(get_json(url, {"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"}, TR_TIMEOUT, body) or [])
	if not out:  # some networks refuse POST: try the plain request
		out = parse_google(get_json(url + "&q=" + quote(text.encode("utf-8")), None, TR_TIMEOUT) or [])
	return out


# Google answers "too many requests" to the skin's own name in the request, while the same
# request from a plain download tool still works: ask like a browser, then like wget.
TR_AGENTS = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
	"Wget/1.21.4")
_tr_agent = [0]


def _tr_tool(url, raw=False):
	"""Fetch with the box's own wget (or curl). Google refuses Python's requests from some boxes
	while the same address works from wget."""
	import subprocess
	for cmd in (["wget", "-q", "--no-check-certificate", "-T", str(TR_TIMEOUT), "-U", TR_AGENTS[0], "-O", "-", url],
			["curl", "-ksSL", "-m", str(TR_TIMEOUT), "-A", TR_AGENTS[0], url]):
		try:
			p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			out, err = p.communicate()
		except Exception:
			continue  # this tool is not on the box
		if p.returncode == 0 and out:
			text = out.decode("utf-8", "ignore")
			if raw:
				return text
			try:
				return json.loads(text)
			except Exception:
				pass
	return None


def _tr_get(url, raw=False, block=True):
	"""JSON (or the raw page) from a translation address; failures are written to the enigma2 log."""
	if _tr_agent[0] == -1:  # wget worked last time: go straight to it
		data = _tr_tool(url, raw)
		if data is not None:
			return data
	last = None
	for n in range(len(TR_AGENTS)):
		i = n if _tr_agent[0] < 0 else (_tr_agent[0] + n) % len(TR_AGENTS)
		try:
			r = _open(url, {"User-Agent": TR_AGENTS[i], "Accept": "application/json,text/html,*/*"}, TR_TIMEOUT)
			text = r.read().decode("utf-8", "ignore")
			data = text if raw else json.loads(text)
			_tr_agent[0] = i  # keep using the one that works
			return data
		except Exception as e:
			last = e
			if getattr(e, "code", 0) not in (403, 429):
				break  # not a refusal (network, timeout): another name will not help
	if getattr(last, "code", 0) in (403, 429) and _tr_agent[0] != -1:
		data = _tr_tool(url, raw)
		if data is not None:
			_tr_agent[0] = -1  # remember: use wget from now on
			return data
	print("[MohammedSkin] translate: %s: %s" % (url.split("?")[0], last))
	if block and getattr(last, "code", 0) in (403, 429, 503):  # refused every way: rest Google a while
		_tr_block["google"] = time.time() + 600
	return None


def _parse_mobile(page):
	"""Text of <div class="result-container"> in Google's mobile translate page."""
	m = re.search(r'class="result-container"[^>]*>(.*?)</div>', page or "", re.S)
	if not m:
		return ""
	try:
		from html import unescape
	except ImportError:
		from HTMLParser import HTMLParser
		unescape = HTMLParser().unescape
	return unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()


# ---- Bing (Microsoft) web translator: free, no key, works from each box's own internet address

_bing = {"t": 0, "ig": "", "iid": "", "key": "", "token": "", "opener": None}


def _bing_session():
	"""Read the tokens Bing's translator page gives every visitor (valid for a while)."""
	if _bing["token"] and time.time() - _bing["t"] < 1800:
		return True
	try:
		try:
			from http.cookiejar import CookieJar
			from urllib.request import build_opener, HTTPCookieProcessor, HTTPSHandler
		except ImportError:
			from cookielib import CookieJar
			from urllib2 import build_opener, HTTPCookieProcessor, HTTPSHandler
		ctx = _ssl_ctx or ssl.create_default_context()
		opener = build_opener(HTTPCookieProcessor(CookieJar()), HTTPSHandler(context=ctx))
		opener.addheaders = [("User-Agent", TR_AGENTS[0]), ("Accept-Language", "en-US,en;q=0.8")]
		page = opener.open("https://www.bing.com/translator", timeout=TR_TIMEOUT).read().decode("utf-8", "ignore")
		ig = re.search(r'IG:"([A-Za-z0-9]+)"', page)
		iid = re.search(r'data-iid="([^"]+)"', page)
		ap = re.search(r'params_AbusePreventionHelper\s*=\s*\[\s*(\d+)\s*,\s*"([^"]+)"', page)
		if not (ig and ap):
			print("[MohammedSkin] translate bing: page changed")
			_tr_block["bing"] = time.time() + 3600
			return False
		_bing.update(t=time.time(), ig=ig.group(1), iid=(iid.group(1) if iid else "translator.5028"),
			key=ap.group(1), token=ap.group(2), opener=opener)
		return True
	except Exception as e:
		print("[MohammedSkin] translate bing: %s" % e)
		_tr_block["bing"] = time.time() + 300
		return False


def _bing_translate(text, target):
	if time.time() < _tr_block.get("bing", 0) or not _bing_session():
		return ""
	out = []
	for part in _chunks(text, 900):
		body = ("fromLang=auto-detect&to=%s&text=%s&token=%s&key=%s" % (MS_CODES.get(target, target), quote(part.encode("utf-8")),
			quote(_bing["token"]), _bing["key"])).encode("ascii")
		url = "https://www.bing.com/ttranslatev3?isVertical=1&&IG=%s&IID=%s.1" % (_bing["ig"], _bing["iid"])
		try:
			r = _bing["opener"].open(Request(url, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"}), timeout=TR_TIMEOUT)
			data = json.loads(r.read().decode("utf-8", "ignore"))
			out.append(data[0]["translations"][0]["text"].strip())
		except Exception as e:
			print("[MohammedSkin] translate bing: %s" % e)
			_bing["token"] = ""  # get fresh tokens next time
			if getattr(e, "code", 0) in (403, 429):
				_tr_block["bing"] = time.time() + 600
			return ""
	return " ".join(out)


def _parse_dict(data):
	"""clients5 'dict-chrome-ex' answer: ["text"] or [["text", "lang"], ...]."""
	try:
		out = []
		for seg in data:
			out.append(seg[0] if isinstance(seg, list) else seg)
		return "".join(x for x in out if isinstance(x, str)).strip()
	except Exception:
		return ""


def _tr_post(name, url, headers, body):
	"""POST for the translation services; errors are logged and 403/429 make that service rest a while."""
	if time.time() < _tr_block.get(name, 0):
		return None
	try:
		r = _open(url, headers, TR_TIMEOUT, body)
		return json.loads(r.read().decode("utf-8", "ignore"))
	except Exception as e:
		print("[MohammedSkin] translate %s: %s" % (name, e))
		if getattr(e, "code", 0) in (401, 403, 429, 503):
			_tr_block[name] = time.time() + (60 if name == "edge" else 600)
			if name == "edge":
				_edge_token[:] = []  # token expired or refused: get a new one next time
		return None


def _google(text, target):
	if time.time() < _tr_block.get("google", 0):
		return ""
	out = []
	for part in _chunks(text, 600):
		q = quote(part.encode("utf-8"))
		res = parse_google(_tr_get("https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=%s&dt=t&q=%s" % (target, q), block=False) or [])
		if not res:
			res = _parse_dict(_tr_get("https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=auto&tl=%s&q=%s" % (target, q), block=False) or [])
		if not res:  # Google's simple mobile page: another door of the same free service
			res = _parse_mobile(_tr_get("https://translate.google.com/m?sl=auto&tl=%s&hl=%s&q=%s" % (target, target, q), raw=True) or "")
		if not res:
			if time.time() >= _tr_block.get("google", 0):
				_tr_block["google"] = time.time() + 300  # every door refused: let Bing work for a while
			return ""
		out.append(res)
	return " ".join(out)


_edge_token = []


def _edge(text, target):
	"""Microsoft's translator as used by the Edge browser (free, no key)."""
	if time.time() < _tr_block.get("edge", 0):
		return ""
	if not _edge_token or time.time() - _edge_token[1] > 480:
		try:
			tok = _open("https://edge.microsoft.com/translate/auth", None, TR_TIMEOUT).read().decode("utf-8", "ignore").strip()
		except Exception as e:
			print("[MohammedSkin] translate edge auth: %s" % e)
			_tr_block["edge"] = time.time() + (6 * 3600 if getattr(e, "code", 0) == 404 else 120)
			return ""
		_edge_token[:] = [tok, time.time()]
	body = json.dumps([{"Text": text[:TR_MAX]}]).encode("utf-8")
	data = _tr_post("edge", "https://api-edge.cognitive.microsofttranslator.com/translate?from=&to=%s&api-version=3.0" % MS_CODES.get(target, target),
		{"Authorization": "Bearer " + _edge_token[0], "Content-Type": "application/json"}, body)
	try:
		return data[0]["translations"][0]["text"].strip()
	except Exception:
		return ""


def _own_key(text, target):
	"""The user's own key from the setup: Microsoft Translator or DeepL."""
	s = settings()
	key = (s.get("tr_key") or "").strip()
	service = s.get("tr_service", "auto")
	if not key or service == "auto":
		return ""
	if service == "deepl":
		host = "api-free.deepl.com" if key.endswith(":fx") else "api.deepl.com"
		body = ("text=%s&target_lang=%s" % (quote(text[:TR_MAX].encode("utf-8")), DEEPL_CODES.get(target, target.upper()))).encode("ascii")
		data = _tr_post("deepl", "https://%s/v2/translate" % host,
			{"Authorization": "DeepL-Auth-Key " + key, "Content-Type": "application/x-www-form-urlencoded"}, body)
		try:
			return data["translations"][0]["text"].strip()
		except Exception:
			return ""
	headers = {"Ocp-Apim-Subscription-Key": key, "Content-Type": "application/json"}
	region = (s.get("tr_region") or "").strip()
	if region:
		headers["Ocp-Apim-Subscription-Region"] = region
	data = _tr_post("microsoft", "https://api.cognitive.microsofttranslator.com/translate?api-version=3.0&to=%s" % MS_CODES.get(target, target),
		headers, json.dumps([{"Text": text[:TR_MAX]}]).encode("utf-8"))
	try:
		return data[0]["translations"][0]["text"].strip()
	except Exception:
		return ""


TR_LANGS = (("ar", u"العربية Arabic"), ("en", "English"), ("tr", u"Türkçe Turkish"), ("fr", u"Français French"),
	("de", "Deutsch German"), ("es", u"Español Spanish"), ("it", "Italiano Italian"), ("fa", u"فارسی Persian"),
	("ur", u"اردو Urdu"), ("ru", u"Русский Russian"), ("nl", "Nederlands Dutch"), ("pl", "Polski Polish"),
	("pt", u"Português Portuguese"), ("id", "Indonesia Indonesian"), ("hi", u"हिन्दी Hindi"),
	("uk", u"Українська Ukrainian"), ("zh-CN", u"中文 Chinese"), ("ja", u"日本語 Japanese"), ("el", u"Ελληνικά Greek"),
	("ro", u"Română Romanian"), ("cs", u"Čeština Czech"), ("sv", "Svenska Swedish"), ("hu", "Magyar Hungarian"),
	("bg", u"Български Bulgarian"))
DEEPL_CODES = {"en": "EN-GB", "pt": "PT-PT", "zh-CN": "ZH"}
MS_CODES = {"zh-CN": "zh-Hans"}  # Microsoft / Bing names for the same languages
CJK = ("zh", "zh-CN", "ja")


def apply_cjk_font(base=SKIN_DIR):
	"""Chinese and Japanese need their own letters: the skin's fonts/fallback.font (picked up by enigma2 for any
	letter the normal fonts lack) is there only while the setup or the translation uses one of them.
	Returns True when it changed (the GUI must restart to load it)."""
	s = settings()
	need = s.get("ui_lang") in CJK or (s.get("translate") and s.get("tr_lang") in CJK) or (s.get("weather", True) and s.get("weather_lang") in CJK)
	src = os.path.join(base, "fonts", "cjk.otf")
	dst = os.path.join(base, "fonts", "fallback.font")
	try:
		if need and os.path.isfile(src) and not os.path.exists(dst):
			import shutil
			shutil.copyfile(src, dst + ".part")
			os.rename(dst + ".part", dst)
			return True
		if not need and os.path.exists(dst):
			os.remove(dst)
			return True
	except Exception as e:
		print("[MohammedSkin] cjk font: %s" % e)
	return False


def tr_target():
	v = settings().get("tr_lang", "ar")
	return v if v in [l[0] for l in TR_LANGS] else "ar"


def translate_now(text, target=None):
	target = target or tr_target()
	"""Your own key first (if set), then Google, then Microsoft (Edge). Returns '' when all fail,
	so the original stays on screen."""
	for fn in (_own_key, _google, _bing_translate):
		try:
			out = fn(text, target)
		except Exception as e:
			print("[MohammedSkin] translate: %s" % e)
			out = ""
		if out and (target != "ar" or is_arabic(out)):  # Arabic: make sure it really is Arabic
			return out
	return ""


# ---- translations kept on the box: programmes repeat, so most are translated only once

TR_FILE = "/etc/enigma2/MohammedSkin_translations.json"
TR_KEEP = 3000
_tr_disk = {"loaded": False, "dirty": 0, "saved": 0}


def _tr_load():
	if _tr_disk["loaded"]:
		return
	_tr_disk["loaded"] = True
	try:
		with open(TR_FILE) as f:
			data = json.load(f)
		for k, v in data.items():
			if v:
				_tr_cache[k] = v
	except Exception:
		pass


def _tr_save(force=False):
	if not _tr_disk["dirty"] or (not force and _tr_disk["dirty"] < 10 and time.time() - _tr_disk["saved"] < 120):
		return
	try:
		with _tr_lock:
			items = [(k, v) for k, v in _tr_cache.items() if v][-TR_KEEP:]
		with open(TR_FILE + ".tmp", "w") as f:
			json.dump(dict(items), f, ensure_ascii=False)
		os.rename(TR_FILE + ".tmp", TR_FILE)
		_tr_disk["dirty"], _tr_disk["saved"] = 0, time.time()
	except Exception as e:
		print("[MohammedSkin] translate save: %s" % e)


_tr_block = {}


_tr_state = {"block_until": 0, "last": 0, "worker": None}
_tr_queue = []  # newest last; only the newest few are translated (the ones on screen)
_tr_cond = threading.Condition(_tr_lock)
TR_QUEUE_MAX = 8
TR_GAP = 0.35  # seconds between two requests: Google blocks boxes that ask too fast


def _tr_worker():
	while True:
		with _tr_cond:
			while not _tr_queue:
				_tr_cond.wait()
			key, text, target = _tr_queue.pop()  # newest first: what is on screen now
		wait = TR_GAP - (time.time() - _tr_state["last"])
		if wait > 0:
			time.sleep(wait)
		res = ""
		try:
			res = translate_now(text, target)
		except Exception as e:
			print("[MohammedSkin] translate: %s" % e)
		_tr_state["last"] = time.time()
		with _tr_lock:
			if len(_tr_cache) > TR_KEEP + 500:
				for k in list(_tr_cache)[:500]:
					del _tr_cache[k]
				_tr_failed.clear()
			_tr_cache[key] = res
			if not res:
				_tr_failed[key] = time.time()
			cbs = _tr_inflight.pop(key, [])
		if res:
			_tr_disk["dirty"] += 1
			_tr_save()
		for cb in cbs:
			try:
				from twisted.internet import reactor
				reactor.callFromThread(cb)
			except Exception:
				pass


def translated(text, callback):
	"""Return the cached Arabic text, or None and queue it for translation (callback() on the GUI thread)."""
	target = tr_target()
	if not text or (target == "ar" and is_arabic(text)):
		return text
	raw = (target + "|" + text) if target != "ar" else text  # Arabic keeps the old keys (saved translations stay valid)
	key = md5(raw.encode("utf-8") if not isinstance(raw, bytes) else raw).hexdigest()
	if not _tr_disk["loaded"]:
		_tr_load()
	with _tr_lock:
		if key in _tr_cache:
			if _tr_cache[key]:
				return _tr_cache[key]
			if time.time() - _tr_failed.get(key, 0) < TR_RETRY:
				return text  # failed a moment ago: show the original, try again a little later
			del _tr_cache[key]
		if key in _tr_inflight:
			if callback not in _tr_inflight[key]:
				_tr_inflight[key].append(callback)
			return None
		_tr_inflight[key] = [callback]
		_tr_queue.append((key, text, target))
		while len(_tr_queue) > TR_QUEUE_MAX:  # scrolled past: forget the old ones
			old = _tr_queue.pop(0)[0]
			_tr_inflight.pop(old, None)
		if _tr_state["worker"] is None:
			th = threading.Thread(target=_tr_worker, name="MohammedSkinTranslate")
			th.daemon = True
			th.start()
			_tr_state["worker"] = th
		_tr_cond.notify()
	return None


# ---------------------------------------------------------------- infobar clocks

CLOCK_ORDER = ("royal", "arabesque", "ornate") + tuple("c%02d" % i for i in range(1, 25)) + ("none",)


def load_clocks(base=SKIN_DIR):
	try:
		with open(os.path.join(base, "clocks", "clocks.json")) as f:
			return json.load(f)
	except Exception:
		return {}


def clock_preview(name, theme, base=SKIN_DIR):
	return (_picture(os.path.join(base, "clocks", name, theme, "preview")) or _picture(os.path.join(base, "clocks", name, "red", "preview"))
		or _picture(os.path.join(base, "clocks", name, "common", "preview")) or "")


def clock_frames_ready(name, theme, base=SKIN_DIR):
	"""Only the red frames of each clock ship (less space and fewer files on the box); the frames in another
	colour are made here from the red ones the first time that clock and colour are used together."""
	red = os.path.join(base, "clocks", name, "red")
	dst = os.path.join(base, "clocks", name, theme)
	if not os.path.isdir(red):
		return os.path.isdir(dst)
	need = [fn for fn in os.listdir(red) if not fn.startswith("preview.") and not os.path.isfile(os.path.join(dst, fn))]
	if not need:
		return True
	t = load_themes(base).get(theme)
	if not t:
		return False
	try:
		import shutil
		if not os.path.isdir(dst):
			os.makedirs(dst)
		for fn in need:
			if fn.endswith(".png"):
				recolor_png(os.path.join(red, fn), os.path.join(dst, fn), t["accent"])
			else:
				shutil.copyfile(os.path.join(red, fn), os.path.join(dst, fn + ".part"))
				os.rename(os.path.join(dst, fn + ".part"), os.path.join(dst, fn))
		return True
	except Exception as e:
		print("[MohammedSkin] clock colour %s/%s failed: %s" % (name, theme, e))
		return False


def install_clock_files(name, theme, base=SKIN_DIR):
	"""Fill <skin>/clock/ with the dial and hand frames of one clock in one colour theme."""
	import shutil
	clocks = load_clocks(base)
	if name not in clocks:
		return False
	src = os.path.join(base, "clocks", name)
	hands = clocks[name].get("hands")  # the new dials use the hands of another clock (one set of frames for all)
	frames = hands if hands in clocks else name
	if theme != "red" and not clock_frames_ready(frames, theme, base):
		theme = "red"
	dst = os.path.join(base, "clock")
	if os.path.isdir(dst):
		for fn in os.listdir(dst):
			os.remove(os.path.join(dst, fn))
	else:
		os.makedirs(dst)
	dirs = [os.path.join(base, "clocks", frames, sub) for sub in ("common", theme)]
	if frames != name:
		dirs.append(os.path.join(src, "common"))  # its own dial last, over the one of the hands' clock
	for d in dirs:
		if not os.path.isdir(d):
			continue
		for fn in os.listdir(d):
			if not fn.startswith("preview."):
				shutil.copyfile(os.path.join(d, fn), os.path.join(dst, fn))
	return True


def apply_clock(name, base=SKIN_DIR):
	"""Switch the infobar clock: copy its frames and swap its block in skin.xml."""
	theme = settings().get("theme", "red")
	if not os.path.isfile(os.path.join(base, "clocks", name, "snippet.xml")):
		return False  # files missing (half update): keep the current clock instead of failing the whole save
	if not install_clock_files(name, theme, base):
		return False
	with open(os.path.join(base, "clocks", name, "snippet.xml")) as f:
		snippet = f.read()
	skin = os.path.join(base, "skin.xml")
	with open(skin) as f:
		xml = f.read()
	snippet = shifted(snippet, xml, "CLOCK")
	# infobar styles without an analog clock have no CLOCK block: the choice is still saved
	new = re.sub(r"[ \t]*<!-- CLOCK START.*?<!-- CLOCK END -->\n?", lambda m: snippet, xml, count=1, flags=re.S)
	tmp = skin + ".tmp"
	with open(tmp, "w") as f:
		f.write(new)
	os.rename(tmp, skin)
	s = dict(settings())
	s["clock"] = name
	save_settings(s)
	return True


# ---------------------------------------------------------------- menu / channel list styles

STYLE_MARKERS = {"infobar": "IB", "menu": "MENU", "channels": "CHANNELS", "sib": "SIB", "ibposter": "IBPOSTER", "image": "WINDOWSTYLE", "dots": "DOTS"}
STYLE_DEFAULTS = {"menu": "classic", "channels": "classic", "sib": "classic", "ibposter": "left"}


def shifted(snippet, xml, marker):
	"""Infobar styles place the clock / running dots elsewhere: they say so with
	<!-- MARKER OFFSET dx,dy --> and every position in the snippet moves by that much."""
	m = re.search(r"<!-- %s OFFSET (-?\d+),(-?\d+) -->" % marker, xml)
	if not m:
		return snippet
	dx, dy = int(m.group(1)), int(m.group(2))
	return re.sub(r'position="(\d+),(\d+)"', lambda p: 'position="%d,%d"' % (int(p.group(1)) + dx, int(p.group(2)) + dy), snippet)


def load_styles(kind, base=SKIN_DIR):
	"""Returns [(name, label), ...] for 'menu' or 'channels'."""
	try:
		with open(os.path.join(base, "styles", kind, "styles.json")) as f:
			data = json.load(f)
		return [(n, data["labels"].get(n, n)) for n in data["order"] if os.path.isfile(os.path.join(base, "styles", kind, n, "snippet.xml"))]
	except Exception:
		return [("classic", "Classic")]


def extra_preview(kind, name, base=SKIN_DIR):
	"""Preview picture of a size / font / transparency / weather choice, or None."""
	for ext in (".jpg", ".png"):
		p = os.path.join(base, "previews", kind, name + ext)
		if os.path.isfile(p):
			return p
	return None


def style_preview(kind, name, theme, base=SKIN_DIR):
	return (_picture(os.path.join(base, "styles", kind, name, theme)) or _picture(os.path.join(base, "styles", kind, name, "red")) or "")


def current_style(kind, base=SKIN_DIR):
	try:
		with open(os.path.join(base, "skin.xml")) as f:
			m = re.search(r"<!-- %s START \((\w+)\) -->" % STYLE_MARKERS[kind], f.read())
		return m.group(1) if m else "classic"
	except Exception:
		return "classic"


def apply_style(kind, name, base=SKIN_DIR):
	"""Swap the Menu or ChannelSelection screen in skin.xml for the chosen style."""
	marker = STYLE_MARKERS[kind]
	try:
		with open(os.path.join(base, "styles", kind, name, "snippet.xml")) as f:
			snippet = f.read()
	except Exception:
		return False
	theme = load_themes(base).get(settings().get("theme", "red"))
	if theme:  # poster fill follows the theme background
		snippet = re.sub(r'fill="#00[0-9A-Fa-f]{6}"', 'fill="#00%s"' % theme["ink"].lstrip("#").upper(), snippet)
	snippet = tune_snippet(kind, snippet, base)
	skin = os.path.join(base, "skin.xml")
	with open(skin) as f:
		xml = f.read()
	pat = r"[ \t]*<!-- %s START.*?<!-- %s END -->\n?" % (marker, marker)
	if not re.search(pat, xml, re.S):
		return False
	snippet = shifted(snippet, xml, marker)
	new = re.sub(pat, lambda m: snippet, xml, count=1, flags=re.S)
	tmp = skin + ".tmp"
	with open(tmp, "w") as f:
		f.write(new)
	os.rename(tmp, skin)
	s = dict(settings())
	s[kind + "_style"] = name
	save_settings(s)
	return True


# ---------------------------------------------------------------- sizes and transparency (setup options)
# Channel list text / rows, plugin list text and the first infobar background are tuned while a
# style is put into skin.xml, so every style (and every later style change) keeps the user's choice.

CH_FONT = (("small", "Small", 0.85), ("normal", "Normal", 1.0), ("large", "Large", 1.15), ("xlarge", "Extra large", 1.3))
CH_ROWS = (("compact", "Compact (more channels)", 0.8), ("normal", "Normal", 1.0), ("large", "Large", 1.2), ("xlarge", "Extra large (fewer channels)", 1.4))
PL_FONT = (("small", "Small", 0.85), ("normal", "Normal", 1.0), ("large", "Large", 1.2), ("xlarge", "Extra large", 1.4))
IB_ALPHA = (("clear", "Very transparent", 0.45), ("light", "Transparent", 0.7), ("normal", "Normal", 1.0),
	("dark", "Dark", 1.35), ("xdark", "Very dark", 1.75))
TUNE_DIR = "tune"  # under img/: generated copies of the infobar background and channel rows


def _factor(table, value):
	for n, label, f in table:
		if n == value:
			return f
	return 1.0


def tune_value(key, table):
	v = settings().get(key, "normal")
	return v if v in [n for n, l, f in table] else "normal"


# ---- PNG helpers: Pillow when it is installed, otherwise a small pure-Python reader/writer (RGBA only)

def _png_read(path):
	import struct
	import zlib
	with open(path, "rb") as f:
		data = f.read()
	if data[:8] != b"\x89PNG\r\n\x1a\n":
		raise ValueError("not a png")
	pos, idat, w = 8, [], 0
	while pos < len(data):
		ln = struct.unpack(">I", data[pos:pos + 4])[0]
		typ = data[pos + 4:pos + 8]
		body = data[pos + 8:pos + 8 + ln]
		if typ == b"IHDR":
			w, h, depth, ctype, comp, filt, inter = struct.unpack(">IIBBBBB", body)
			if depth != 8 or ctype not in (2, 6) or inter:
				raise ValueError("unsupported png")
			bpp = 4 if ctype == 6 else 3
		elif typ == b"IDAT":
			idat.append(body)
		elif typ == b"IEND":
			break
		pos += 12 + ln
	raw = zlib.decompress(b"".join(idat))
	stride = w * bpp
	rows, prev, i = [], bytearray(stride), 0
	for y in range(h):
		ft = raw[i]
		line = bytearray(raw[i + 1:i + 1 + stride])
		i += 1 + stride
		if ft == 1:
			for x in range(bpp, stride):
				line[x] = (line[x] + line[x - bpp]) & 255
		elif ft == 2:
			for x in range(stride):
				line[x] = (line[x] + prev[x]) & 255
		elif ft == 3:
			for x in range(stride):
				left = line[x - bpp] if x >= bpp else 0
				line[x] = (line[x] + ((left + prev[x]) >> 1)) & 255
		elif ft == 4:
			for x in range(stride):
				a = line[x - bpp] if x >= bpp else 0
				b = prev[x]
				c = prev[x - bpp] if x >= bpp else 0
				p = a + b - c
				pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
				line[x] = (line[x] + (a if pa <= pb and pa <= pc else (b if pb <= pc else c))) & 255
		if bpp == 3:
			rgba = bytearray(w * 4)
			rgba[0::4], rgba[1::4], rgba[2::4] = line[0::3], line[1::3], line[2::3]
			rgba[3::4] = b"\xff" * w
			line = rgba
		rows.append(line)
		prev = line if bpp == 4 else bytearray(raw[i - stride:i])
	return w, h, rows


def _png_write(path, w, h, rows):
	import struct
	import zlib

	def chunk(t, b):
		return struct.pack(">I", len(b)) + t + b + struct.pack(">I", zlib.crc32(t + b) & 0xffffffff)
	raw = b"".join(b"\x00" + bytes(r) for r in rows)
	data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)) + \
		chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
	with open(path + ".part", "wb") as f:
		f.write(data)
	os.rename(path + ".part", path)


def _stale(src, out):
	try:
		return not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(src)
	except OSError:
		return True


def alpha_png(src, out, factor):
	"""Copy of src with its transparency scaled (factor < 1: see-through, > 1: darker). Returns out or None."""
	if not _stale(src, out):
		return out
	d = os.path.dirname(out)
	if not os.path.isdir(d):
		os.makedirs(d)
	lut = bytearray(min(255, int(round(a * factor))) for a in range(256))
	try:
		from PIL import Image
		im = Image.open(src).convert("RGBA")
		r, g, b, a = im.split()
		im = Image.merge("RGBA", (r, g, b, a.point(list(lut))))
		im.save(out + ".part", "PNG")
		os.rename(out + ".part", out)
		return out
	except ImportError:
		pass
	except Exception:
		return None
	try:
		w, h, rows = _png_read(src)
		for line in rows:
			line[3::4] = line[3::4].translate(lut)
		_png_write(out, w, h, rows)
		return out
	except Exception:
		return None


def height_png(src, out, height):
	"""Copy of src stretched to a new height (channel list row and selection bars). Returns out or None."""
	if not _stale(src, out):
		return out
	d = os.path.dirname(out)
	if not os.path.isdir(d):
		os.makedirs(d)
	try:
		from PIL import Image
		im = Image.open(src).convert("RGBA")
		im = im.resize((im.size[0], height), Image.LANCZOS if hasattr(Image, "LANCZOS") else Image.ANTIALIAS)
		im.save(out + ".part", "PNG")
		os.rename(out + ".part", out)
		return out
	except ImportError:
		pass
	except Exception:
		return None
	try:
		w, h, rows = _png_read(src)
		# keep the rounded top and bottom edges as they are, stretch the middle
		edge = min(h // 4, height // 4, 14)
		mid_src, mid_dst = h - 2 * edge, height - 2 * edge
		new = rows[:edge]
		for y in range(mid_dst):
			new.append(rows[edge + min(mid_src - 1, int((y + 0.5) * mid_src / mid_dst))])
		new += rows[h - edge:]
		_png_write(out, w, height, new)
		return out
	except Exception:
		return None


# ---- snippet tuning

_IB_BG = re.compile(r'(pixmap=")([^"]*/img/)((?:ib_scrim|ibx_\w+?_bg))(?:_a\w+)?\.png(")')


WEATHER_POS = (("top_right", "Top right", 0, 0), ("top_center", "Top centre", -715, 0),
	("above_right", "Above the infobar, right", 0, 520), ("above_left", "Above the infobar, left", -1430, 520))


def _weather_place(snippet):
	pos = settings().get("weather_pos", "top_right")
	dx, dy = 0, 0
	for n, l, x, y in WEATHER_POS:
		if n == pos:
			dx, dy = x, y
	if not dx and not dy:
		return snippet

	def move(m):
		return re.sub(r'position="(\d+),(\d+)"', lambda p: 'position="%d,%d"' % (int(p.group(1)) + dx, int(p.group(2)) + dy), m.group(0))
	return re.sub(r"<!-- WEATHER START \(card\) -->.*?<!-- WEATHER END -->", move, snippet, flags=re.S)


IB_CHAN = (("normal", "Normal", 1.0), ("large", "Large", 1.25), ("xlarge", "Extra large", 1.5), ("xxlarge", "Biggest", 1.75))


def _chan_row(snippet):
	"""Channel logo, number and name above a compact infobar: bigger by the chosen step, growing upwards so
	they never reach into the bar."""
	f = _factor(IB_CHAN, tune_value("ib_chan", IB_CHAN))
	if f == 1.0:
		return snippet

	def grow(m):
		block = m.group(0)
		boxes = [tuple(map(int, b)) for b in re.findall(r'position="(\d+),(\d+)" size="(\d+),(\d+)"', block)]
		if len(boxes) < 3:
			return block
		(px, py, pw, ph), (nx, ny, nw, nh), (tx, ty, tw, th) = boxes[:3]
		bottom = py + ph
		pw2, ph2 = int(round(pw * f)), int(round(ph * f))
		h2 = int(round(nh * f))
		y2 = bottom - ph2 // 2 - h2 // 2
		nx2 = px + pw2 + int(round((nx - px - pw) * f))
		nw2 = int(round(nw * f))
		tx2 = nx2 + nw2 + (tx - nx - nw)
		tw2 = int(round(tw * f))
		new = [(px, bottom - ph2, pw2, ph2), (nx2, y2, nw2, h2), (tx2, y2, tw2, h2)]
		it = iter(new)
		block = re.sub(r'position="\d+,\d+" size="\d+,\d+"', lambda _m: 'position="%d,%d" size="%d,%d"' % next(it), block, count=3)
		return re.sub(r'font="(\w+);(\d+)"', lambda fm: 'font="%s;%d"' % (fm.group(1), int(round(int(fm.group(2)) * f))), block)
	return re.sub(r"<!-- CHANROW START -->.*?<!-- CHANROW END -->", grow, snippet, flags=re.S)


def _tune_infobar(snippet, base):
	snippet = _weather_place(snippet)
	snippet = _chan_row(snippet)
	level = tune_value("ib_alpha", IB_ALPHA)
	if level == "normal":
		return snippet
	factor = _factor(IB_ALPHA, level)

	def sub(m):
		name = m.group(3)
		src = os.path.join(base, "img", name + ".png")
		out = alpha_png(src, os.path.join(base, "img", TUNE_DIR, "%s_a%s.png" % (name, level)), factor)
		if not out:
			return m.group(0)
		return '%s%s%s/%s_a%s.png%s' % (m.group(1), m.group(2), TUNE_DIR, name, level, m.group(4))
	return _IB_BG.sub(sub, snippet)


_FONT_ATTR = re.compile(r'(service(?:Number|Name|Info|NextInfo|RemainingInfo)Font=")(\w+);(\d+)(")')
_ROW_PIX = re.compile(r'((?:selectionPixmap|backgroundPixmap)=")([^"]*/img/)(\w+?)\.png(")')


CH_PREVIEW = (("poster", "Posters"), ("live", "Live TV picture"))
_POSTER_TAG = re.compile(r'<widget source="ServiceEvent" render="MohammedPoster"[^>]*/>')


def ch_preview():
	v = settings().get("ch_preview", "poster")
	return v if v in [p[0] for p in CH_PREVIEW] else "poster"


_ELEMENT = re.compile(r'[ \t]*<(widget|ePixmap|eLabel)\b[^>]*?(?:/>|>.*?</widget>)[ \t]*\n?', re.S)
_BOX = re.compile(r'position="(\d+),(\d+)" size="(\d+),(\d+)"')


def _live_channels(snippet):
	"""Live TV picture in the channel list: the channel playing now, as big as the style allows.
	Wide backdrop styles: in place of the backdrop. Carousel: in place of the poster wheel.
	Poster styles: the poster and its details stay, the picture takes the place of the description
	and the next programme under them."""
	if ch_preview() != "live":
		return snippet
	pig = '<widget source="session.VideoPicture" render="Pig" position="%d,%d" size="%d,%d" backgroundColor="transparent" zPosition="%d" />'

	def overlap(a, b):
		return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]

	def fit(box, z, top=False):
		x, y, w, h = box
		vw, vh = w, int(round(w * 9 / 16.0))
		if vh > h:
			vh, vw = h, int(round(h * 16 / 9.0))
		return pig % (x + (w - vw) // 2, y if top else y + (h - vh) // 2, vw, vh, z)

	elems = []  # (text, box, z) of every element with a place on screen
	for m in _ELEMENT.finditer(snippet):
		t = m.group(0)
		bm = _BOX.search(t)
		if bm:
			zm = re.search(r'zPosition="(\d+)"', t)
			elems.append((t, tuple(map(int, bm.groups())), int(zm.group(1)) if zm else 1))
	now = [e for e in elems if 'render="MohammedPoster"' in e[0] and 'event="now"' in e[0]]
	if not now:
		return snippet
	posters = [e for e in now if 'kind="poster"' in e[0]]
	scenes = [e for e in now if 'kind="scene"' in e[0]]
	for t, box, z in now:  # a wide backdrop that no poster touches: the picture takes its place
		if 'kind="backdrop"' in t and 500 <= box[2] < 1900 and not [p for p in posters if overlap(p[1], box)]:  # not a full-screen background
			return snippet.replace(t, fit(box, z), 1)
	if not posters:
		return snippet
	if scenes:  # carousel: the whole wheel of pictures makes room
		wheel = posters + scenes
		x0 = min(e[1][0] for e in wheel)
		y0 = min(e[1][1] for e in wheel)
		x1 = max(e[1][0] + e[1][2] for e in wheel)
		y1 = max(e[1][1] + e[1][3] for e in wheel)
		out = snippet
		for e in wheel[1:]:
			out = out.replace(e[0], "", 1)
		return out.replace(wheel[0][0], fit((x0, y0, x1 - x0, y1 - y0), max(e[2] for e in wheel)) + "\n", 1)
	poster = max(posters, key=lambda p: p[1][2] * p[1][3])
	px, py, pw, ph = poster[1]
	desc = [e for e in elems if 'Description</convert>' in e[0] and 'NextDescription' not in e[0] and e[1][1] >= py + ph // 2]
	if not desc:
		return snippet
	d = min(desc, key=lambda e: e[1][1])
	dx, dy = d[1][0], d[1][1]
	# the description and everything under it in that column (next programme, its poster, the line)
	area = [e for e in elems if e[1][1] >= dy - 4 and e[1][0] >= dx - 30 and e[1][1] + e[1][3] <= 1000
		and ('source="ServiceEvent"' in e[0] or (e[0].lstrip().startswith("<ePixmap") and e[1][3] <= 4))]
	x0 = min(e[1][0] for e in area)
	x1 = max(e[1][0] + e[1][2] for e in area)
	y1 = max(e[1][1] + e[1][3] for e in area)
	out = snippet
	for e in area:
		if e is not d:
			out = out.replace(e[0], "", 1)
	return out.replace(d[0], fit((x0, dy, x1 - x0, y1 - dy), max(4, d[2]), top=True) + "\n", 1)


EVENT_COLORS = (("default", "Theme colour", ""), ("white", "White", "#FFFFFF"), ("red", "Red", "#FF4B4B"),
	("green", "Green", "#3FDC6E"), ("yellow", "Yellow", "#FFD93F"), ("orange", "Orange", "#FF9C33"),
	("blue", "Blue", "#4DA3FF"), ("cyan", "Turquoise", "#3ADBE8"), ("purple", "Purple", "#B67CFF"),
	("pink", "Pink", "#FF70B3"), ("gold", "Gold", "#E9C46A"), ("grey", "Grey", "#9CA2AA"))
_LIST_TAG = re.compile(r'<widget name="list"[^>]*serviceItemHeight="\d+"[^>]*/>')


def event_color():
	v = settings().get("event_color", "default")
	return v if v in [c[0] for c in EVENT_COLORS] else "default"


def _list_extras(snippet, base):
	"""Event name colour next to each channel, and the bar for 'two lines per entry' (OpenViX / OpenBH draw
	that bar from selectionPixmapLarge, without it the cursor is gone)."""
	col = [c[2] for c in EVENT_COLORS if c[0] == event_color()][0]
	vix = settings().get("family", "vix") == "vix"

	def fix(m):
		tag = m.group(0)
		if col:
			for attr in ("colorServiceDescription", "foregroundColorEvent"):
				tag = re.sub(r'(\s%s=")[^"]*(")' % attr, lambda a: a.group(1) + "#00" + col[1:] + a.group(2), tag)
		hm = re.search(r'serviceItemHeight="(\d+)"', tag)
		pm = re.search(r'selectionPixmap="([^"]*/img/)(?:%s/)?(\w+?)(?:_h\d+)?\.png"' % TUNE_DIR, tag)
		if vix and hm and pm and "selectionPixmapLarge" not in tag:
			h2 = int(round(int(hm.group(1)) * 1.6))
			out = height_png(os.path.join(base, "img", pm.group(2) + ".png"), os.path.join(base, "img", TUNE_DIR, "%s_h%d.png" % (pm.group(2), h2)), h2)
			if out:
				tag = tag.replace(hm.group(0), '%s itemHeightTwoLine="%d" selectionPixmapLarge="%s%s/%s_h%d.png"' % (hm.group(0), h2, pm.group(1), TUNE_DIR, pm.group(2), h2), 1)
		return tag
	return _LIST_TAG.sub(fix, snippet)


def _tune_channels(snippet, base):
	snippet = _live_channels(snippet)
	ff = _factor(CH_FONT, tune_value("ch_font", CH_FONT))
	rf = _factor(CH_ROWS, tune_value("ch_rows", CH_ROWS))
	if ff == 1.0 and rf == 1.0:
		return _list_extras(snippet, base)

	def tune_list(m):
		tag = m.group(0)
		if ff != 1.0:
			tag = _FONT_ATTR.sub(lambda f: "%s%s;%d%s" % (f.group(1), f.group(2), max(14, int(round(int(f.group(3)) * ff))), f.group(4)), tag)
		hm = re.search(r'serviceItemHeight="(\d+)"', tag)
		if rf != 1.0 and hm:
			old = int(hm.group(1))
			new = max(36, int(round(old * rf)))
			tag = tag.replace(hm.group(0), 'serviceItemHeight="%d"' % new)
			sm = re.search(r'size="(\d+),(\d+)"', tag)
			if sm:  # whole rows only, so the last row is never cut
				h = int(sm.group(2))
				tag = tag.replace(sm.group(0), 'size="%s,%d"' % (sm.group(1), max(new, h // new * new)), 1)

			def pix(p):
				src = os.path.join(base, "img", p.group(3) + ".png")
				out = height_png(src, os.path.join(base, "img", TUNE_DIR, "%s_h%d.png" % (p.group(3), new)), new)
				if not out:
					return p.group(0)
				return "%s%s%s/%s_h%d.png%s" % (p.group(1), p.group(2), TUNE_DIR, p.group(3), new, p.group(4))
			tag = _ROW_PIX.sub(pix, tag)
		return tag
	return _list_extras(re.sub(r'<widget name="list"[^>]*serviceItemHeight="\d+"[^>]*/>', tune_list, snippet), base)


def tune_snippet(kind, snippet, base=SKIN_DIR):
	try:
		if kind == "infobar":
			return _tune_infobar(snippet, base)
		if kind == "channels":
			return _tune_channels(snippet, base)
	except Exception as e:
		print("[MohammedSkin] tune %s: %s" % (kind, e))
	return snippet


def plugin_browser_kind(root=""):
	"""'vix' when this image's plugin browser can show a grid from the skin (new OpenViX / OpenBH),
	'atv' when it has its own list / grid choice (OpenATV and images based on it), else ''."""
	for fn in ("PluginBrowser.py", "PluginBrowser.pyc", "__pycache__"):
		path = root + "/usr/lib/enigma2/python/Screens/" + fn
		files = [path]
		if fn == "__pycache__":
			try:
				files = [os.path.join(path, x) for x in os.listdir(path) if x.startswith("PluginBrowser.")]
			except Exception:
				files = []
		for p in files:
			try:
				with open(p, "rb") as f:
					data = f.read()
			except Exception:
				continue
			if b"usesTemplatedList" in data:
				return "vix"
			if b"pluginListLayout" in data:
				return "atv"
	return ""


def _grid_screens(level, kind):
	"""Grid screens for the plugin browser: PluginBrowserGrid (OpenATV) and, on OpenViX images that
	support it, PluginBrowser with a grid list."""
	f = _factor(PL_FONT, level)
	cw, ch = int(round(296 * f)), int(round(206 * f))
	area_w, area_h = 1800, 800
	cols = max(2, area_w // cw)
	cw = area_w // cols
	rows = max(1, area_h // ch)
	gh = rows * ch
	m = 7
	iw, ih = cw - 2 * m - 40, int(round((cw - 2 * m - 40) / 2.5))
	ix, iy = (cw - iw) // 2, m + int(round(18 * f))
	ty = iy + ih + int(round(10 * f))
	th = ch - ty - m - 6
	fsize = int(round(25 * f))
	ink = _theme_rgb("ink", "#060304")
	tile = 0x00000000 | (min(255, ink[0] + 30) << 16) | (min(255, ink[1] + 28) << 8) | min(255, ink[2] + 30)
	template = '''
				{
				"template":
					[
					MultiContentEntryText(pos=(%(m)d, %(m)d), size=(%(tw)d, %(thh)d), font=0, backcolor=0x%(tile)08X),
					MultiContentEntryPixmapAlphaBlend(pos=(%(ix)d, %(iy)d), size=(%(iw)d, %(ih)d), png=3, flags=BT_SCALE),
					MultiContentEntryText(pos=(%(tx)d, %(ty)d), size=(%(tww)d, %(th)d), font=0, flags=RT_HALIGN_CENTER | RT_VALIGN_CENTER | RT_WRAP, text=1)
					],
				"fonts": [parseFont("Semi;%(fs)d")],
				"itemWidth": %(cw)d,
				"itemHeight": %(ch)d%(orient)s
				}
			'''
	vals = dict(m=m, tw=cw - 2 * m, thh=ch - 2 * m, tile=tile, ix=ix, iy=iy, iw=iw, ih=ih, tx=m + 8, ty=ty, tww=cw - 2 * m - 16, th=th, fs=fsize, cw=cw, ch=ch)
	common = '''		<eLabel position="0,0" size="1920,4" backgroundColor="crimson" />
		<widget source="Title" render="Label" position="60,22" size="1800,56" font="Title;42" foregroundColor="ivory" backgroundColor="panel" transparent="1" />
		<widget name="description" position="60,%(dy)d" size="1800,40" font="Regular;26" foregroundColor="ivorydim" backgroundColor="panel" valign="center" transparent="1" />
''' % dict(dy=110 + gh + 14)
	out = '''	<screen name="PluginBrowserGrid" title="Plugin Browser" position="0,0" size="1920,1080" backgroundColor="panel" flags="wfNoBorder">
%(common)s		<widget source="pluginGrid" render="Listbox" position="60,110" size="%(gw)d,%(gh)d" conditional="pluginGrid" listOrientation="grid" scrollbarMode="showOnDemand" backgroundColor="panel" foregroundColor="ivory" backgroundColorSelected="selbg" foregroundColorSelected="selfg" transparent="1">
			<convert type="TemplatedMultiContent">%(tpl)s</convert>
		</widget>
		<widget name="quickselect" position="60,110" size="%(gw)d,%(gh)d" font="Title;120" foregroundColor="gold" halign="center" valign="center" transparent="1" zPosition="5" />
		<widget source="key_red" render="Label" position="88,%(ky)d" size="240,40" font="Regular;24" foregroundColor="ivory" backgroundColor="panel" valign="center" transparent="1" />
		<widget source="key_green" render="Label" position="388,%(ky)d" size="240,40" font="Regular;24" foregroundColor="ivory" backgroundColor="panel" valign="center" transparent="1" />
		<widget source="key_yellow" render="Label" position="688,%(ky)d" size="240,40" font="Regular;24" foregroundColor="ivory" backgroundColor="panel" valign="center" conditional="key_yellow" transparent="1" />
		<widget source="key_blue" render="Label" position="988,%(ky)d" size="240,40" font="Regular;24" foregroundColor="ivory" backgroundColor="panel" valign="center" conditional="key_blue" transparent="1" />
		<eLabel position="60,%(kd)d" size="18,18" backgroundColor="keyred" />
		<eLabel position="360,%(kd)d" size="18,18" backgroundColor="keygreen" />
		<eLabel position="660,%(kd)d" size="18,18" backgroundColor="keyyellow" />
		<eLabel position="960,%(kd)d" size="18,18" backgroundColor="keyblue" />
		<widget source="key_menu" render="Label" position="1640,%(ky)d" size="100,40" font="Regular;22" foregroundColor="ivorydim" backgroundColor="panel" halign="center" valign="center" conditional="key_menu" transparent="1" />
		<widget source="key_help" render="Label" position="1760,%(ky)d" size="100,40" font="Regular;22" foregroundColor="ivorydim" backgroundColor="panel" halign="center" valign="center" conditional="key_help" transparent="1" />
	</screen>
''' % dict(common=common, gw=cols * cw, gh=gh, sh=1080, ky=1010, kd=1021, tpl=template % dict(vals, orient=""))
	if kind == "vix":
		out += '''	<screen name="PluginBrowser" title="Plugin Browser" position="0,0" size="1920,1080" backgroundColor="panel" flags="wfNoBorder">
%(common)s		<widget source="list" render="Listbox" position="60,110" size="%(gw)d,%(gh)d" scrollbarMode="showOnDemand" backgroundColor="panel" foregroundColor="ivory" backgroundColorSelected="selbg" foregroundColorSelected="selfg" transparent="1">
			<convert type="TemplatedMultiContent">%(tpl)s</convert>
		</widget>
		<widget name="key_red" position="88,%(ky)d" size="300,40" font="Regular;24" foregroundColor="ivory" backgroundColor="panel" valign="center" transparent="1" />
		<widget name="key_green" position="448,%(ky)d" size="300,40" font="Regular;24" foregroundColor="ivory" backgroundColor="panel" valign="center" transparent="1" />
		<widget name="key_yellow" position="808,%(ky)d" size="360,40" font="Regular;24" foregroundColor="ivory" backgroundColor="panel" valign="center" transparent="1" />
		<eLabel position="60,%(kd)d" size="18,18" backgroundColor="keyred" />
		<eLabel position="420,%(kd)d" size="18,18" backgroundColor="keygreen" />
		<eLabel position="780,%(kd)d" size="18,18" backgroundColor="keyyellow" />
	</screen>
''' % dict(common=common.replace('<widget name="description"', '<widget source="description"').replace('font="Regular;26" foregroundColor="ivorydim"', 'render="Label" font="Regular;26" foregroundColor="ivorydim"'),
			gw=cols * cw, gh=gh, sh=1080, ky=1010, kd=1021, tpl=template % dict(vals, orient=',\n\t\t\t\t"orientation": "orGrid"'))
	return out


def plugins_block(level):
	"""Plugin list: font aliases (OpenViX / OpenBH and older images), entry layout, a
	PluginBrowserList screen (OpenATV / PurE2 / EGAMI) and the grid screens."""
	layout = settings().get("pl_layout", "grid")
	kind = plugin_browser_kind()
	grid = _grid_screens(level, kind if layout == "grid" else "") if kind else ""
	f = _factor(PL_FONT, level)
	f0, f1, rowh = int(round(30 * f)), int(round(24 * f)), int(round(75 * f))
	iw, ih = int(round(150 * f)), int(round(60 * f))
	ix, iy = 15, (rowh - ih) // 2
	nx, ny, nh = ix + iw + 20, int(round(6 * f)), int(round(38 * f))
	dy, dh = ny + nh, int(round(30 * f))
	listh = 820 // rowh * rowh
	return ('''	<!-- PLUGINS START (%(level)s) -->
	<parameters>
		<!-- lists of the image (choice boxes, multiboot, file and selection lists): text boxes sized to the fonts above -->
		<parameter name="AllowUserDatesAndTimes" value="1,1" />
		<parameter name="ChoicelistDash" value="0,4,1100,46" />
		<parameter name="ChoicelistName" value="62,4,1030,46" />
		<parameter name="ChoicelistNameSingle" value="12,4,1080,46" />
		<parameter name="ChoicelistIcon" value="10,8,42,34" />
		<parameter name="SelectionListDescr" value="62,4,1500,46" />
		<parameter name="SelectionListLock" value="12,10,30,30" />
		<parameter name="SelectionListLockOff" value="12,10,30,30" />
		<parameter name="FileListName" value="52,4,1500,46" />
		<parameter name="FileListIcon" value="12,12,26,26" />
		<parameter name="FileListMultiName" value="92,4,1460,46" />
		<parameter name="FileListMultiIcon" value="52,12,26,26" />
		<parameter name="FileListMultiLock" value="12,10,30,30" />
		<parameter name="ServiceInfo" value="0,4,450,46" />
		<parameter name="ServiceInfoLeft" value="0,4,450,46" />
		<parameter name="ServiceInfoRight" value="460,4,1000,46" />
		<parameter name="PluginBrowserName" value="%(nx)d,%(ny)d,%(nh)d" />
		<parameter name="PluginBrowserDescr" value="%(nx)d,%(dy)d,%(dh)d" />
		<parameter name="PluginBrowserIcon" value="%(ix)d,%(iy)d,%(iw)d,%(ih)d" />
	</parameters>
	<screen name="PluginBrowserList" title="Plugin Browser" position="0,0" size="1920,1080" backgroundColor="panel" flags="wfNoBorder">
		<eLabel position="0,0" size="1920,4" backgroundColor="crimson" />
		<widget source="Title" render="Label" position="60,22" size="1800,56" font="Title;42" foregroundColor="ivory" backgroundColor="panel" transparent="1" />
		<widget source="pluginList" render="Listbox" position="60,104" size="1800,%(listh)d" conditional="pluginList" listOrientation="vertical" scrollbarMode="showOnDemand" backgroundColor="panel" foregroundColor="ivory" backgroundColorSelected="selbg" foregroundColorSelected="selfg" transparent="1">
			<convert type="TemplatedMultiContent">
				{
				"template":
					[
					MultiContentEntryPixmapAlphaBlend(pos=(%(ix)d, %(iy)d), size=(%(iw)d, %(ih)d), png=3, flags=BT_SCALE),
					MultiContentEntryText(pos=(%(nx)d, %(ny)d), size=(%(tw)d, %(nh)d), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=1),
					MultiContentEntryText(pos=(%(nx)d, %(dy)d), size=(%(tw)d, %(dh)d), font=1, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=2)
					],
				"fonts": [parseFont("Semi;%(f0)d"), parseFont("Regular;%(f1)d")],
				"itemHeight": %(rowh)d
				}
			</convert>
		</widget>
		<widget name="quickselect" position="60,104" size="1800,%(listh)d" font="Title;120" foregroundColor="gold" halign="center" valign="center" transparent="1" zPosition="5" />
		<widget name="description" position="60,950" size="1800,40" font="Regular;26" foregroundColor="ivorydim" backgroundColor="panel" valign="center" transparent="1" />
		<eLabel position="60,1021" size="18,18" backgroundColor="keyred" />
		<widget source="key_red" render="Label" position="88,1010" size="260,40" font="Regular;24" foregroundColor="ivory" backgroundColor="panel" valign="center" transparent="1" />
		<eLabel position="360,1021" size="18,18" backgroundColor="keygreen" />
		<widget source="key_green" render="Label" position="388,1010" size="260,40" font="Regular;24" foregroundColor="ivory" backgroundColor="panel" valign="center" transparent="1" />
		<eLabel position="660,1021" size="18,18" backgroundColor="keyyellow" />
		<widget source="key_yellow" render="Label" position="688,1010" size="260,40" font="Regular;24" foregroundColor="ivory" backgroundColor="panel" valign="center" conditional="key_yellow" transparent="1" />
		<eLabel position="960,1021" size="18,18" backgroundColor="keyblue" />
		<widget source="key_blue" render="Label" position="988,1010" size="260,40" font="Regular;24" foregroundColor="ivory" backgroundColor="panel" valign="center" conditional="key_blue" transparent="1" />
		<widget source="key_menu" render="Label" position="1640,1010" size="100,40" font="Regular;22" foregroundColor="ivorydim" backgroundColor="panel" halign="center" valign="center" conditional="key_menu" transparent="1" />
		<widget source="key_help" render="Label" position="1760,1010" size="100,40" font="Regular;22" foregroundColor="ivorydim" backgroundColor="panel" halign="center" valign="center" conditional="key_help" transparent="1" />
	</screen>
%(grid)s	<!-- PLUGINS END -->
''' % dict(grid=grid, level=level, nx=nx, ny=ny, nh=nh, dy=dy, dh=dh, ix=ix, iy=iy, iw=iw, ih=ih, tw=1800 - nx - 30,
		f0=f0, f1=f1, rowh=rowh, listh=listh), f0, f1, rowh)


def apply_plugin_fonts(base=SKIN_DIR):
	"""Write the plugin list size into skin.xml (font aliases + PLUGINS block)."""
	level = tune_value("pl_font", PL_FONT)
	block, f0, f1, rowh = plugins_block(level)
	skin = os.path.join(base, "skin.xml")
	with open(skin) as f:
		xml = f.read()
	new = re.sub(r'<alias name="PluginBrowser0"[^>]*/>', '<alias name="PluginBrowser0" font="Semi" size="%d" height="%d" />' % (f0, rowh), xml)
	new = re.sub(r'<alias name="PluginBrowser1"[^>]*/>', '<alias name="PluginBrowser1" font="Regular" size="%d" />' % f1, new)
	pat = r"[ \t]*<!-- PLUGINS START.*?<!-- PLUGINS END -->\n?"
	if re.search(pat, new, re.S):
		new = re.sub(pat, lambda m: block, new, count=1, flags=re.S)
	else:
		new = new.replace("\t<!-- IB START", block + "\n\t<!-- IB START", 1)
	if new != xml:
		tmp = skin + ".tmp"
		with open(tmp, "w") as f:
			f.write(new)
		os.rename(tmp, skin)
	return True


def apply_tuning(base=SKIN_DIR):
	"""Put the size / transparency choices into skin.xml for the styles in use now."""
	apply_style("channels", current_style("channels", base), base)
	apply_infobar(current_style("infobar", base), base)
	apply_plugin_fonts(base)
	return True


# ---------------------------------------------------------------- Arabic fonts
# The text font is also the replacement font: every Arabic letter on screen (channel names,
# menus, EPG) uses it. The title font is used for the big Arabic event titles.

AR_TEXT_FONTS = (
	("tajawal", "Tajawal", "fonts/ar-text.ttf", "fonts/ar-text-bold.ttf"),
	("cairo", "Cairo", "fonts/arabic/cairo-regular.ttf", "fonts/arabic/cairo-bold.ttf"),
	("almarai", "Almarai", "fonts/arabic/almarai-regular.ttf", "fonts/arabic/almarai-bold.ttf"),
	("notokufi", "Noto Kufi", "fonts/arabic/notokufi-regular.ttf", "fonts/arabic/notokufi-bold.ttf"),
	("plex", "IBM Plex Arabic", "fonts/arabic/plex-regular.ttf", "fonts/arabic/plex-bold.ttf"),
	("amiri", "Amiri (classic naskh)", "fonts/arabic/amiri-regular.ttf", "fonts/arabic/amiri-bold.ttf"),
	("dejavu", "DejaVu (widest glyph cover)", "fonts/moh-arabic.ttf", "fonts/moh-arabic.ttf"),
)
AR_TITLE_FONTS = (
	("lalezar", "Lalezar", "fonts/ar-title.ttf"),
	("cairo", "Cairo Black", "fonts/arabic/cairo-black.ttf"),
	("changa", "Changa", "fonts/arabic/changa-bold.ttf"),
	("elmessiri", "El Messiri", "fonts/arabic/elmessiri-bold.ttf"),
	("ruqaa", "Aref Ruqaa", "fonts/arabic/arefruqaa-bold.ttf"),
	("rakkas", "Rakkas", "fonts/arabic/rakkas.ttf"),
)


def font_value(key, table, default):
	v = settings().get(key, default)
	return v if v in [t[0] for t in table] else default


def apply_arabic_fonts(base=SKIN_DIR):
	"""Point the ArText / ArTextBold / ArTitle / Replacement fonts in skin.xml at the chosen files."""
	text = font_value("ar_text_font", AR_TEXT_FONTS, "tajawal")
	title = font_value("ar_title_font", AR_TITLE_FONTS, "lalezar")
	t = [f for f in AR_TEXT_FONTS if f[0] == text][0]
	ti = [f for f in AR_TITLE_FONTS if f[0] == title][0]
	files = {"ArText": t[2], "ArTextBold": t[3], "ArTitle": ti[2]}
	skin = os.path.join(base, "skin.xml")
	with open(skin) as f:
		xml = f.read()
	new = xml
	for name, rel in files.items():
		if not os.path.isfile(os.path.join(base, rel)):
			continue
		new = re.sub(r'(<font name="%s" filename=")[^"]*(")' % name, r"\g<1>%s/%s\g<2>" % (SKIN_DIR, rel), new)
	if os.path.isfile(os.path.join(base, t[2])):
		new = re.sub(r'(<font name="Replacement" filename=")[^"]*(")', r"\g<1>%s/%s\g<2>" % (SKIN_DIR, t[2]), new)
	if new != xml:
		tmp = skin + ".tmp"
		with open(tmp, "w") as f:
			f.write(new)
		os.rename(tmp, skin)
	return True


# ---------------------------------------------------------------- weather (Open-Meteo, no key needed)

WEATHER_TTL = 30 * 60
_weather = {"t": 0, "data": None, "busy": False, "cbs": [], "loc": None}
# WMO weather code -> (icon, English, Arabic)
WMO = {
	0: ("clear", "Clear", u"صافٍ"), 1: ("partly", "Mostly clear", u"صافٍ غالباً"), 2: ("partly", "Partly cloudy", u"غائم جزئياً"),
	3: ("cloudy", "Cloudy", u"غائم"), 45: ("fog", "Fog", u"ضباب"), 48: ("fog", "Fog", u"ضباب"),
	51: ("drizzle", "Drizzle", u"رذاذ"), 53: ("drizzle", "Drizzle", u"رذاذ"), 55: ("drizzle", "Drizzle", u"رذاذ"),
	56: ("drizzle", "Freezing drizzle", u"رذاذ متجمد"), 57: ("drizzle", "Freezing drizzle", u"رذاذ متجمد"),
	61: ("rain", "Light rain", u"مطر خفيف"), 63: ("rain", "Rain", u"مطر"), 65: ("rain", "Heavy rain", u"مطر غزير"),
	66: ("rain", "Freezing rain", u"مطر متجمد"), 67: ("rain", "Freezing rain", u"مطر متجمد"),
	71: ("snow", "Light snow", u"ثلج خفيف"), 73: ("snow", "Snow", u"ثلج"), 75: ("snow", "Heavy snow", u"ثلج كثيف"),
	77: ("snow", "Snow grains", u"حبيبات ثلج"), 80: ("rain", "Showers", u"زخات مطر"), 81: ("rain", "Showers", u"زخات مطر"),
	82: ("rain", "Heavy showers", u"زخات غزيرة"), 85: ("snow", "Snow showers", u"زخات ثلج"), 86: ("snow", "Snow showers", u"زخات ثلج"),
	95: ("storm", "Thunderstorm", u"عاصفة رعدية"), 96: ("storm", "Thunderstorm", u"عاصفة رعدية"), 99: ("storm", "Thunderstorm", u"عاصفة رعدية"),
}


# weather words in the other languages of the setup (Arabic and English are in WMO above)
WEATHER_LANGS = (("ar", u"العربية"), ("en", "English"), ("zh", u"简体中文"), ("uk", u"Українська"), ("ru", u"Русский"),
	("de", "Deutsch"), ("fr", u"Français"), ("es", u"Español"), ("it", "Italiano"), ("pt", u"Português"),
	("nl", "Nederlands"), ("pl", "Polski"), ("tr", u"Türkçe"), ("fa", u"فارسی"), ("ja", u"日本語"))
WX_WORDS = {
	"zh": {"Clear": u"晴", "Mostly clear": u"大部晴朗", "Partly cloudy": u"多云", "Cloudy": u"阴", "Fog": u"雾", "Drizzle": u"毛毛雨", "Freezing drizzle": u"冻毛毛雨", "Light rain": u"小雨", "Rain": u"雨", "Heavy rain": u"大雨", "Freezing rain": u"冻雨", "Light snow": u"小雪", "Snow": u"雪", "Heavy snow": u"大雪", "Snow grains": u"米雪", "Showers": u"阵雨", "Heavy showers": u"强阵雨", "Snow showers": u"阵雪", "Thunderstorm": u"雷暴", "Humidity": u"湿度"},
	"ja": {"Clear": u"快晴", "Mostly clear": u"おおむね晴れ", "Partly cloudy": u"晴れ時々曇り", "Cloudy": u"曇り", "Fog": u"霧", "Drizzle": u"霧雨", "Freezing drizzle": u"着氷性の霧雨", "Light rain": u"小雨", "Rain": u"雨", "Heavy rain": u"大雨", "Freezing rain": u"着氷性の雨", "Light snow": u"小雪", "Snow": u"雪", "Heavy snow": u"大雪", "Snow grains": u"霧雪", "Showers": u"にわか雨", "Heavy showers": u"強いにわか雨", "Snow showers": u"にわか雪", "Thunderstorm": u"雷雨", "Humidity": u"湿度"},
	"uk": {"Clear": u"Ясно", "Mostly clear": u"Переважно ясно", "Partly cloudy": u"Мінлива хмарність", "Cloudy": u"Хмарно", "Fog": u"Туман", "Drizzle": u"Мряка", "Freezing drizzle": u"Крижана мряка", "Light rain": u"Невеликий дощ", "Rain": u"Дощ", "Heavy rain": u"Сильний дощ", "Freezing rain": u"Крижаний дощ", "Light snow": u"Невеликий сніг", "Snow": u"Сніг", "Heavy snow": u"Сильний сніг", "Snow grains": u"Снігова крупа", "Showers": u"Злива", "Heavy showers": u"Сильна злива", "Snow showers": u"Снігопад", "Thunderstorm": u"Гроза", "Humidity": u"Вологість"},
	"ru": {"Clear": u"Ясно", "Mostly clear": u"Преимущественно ясно", "Partly cloudy": u"Переменная облачность", "Cloudy": u"Облачно", "Fog": u"Туман", "Drizzle": u"Морось", "Freezing drizzle": u"Ледяная морось", "Light rain": u"Небольшой дождь", "Rain": u"Дождь", "Heavy rain": u"Сильный дождь", "Freezing rain": u"Ледяной дождь", "Light snow": u"Небольшой снег", "Snow": u"Снег", "Heavy snow": u"Сильный снег", "Snow grains": u"Снежная крупа", "Showers": u"Ливень", "Heavy showers": u"Сильный ливень", "Snow showers": u"Снегопад", "Thunderstorm": u"Гроза", "Humidity": u"Влажность"},
	"de": {"Clear": u"Klar", "Mostly clear": u"Überwiegend klar", "Partly cloudy": u"Teilweise bewölkt", "Cloudy": u"Bewölkt", "Fog": u"Nebel", "Drizzle": u"Nieselregen", "Freezing drizzle": u"Gefrierender Niesel", "Light rain": u"Leichter Regen", "Rain": u"Regen", "Heavy rain": u"Starker Regen", "Freezing rain": u"Gefrierender Regen", "Light snow": u"Leichter Schnee", "Snow": u"Schnee", "Heavy snow": u"Starker Schnee", "Snow grains": u"Schneegriesel", "Showers": u"Schauer", "Heavy showers": u"Starke Schauer", "Snow showers": u"Schneeschauer", "Thunderstorm": u"Gewitter", "Humidity": u"Luftfeuchte"},
	"fr": {"Clear": u"Dégagé", "Mostly clear": u"Plutôt dégagé", "Partly cloudy": u"Partiellement nuageux", "Cloudy": u"Nuageux", "Fog": u"Brouillard", "Drizzle": u"Bruine", "Freezing drizzle": u"Bruine verglaçante", "Light rain": u"Pluie faible", "Rain": u"Pluie", "Heavy rain": u"Forte pluie", "Freezing rain": u"Pluie verglaçante", "Light snow": u"Neige faible", "Snow": u"Neige", "Heavy snow": u"Forte neige", "Snow grains": u"Neige en grains", "Showers": u"Averses", "Heavy showers": u"Fortes averses", "Snow showers": u"Averses de neige", "Thunderstorm": u"Orage", "Humidity": u"Humidité"},
	"es": {"Clear": u"Despejado", "Mostly clear": u"Mayormente despejado", "Partly cloudy": u"Parcialmente nublado", "Cloudy": u"Nublado", "Fog": u"Niebla", "Drizzle": u"Llovizna", "Freezing drizzle": u"Llovizna helada", "Light rain": u"Lluvia ligera", "Rain": u"Lluvia", "Heavy rain": u"Lluvia fuerte", "Freezing rain": u"Lluvia helada", "Light snow": u"Nieve ligera", "Snow": u"Nieve", "Heavy snow": u"Nieve fuerte", "Snow grains": u"Granos de nieve", "Showers": u"Chubascos", "Heavy showers": u"Chubascos fuertes", "Snow showers": u"Chubascos de nieve", "Thunderstorm": u"Tormenta", "Humidity": u"Humedad"},
	"it": {"Clear": u"Sereno", "Mostly clear": u"Prevalentemente sereno", "Partly cloudy": u"Parzialmente nuvoloso", "Cloudy": u"Nuvoloso", "Fog": u"Nebbia", "Drizzle": u"Pioviggine", "Freezing drizzle": u"Pioviggine gelata", "Light rain": u"Pioggia debole", "Rain": u"Pioggia", "Heavy rain": u"Pioggia forte", "Freezing rain": u"Pioggia gelata", "Light snow": u"Neve debole", "Snow": u"Neve", "Heavy snow": u"Neve forte", "Snow grains": u"Neve granulosa", "Showers": u"Rovesci", "Heavy showers": u"Forti rovesci", "Snow showers": u"Rovesci di neve", "Thunderstorm": u"Temporale", "Humidity": u"Umidità"},
	"pt": {"Clear": u"Limpo", "Mostly clear": u"Maioritariamente limpo", "Partly cloudy": u"Parcialmente nublado", "Cloudy": u"Nublado", "Fog": u"Nevoeiro", "Drizzle": u"Chuvisco", "Freezing drizzle": u"Chuvisco gelado", "Light rain": u"Chuva fraca", "Rain": u"Chuva", "Heavy rain": u"Chuva forte", "Freezing rain": u"Chuva gelada", "Light snow": u"Neve fraca", "Snow": u"Neve", "Heavy snow": u"Neve forte", "Snow grains": u"Grãos de neve", "Showers": u"Aguaceiros", "Heavy showers": u"Aguaceiros fortes", "Snow showers": u"Aguaceiros de neve", "Thunderstorm": u"Trovoada", "Humidity": u"Humidade"},
	"nl": {"Clear": u"Helder", "Mostly clear": u"Overwegend helder", "Partly cloudy": u"Half bewolkt", "Cloudy": u"Bewolkt", "Fog": u"Mist", "Drizzle": u"Motregen", "Freezing drizzle": u"IJzel-motregen", "Light rain": u"Lichte regen", "Rain": u"Regen", "Heavy rain": u"Zware regen", "Freezing rain": u"IJzel", "Light snow": u"Lichte sneeuw", "Snow": u"Sneeuw", "Heavy snow": u"Zware sneeuw", "Snow grains": u"Motsneeuw", "Showers": u"Buien", "Heavy showers": u"Zware buien", "Snow showers": u"Sneeuwbuien", "Thunderstorm": u"Onweer", "Humidity": u"Vochtigheid"},
	"pl": {"Clear": u"Bezchmurnie", "Mostly clear": u"Przeważnie bezchmurnie", "Partly cloudy": u"Częściowe zachmurzenie", "Cloudy": u"Pochmurno", "Fog": u"Mgła", "Drizzle": u"Mżawka", "Freezing drizzle": u"Marznąca mżawka", "Light rain": u"Słaby deszcz", "Rain": u"Deszcz", "Heavy rain": u"Ulewa", "Freezing rain": u"Marznący deszcz", "Light snow": u"Słaby śnieg", "Snow": u"Śnieg", "Heavy snow": u"Intensywny śnieg", "Snow grains": u"Śnieg ziarnisty", "Showers": u"Przelotne opady", "Heavy showers": u"Silne przelotne opady", "Snow showers": u"Przelotny śnieg", "Thunderstorm": u"Burza", "Humidity": u"Wilgotność"},
	"tr": {"Clear": u"Açık", "Mostly clear": u"Çoğunlukla açık", "Partly cloudy": u"Parçalı bulutlu", "Cloudy": u"Bulutlu", "Fog": u"Sis", "Drizzle": u"Çisenti", "Freezing drizzle": u"Donan çisenti", "Light rain": u"Hafif yağmur", "Rain": u"Yağmur", "Heavy rain": u"Şiddetli yağmur", "Freezing rain": u"Donan yağmur", "Light snow": u"Hafif kar", "Snow": u"Kar", "Heavy snow": u"Yoğun kar", "Snow grains": u"Kar taneleri", "Showers": u"Sağanak", "Heavy showers": u"Kuvvetli sağanak", "Snow showers": u"Kar sağanağı", "Thunderstorm": u"Gök gürültülü fırtına", "Humidity": u"Nem"},
	"fa": {"Clear": u"صاف", "Mostly clear": u"عمدتاً صاف", "Partly cloudy": u"نیمه ابری", "Cloudy": u"ابری", "Fog": u"مه", "Drizzle": u"نم‌نم باران", "Freezing drizzle": u"نم‌نم یخ‌زده", "Light rain": u"باران سبک", "Rain": u"باران", "Heavy rain": u"باران شدید", "Freezing rain": u"باران یخ‌زده", "Light snow": u"برف سبک", "Snow": u"برف", "Heavy snow": u"برف سنگین", "Snow grains": u"دانه‌های برف", "Showers": u"رگبار", "Heavy showers": u"رگبار شدید", "Snow showers": u"رگبار برف", "Thunderstorm": u"رعد و برق", "Humidity": u"رطوبت"},
}


def weather_lang():
	v = settings().get("weather_lang", "ar")
	return v if v in [l[0] for l in WEATHER_LANGS] else "ar"


def _wx_word(en_word, lang):
	return WX_WORDS.get(lang, {}).get(en_word, en_word)


def _weather_location():
	"""(lat, lon, city) from the city typed in the setup, else from the internet address of the box."""
	s = settings()
	lang = weather_lang()
	mode = s.get("weather_mode") or ("city" if (s.get("weather_city") or "").strip() else "auto")
	if mode == "list" and s.get("weather_lat") is not None:  # picked from the country / city list
		try:
			return (float(s["weather_lat"]), float(s["weather_lon"]),
				(s.get("weather_place_ar") if lang == "ar" else s.get("weather_place_en")) or s.get("weather_place_en") or "")
			# (a city picked from the list keeps its English name in the other languages)
		except Exception:
			pass
	city = (s.get("weather_city") or "").strip() if mode == "city" else ""
	cache = _weather.get("loc")
	if cache and cache[0] == (city, lang):
		return cache[1]
	loc = None
	if city:
		d = get_json("https://geocoding-api.open-meteo.com/v1/search?count=1&language=%s&name=%s" % (lang, quote(city.encode("utf-8"))))
		r = (d or {}).get("results") or []
		if r:
			loc = (r[0]["latitude"], r[0]["longitude"], r[0].get("name") or city)
	else:
		d = get_json("https://ipwho.is/?fields=success,city,latitude,longitude")
		if d and d.get("success") and d.get("latitude") is not None:
			loc = (d["latitude"], d["longitude"], d.get("city") or "")
		else:
			d = get_json("http://ip-api.com/json/?fields=status,city,lat,lon")
			if d and d.get("status") == "success":
				loc = (d["lat"], d["lon"], d.get("city") or "")
		if loc and lang != "en" and loc[2]:  # the city's name in the weather language
			g = get_json("https://geocoding-api.open-meteo.com/v1/search?count=1&language=%s&name=%s" % (lang, quote(loc[2].encode("utf-8"))))
			r = (g or {}).get("results") or []
			if r and r[0].get("name"):
				loc = (loc[0], loc[1], r[0]["name"])
	if loc:
		_weather["loc"] = ((city, lang), loc)
	return loc


def _weather_work():
	data = None
	try:
		loc = _weather_location()
		if loc:
			s = settings()
			unit = "&temperature_unit=fahrenheit&wind_speed_unit=mph" if s.get("weather_units") == "f" else ""
			d = get_json("https://api.open-meteo.com/v1/forecast?latitude=%.4f&longitude=%.4f&current=temperature_2m,weather_code,is_day,"
				"relative_humidity_2m,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min&forecast_days=1&timezone=auto%s" % (loc[0], loc[1], unit))
			cur = (d or {}).get("current") or {}
			if cur.get("temperature_2m") is not None:
				code = int(cur.get("weather_code") or 0)
				icon, en, ar = WMO.get(code, ("cloudy", "Cloudy", u"غائم"))
				day = bool(cur.get("is_day", 1))
				if icon in ("clear", "partly"):
					icon += "_day" if day else "_night"
				daily = d.get("daily") or {}
				data = {"temp": int(round(cur["temperature_2m"])), "icon": icon, "en": en, "ar": ar, "city": loc[2],
					"tmax": int(round((daily.get("temperature_2m_max") or [cur["temperature_2m"]])[0])),
					"tmin": int(round((daily.get("temperature_2m_min") or [cur["temperature_2m"]])[0])),
					"hum": cur.get("relative_humidity_2m"), "wind": cur.get("wind_speed_10m"),
					"wunit": "mph" if s.get("weather_units") == "f" else "km/h"}
	except Exception as e:
		print("[MohammedSkin] weather: %s" % e)
	_weather["busy"] = False
	if data:
		_weather["data"], _weather["t"] = data, time.time()
	else:
		_weather["t"] = time.time() - WEATHER_TTL + 5 * 60  # try again in 5 minutes
	cbs, _weather["cbs"] = _weather["cbs"], []
	for cb in cbs:
		try:
			from twisted.internet import reactor
			reactor.callFromThread(cb)
		except Exception:
			pass


_places = []


def weather_places():
	"""[{code, en, ar, cities: [[en, ar, lat, lon], ...]}, ...]: Arab countries first, biggest cities first."""
	if not _places:
		try:
			with open(os.path.join(SKIN_DIR, "weather", "places.json")) as f:
				_places.extend(json.load(f))
		except Exception as e:
			print("[MohammedSkin] places: %s" % e)
	return _places


def weather(callback=None):
	"""Current weather dict (or None). Refreshes in the background every 30 minutes; callback() runs on the GUI thread then."""
	if not settings().get("weather", True):
		return None
	if time.time() - _weather["t"] > WEATHER_TTL:
		if callback is not None and callback not in _weather["cbs"]:
			_weather["cbs"].append(callback)
		if not _weather["busy"]:
			_weather["busy"] = True
			th = threading.Thread(target=_weather_work, name="MohammedSkinWeather")
			th.daemon = True
			th.start()
	return _weather["data"]


def reset_weather():
	_weather.update({"t": 0, "data": None, "loc": None})


def weather_text(kind, data=None):
	data = data or _weather["data"]
	if not data or not settings().get("weather", True):
		return ""
	lang = weather_lang()
	ar = lang == "ar"
	deg = u"°"
	if kind == "Temp":
		return u"%d%s" % (data["temp"], deg)
	cond = data["ar"] if ar else _wx_word(data["en"], lang)
	if kind == "Condition":
		return cond
	if kind == "City":
		return data["city"]
	if kind == "MinMax":
		return u"%d%s / %d%s" % (data["tmax"], deg, data["tmin"], deg)
	if kind == "Humidity":
		return (u"الرطوبة %s%%" if ar else _wx_word("Humidity", lang) + u" %s%%") % data["hum"] if data.get("hum") is not None else ""
	if kind == "Wind":
		return u"%d %s" % (int(round(data["wind"] or 0)), data["wunit"]) if data.get("wind") is not None else ""
	if kind == "Line":
		return u"%s  •  %s" % (cond, data["city"]) if data["city"] else cond
	return ""


# ---------------------------------------------------------------- Arabic posters for Arabic channels
# Nilesat 7.0W / 8.0W, Arabsat and Badr 26.0E, 30.5E, 20.0E
ARAB_ORBITALS = (3530, 3520, 260, 255, 305, 200)


def arabic_channel(ref=None, name=""):
	if _ARABIC.search(name or ""):
		return True
	if ref is None:
		return False
	try:
		s = ref.toString() if hasattr(ref, "toString") else str(ref)
		ns = int(s.split(":")[6], 16)
		return (ns >> 16) in ARAB_ORBITALS
	except Exception:
		return False


def want_arabic_poster(ref=None, name="", title=""):
	mode = settings().get("arabic_posters", "auto")
	if mode == "off":
		return False
	if mode == "always":
		return True
	return bool(_ARABIC.search(title or "")) or arabic_channel(ref, name)


def tmdb_arabic_poster(tmdb_id, tmdb_type):
	"""URL of an Arabic poster for this title on TMDB, or None."""
	key = tmdb_key()
	if not key or not tmdb_id or tmdb_type not in ("movie", "tv"):
		return None
	url = "https://api.themoviedb.org/3/%s/%s/images?include_image_language=ar" % (tmdb_type, tmdb_id)
	headers = None
	if key.startswith("eyJ"):
		headers = {"Authorization": "Bearer " + key}
	else:
		url += "&api_key=" + key
	data = get_json(url, headers) or {}
	posters = [p for p in data.get("posters", []) if p.get("iso_639_1") == "ar" and p.get("file_path")]
	if not posters:
		return None
	posters.sort(key=lambda p: (-(p.get("vote_average") or 0), -(p.get("vote_count") or 0)))
	return "https://image.tmdb.org/t/p/w342" + posters[0]["file_path"]


# ---------------------------------------------------------------- 3D channel logo card
# Shown in place of a poster or backdrop when a channel has no event, nothing was found,
# or the poster was hidden by the adult filter. Needs python3-pillow; made once per size in /tmp.

def picon_path(ref):
	try:
		from Components.Renderer.Picon import getPiconName
		p = getPiconName(ref.toString() if hasattr(ref, "toString") else str(ref))
		if p and os.path.isfile(p):
			return p
	except Exception:
		pass
	try:  # older images
		s = (ref.toString() if hasattr(ref, "toString") else str(ref)).rstrip(":").split(":")
		name = "_".join(s[:10])
		for d in ("/usr/share/enigma2/picon", "/media/hdd/picon", "/media/usb/picon", "/media/mmc/picon", "/picon"):
			p = os.path.join(d, name + ".png")
			if os.path.isfile(p):
				return p
	except Exception:
		pass
	return None


def _theme_rgb(key, default):
	t = load_themes().get(settings().get("theme", "red")) or {}
	v = (t.get(key) or default).lstrip("#")
	try:
		return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))
	except Exception:
		v = default.lstrip("#")
		return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))


def _raqm():
	try:
		from PIL import features
		return bool(features.check("raqm"))
	except Exception:
		return False


_logo_busy = {}


def picon3d_async(ref, name, w, h, callback):
	"""Like picon3d, but made in the background: returns the path when it is ready now, else None and
	callback(path or None) runs on the GUI thread later."""
	sref = ref.toString() if hasattr(ref, "toString") else str(ref or "")
	key = md5((u"%s|%s|%s|%dx%d|%s" % (sref, name, settings().get("theme", "red"), w, h, logo_style())).encode("utf-8")).hexdigest()
	out = os.path.join(CACHE_DIR, "logo3d_%s.jpg" % key)
	if os.path.exists(out):
		return out
	with _lock:
		if key in _logo_busy:
			_logo_busy[key].append(callback)
			return None
		_logo_busy[key] = [callback]

	def work():
		path = None
		try:
			path = picon3d(ref, name, w, h)
		except Exception:
			path = None
		with _lock:
			cbs = _logo_busy.pop(key, [])
		for cb in cbs:
			try:
				from twisted.internet import reactor
				reactor.callFromThread(cb, path)
			except Exception:
				pass
	th = threading.Thread(target=work, name="MohammedSkinLogo")
	th.daemon = True
	th.start()
	return None


LOGO_STYLES = (("3d", "3D card"), ("full", "Full size logo"), ("plain", "Plain logo"))


def logo_style():
	v = settings().get("logo_style", "3d")
	return v if v in [n for n, l in LOGO_STYLES] else "3d"


def _logo_flat(ref, name, w, h, out):
	"""Channel logo filling the whole poster place: 'full' puts it over a soft, blurred copy of itself;
	'plain' on the dark colour of the theme. None when there is no logo file (the 3D card is used then)."""
	from PIL import Image, ImageDraw, ImageFilter
	pp = picon_path(ref) if ref is not None else None
	if not pp:
		return None
	try:
		if not os.path.isdir(CACHE_DIR):
			os.makedirs(CACHE_DIR)
		logo = Image.open(pp).convert("RGBA")
		bbox = logo.getbbox()
		if bbox:
			logo = logo.crop(bbox)
		ink = _theme_rgb("ink", "#060304")
		accent = _theme_rgb("accent", "#C8102E")
		bg = Image.new("RGB", (w, h), ink)
		if logo_style() == "full":
			# the logo itself, stretched over everything and blurred: the colours of the channel fill the place
			lw, lh = logo.size
			r = max(w / float(lw), h / float(lh)) * 1.15
			big = logo.resize((max(1, int(lw * r)), max(1, int(lh * r))), Image.BILINEAR)
			small = big.resize((max(1, big.size[0] // 8), max(1, big.size[1] // 8)), Image.BILINEAR).filter(ImageFilter.GaussianBlur(3))
			big = small.resize(big.size, Image.BILINEAR)
			layer = Image.new("RGBA", (w, h), ink + (255,))
			layer.alpha_composite(big, ((w - big.size[0]) // 2, (h - big.size[1]) // 2))
			bg = Image.blend(layer.convert("RGB"), Image.new("RGB", (w, h), ink), 0.45)
			fill = 0.92
		else:
			d = ImageDraw.Draw(bg)
			for y in range(h):  # dark, a little of the theme colour at the bottom
				t = y / float(h)
				d.line([(0, y), (w, y)], fill=tuple(int(ink[i] * (1 - t * 0.4) + accent[i] * 0.16 * t) for i in range(3)))
			fill = 0.94
		lw, lh = logo.size
		r = min(w * fill / float(lw), h * fill / float(lh))
		logo = logo.resize((max(1, int(lw * r)), max(1, int(lh * r))), Image.LANCZOS if hasattr(Image, "LANCZOS") else Image.ANTIALIAS)
		img = bg.convert("RGBA")
		sh = Image.new("RGBA", logo.size, (0, 0, 0, 0))
		sh.putalpha(logo.split()[3].point(lambda v: int(v * 0.6)))
		px, py = (w - logo.size[0]) // 2, (h - logo.size[1]) // 2
		img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(max(2, w // 60))), (px + max(2, w // 120), py + max(2, w // 120)))
		img.alpha_composite(logo, (px, py))
		img.convert("RGB").save(out + ".part", "JPEG", quality=90)
		os.rename(out + ".part", out)
		return out
	except Exception as e:
		print("[MohammedSkin] logo: %s" % e)
		return None


def picon3d(ref, name, w, h):
	"""Path of a 3D channel-logo picture of w x h for this channel, or None (no Pillow / error)."""
	if w < 40 or h < 40:
		return None
	sref = ref.toString() if hasattr(ref, "toString") else str(ref or "")
	key = md5((u"%s|%s|%s|%dx%d|%s" % (sref, name, settings().get("theme", "red"), w, h, logo_style())).encode("utf-8")).hexdigest()
	out = os.path.join(CACHE_DIR, "logo3d_%s.jpg" % key)
	if os.path.exists(out):
		return out
	try:
		from PIL import Image, ImageDraw, ImageFilter, ImageFont
	except ImportError:
		return None
	if logo_style() != "3d":
		p = _logo_flat(ref, name, w, h, out)
		if p:
			return p
	try:
		if not os.path.isdir(CACHE_DIR):
			os.makedirs(CACHE_DIR)
		ink, accent = _theme_rgb("ink", "#060304"), _theme_rgb("accent", "#C8102E")
		ss = 1  # receivers are slow: draw at the final size, blur only on small copies
		W, H = w * ss, h * ss
		im = Image.new("RGB", (W, H), ink)
		d = ImageDraw.Draw(im)
		for y in range(H):  # deep gradient towards the accent at the bottom
			t = y / float(H)
			c = tuple(int(ink[i] * (1 - t * 0.55) + accent[i] * 0.22 * t) for i in range(3))
			d.line([(0, y), (W, y)], fill=c)
		q = 6  # glow drawn 6x smaller, then stretched (a big blur is very slow on a receiver)
		sw_, sh_ = max(8, W // q), max(8, H // q)
		glow = Image.new("L", (sw_, sh_), 0)
		gr = int(min(sw_, sh_) * 0.42)
		ImageDraw.Draw(glow).ellipse((sw_ // 2 - gr, int(sh_ * 0.44) - gr, sw_ // 2 + gr, int(sh_ * 0.44) + gr), fill=150)
		glow = glow.filter(ImageFilter.GaussianBlur(max(1, gr * 0.45))).resize((W, H), Image.BILINEAR)
		im = Image.composite(Image.new("RGB", (W, H), accent), im, glow)
		# floor
		fy = int(H * (0.70 if H > W else 0.74))
		floor = Image.new("L", (W, H), 0)
		fd = ImageDraw.Draw(floor)
		for y in range(fy, H):
			k = min(1.0, (y - fy) / 14.0)  # soft edge, then fading away
			fd.line([(0, y), (W, y)], fill=int(90 * k * (1 - (y - fy) / float(H - fy + 1))))
		im = Image.composite(Image.new("RGB", (W, H), tuple(min(255, int(c * 0.6 + 20)) for c in accent)), im, floor)
		d = ImageDraw.Draw(im)
		d.line([(int(W * 0.08), fy), (int(W * 0.92), fy)], fill=tuple(min(255, c + 60) for c in accent), width=max(1, ss))
		# the logo on a glass slab, turned a little towards the viewer
		slab_w = int(W * (0.78 if H > W else 0.56))
		slab_h = int(slab_w * 0.62)
		depth = max(6, int(slab_w * 0.06))
		slab = Image.new("RGBA", (slab_w + depth, slab_h + depth), (0, 0, 0, 0))
		sd = ImageDraw.Draw(slab)
		rad = max(8, slab_h // 9)
		for i in range(depth, 0, -1):  # extruded edge
			shade = tuple(int(c * (0.35 + 0.4 * (1 - i / float(depth)))) for c in accent)
			sd.rounded_rectangle((i, i, i + slab_w - 1, i + slab_h - 1), radius=rad, fill=shade + (255,))
		face = Image.new("RGBA", (slab_w, slab_h), (0, 0, 0, 0))
		fdr = ImageDraw.Draw(face)
		top_c = tuple(min(255, int(c * 0.55 + 38)) for c in ink)
		bot_c = tuple(int(c * 0.6) for c in ink)
		for y in range(slab_h):
			t = y / float(slab_h)
			fdr.line([(0, y), (slab_w, y)], fill=tuple(int(top_c[i] + (bot_c[i] - top_c[i]) * t) for i in range(3)) + (255,))
		fmask = Image.new("L", (slab_w, slab_h), 0)
		ImageDraw.Draw(fmask).rounded_rectangle((0, 0, slab_w - 1, slab_h - 1), radius=rad, fill=255)
		face.putalpha(fmask)
		gloss = Image.new("RGBA", (slab_w, slab_h), (0, 0, 0, 0))
		ImageDraw.Draw(gloss).rounded_rectangle((3 * ss, 3 * ss, slab_w - 3 * ss, slab_h // 2), radius=rad, fill=(255, 255, 255, 26))
		face.alpha_composite(gloss)
		ImageDraw.Draw(face).rounded_rectangle((0, 0, slab_w - 1, slab_h - 1), radius=rad, outline=accent + (255,), width=max(2, ss * 2))
		slab.alpha_composite(face, (0, 0))
		logo = None
		pp = picon_path(ref) if ref is not None else None
		if pp:
			try:
				logo = Image.open(pp).convert("RGBA")
				bbox = logo.getbbox()
				if bbox:
					logo = logo.crop(bbox)
			except Exception:
				logo = None
		if logo is not None:
			lw, lh = int(slab_w * 0.84), int(slab_h * 0.78)
			r = min(lw / float(logo.size[0]), lh / float(logo.size[1]))
			logo = logo.resize((max(1, int(logo.size[0] * r)), max(1, int(logo.size[1] * r))), Image.LANCZOS if hasattr(Image, "LANCZOS") else Image.ANTIALIAS)
			slab.alpha_composite(logo, ((slab_w - logo.size[0]) // 2, (slab_h - logo.size[1]) // 2))
		else:
			txt = (name or "TV").strip()
			if _ARABIC.search(txt) and not _raqm():
				txt = "TV"  # Arabic needs the shaping library to look right
			fpath = os.path.join(SKIN_DIR, "fonts", "moh-title.otf")
			if _ARABIC.search(txt):
				fpath = os.path.join(SKIN_DIR, [f for f in AR_TEXT_FONTS if f[0] == font_value("ar_text_font", AR_TEXT_FONTS, "tajawal")][0][3])
			size = int(slab_h * 0.36)
			try:
				font = ImageFont.truetype(fpath, size)
				while size > 10 and sd.textlength(txt, font=font) > slab_w * 0.86:
					size -= 2
					font = ImageFont.truetype(fpath, size)
			except Exception:
				font = ImageFont.load_default()
			sd.text((slab_w // 2, slab_h // 2), txt, font=font, fill=(242, 236, 226, 255), anchor="mm")
		# perspective: right side a little further away
		sw, sh = slab.size
		k = 0.10
		quad_w = int(sw * 0.94)
		persp = slab.transform((quad_w, sh), Image.QUAD,
			(0, 0, 0, sh, sw, sh + int(sh * k), sw, -int(sh * k)), Image.BICUBIC)
		px = (W - persp.size[0]) // 2
		py = fy - persp.size[1] - int(H * 0.02)
		shadow = Image.new("L", (sw_, sh_), 0)
		ImageDraw.Draw(shadow).ellipse((px // q, (fy - int(H * 0.025)) // q, (px + persp.size[0]) // q, (fy + int(H * 0.03)) // q), fill=170)
		shadow = shadow.filter(ImageFilter.GaussianBlur(2)).resize((W, H), Image.BILINEAR)
		im = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), im, shadow)
		im = im.convert("RGBA")
		im.alpha_composite(persp, (px, max(0, py)))
		# reflection on the floor
		refl = persp.transpose(Image.FLIP_TOP_BOTTOM)
		mask = Image.new("L", refl.size, 0)
		md = ImageDraw.Draw(mask)
		for y in range(refl.size[1]):
			md.line([(0, y), (refl.size[0], y)], fill=max(0, int(70 * (1 - y / (refl.size[1] * 0.55)))))
		a = refl.split()[3]
		from PIL import ImageChops
		refl.putalpha(ImageChops.multiply(a, mask))
		im.alpha_composite(refl, (px, fy + int(H * 0.004)))
		# channel name under the floor line on tall cards
		if H > W * 1.2 and name and (_raqm() or not _ARABIC.search(name)):
			fpath = os.path.join(SKIN_DIR, "fonts", "moh-semibold.otf")
			if _ARABIC.search(name):
				fpath = os.path.join(SKIN_DIR, [f for f in AR_TEXT_FONTS if f[0] == font_value("ar_text_font", AR_TEXT_FONTS, "tajawal")][0][3])
			try:
				size = int(W * 0.085)
				font = ImageFont.truetype(fpath, size)
				dd = ImageDraw.Draw(im)
				while size > 10 and dd.textlength(name, font=font) > W * 0.88:
					size -= 2
					font = ImageFont.truetype(fpath, size)
				dd.text((W // 2, int(H * 0.88)), name, font=font, fill=(242, 236, 226, 255), anchor="mm")
			except Exception:
				pass
		im = im.convert("RGB")
		if im.size != (w, h):
			im = im.resize((w, h), Image.BILINEAR)
		im.save(out + ".part", "JPEG", quality=90)
		os.rename(out + ".part", out)
		return out
	except Exception as e:
		print("[MohammedSkin] logo card: %s" % e)
		return None


# ---------------------------------------------------------------- online update (GitHub)

def version_tuple(v):
	out = []
	for part in re.split(r"[.\-]", (v or "").strip()):
		if part.isdigit():
			out.append(int(part))
		else:
			break
	return tuple(out)


def latest_version():
	"""Version string published on GitHub, or None when it cannot be read."""
	try:
		v = _open(UPDATE_BASE + "/version.txt?t=%d" % int(time.time())).read().decode("utf-8", "ignore").strip()
		return v if version_tuple(v) else None
	except Exception:
		return None


def install_complete(base=SKIN_DIR):
	"""The package writes .installed (its version) as its very last step; a missing or older mark means the
	last update stopped half way (no space, power cut, crash), so it is offered again."""
	try:
		with open(os.path.join(base, ".installed")) as f:
			return f.read().strip() == SKIN_VERSION
	except Exception:
		return False


def check_update(callback):
	"""callback(latest_or_None, newer_bool) is called on the main thread."""
	def work():
		v = latest_version()
		newer = bool(v) and (version_tuple(v) > version_tuple(SKIN_VERSION) or not install_complete())
		try:
			from twisted.internet import reactor
			reactor.callFromThread(callback, v, newer)
		except Exception:
			pass
	th = threading.Thread(target=work, name="MohammedSkinUpdate")
	th.daemon = True
	th.start()


# ---------------------------------------------------------------- image detection (OpenViX, OpenBH, OpenATV, PurE2, EGAMI)

IMAGE_NAMES = {"openvix": "OpenViX", "openbh": "OpenBlackHole", "openatv": "OpenATV", "pure2": "PurE2", "egami": "EGAMI"}
IMAGE_ALIASES = {"openblackhole": "openbh", "blackhole": "openbh", "bh": "openbh", "vix": "openvix", "atv": "openatv",
	"purezwei": "pure2", "pure": "pure2", "egamiimage": "egami"}
# images whose enigma2 uses the OpenViX window-style colour names (colLabelForeground ...)
VIX_FAMILY = ("openvix", "openbh")
ATV_FAMILY = ("openatv", "pure2", "egami")


def _read_lines(path):
	try:
		with open(path, "rb") as f:
			return f.read().decode("utf-8", "ignore").splitlines()
	except Exception:
		return []


def _norm(value):
	v = re.sub(r"[^a-z0-9]", "", (value or "").strip().strip("'\"").lower())
	v = IMAGE_ALIASES.get(v, v)
	if v in IMAGE_NAMES:
		return v
	for key in IMAGE_NAMES:  # "openatv8" / "openbh60" / "pure2760"
		if v.startswith(key):
			return key
	return ""


def image_key(root=""):
	"""Which image this box runs: openvix, openbh, openatv, pure2, egami, or "" when unknown."""
	for line in _read_lines(root + "/usr/lib/enigma.info"):
		if line.startswith("distro="):
			k = _norm(line.split("=", 1)[1])
			if k:
				return k
	for line in _read_lines(root + "/usr/lib/enigma.info"):
		if line.startswith("displaydistro="):
			k = _norm(line.split("=", 1)[1])
			if k:
				return k
	for line in _read_lines(root + "/etc/image-version"):
		low = line.lower()
		if low.startswith("distro=") or low.startswith("creator") or low.startswith("comment="):
			k = _norm(line.split("=", 1)[-1])
			if k:
				return k
	for line in _read_lines(root + "/etc/issue")[:2]:
		for token in line.split():
			k = _norm(token)
			if k:
				return k
	if os.path.exists(root + "/etc/bhversion"):
		return "openbh"
	if os.path.exists(root + "/etc/vixversion"):
		return "openvix"
	return ""


def image_name(root=""):
	return IMAGE_NAMES.get(image_key(root), "")


def image_label(root=""):
	"""Text for the glowing label in the middle of the infobar."""
	name = image_name(root)
	return (name + " Moh") if name else "Moh"


def skin_family(root=""):
	"""'vix' when enigma2 uses the OpenViX window-style colour names, else 'atv'.
	Read from the image's own enigma module, so unknown images are handled too.
	When in doubt we stay with 'vix': OpenATV-style images only log a warning for the
	vix names, while OpenViX-style images refuse a skin with the atv names."""
	for fn in ("enigma.py", "enigma.pyc"):
		try:
			with open(root + "/usr/lib/enigma2/python/" + fn, "rb") as f:
				data = f.read()
		except Exception:
			continue
		if b"colLabelForeground" in data:
			return "vix"
		if b"colListboxBackgroundSelected" in data and b"colForeground" in data:
			return "atv"
	return "atv" if image_key(root) in ATV_FAMILY else "vix"


def current_family(base=SKIN_DIR):
	return current_style("image", base)


def _keyboard_rows(fam, base=SKIN_DIR):
	"""Virtual keyboard rows: OpenATV-style images (OpenATV, PurE2, EGAMI) draw their keyboard window for
	45 pixel rows, so bigger rows push the last keys out of the window there."""
	line = '<alias name="VirtualKeyboard" font="Regular" size="%s" />' % ('28" height="45' if fam == "atv" else '34" height="68')
	skin = os.path.join(base, "skin.xml")
	try:
		with open(skin) as f:
			xml = f.read()
		new = re.sub(r'<alias name="VirtualKeyboard"[^>]*/>', line, xml)
		if new == xml:
			return False
		tmp = skin + ".tmp"
		with open(tmp, "w") as f:
			f.write(new)
		os.rename(tmp, skin)
		return True
	except Exception as e:
		print("[MohammedSkin] keyboard rows: %s" % e)
		return False


def adapt_image(base=SKIN_DIR, root=""):
	"""Put the window style that matches this image into skin.xml. Returns (image_key, family, changed)."""
	key = image_key(root)
	fam = skin_family(root)
	changed = False
	if current_family(base) != fam:
		changed = apply_style("image", fam, base)
	# long image names (OpenBlackHole) get running dots with a wider gap
	dots = "wide" if len(image_label(root)) > 13 else "normal"
	if current_style("dots", base) != dots:
		changed = apply_style("dots", dots, base) or changed
	changed = _keyboard_rows(fam, base) or changed
	s = dict(settings())
	if s.get("image") != key or s.get("family") != fam:
		s["image"], s["family"] = key, fam
		save_settings(s)
	return key, fam, changed


def apply_infobar(name, base=SKIN_DIR):
	"""Switch the whole first infobar, then put the user's clock, poster place and running dots back in."""
	if not apply_style("infobar", name, base):
		return False
	s = settings()
	apply_clock(s.get("clock", "royal"), base)
	apply_style("ibposter", s.get("ibposter_style", "left"), base)  # only the classic infobar has this block
	adapt_image(base)  # running dots for the image name
	return True


def reapply_all(base=SKIN_DIR, log=print):
	"""After an install or update: adapt to the image and restore every choice the user made."""
	key, fam, _ = adapt_image(base)
	log("MohammedSkin: image %s (%s family)" % (IMAGE_NAMES.get(key, "unknown"), fam))
	s = settings()
	ib = s.get("infobar_style", "classic")
	if ib != "classic":
		log("MohammedSkin: re-applying infobar style %s" % ib)
		apply_style("infobar", ib, base)
	clock, theme = s.get("clock", "royal"), s.get("theme", "red")
	if clock != "royal":
		log("MohammedSkin: re-applying clock %s" % clock)
		apply_clock(clock, base)
	if theme != "red":
		log("MohammedSkin: re-applying theme %s" % theme)
		apply_theme(theme, base)
	for kind, default in STYLE_DEFAULTS.items():
		name = s.get(kind + "_style", default)
		if name != default:
			log("MohammedSkin: re-applying %s style %s" % (kind, name))
			apply_style(kind, name, base)
	adapt_image(base)
	try:  # sizes, plugin list, infobar transparency and fonts follow the styles that are in use now
		apply_tuning(base)
		apply_arabic_fonts(base)
		apply_cjk_font(base)
		log("MohammedSkin: sizes and transparency applied")
	except Exception as e:
		log("MohammedSkin: tuning failed: %s" % e)
	return key, fam


# ---------------------------------------------------------------- rating / year / genre of an event

def event_entry(event, callback=None):
	"""Cached lookup entry (poster, rating, year, genres) for an EPG event. When it is not known yet the
	lookup starts in the background and callback() runs on the GUI thread once it is."""
	if event is None:
		return None
	try:
		title, year = clean_title(event.getEventName() or "")
	except Exception:
		return None
	if no_event_title(title):
		return None
	key = cache_key(title, year)
	e = cached(key)
	if e is not None or callback is None:
		return e
	arabic = bool(_ARABIC.search(title))
	if not arabic:
		try:
			import NavigationInstance
			arabic = arabic_channel(NavigationInstance.instance.getCurrentlyPlayingServiceReference())
		except Exception:
			pass
	return request(title, year, guess_kind(event), lambda entry: callback(), arabic=arabic)


def rating_of(entry):
	try:
		r = float(entry.get("rating") or 0)
	except Exception:
		r = 0
	return max(0.0, min(10.0, r))


try:
	set_cache_dir()
except Exception:
	pass


# ---------------------------------------------------------------- windows of plugins made for smaller screens
# Many plugins carry their own small window (made for 1280x720 or 720x576) and the image keeps old
# small windows in skin_default.xml. On a full HD skin they show tiny, in a corner. enigma2 scales a
# window by itself when its <screen> says which resolution it was drawn for, so we add
# resolution="1280,720" to every such window that has no size of its own beyond that (and is not a
# front display window). Windows of this skin, and windows already made for full HD, are left alone.
FIT_RES = "1280,720"
_SCREEN_TAG = re.compile(r"<screen\b[^>]*>", re.S)
_SIZE_ATTR = re.compile(r'size\s*=\s*"\s*(\d+)\s*,\s*(\d+)\s*"')
_NOT_TV = ("summary", "lcd", "display", "vfd", "oled")


_POS_ATTR = re.compile(r'position\s*=\s*"\s*([^",]+)\s*,\s*([^"]+?)\s*"')


def _small(w, h, pos=""):
	"""A window drawn for 1280x720: small enough, and (with a fixed position) inside the 1280x720 screen."""
	if not (300 <= w <= 1280 and 130 <= h <= 720):
		return False
	m = _POS_ATTR.search(pos or "")
	if m:
		try:
			if int(m.group(1)) + w > 1280 or int(m.group(2)) + h > 720:
				return False
		except ValueError:
			pass  # center, center: fine
	return True


_FONT_SIZE = re.compile(r'font\s*=\s*"[^";]*;\s*(\d+)')
_ITEM_H = re.compile(r'itemHeight\s*=\s*"\s*(\d+)')


def _made_for_fhd(text):
	"""Windows already drawn for full HD (big fonts, tall rows) must not be enlarged again,
	even when they are small: that is what made some plugin windows too big."""
	sizes = sorted(int(x) for x in _FONT_SIZE.findall(text or ""))
	rows = [int(x) for x in _ITEM_H.findall(text or "")]
	if sizes and sizes[len(sizes) // 2] >= 25:
		return True
	return bool(rows) and max(rows) >= 45


def fit_skin_text(text, name=""):
	"""The same skin text with resolution="1280,720" added to its first <screen> when that window is small."""
	if isinstance(text, (list, tuple)):
		return type(text)(fit_skin_text(t, name) for t in text) if isinstance(text, tuple) else text
	if not isinstance(text, str) or "<screen" not in text or [k for k in _NOT_TV if k in name.lower()]:
		return text
	m = _SCREEN_TAG.search(text)
	if not m:
		return text
	tag = m.group(0)
	if "resolution=" in tag or " id=" in tag:
		return text
	sm = _SIZE_ATTR.search(tag)
	if not sm or not _small(int(sm.group(1)), int(sm.group(2)), tag) or _made_for_fhd(text):
		return text
	return text[:m.start()] + '<screen resolution="%s"' % FIT_RES + tag[len("<screen"):] + text[m.end():]


def _fit_dom(names=None):
	"""Same for windows read from skin files that are not this skin's (skin_default.xml, plugin skin files)."""
	try:
		import skin as S
		dom = S.domScreens
	except Exception:
		return
	for name in (names if names is not None else list(dom.keys())):
		item = dom.get(name)
		if not item:
			continue
		elem, path = item[0], item[1] if len(item) > 1 else ""
		try:
			if (path or "").startswith(SKIN_DIR) or "resolution" in elem.attrib or "id" in elem.attrib:
				continue
			if [k for k in _NOT_TV if k in (name or "").lower()]:
				continue
			sm = _SIZE_ATTR.search('size="%s"' % elem.attrib.get("size", ""))
			if sm and _small(int(sm.group(1)), int(sm.group(2)), 'position="%s"' % elem.attrib.get("position", "")) and not _made_for_fhd(
					" ".join('font="%s" itemHeight="%s"' % (e.attrib.get("font", ""), e.attrib.get("itemHeight", "")) for e in elem.iter())):
				elem.attrib["resolution"] = FIT_RES
		except Exception:
			pass


_fitter = []


def install_screen_fitter():
	"""Hook once into Screen: small built-in windows of plugins are scaled up before they are drawn."""
	if _fitter or not settings().get("fit_screens", True):
		return False
	try:
		from Screens.Screen import Screen
	except Exception:
		return False
	_fit_dom()
	init0 = Screen.__init__
	setattr0 = Screen.__setattr__

	def __init__(self, *args, **kwargs):
		init0(self, *args, **kwargs)
		try:
			name = self.__class__.__name__
			_fit_dom([name])
			text = getattr(self.__class__, "skin", None)
			if text and "skin" not in self.__dict__:
				fitted = fit_skin_text(text, name)
				if fitted is not text:
					object.__setattr__(self, "skin", fitted)
		except Exception:
			pass

	def __setattr__(self, key, value):
		if key == "skin" and isinstance(value, (str, tuple)):  # plugins that pick their window in __init__
			try:
				value = fit_skin_text(value, self.__class__.__name__)
			except Exception:
				pass
		elif key == "skinName":
			try:
				_fit_dom(value if isinstance(value, list) else [value])
			except Exception:
				pass
		setattr0(self, key, value)

	Screen.__init__ = __init__
	Screen.__setattr__ = __setattr__
	_fitter.append(True)
	return True


# ---------------------------------------------------------------------------------------------
# Automatic windows for plugins: a plugin window that this skin has no design for is read
# (what it holds: a settings list, a plain list or a long text, its labels and colour keys)
# and gets a window drawn in the skin's own style. Windows with pictures, sliders, video or
# their own list layouts keep the plugin's design, enlarged to the screen (see above).
# ---------------------------------------------------------------------------------------------

_KEY_RE = re.compile(r"(?i)^(?:key_?|button_?|btn_?)?(red|green|yellow|blue)(?:_?text|_?label)?$")
_LIST_NAMES = ("config", "list", "menu", "filelist", "entries", "menulist", "mylist", "liste", "streamlist", "choicelist")
_HIDDEN_NAMES = ("helpwindow", "vkeyicon", "key_help", "key_menu", "key_info", "key_text", "key_0", "footnote", "image", "screenpath")
_auto_cache = {}
_auto_off = set()


def _mro(obj):
	try:
		return set(c.__name__ for c in type(obj).__mro__)
	except Exception:
		return set()


def _kind(key, obj):
	"""What a screen part is, for the automatic window."""
	names = _mro(obj)
	low = key.lower()
	if "GUIComponent" in names:
		if "ConfigList" in names or "ConfigListScreen" in names:
			return "config"
		if "ScrollLabel" in names:
			return "scroll"
		if "MenuList" in names:
			content = type(getattr(obj, "l", None)).__name__
			return "strlist" if content in ("eListboxPythonStringContent", "eListboxPythonConfigContent") else "complex"
		if "Label" in names or "Button" in names:
			return "keyLabel" if _KEY_RE.match(key) else ("hide" if low in _HIDDEN_NAMES else "label")
		if "Pixmap" in names and (low in _HIDDEN_NAMES or _KEY_RE.match(key)):
			return "hidePix"
		return "complex"
	if "Source" in names or "Element" in names:
		if "Boolean" in names:
			return "ignore"
		if "StaticText" in names:
			return "keyStatic" if _KEY_RE.match(key) else ("ignore" if key == "Title" or low in _HIDDEN_NAMES else "static")
		if "Clock" in names:
			return "ignore"
		return "complex"
	return "ignore"  # action maps and other helpers


def _orig_positions(screen, names):
	"""y position of each widget in the plugin's own design (to keep its labels above or below the list)."""
	elem = None
	try:
		import skin as S
		for n in names:
			if n in S.domScreens:
				elem = S.domScreens[n][0]
				break
	except Exception:
		pass
	if elem is None:
		text = getattr(screen, "skin", None)
		if isinstance(text, (tuple, list)):
			text = [t for t in text if isinstance(t, str) and "<screen" in t and ' id="2"' not in t and " id='2'" not in t]
			text = text[0] if text else None
		if isinstance(text, str):
			try:
				from xml.etree.ElementTree import fromstring
				elem = fromstring(text.strip())
			except Exception:
				elem = None
	pos = {}
	if elem is None:
		return pos
	try:  # the size the plugin's window has on a full HD screen
		w, h = [int(v) for v in elem.attrib.get("size", "0,0").split(",")]
		res = elem.attrib.get("resolution", "")
		hd = res.startswith("1280") or (not res and not _made_for_fhd(" ".join('font="%s"' % e.attrib.get("font", "") for e in elem.iter())))
		pos["__width__"] = int(w * 1.5) if hd else w
	except Exception:
		pass
	for w in elem.iter("widget"):
		key = w.attrib.get("name") or w.attrib.get("source")
		try:
			y = int(str(w.attrib.get("position", "0,0")).split(",")[1].strip())
		except (ValueError, IndexError):
			y = 9999
		if key and key not in pos:
			pos[key] = y
	return pos


def _xa(text):
	return str(text).replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


def plan_auto_screen(parts, pos):
	"""parts: [(key, kind)]. Returns the window as skin XML, or None when this window should keep its own design."""
	kinds = [k for n, k in parts]
	if "complex" in kinds:
		return None
	lists = [n for n, k in parts if k in ("config", "strlist")]
	scrolls = [n for n, k in parts if k == "scroll"]
	texts = [(n, k) for n, k in parts if k in ("label", "static")]
	# only the labels the plugin's own design shows (screens carry a few empty helpers)
	shown = [k for k in pos if not k.startswith("__")]
	texts = [t for t in texts if t[0] in shown] if shown else [t for t in texts if t[0] != "title"]
	keys = {}
	for n, k in parts:
		m = _KEY_RE.match(n)
		if k in ("keyLabel", "keyStatic") and m:
			c = m.group(1).lower()
			if c not in keys or n.lower().startswith("key_"):
				keys[c] = (n, k)
	if len(lists) + len(scrolls) != 1 or len(texts) > 4:
		return None
	main = (lists or scrolls)[0]
	mainY = pos.get(main, 0)
	above = sorted([t for t in texts if pos.get(t[0], 9999) < mainY], key=lambda t: pos.get(t[0], 0))
	below = sorted([t for t in texts if t not in above], key=lambda t: pos.get(t[0], 9999))
	W, H = (1600, 900) if scrolls else (1400, 860)
	if lists and 0 < pos.get("__width__", 9999) < 1000:  # a small window (e.g. a list of a few cams): a smaller frame
		W, H = 1150, 740
	x, w = 50, W - 100
	out = ['<screen name="MohammedAuto" position="center,center" size="%d,%d" backgroundColor="transparent" flags="wfNoBorder">' % (W, H),
		'<eLabel position="0,0" size="%d,%d" backgroundColor="panel" zPosition="-1" />' % (W, H),
		'<eLabel position="0,0" size="%d,4" backgroundColor="crimson" zPosition="1" />' % W,
		'<widget source="Title" render="Label" position="%d,26" size="%d,64" font="Title;44" foregroundColor="ivory" backgroundColor="panel" transparent="1" noWrap="1" zPosition="1" />' % (x, w),
		'<eLabel position="%d,104" size="%d,1" backgroundColor="line" zPosition="1" />' % (x, w)]

	def text(n, k, y, h, font, color, extra=""):
		attr = 'source="%s" render="Label"' % _xa(n) if k == "static" else 'name="%s"' % _xa(n)
		return '<widget %s position="%d,%d" size="%d,%d" font="%s" foregroundColor="%s" backgroundColor="panel" transparent="1" zPosition="2"%s />' % (attr, x, y, w, h, font, color, extra)

	y = 120
	for n, k in above:
		out.append(text(n, k, y, 40, "Semi;28", "gold", ' noWrap="1"'))
		y += 46
	keysY = H - 56
	bottom = keysY - 16
	lows = []
	for i, (n, k) in enumerate(reversed(below)):
		last = i == len(below) - 1  # the first label under the list gets two lines
		h = 76 if last else 36
		bottom -= h + 6
		lows.append((n, k, bottom, h, "Regular;24" if last else "Regular;22", "smoke" if last else "ivorydim", "" if last else ' noWrap="1"'))
	mainBottom = (bottom - 14) if below else (keysY - 20)
	if lists:
		out.append('<widget name="%s" position="%d,%d" size="%d,%d" backgroundColor="panel" foregroundColor="ivory" backgroundColorSelected="selbg" foregroundColorSelected="selfg" scrollbarMode="showOnDemand" transparent="1" zPosition="2" />' % (_xa(main), x, y + 6, w, mainBottom - y - 6))
	else:
		out.append('<widget name="%s" position="%d,%d" size="%d,%d" font="Regular;26" foregroundColor="ivory" backgroundColor="panel" transparent="1" zPosition="2" />' % (_xa(main), x, y + 6, w, mainBottom - y - 6))
	if below:
		out.append('<eLabel position="%d,%d" size="%d,1" backgroundColor="line" zPosition="1" />' % (x, mainBottom + 6, w))
	for n, k, ty, h, font, color, extra in lows:
		out.append(text(n, k, ty, h, font, color, extra))
	step = w // 4
	for i, c in enumerate(("red", "green", "yellow", "blue")):
		if c not in keys:
			continue
		n, k = keys[c]
		kx = x + i * step
		attr = 'source="%s" render="Label"' % _xa(n) if k == "keyStatic" else 'name="%s"' % _xa(n)
		out.append('<eLabel position="%d,%d" size="18,18" backgroundColor="key%s" zPosition="1" />' % (kx, keysY + 11, c))
		out.append('<widget %s position="%d,%d" size="%d,40" font="Regular;24" foregroundColor="ivory" backgroundColor="panel" valign="center" transparent="1" noWrap="1" zPosition="2" />' % (attr, kx + 28, keysY, step - 40))
	for n, k in parts:
		if k == "hidePix":
			out.append('<widget name="%s" position="0,1100" size="4,4" pixmap="%s/img/blank.png" alphatest="on" zPosition="-1" />' % (_xa(n), SKIN_DIR))
		elif k == "hide":
			out.append('<widget name="%s" position="0,1100" size="4,4" font="Regular;10" transparent="1" zPosition="-1" />' % _xa(n))
	out.append("</screen>")
	return "\n".join(out)


def _ours(names):
	"""True when this skin (or the user's own skin_user.xml) already has a window for one of these names."""
	try:
		import skin as S
	except Exception:
		return True
	for n in names:
		item = S.domScreens.get(n)
		if item:
			path = (item[1] if len(item) > 1 else "") or ""
			image_default = "/skin_default" in path or path.rstrip("/") == "/usr/share/enigma2"  # the image's fallback skin
			return not (image_default or "/Plugins/" in path)
	return False


def auto_window(screen, names):
	"""The name of an automatic window for this screen (registered in the skin), or None."""
	cls = screen.__class__
	tag = (cls.__module__, cls.__name__, tuple(names))
	if tag in _auto_off:
		return None
	if _ours(names):
		return None
	parts = []
	for key in list(screen.keys()):
		parts.append((key, _kind(key, screen[key])))
	sig = tag + (tuple(parts),)
	name = _auto_cache.get(sig)
	if name:
		return name
	xml = plan_auto_screen(parts, _orig_positions(screen, names))
	if not xml:
		_auto_off.add(tag) if len(_auto_off) < 500 else None
		return None
	import skin as S
	from xml.etree.ElementTree import fromstring
	name = "MohammedAuto_%d" % (len(_auto_cache) + 1)
	elem = fromstring(xml)
	elem.attrib["name"] = name
	S.domScreens[name] = (elem, SKIN_DIR + "/")
	_auto_cache[sig] = name
	return name


_KEYS4 = ("red", "green", "yellow", "blue")
_keys_done = set()  # windows already checked (kept out of the window's own attributes)


def ensure_keys(screen, names):
	"""A window of this skin that shows none of the colour keys the screen offers gets a key row added
	under it (the window grows by one row), so the keys of every window can always be seen."""
	try:
		import skin as S
		from xml.etree.ElementTree import SubElement
	except Exception:
		return
	elem = None
	for n in names:
		item = S.domScreens.get(n)
		if item:
			if (item[1] or "").startswith(SKIN_DIR):
				elem = item[0]
			break
	if elem is None or id(elem) in _keys_done:
		return
	used = set()
	for w in elem.iter("widget"):
		used.add(w.attrib.get("name") or w.attrib.get("source") or "")
	if any(("key_" + c) in used for c in _KEYS4):
		_keys_done.add(id(elem))  # the design shows its keys itself
		return
	keys = []
	for c in _KEYS4:
		k = "key_" + c
		if k in screen:
			kind = _kind(k, screen[k])
			if kind in ("keyLabel", "keyStatic"):
				keys.append((c, k, kind))
	if not keys:
		return  # nothing to show (the same screen class may show keys another time: check again then)
	try:
		w, h = [int(v) for v in elem.attrib.get("size", "0,0").split(",")]
	except ValueError:
		return
	pos = elem.attrib.get("position", "")
	if w < 700 or h < 300 or h > 1000 or not pos.replace(" ", "").startswith("center"):
		_keys_done.add(id(elem))
		return
	for e in list(elem):  # the window background grows with the window
		if e.tag == "eLabel" and e.attrib.get("size", "").replace(" ", "") == "%d,%d" % (w, h):
			e.attrib["size"] = "%d,%d" % (w, h + 56)
	elem.attrib["size"] = "%d,%d" % (w, h + 56)
	step = (w - 100) // 4
	for i, (c, k, kind) in enumerate(keys):
		x = 50 + i * step
		SubElement(elem, "eLabel", {"position": "%d,%d" % (x, h + 15), "size": "18,18", "backgroundColor": "key" + c, "zPosition": "3"})
		a = {"position": "%d,%d" % (x + 28, h + 4), "size": "%d,40" % (step - 40), "font": "Regular;24", "foregroundColor": "ivory",
			"backgroundColor": "panel", "valign": "center", "transparent": "1", "noWrap": "1", "zPosition": "3"}
		if kind == "keyStatic":
			a.update({"source": k, "render": "Label"})
		else:
			a["name"] = k
		SubElement(elem, "widget", a)
	_keys_done.add(id(elem))



# ---------------------------------------------------------------------------------------------
# Windows from the image's own skin: every image (OpenViX, OpenBh, OpenATV, PurE2, EGAMI) ships a
# default full HD skin that has a window for each of its own screens and plugins, with the right
# widget names for that image. A window this skin has no design for is taken from there, with the
# image skin's colours and fonts turned into this skin's colours and fonts.
# ---------------------------------------------------------------------------------------------

_borrow = {"ready": False, "screens": {}, "thread": None, "dir": ""}
_OUR_FONTS = {"Regular": "moh-regular.otf", "Semi": "moh-semibold.otf", "Title": "moh-title.otf", "Fixed": "moh-mono.ttf",
	"Console": "moh-mono.ttf"}


def _image_default_skin():
	try:
		import skin as S
		name = getattr(S, "DEFAULT_SKIN", "") or ""
	except Exception:
		return ""
	if not name or name.startswith("MohammedSkin") or "skin_default" in name:
		return ""
	path = "/usr/share/enigma2/" + name
	return path if os.path.isfile(path) else ""


def _our_font_file(name):
	low = name.lower()
	if "mono" in low or "console" in low or "fixed" in low or "lcd" in low:
		f = "moh-mono.ttf"
	elif "title" in low or "head" in low:
		f = "moh-title.otf"
	elif "bold" in low or "semi" in low or "medium" in low or "black" in low:
		f = "moh-semibold.otf"
	else:
		f = "moh-regular.otf"
	return os.path.join(SKIN_DIR, "fonts", f)


def _color_target(value, name=""):
	"""Which colour of this skin an image-skin colour becomes (by how dark / bright / coloured it is)."""
	low = name.lower()
	for c in ("red", "green", "yellow", "blue"):
		if c in low and ("key" in low or "button" in low or "btn" in low):
			return "key" + c  # colour keys keep their colour
	if "select" in low or "cursor" in low or "focus" in low or "highlight" in low:
		if "fg" in low or "fore" in low or "text" in low or "font" in low:
			return "selfg"  # text on the selection bar
		return "selbg"  # the selection bar is this skin's selection colour
	v = value.strip().lstrip("#")
	if len(v) == 6:
		v = "00" + v
	try:
		a, r, g, b = int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16), int(v[6:8], 16)
	except ValueError:
		return None
	if a >= 0xF0:
		return None  # transparent stays transparent
	hi, lo = max(r, g, b), min(r, g, b)
	light = (hi + lo) / 510.0
	sat = 0 if hi == 0 else (hi - lo) / float(hi)
	if sat > 0.45 and 0.2 < light < 0.85:
		return "crimson"  # their accent becomes ours
	if light < 0.22:
		return "panel"
	if light > 0.8:
		return "ivory"
	if light > 0.55:
		return "ivorydim"
	return "line" if light < 0.38 else "smoke"


def _read_image_skin(path):
	from xml.etree.ElementTree import parse
	base = os.path.dirname(path) + "/"
	screens, colors, fonts, aliases = {}, {}, {}, {}
	todo, seen = [path], set()
	while todo and len(seen) < 25:
		f = todo.pop(0)
		if f in seen or not os.path.isfile(f):
			continue
		seen.add(f)
		try:
			root = parse(f).getroot()
		except Exception as e:
			print("[MohammedSkin] image skin %s: %s" % (f, e))
			continue
		for out in root.findall("output"):  # the size the image skin is drawn for (HD skins are scaled up)
			if out.attrib.get("id", "0") == "0":
				r = out.find("resolution")
				if r is not None and r.attrib.get("xres") and not _borrow.get("res"):
					_borrow["res"] = "%s,%s" % (r.attrib["xres"], r.attrib.get("yres", "720"))
		for inc in root.findall("include"):
			fn = inc.attrib.get("filename", "")
			if fn:
				todo.append(fn if fn.startswith("/") else base + fn)
		for c in root.iter("color"):
			if c.attrib.get("name") and c.attrib.get("value") and "," not in c.attrib["value"]:
				colors.setdefault(c.attrib["name"], c.attrib["value"])
		for fo in root.iter("font"):
			if fo.attrib.get("name") and fo.attrib.get("filename"):
				fonts.setdefault(fo.attrib["name"], fo.attrib.get("scale", "100"))
		for al in root.iter("alias"):
			if al.attrib.get("name") and al.attrib.get("font"):
				aliases.setdefault(al.attrib["name"], al.attrib)
		for s in root.findall("screen"):
			n = s.attrib.get("name")
			sid = s.attrib.get("id")
			if n and (not sid or sid == "0"):
				screens.setdefault(n, s)
	return base, screens, colors, fonts, aliases


def _load_borrow():
	try:
		path = _image_default_skin()
		if not path:
			return
		base, screens, colors, fonts, aliases = _read_image_skin(path)
		_borrow.update({"dir": base, "screens": screens, "colors": colors, "fonts": fonts, "aliases": aliases})
		print("[MohammedSkin] image skin %s: %d windows ready" % (path, len(screens)))
	except Exception as e:
		print("[MohammedSkin] image skin: %s" % e)
	finally:
		_borrow["ready"] = True


def _borrow_styles():
	"""Once, on the GUI thread: the image skin's colour and font names, in this skin's colours and fonts."""
	if _borrow.get("styled"):
		return
	_borrow["styled"] = True
	try:
		import skin as S
		for name, value in _borrow.get("colors", {}).items():
			if name in S.colors:
				continue
			target = _color_target(value, name)
			if target == "white" and "white" not in S.colors:
				target = "ivory"
			if target and target in S.colors:
				S.colors[name] = S.colors[target]
			else:
				try:
					S.colors[name] = S.parseColor(value)
				except Exception:
					pass
		try:
			from enigma import addFont
		except Exception:
			addFont = None
		for name, scale in _borrow.get("fonts", {}).items():
			if addFont and name not in _OUR_FONTS and name not in ("Replacement", "Subtitlefont", "ArTitle", "ArText", "ArTextBold"):
				try:
					addFont(_our_font_file(name), name, int(scale) if str(scale).isdigit() else 100, False, 0)
				except Exception:
					pass
		for name, a in _borrow.get("aliases", {}).items():
			if name not in S.fonts:
				try:
					S.fonts[name] = (a["font"], int(a.get("size", 20)), int(a.get("height", 25)), int(a.get("width", 18)))
				except Exception:
					pass
	except Exception as e:
		print("[MohammedSkin] image skin styles: %s" % e)


_KEYPIX = re.compile(r"(?i)(?:^|[/_-])(red|green|yellow|blue)(?:[_-]?(?:button|key|small|big|hd|fhd))?\.(?:png|svg)$")
_FONT_SPEC = re.compile(r"^\s*([^;]+);\s*(\d+)\s*$")
_COLOR_ATTRS = ("foregroundColor", "backgroundColor", "foregroundColorSelected", "backgroundColorSelected", "borderColor",
	"shadowColor", "scrollbarSliderForegroundColor", "scrollbarSliderBorderColor", "scrollbarBackgroundColor",
	"scrollbarForegroundColor", "scrollbarBorderColor")
_LIST_RENDERS = ("Listbox", "ChannelSelectionHorizontal")


def _our_font(spec, title=False):
	m = _FONT_SPEC.match(spec or "")
	if not m:
		return spec
	fam, size = m.group(1).strip().lower(), m.group(2)
	if title:
		return "Title;%s" % size
	if "mono" in fam or "console" in fam or "fixed" in fam:
		return "Fixed;%s" % size
	if "bold" in fam or "semi" in fam or "medium" in fam or "title" in fam or "head" in fam or "black" in fam:
		return "Semi;%s" % size
	return "Regular;%s" % size


def _wh(e):
	try:
		w, h = [int(v) for v in e.attrib.get("size", "0,0").split(",")]
		return w, h
	except ValueError:
		return 0, 0


def _restyle(elem, panel=False):
	"""The image skin's window with its layout kept (positions, sizes, widgets, font sizes) and this skin's
	look: its background, accent line, fonts and theme colours; the image skin's own graphics are left out."""
	W, H = _wh(elem)
	if not W and elem.attrib.get("position", "").strip() == "fill":
		W, H = [int(v) for v in (_borrow.get("res") or "1920,1080").split(",")]
	if not panel:
		elem.attrib["backgroundColor"] = "transparent"
		elem.attrib["flags"] = "wfNoBorder"
	for e in list(elem):
		tag = e.tag
		w, h = _wh(e)
		if tag == "ePixmap":
			m = _KEYPIX.search(e.attrib.get("pixmap", ""))
			elem.remove(e)
			if m and w and h:  # a colour key picture becomes this skin's key dot
				try:
					x, y = [int(v) for v in e.attrib.get("position", "0,0").split(",")]
				except ValueError:
					continue
				d = 18
				dot = {"position": "%d,%d" % (x + 2, y + max(0, (h - d) // 2)), "size": "%d,%d" % (d, d),
					"backgroundColor": "key" + m.group(1).lower(), "zPosition": "1"}
				from xml.etree.ElementTree import Element
				elem.append(Element("eLabel", dot))
			continue
		if tag == "eLabel":
			big = (W and H and w >= W * 0.6 and h >= H * 0.4) or (panel and not W and w >= 600 and h >= 300)
			if big and not e.attrib.get("text"):
				elem.remove(e)  # the image skin's window background: ours comes instead
				continue
			if e.attrib.get("text"):
				e.attrib["font"] = _our_font(e.attrib.get("font", "Regular;24"))
				e.attrib["foregroundColor"] = "ivorydim"
				e.attrib["backgroundColor"] = "panel"
				e.attrib["transparent"] = "1"
			elif (h and h <= 4) or (w and w <= 4):
				e.attrib["backgroundColor"] = "line"  # thin lines
			else:  # boxes and bars: this skin's panel, or its accent where the image skin had a coloured bar
				c = e.attrib.get("backgroundColor", "")
				val = _borrow.get("colors", {}).get(c, c if c.startswith("#") else "")
				e.attrib["backgroundColor"] = "crimson" if val and _color_target(val, c) == "crimson" else "panel"
			for a in ("backgroundPixmap", "pixmap"):
				e.attrib.pop(a, None)
			continue
		if tag == "widget":
			a = e.attrib
			title = a.get("source") == "Title"
			if "font" in a:
				a["font"] = _our_font(a["font"], title)
			render = a.get("render", "")
			is_list = render in _LIST_RENDERS or a.get("name") in ("list", "config", "menu", "filelist", "entries", "menulist") or "itemHeight" in a
			for k in ("selectionPixmap", "selectionPixmapLarge", "backgroundPixmap", "scrollbarSliderPicture", "scrollbarbackgroundPicture",
					"scrollbarBackgroundPicture", "sliderPixmap", "itemCornerRadius", "itemCornerRadiusSelected", "cornerRadius"):
				a.pop(k, None)
			if render == "Progress" or render == "PositionGauge":
				a.pop("pixmap", None)
				a["foregroundColor"] = "crimson"
				a["backgroundColor"] = "line"
				continue
			if is_list:
				a["foregroundColor"] = "ivory"
				a["backgroundColor"] = "panel"
				a["foregroundColorSelected"] = "selfg"
				a["backgroundColorSelected"] = "selbg"
				a["transparent"] = "1"
			elif "font" in a or render in ("Label", "FixedLabel", "VRunningText", "RunningText") or (not render and not a.get("pixmap") and not a.get("pixmaps")):
				a["foregroundColor"] = "ivory" if title or "font" not in a or int((_FONT_SPEC.match(a["font"]) or [0, 0, "0"])[2]) >= 30 else "ivorydim"
				a["backgroundColor"] = "panel"
				a["transparent"] = "1"
				a.pop("backgroundColorSelected", None)
			for k in ("borderColor", "shadowColor"):
				a.pop(k, None)
			continue
	if not panel and W and H:
		from xml.etree.ElementTree import Element
		elem.insert(0, Element("eLabel", {"position": "0,0", "size": "%d,%d" % (W, H), "backgroundColor": "panel", "zPosition": "-1"}))
		elem.insert(1, Element("eLabel", {"position": "0,0", "size": "%d,4" % W, "backgroundColor": "crimson", "zPosition": "1"}))
	return elem


def _register_borrowed(name):
	"""Put the image skin's window (and the panels it uses) where the skin reader finds it."""
	import skin as S
	from copy import deepcopy
	src = _borrow["screens"].get(name)
	if src is None:
		return False
	_borrow_styles()
	elem = _restyle(deepcopy(src))
	# the panels it uses come from the image skin too, under their own names (other windows keep theirs)
	todo = [elem]
	while todo:
		e = todo.pop()
		for p in e.iter("panel"):
			pn = p.attrib.get("name")
			if pn and pn in _borrow["screens"] and not pn.startswith("msimg_"):
				new = "msimg_" + pn
				p.attrib["name"] = new
				if new not in S.domScreens:
					pe = _restyle(deepcopy(_borrow["screens"][pn]), panel=True)
					S.domScreens[new] = (pe, _borrow["dir"])
					todo.append(pe)
	res = _borrow.get("res")
	if res and res != "1920,1080":
		for e in [elem] + [S.domScreens[k][0] for k in list(S.domScreens) if k.startswith("msimg_")]:
			e.attrib.setdefault("resolution", res)
	S.domScreens[name] = (elem, _borrow["dir"])
	return True


def borrowed_window(names):
	if not _borrow["ready"]:
		th = _borrow.get("thread")
		if th is not None:
			th.join(10)
		if not _borrow["ready"]:
			return None
	for n in names:
		if n in _borrow["screens"]:
			return n if _register_borrowed(n) else None
	return None


def start_image_skin():
	if _borrow.get("thread") is None and not _borrow["ready"]:
		_borrow["thread"] = threading.Thread(target=_load_borrow, name="MohammedSkinImageSkin")
		_borrow["thread"].daemon = True
		_borrow["thread"].start()


_reader = []


def install_auto_windows():
	"""Hook once into the skin reader: plugin windows without a design here get one in the skin's style."""
	if _reader or not settings().get("fit_screens", True):
		return False
	try:
		import sys
		import skin as S
		orig = S.readSkin
	except Exception:
		return False

	def readSkin(screen, skin, names, desktop):
		try:
			if not isinstance(names, list):
				names = [names]
			small = desktop.size().width() < 1000
			if not small and "Summary" not in screen.__class__.__name__:
				if not _ours(names):
					own = [n for n in names if n == "Setup" and _ours([n])]
					if own:  # settings screens: this skin's settings window (with its keys)
						ensure_keys(screen, own)
						return orig(screen, skin, own + names, desktop)
					got = borrowed_window(names)  # the image's own skin has this window
					if got:
						ensure_keys(screen, [got])
						return orig(screen, skin, names, desktop)
				auto = auto_window(screen, names)
				if auto:
					return orig(screen, skin, [auto] + names, desktop)
				ensure_keys(screen, names)
		except Exception as e:
			print("[MohammedSkin] auto window: %s" % e)
		return orig(screen, skin, names, desktop)

	start_image_skin()
	S.readSkin = readSkin
	for mod in list(sys.modules.values()):
		try:
			if getattr(mod, "readSkin", None) is orig:
				mod.readSkin = readSkin
		except Exception:
			pass
	_reader.append(True)
	return True
