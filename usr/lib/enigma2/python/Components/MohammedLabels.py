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
