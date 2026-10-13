# -*- coding: utf-8 -*-
# MohammedSkin: the small words the infobars write themselves ("Now playing", "Then at", "min left", ...) in the language
# chosen in the setup ("Infobar texts language"). English stays the default. Programme titles, descriptions and genres
# are never touched: they come from the channel.

from Components import MohammedSkinUtils as U

LABEL_LANGS = (("en", "English"), ("ar", u"العربية"), ("el", u"Ελληνικά"), ("uk", u"Українська"), ("ru", u"Русский"), ("pl", "Polski"),
	("tr", u"Türkçe"), ("de", "Deutsch"), ("fr", u"Français"), ("es", u"Español"), ("it", "Italiano"),
	("pt", u"Português"), ("nl", "Nederlands"), ("fa", u"فارسی"), ("zh", u"中文"), ("ja", u"日本語"))

# English text -> {language: text}. "min" is the unit after a number, "min left" the words after a number.
LABELS = {
	"Now playing": {"ar": u"يُعرض الآن", "el": u"Τώρα", "uk": u"Зараз в ефірі", "ru": u"Сейчас в эфире", "pl": u"Teraz", "tr": u"Şimdi",
		"de": u"Jetzt läuft", "fr": u"En cours", "es": u"Ahora", "it": u"In onda", "pt": u"Agora", "nl": u"Nu bezig", "fa": u"در حال پخش", "zh": u"正在播放", "ja": u"放送中"},
	"Then at": {"ar": u"ثم الساعة", "el": u"Μετά στις", "uk": u"Далі о", "ru": u"Далее в", "pl": u"Potem o", "tr": u"Sonra",
		"de": u"Danach um", "fr": u"Ensuite à", "es": u"Luego a las", "it": u"Poi alle", "pt": u"Depois às", "nl": u"Daarna om", "fa": u"سپس ساعت", "zh": u"接下来", "ja": u"次は"},
	"Next:": {"ar": u"التالي:", "el": u"Επόμενο:", "uk": u"Далі:", "ru": u"Далее:", "pl": u"Następnie:", "tr": u"Sonraki:",
		"de": u"Danach:", "fr": u"Ensuite :", "es": u"Siguiente:", "it": u"Poi:", "pt": u"A seguir:", "nl": u"Straks:", "fa": u"بعدی:", "zh": u"下一个:", "ja": u"次:"},
	"Next at": {"ar": u"التالي الساعة", "el": u"Επόμενο στις", "uk": u"Наступне о", "ru": u"Следующее в", "pl": u"Następny o", "tr": u"Sonraki saat",
		"de": u"Nächste um", "fr": u"Suivant à", "es": u"Siguiente a las", "it": u"Prossimo alle", "pt": u"Próximo às", "nl": u"Volgende om", "fa": u"بعدی ساعت", "zh": u"下一个", "ja": u"次の番組"},
	"NEXT": {"ar": u"التالي", "el": u"ΕΠΟΜΕΝΟ", "uk": u"ДАЛІ", "ru": u"ДАЛЕЕ", "pl": u"NASTĘPNY", "tr": u"SONRAKİ",
		"de": u"DANACH", "fr": u"SUIVANT", "es": u"SIGUIENTE", "it": u"PROSSIMO", "pt": u"SEGUINTE", "nl": u"VOLGENDE", "fa": u"بعدی", "zh": u"下一个", "ja": u"次"},
	"Film": {"ar": u"فيلم", "el": u"Ταινία", "uk": u"Фільм", "ru": u"Фильм", "pl": u"Film", "tr": u"Film",
		"de": u"Film", "fr": u"Film", "es": u"Película", "it": u"Film", "pt": u"Filme", "nl": u"Film", "fa": u"فیلم", "zh": u"电影", "ja": u"映画"},
	"Series": {"ar": u"مسلسل", "el": u"Σειρά", "uk": u"Серіал", "ru": u"Сериал", "pl": u"Serial", "tr": u"Dizi",
		"de": u"Serie", "fr": u"Série", "es": u"Serie", "it": u"Serie", "pt": u"Série", "nl": u"Serie", "fa": u"سریال", "zh": u"剧集", "ja": u"シリーズ"},
	"min": {"ar": u"دقيقة", "el": u"λεπτά", "uk": u"хв", "ru": u"мин", "pl": u"min", "tr": u"dk",
		"de": u"Min.", "fr": u"min", "es": u"min", "it": u"min", "pt": u"min", "nl": u"min", "fa": u"دقیقه", "zh": u"分钟", "ja": u"分"},
	"min left": {"ar": u"دقيقة متبقية", "el": u"λεπτά ακόμη", "uk": u"хв залишилось", "ru": u"мин осталось", "pl": u"min do końca", "tr": u"dk kaldı",
		"de": u"Min. übrig", "fr": u"min restantes", "es": u"min restantes", "it": u"min rimanenti", "pt": u"min restantes", "nl": u"min resterend", "fa": u"دقیقه مانده", "zh": u"分钟剩余", "ja": u"分残り"},
}


# fixed texts of some screens (written into skin.xml when the skin is tuned)
LABELS.update({
	"Playing": {"ar": u"قيد التشغيل", "el": u"Αναπαραγωγή", "uk": u"Відтворення", "ru": u"Воспроизведение", "pl": u"Odtwarzanie", "tr": u"Oynatılıyor",
		"de": u"Wiedergabe", "fr": u"Lecture", "es": u"Reproduciendo", "it": u"In riproduzione", "pt": u"A reproduzir", "nl": u"Afspelen", "fa": u"در حال پخش", "zh": u"播放中", "ja": u"再生中"},
	"Volume": {"ar": u"الصوت", "el": u"Ένταση", "uk": u"Гучність", "ru": u"Громкость", "pl": u"Głośność", "tr": u"Ses",
		"de": u"Lautstärke", "fr": u"Volume", "es": u"Volumen", "it": u"Volume", "pt": u"Volume", "nl": u"Volume", "fa": u"صدا", "zh": u"音量", "ja": u"音量"},
	"NOW": {"ar": u"الآن", "el": u"ΤΩΡΑ", "uk": u"ЗАРАЗ", "ru": u"СЕЙЧАС", "pl": u"TERAZ", "tr": u"ŞİMDİ",
		"de": u"JETZT", "fr": u"MAINT.", "es": u"AHORA", "it": u"ORA", "pt": u"AGORA", "nl": u"NU", "fa": u"اکنون", "zh": u"现在", "ja": u"今"},
	"Live Channels": {"ar": u"القنوات المباشرة", "el": u"Ζωντανά κανάλια", "uk": u"Прямі канали", "ru": u"Прямой эфир", "pl": u"Kanały na żywo", "tr": u"Canlı kanallar",
		"de": u"Live-Sender", "fr": u"Chaînes en direct", "es": u"Canales en vivo", "it": u"Canali in diretta", "pt": u"Canais em direto", "nl": u"Live zenders", "fa": u"کانال‌های زنده", "zh": u"直播频道", "ja": u"ライブチャンネル"},
	"Program Info": {"ar": u"معلومات", "el": u"Πληροφ.", "uk": u"Інфо", "ru": u"Инфо", "pl": u"Info", "tr": u"Bilgi",
		"de": u"Info", "fr": u"Infos", "es": u"Info", "it": u"Info", "pt": u"Info", "nl": u"Info", "fa": u"اطلاعات", "zh": u"信息", "ja": u"情報"},
	"Options": {"ar": u"خيارات", "el": u"Επιλογές", "uk": u"Опції", "ru": u"Опции", "pl": u"Opcje", "tr": u"Seçenekler",
		"de": u"Optionen", "fr": u"Options", "es": u"Opciones", "it": u"Opzioni", "pt": u"Opções", "nl": u"Opties", "fa": u"گزینه‌ها", "zh": u"选项", "ja": u"オプション"},
	"Back": {"ar": u"رجوع", "el": u"Πίσω", "uk": u"Назад", "ru": u"Назад", "pl": u"Wstecz", "tr": u"Geri",
		"de": u"Zurück", "fr": u"Retour", "es": u"Atrás", "it": u"Indietro", "pt": u"Voltar", "nl": u"Terug", "fa": u"بازگشت", "zh": u"返回", "ja": u"戻る"},
})
STATIC = ("Playing", "Volume", "NOW", "Live Channels", "Program Info", "Options", "Back")


def lang():
	v = U.settings().get("label_lang", "en")
	return v if v in [l[0] for l in LABEL_LANGS] else "en"


def label(text):
	"""The infobar word in the chosen language; text that is not one of the words comes back unchanged."""
	lg = lang()
	if lg == "en":
		return text
	return LABELS.get(text, {}).get(lg, text)


def minutes(n):
	return u"%d %s" % (n, label("min"))


def minutes_left(n):
	return u"%d %s" % (n, label("min left"))


def translate_static(xml):
	"""The fixed words of the screens (skin.xml and style snippets) in the chosen language. Every earlier spelling of a word is
	found again, so a language change always starts from the right word."""
	import re
	lg = lang()
	back = {}
	for en in STATIC:
		for text in [en] + list(LABELS[en].values()):
			back[text] = en
	def one(m):
		en = back.get(m.group(2))
		if not en:
			return m.group(0)
		return m.group(1) + (en if lg == "en" else LABELS[en].get(lg, en)) + m.group(3)
	return re.sub(r'(<eLabel text=")([^"]*)(")', one, xml)


# --- room for the words of every language -----------------------------------------------------------------------------------
# The boxes of the infobars are drawn for the English words. A longer word of another language ("Sonraki saat" for "Next at")
# would be cut or run into the time next to it, so the box gets the width the word needs and what stands right of it on the
# same row moves over by the same amount.

_FONT_FILES = {"Regular": "moh-regular.otf", "Semi": "moh-semibold.otf", "Title": "moh-title.otf"}
_font_cache = {}


def _script(text):
	for ch in text:
		o = ord(ch)
		if 0x0600 <= o <= 0x08FF:
			return "arabic"
		if o >= 0x2E80:
			return "cjk"
	return "latin"


def text_width(text, font, size):
	"""Width in pixels of the text in a skin font: measured with the font file when PIL is on the box, else estimated (generously)."""
	sc = _script(text)
	if sc == "cjk":
		return int(len(text) * size * 1.05)
	if sc == "arabic":
		return int(len(text) * size * 0.58)
	fn = _FONT_FILES.get(font, "moh-regular.otf")
	try:
		from PIL import ImageFont
		key = (fn, size)
		f = _font_cache.get(key)
		if f is None:
			f = _font_cache[key] = ImageFont.truetype(U.SKIN_DIR + "/fonts/" + fn, size)
		return int(f.getlength(text)) + 2
	except Exception:
		up = sum(1 for c in text if c.isupper())
		return int(((len(text) - up) * 0.56 + up * 0.7) * size) + 2


def _sample(conv):
	"""The longest text a converter of the skin can write in the chosen language (None when it is not a word of ours)."""
	import re
	m = re.match(r"(?:Text|NextText|NoEventText):(.+)$", conv)
	if m:
		return label(m.group(1))
	if conv == "Kind":
		return max([label("Film"), label("Series")], key=len)
	if conv == "Remaining":
		return u"199 " + label("min left")
	if conv == "Duration":
		return u"199 " + label("min")
	return None


def fit_labels(xml):
	"""Widen the boxes of the infobar words for the chosen language. What follows on the same row (the time after "Next at") moves
	over by the same amount; nothing is ever pushed into another box, the word is cut short instead."""
	import re
	if lang() == "en":
		return xml
	elem = re.compile(r'<(widget|eLabel|ePixmap)\b([^>]*?)position="(-?\d+),(-?\d+)"(\s+size=")(\d+),(\d+)(")([^>]*?)(/?)>', re.S)
	items = []
	for m in elem.finditer(xml):
		x, y, w, h = int(m.group(3)), int(m.group(4)), int(m.group(6)), int(m.group(7))
		items.append(dict(m=m, tag=m.group(1), x=x, y=y, w=w, h=h, nx=x, nw=w, label='render="Label"' in m.group(0)))

	def same_row(a, b):
		return a["y"] < b["y"] + b["h"] and a["y"] + a["h"] > b["y"]

	def obstacle(it, start, skip):
		"""x of the nearest box right of `start` on the row (backgrounds of the whole bar do not count)."""
		best = 1900
		for o in items:
			if o is it or id(o) in skip or o["w"] >= 900 or o["x"] < start - 2 or not same_row(it, o) or o["x"] >= 1900:
				continue
			best = min(best, o["x"])
		return best

	for it in items:
		m = it["m"]
		if it["tag"] != "widget" or not it["label"] or m.group(10) == "/":
			continue
		if "halign" in m.group(0) and 'halign="left"' not in m.group(0):
			continue
		end = xml.find("</widget>", m.end())
		body = xml[m.end():end] if end > 0 else ""
		cv = re.search(r'<convert type="MohammedInfo">([^<]+)</convert>', body)
		fo = re.search(r'font="(\w+);(\d+)"', m.group(0))
		if not cv or not fo:
			continue
		conv = cv.group(1).strip()
		txt = _sample(conv)
		if not txt:
			continue
		want = text_width(txt, fo.group(1), int(fo.group(2))) + 6 - it["nw"]
		if want <= 2:
			continue
		old_end = it["x"] + it["w"]
		chain, front = [], old_end
		if re.match(r"(?:Text|NextText|NoEventText):", conv):  # the value that follows the word moves with it
			moved = True
			while moved:
				moved = False
				for o in items:
					if o is it or o in chain or not o["label"] or o["w"] >= 900 or not same_row(it, o) or not (0 <= o["x"] - front <= 48):
						continue
					chain.append(o)
					front = o["x"] + o["w"]
					moved = True
		room = obstacle(it, front, set(id(c) for c in chain)) - front - 4
		delta = min(want, max(0, room), 200)
		if delta <= 2:
			continue
		it["nw"] += delta
		for c in chain:
			c["nx"] = c["x"] + delta
	out, last = [], 0
	for it in items:
		if it["nx"] == it["x"] and it["nw"] == it["w"]:
			continue
		m = it["m"]
		s = m.group(0)
		s = s.replace('position="%d,%d"' % (it["x"], it["y"]), 'position="%d,%d"' % (it["nx"], it["y"]), 1)
		s = s.replace('size="%d,%d"' % (it["w"], it["h"]), 'size="%d,%d"' % (it["nw"], it["h"]), 1)
		out.append(xml[last:m.start()])
		out.append(s)
		last = m.end()
	out.append(xml[last:])
	return "".join(out)
