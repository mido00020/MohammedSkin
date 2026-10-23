# -*- coding: utf-8 -*-
# MohammedSkin Setup: colour theme (with preview), second infobar and poster layouts, rating stars,
# Arabic translation, optional API keys and poster options.
# Posters need the user's own key.
# Works on OpenViX, OpenBlackHole, OpenATV, PurE2 and EGAMI: the skin adapts itself to the image.

from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.Label import Label
from Components.MultiContent import MultiContentEntryText
from Components.config import ConfigText, ConfigYesNo, ConfigSelection, getConfigListEntry
from Components.Pixmap import Pixmap
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Screens.Standby import TryQuitMainloop
from Tools.LoadPixmap import LoadPixmap
from enigma import ePicLoad, eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_CENTER, RT_WRAP
from .lang import tr, UI_LANGS, RTL

from Components import MohammedSkinUtils as U

LANGUAGES = [("en-US", "English"), ("ar-SA", "العربية"), ("zh-CN", "简体中文"), ("uk-UA", "Українська"), ("ru-RU", "Русский"),
	("de-DE", "Deutsch"), ("fr-FR", "Français"), ("tr-TR", "Türkçe"), ("es-ES", "Español"), ("it-IT", "Italiano"),
	("pt-PT", "Português"), ("nl-NL", "Nederlands"), ("pl-PL", "Polski"), ("fa-IR", "فارسی"), ("ja-JP", "日本語")]


IMG = "/usr/share/enigma2/MohammedSkin/img/"
try:
	from Components.config import KEY_LEFT, KEY_RIGHT
except ImportError:
	try:
		from Components.config import ACTIONKEY_LEFT as KEY_LEFT, ACTIONKEY_RIGHT as KEY_RIGHT
	except ImportError:
		KEY_LEFT, KEY_RIGHT = 0, 1


def ui_lang():
	v = U.settings().get("ui_lang")
	return v if v in [l[0] for l in UI_LANGS] else "en"


def _skin_active():
	try:
		from Components.config import config
		return config.skin.primary_skin.value.startswith("MohammedSkin/")
	except Exception:
		return False


def _hex(c, alpha="00"):
	return "#" + alpha + c.lstrip("#").upper()


def build_skin(lang):
	"""Full-screen setup in the look of the skin: theme colours, glowing line, running dots; mirrored for Arabic."""
	t = U.load_themes().get(U.settings().get("theme", "red")) or U.load_themes().get("red") or {}
	ink, acc, acc2, line = _hex(t.get("ink", "#060304")), _hex(t.get("accent", "#C8102E")), _hex(t.get("accent2", "#FF5A4E")), _hex(t.get("line", "#2A2627"))
	own = _skin_active()
	ft = "Title" if own else "Regular"
	fs = "Semi" if own else "Regular"
	W = 1920
	rtl = lang in RTL
	side = "ar" if rtl else "en"  # pictures drawn for right-to-left or left-to-right

	def X(x, w):
		return W - x - w if rtl else x
	h = "right" if rtl else "left"
	hr = "left" if rtl else "right"
	e = []
	a = e.append
	a('<screen name="MohammedSkinSetup" position="0,0" size="1920,1080" title="MohammedSkin Setup" backgroundColor="%s" flags="wfNoBorder">' % ink)
	a('<ePixmap pixmap="%ssetup_glow_%s.png" position="%d,0" size="1100,700" alphatest="blend" zPosition="0" />' % (IMG, side, X(0, 1100)))
	# header: MohammedSkin always in English
	a('<eLabel text="MohammedSkin" position="%d,26" size="470,74" font="%s;56" halign="%s" valign="center" foregroundColor="#00F2ECE2" backgroundColor="%s" transparent="1" zPosition="2" />' % (X(64, 470), ft, h, ink))
	a('<widget source="subtitle" render="Label" position="%d,40" size="250,50" font="Regular;32" halign="%s" valign="center" foregroundColor="#00968C84" backgroundColor="%s" transparent="1" zPosition="2" />' % (X(550, 250), h, ink))
	a('<ePixmap pixmap="%ssetup_chip.png" position="%d,46" size="112,38" alphatest="blend" zPosition="2" />' % (IMG, X(810, 112)))
	a('<eLabel text="%s" position="%d,46" size="112,38" font="%s;20" halign="center" valign="center" foregroundColor="%s" backgroundColor="%s" transparent="1" zPosition="3" />' % (U.SKIN_VERSION, X(810, 112), fs, acc2, ink))
	# image name with running dots (identity of the skin)
	a('<widget source="global.CurrentTime" render="MohammedFrames" mode="cycle" frames="%sdots_%%02d.png" count="12" interval="90" position="%d,44" size="360,30" alphatest="blend" zPosition="2" />' % (IMG, X(1300, 360)))
	a('<widget source="imagename" render="Label" position="%d,36" size="460,48" font="%s;32" halign="center" valign="center" foregroundColor="%s" backgroundColor="%s" transparent="1" zPosition="3" />' % (X(1250, 460), ft, acc2, ink))
	a('<widget source="global.CurrentTime" render="Label" position="%d,36" size="130,48" font="%s;36" halign="%s" valign="center" foregroundColor="#0033C8FF" backgroundColor="%s" transparent="1" zPosition="3"><convert type="ClockToText">Format:%%H:%%M</convert></widget>' % (X(1726, 130), ft, hr, ink))
	a('<ePixmap pixmap="%ssetup_line.png" position="64,106" size="1792,30" alphatest="blend" zPosition="2" />' % IMG)
	# categories
	a('<widget name="catsel" pixmap="%ssetup_catsel_%s.png" position="%d,160" size="360,62" alphatest="blend" zPosition="2" />' % (IMG, side, X(64, 360)))
	for i in range(len(CATS)):
		a('<widget source="cat%d" render="Label" position="%d,%d" size="300,62" font="Regular;30" halign="%s" valign="center" foregroundColor="#00C8C2BA" backgroundColor="%s" transparent="1" zPosition="3" />' % (i, X(96, 300), 160 + i * 78, h, ink))
		if i < len(CATS) - 1:
			a('<eLabel position="%d,%d" size="320,1" backgroundColor="%s" zPosition="1" />' % (X(84, 320), 160 + i * 78 + 70, line))
	a('<eLabel position="%d,160" size="2,700" backgroundColor="%s" zPosition="1" />' % (X(460, 2), line))
	# settings of the open category
	a('<widget name="config" position="%d,160" size="700,656" itemHeight="82" selectionPixmap="%ssetup_rowsel.png" scrollbarMode="showNever" backgroundColor="%s" foregroundColor="#00F2ECE2" foregroundColorSelected="#00FFFFFF" transparent="1" zPosition="3" />' % (X(500, 700), IMG, ink))
	# preview
	a('<ePixmap pixmap="%ssetup_frame.png" position="%d,150" size="636,368" alphatest="blend" zPosition="2" />' % (IMG, X(1230, 636)))
	a('<widget name="preview" position="%d,160" size="616,347" zPosition="3" />' % X(1240, 616))
	a('<widget source="themename" render="Label" position="%d,526" size="616,44" font="%s;30" halign="%s" valign="center" foregroundColor="#00F2ECE2" backgroundColor="%s" transparent="1" zPosition="3" />' % (X(1240, 616), fs, h, ink))
	a('<widget source="themehint" render="Label" position="%d,570" size="616,62" font="Regular;22" halign="%s" valign="top" foregroundColor="#00B4AAA0" backgroundColor="%s" transparent="1" zPosition="3" />' % (X(1240, 616), h, ink))
	a('<ePixmap pixmap="%ssetup_card_%s.png" position="%d,636" size="616,226" alphatest="blend" zPosition="2" />' % (IMG, side, X(1240, 616)))
	a('<widget source="help" render="Label" position="%d,652" size="560,196" font="Regular;25" halign="%s" valign="top" foregroundColor="#00D2CCC4" backgroundColor="%s" transparent="1" zPosition="3" />' % (X(1268, 560), h, ink))
	# keys
	a('<eLabel position="64,900" size="1792,2" backgroundColor="%s" zPosition="1" />' % line)
	x = 64
	for key, col in (("key_red", "#00D3202F"), ("key_green", "#002FA84F"), ("key_yellow", "#00E0B321"), ("key_blue", "#001460F0")):
		a('<eLabel position="%d,936" size="34,16" backgroundColor="%s" zPosition="2" />' % (X(x, 34), col))
		a('<widget source="%s" render="Label" position="%d,920" size="300,48" font="Regular;27" halign="%s" valign="center" foregroundColor="#00F2ECE2" backgroundColor="%s" transparent="1" zPosition="3" />' % (key, X(x + 48, 300), h, ink))
		x += 360
	a('<widget source="langname" render="Label" position="%d,920" size="360,48" font="Regular;24" halign="%s" valign="center" foregroundColor="#00968C84" backgroundColor="%s" transparent="1" zPosition="3" />' % (X(1496, 360), hr, ink))
	a('<eLabel text="Posters, scenes and ratings: TMDB. This product uses the TMDB API but is not endorsed or certified by TMDB." position="64,1012" size="1792,30" font="Regular;18" halign="center" valign="center" foregroundColor="#006E6A65" backgroundColor="%s" transparent="1" zPosition="2" />' % ink)
	a('<widget name="HelpWindow" conditional="HelpWindow" position="0,1100" size="4,4" pixmap="%sblank.png" alphatest="on" zPosition="-1" />' % IMG)
	a('<widget name="footnote" conditional="footnote" position="0,1100" size="20,20" font="Regular;10" transparent="1" zPosition="-1" />')
	a('</screen>')
	return "\n".join(e)


CATS = ["Look", "Infobars", "Channel list", "Clock", "Weather", "Posters", "Translation", "Keys", "General"]


def _wide(text, size):
	"""Rough width in pixels of a text at this font size (Chinese / Japanese letters are about square)."""
	try:
		return sum(1.0 if ord(c) >= 0x2E80 else 0.53 for c in text) * size
	except Exception:
		return 0


class MohammedNotice(Screen):
	"""A full-screen message (notice or pledge). OK / green agrees, EXIT / red declines when it asks."""

	def __init__(self, session, title, text, hint, asks=False):
		Screen.__init__(self, session)
		self.skin = """<screen name="MohammedNotice" position="0,0" size="1920,1080" flags="wfNoBorder" backgroundColor="#00050507">
			<eLabel position="0,0" size="1920,1080" backgroundColor="#00050507" zPosition="-1" />
			<eLabel position="200,120" size="1520,880" backgroundColor="#00131319" zPosition="-1" />
			<eLabel position="260,150" size="1400,6" backgroundColor="#C8102E" />
			<widget name="title" position="260,180" size="1400,90" font="Regular;56" halign="center" valign="center" foregroundColor="#FFFFFF" backgroundColor="#00050507" transparent="1" />
			<widget name="text" position="260,300" size="1400,590" font="Regular;38" halign="center" valign="center" foregroundColor="#E8E8E8" backgroundColor="#00050507" transparent="1" />
			<eLabel position="260,925" size="1400,2" backgroundColor="#555555" />
			<widget name="hint" position="260,950" size="1400,60" font="Regular;34" halign="center" valign="center" foregroundColor="#FFD060" backgroundColor="#00050507" transparent="1" />
		</screen>"""
		self.asks = asks
		self["title"] = Label(title)
		self["text"] = Label(text)
		self["hint"] = Label(hint)
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
			{"ok": self.agree, "green": self.agree, "cancel": self.decline, "red": self.decline}, -1)

	def agree(self):
		self.close(True)

	def decline(self):
		self.close(not self.asks)


class SettingList(MenuList):
	"""The settings of one category: name on one side, value on the other, arrows on the line in use."""

	def __init__(self, lang):
		MenuList.__init__(self, [], content=eListboxPythonMultiContent)
		self.lang = lang
		self.l.setFont(0, gFont("Regular", 29))
		self.l.setFont(1, gFont("Regular", 28))
		self.l.setFont(2, gFont("Regular", 24))  # long names in other languages: smaller, on two lines
		self.l.setItemHeight(82)
		self.items = []
		self.focus = False
		self.valueText = lambda cfg: ""
		self.acc2 = 0xFF5A4E

	def build(self, items, valueText, keep=None):
		self.items = items
		self.valueText = valueText
		cur = self.getSelectionIndex() if keep is None else keep
		self.redraw(cur)

	def redraw(self, cur=None):
		if cur is None:
			cur = self.getSelectionIndex()
		rows = []
		ar = self.lang in RTL
		for i, (label, cfg) in enumerate(self.items):
			val = self.valueText(cfg)
			sel = i == cur and self.focus
			if sel and not isinstance(cfg, ConfigText):
				val = (u"‹  %s  ›" % val)
			lflag = (RT_HALIGN_RIGHT if ar else RT_HALIGN_LEFT) | RT_VALIGN_CENTER
			vflag = (RT_HALIGN_LEFT if ar else RT_HALIGN_RIGHT) | RT_VALIGN_CENTER
			lpos, vpos = ((330, 0), (26, 0)) if ar else ((28, 0), (300, 0))
			lf = 2 if _wide(label, 29) > 336 else 0
			vf = 2 if _wide(val, 28) > 366 else 1
			rows.append([(label, cfg),
				MultiContentEntryText(pos=lpos, size=(344, 82), font=lf, flags=lflag | (RT_WRAP if lf == 2 else 0), text=label, color=0xF2ECE2 if sel else 0xD7D1C9, color_sel=0xFFFFFF),
				MultiContentEntryText(pos=vpos, size=(374, 82), font=vf, flags=vflag | (RT_WRAP if vf == 2 else 0), text=val, color=self.acc2 if sel else 0x968C84, color_sel=self.acc2)])
		self.setList(rows)
		if 0 <= cur < len(rows):
			self.moveToIndex(cur)

	def getCurrent(self):
		c = self.l.getCurrentSelection()
		return c and c[0]

	def invalidateCurrent(self):
		self.redraw()


class MohammedSkinSetup(Screen):
	def __init__(self, session):
		self.lang = ui_lang()
		self.skin = build_skin(self.lang)
		Screen.__init__(self, session)
		self.skinName = "MohammedSkinSetup"
		L = self.lang
		t = lambda s: tr(L, s)
		self.t = t
		self.m = lambda ar, en: ar if L == "ar" else t(en)  # one language per message (mixed Arabic / English lines were shown out of order)
		name = U.image_name()
		self.setTitle("MohammedSkin Setup  -  %s" % name if name else "MohammedSkin Setup")
		self["subtitle"] = StaticText(t("Setup"))
		self["imagename"] = StaticText(name or "Enigma2")
		self["langname"] = StaticText(t("Language: English"))
		s = U.settings()
		self.themes = U.load_themes()
		names = [n for n in ("red", "blue", "turquoise", "sky", "gold", "black", "white", "purple", "emerald", "orange", "rose") if n in self.themes] or ["red"]
		self.startTheme = s.get("theme", "red") if s.get("theme", "red") in names else "red"
		self.theme = ConfigSelection(choices=[(n, t(self.themes.get(n, {}).get("label", n))) for n in names], default=self.startTheme)
		self.clocks = U.load_clocks()
		cnames = [n for n in U.CLOCK_ORDER if n in self.clocks] or ["royal"]
		self.startClock = s.get("clock", "royal") if s.get("clock", "royal") in cnames else cnames[0]
		self.clock = ConfigSelection(choices=[(n, t(self.clocks.get(n, {}).get("label", n))) for n in cnames], default=self.startClock)

		def styles(kind):
			lst = [(n, t(l)) for n, l in U.load_styles(kind)]
			start = U.current_style(kind)
			return lst, start, ConfigSelection(choices=lst, default=start if start in [n for n, l in lst] else lst[0][0])
		self.menuStyles, self.startMenu, self.menuStyle = styles("menu")
		self.chStyles, self.startChannels, self.chStyle = styles("channels")
		self.ibxStyles, self.startIbx, self.ibxStyle = styles("infobar")
		self.sibStyles, self.startSib, self.sibStyle = styles("sib")
		self.ibStyles, self.startIb, self.ibStyle = styles("ibposter")
		self.rating = ConfigYesNo(default=bool(s.get("rating", True)))
		self.smooth = ConfigSelection(choices=[("smooth", t("Smooth sweep")), ("tick", t("One step per second"))], default="smooth" if s.get("clock_smooth", True) else "tick")
		self.translate = ConfigYesNo(default=bool(s.get("translate", True)))
		self.trLang = ConfigSelection(choices=list(U.TR_LANGS), default=U.tr_target())
		self.trService = ConfigSelection(choices=[("auto", t("Automatic (Google, then Microsoft) - no key")),
			("microsoft", t("My Microsoft Translator key")), ("deepl", t("My DeepL key"))],
			default=s.get("tr_service", "auto") if s.get("tr_service", "auto") in ("auto", "microsoft", "deepl") else "auto")
		self.trKey = ConfigText(default=s.get("tr_key", ""), fixed_size=False)
		self.trRegion = ConfigText(default=s.get("tr_region", ""), fixed_size=False)
		self.tmdb = ConfigText(default=s.get("tmdb", ""), fixed_size=False)
		self.omdb = ConfigText(default=s.get("omdb", ""), fixed_size=False)
		self.fanart = ConfigText(default=s.get("fanart", ""), fixed_size=False)
		langs = [l[0] for l in LANGUAGES]
		self.language = ConfigSelection(choices=LANGUAGES, default=s.get("language") if s.get("language") in langs else "en-US")
		self.posters = ConfigYesNo(default=bool(s.get("posters", True)))
		self.startTune = (U.tune_value("ch_font", U.CH_FONT), U.tune_value("ch_rows", U.CH_ROWS),
			U.tune_value("pl_font", U.PL_FONT), U.tune_value("ib_alpha", U.IB_ALPHA))
		self.chFont = ConfigSelection(choices=[(n, t(l)) for n, l, f in U.CH_FONT], default=self.startTune[0])
		self.chRows = ConfigSelection(choices=[(n, t(l)) for n, l, f in U.CH_ROWS], default=self.startTune[1])
		self.plFont = ConfigSelection(choices=[(n, t(l)) for n, l, f in U.PL_FONT], default=self.startTune[2])
		self.ibAlpha = ConfigSelection(choices=[(n, t(l)) for n, l, f in U.IB_ALPHA], default=self.startTune[3])
		self.ibChan = ConfigSelection(choices=[(n, t(l)) for n, l, f in U.IB_CHAN], default=U.tune_value("ib_chan", U.IB_CHAN))
		self.chPreview = ConfigSelection(choices=[(n, t(l)) for n, l in U.CH_PREVIEW], default=U.ch_preview())
		self.eventColor = ConfigSelection(choices=[(n, t(l)) for n, l, c in U.EVENT_COLORS], default=U.event_color())
		self.arText = ConfigSelection(choices=[(n, l) for n, l, a, b in U.AR_TEXT_FONTS], default=U.font_value("ar_text_font", U.AR_TEXT_FONTS, "tajawal"))
		self.arTitle = ConfigSelection(choices=[(n, l) for n, l, a in U.AR_TITLE_FONTS], default=U.font_value("ar_title_font", U.AR_TITLE_FONTS, "lalezar"))
		self.startFonts = (self.arText.value, self.arTitle.value)
		self.weather = ConfigYesNo(default=bool(s.get("weather", True)))
		self.weatherCity = ConfigText(default=s.get("weather_city", ""), fixed_size=False)
		self.pick = {"lat": s.get("weather_lat"), "lon": s.get("weather_lon"), "en": s.get("weather_place_en", ""), "ar": s.get("weather_place_ar", "")}
		mode = s.get("weather_mode") or ("city" if s.get("weather_city") else "auto")
		self.weatherLoc = ConfigSelection(choices=self.locChoices(), default=mode if mode in ("auto", "list", "city") else "auto")
		self.weatherUnits = ConfigSelection(choices=[("c", t("Celsius (°C)")), ("f", t("Fahrenheit (°F)"))], default="f" if s.get("weather_units") == "f" else "c")
		self.weatherLang = ConfigSelection(choices=list(U.WEATHER_LANGS), default=s.get("weather_lang") if s.get("weather_lang") in [l[0] for l in U.WEATHER_LANGS] else "ar")
		self.meterBack = ConfigYesNo(default=bool(s.get("ib_meter_back", True)))
		self.weatherForecast = ConfigYesNo(default=bool(s.get("weather_forecast", True)))
		from Components import MohammedLabels as ML
		self.labelLang = ConfigSelection(choices=list(ML.LABEL_LANGS), default=s.get("label_lang") if s.get("label_lang") in [l[0] for l in ML.LABEL_LANGS] else "en")
		self.arPosters = ConfigSelection(choices=[("auto", t("Arabic channels (Nilesat, Arabsat, Badr)")), ("always", t("Always when there is one")), ("off", t("Off"))],
			default=s.get("arabic_posters", "auto") if s.get("arabic_posters", "auto") in ("auto", "always", "off") else "auto")
		self.logo3d = ConfigYesNo(default=bool(s.get("logo3d", True)))
		self.logoStyle = ConfigSelection(choices=[(n, t(l)) for n, l in U.LOGO_STYLES], default=U.logo_style())
		self.posterStore = ConfigSelection(choices=[("ram", t("In memory (fetched again after a restart)")), ("disk", t("Kept on the hard disk / USB"))],
			default="disk" if s.get("poster_store") == "disk" else "ram")
		self.weatherPos = ConfigSelection(choices=[(n, t(l)) for n, l, x, y in U.WEATHER_POS],
			default=s.get("weather_pos", "top_right") if s.get("weather_pos", "top_right") in [p[0] for p in U.WEATHER_POS] else "top_right")
		self.plLayout = ConfigSelection(choices=[("grid", t("Grid (tiles side by side)")), ("list", t("List"))], default="list" if s.get("pl_layout") == "list" else "grid")
		self.startPlace = (self.weatherPos.value, self.plLayout.value, self.ibChan.value, self.chPreview.value, self.eventColor.value)
		self.adult = ConfigSelection(choices=[("off", t("Off")), ("normal", t("On (adult and erotic titles)")),
			("strict", t("Strict (also nudity, R and TV-MA)"))], default=U.adult_level())
		self.backdrops = ConfigYesNo(default=bool(s.get("backdrops", True)))
		self.fitScreens = ConfigYesNo(default=bool(s.get("fit_screens", True)))
		self.ibBackdrop = ConfigSelection(choices=[(n, t(l)) for n, l in U.IB_BACKDROP], default=U.ib_backdrop())
		self.ibLed = ConfigYesNo(default=bool(s.get("ib_led", True)))
		self.menuAnim = ConfigYesNo(default=bool(s.get("menu_anim", True)))
		self.osdFit = ConfigYesNo(default=U.osd_is_full())
		self.ibMeterColor = ConfigSelection(choices=[(n, t(l)) for n, l in U.IB_METER_COLOR], default=U._choice("ib_meter_color", U.IB_METER_COLOR, "classic"))
		self.ibMeterShape = ConfigSelection(choices=[(n, t(l)) for n, l in U.IB_METER_SHAPE], default=U._choice("ib_meter_shape", U.IB_METER_SHAPE, "line"))
		self.menuBg = ConfigSelection(choices=[(n, t(l)) for n, l in U.MENU_BG], default=U._choice("menu_bg", U.MENU_BG, U.MENU_BG_DEFAULT))
		self.epgEnglish = ConfigYesNo(default=bool(s.get("epg_english", True)))
		self.dateFormat = ConfigSelection(choices=[(n, t(l) if n == "skin" else U.date_example(n)) for n, l in U.DATE_FORMAT], default=U._choice("date_format", U.DATE_FORMAT, "skin"))
		self.startBackdrop = (self.ibBackdrop.value, self.ibLed.value, self.ibMeterColor.value, self.ibMeterShape.value, self.menuBg.value, self.menuAnim.value, self.dateFormat.value, self.labelLang.value, self.weatherForecast.value, self.meterBack.value)
		self.uiLang = ConfigSelection(choices=list(UI_LANGS), default=L)
		self.helptext = {
			id(self.theme): "Use LEFT / RIGHT to see each colour theme. Saving a new theme restarts the GUI.",
			id(self.clock): "Use LEFT / RIGHT to see each infobar clock. Saving a new clock restarts the GUI.",
			id(self.menuStyle): "Use LEFT / RIGHT to see each main menu style. Saving a new style restarts the GUI.",
			id(self.chStyle): "Use LEFT / RIGHT to see each channel list style. Saving a new style restarts the GUI.",
			id(self.ibxStyle): "First infobar: classic, or one of the 3D poster and framed poster designs. Saving a new style restarts the GUI.",
			id(self.sibStyle): "Second infobar: classic, or a full-screen backdrop with four or two scenes from the event. Saving a new style restarts the GUI.",
			id(self.ibStyle): "Poster of the classic infobar: in the bar on the left, or above the bar and larger. Saving restarts the GUI.",
			id(self.rating): "Show rating stars, the rating, year and genre of films and series (looked up online with the posters).",
			id(self.smooth): "Smooth sweep moves the seconds hand continuously. Choose one step per second if the box feels slow.",
			id(self.trLang): "Language the event titles and descriptions are translated to. Turn translation off above to keep the original language.",
			id(self.trService): "Automatic needs no key. With your own free key (Microsoft Translator or DeepL) translations come from that service first.",
			id(self.trKey): "Your own translation key (optional). Press OK to type. Only used when the service above is Microsoft or DeepL.",
			id(self.trRegion): "Region of a Microsoft key, e.g. westeurope or uaenorth (leave empty for a global key). Press OK to type.",
			id(self.translate): "Yes: translate event titles and descriptions to the language below. No: show everything in its original language.",
			id(self.tmdb): "Your own free key from themoviedb.org. Needed for posters: the skin has no built-in key. Press OK to type.",
			id(self.omdb): "Optional. Free key from omdbapi.com. Extra poster source. Press OK to type.",
			id(self.fanart): "Optional. Free key from fanart.tv. Extra film backdrops (needs a TMDB key too). Press OK to type.",
			id(self.language): "Language used for TMDB searches.",
			id(self.posters): "Show posters in the infobars and channel list.",
			id(self.backdrops): "Show backdrops behind the event.",
			id(self.chFont): "Size of the channel names, numbers and event text in the channel list. Saving restarts the GUI.",
			id(self.chRows): "Height of each channel row: compact shows more channels, large and extra large show fewer and bigger. Saving restarts the GUI.",
			id(self.plFont): "Size of the text and rows in the plugin list (Menu > Plugins). Saving restarts the GUI.",
			id(self.ibAlpha): "Background of the first infobar: from very transparent (see the picture through it) to very dark. Saving restarts the GUI.",
			id(self.adult): "Hides posters, backdrops and scenes of adult and erotic films, series and channels; the 3D channel logo is shown instead.",
			id(self.arText): "Font for Arabic text everywhere (channel names, menus, descriptions). Saving restarts the GUI.",
			id(self.arTitle): "Font for the big Arabic titles in the infobars and channel list. Saving restarts the GUI.",
			id(self.weather): "Weather at the top right of the infobar and in the second infobar (free, no key needed).",
			id(self.weatherLoc): "Press OK to choose the country, then the city. Automatic finds it from your internet connection (can be wrong: the provider's city).",
			id(self.weatherCity): "Only used when the location is 'typed city': your city in any language. Press OK to type.",
			id(self.weatherUnits): "Temperature in Celsius or Fahrenheit.",
			id(self.weatherLang): "Language of the weather condition and city name.",
			id(self.meterBack): "A solid dark plate behind the SNR and AGC bars so they stay clean on every picture. On some images the soft edges of the bars let the video show through and look ragged. Saving restarts the GUI.",
			id(self.weatherForecast): "Shows the next four days (day, icon, high and low) at the bottom of the second infobar. Saving restarts the GUI.",
			id(self.labelLang): "Language of the small words the infobars write themselves: Now playing, Then at, Next, Film, Series, min, min left. Programme titles and descriptions come from the channel. Saving restarts the GUI.",
			id(self.arPosters): "Use the Arabic poster from TMDB when there is one: for channels on Nilesat, Arabsat and Badr (and Arabic titles), always, or never.",
			id(self.weatherPos): "Where the weather card sits in the first infobar: top right, top centre, or just above the infobar. Saving restarts the GUI.",
			id(self.plLayout): "Plugin list (Menu > Plugins) as tiles side by side or as a list. The grid needs a recent image (OpenViX / OpenBH 6.7+ or OpenATV). Saving restarts the GUI.",
			id(self.logo3d): "When a channel has no event, no poster was found or the poster is hidden, show its logo on a 3D card instead.",
			id(self.uiLang): "Language of this setup screen. Saving switches it at once.",
			id(self.dateFormat): "How the date is written in the infobars, the second infobar and the channel lists. Narrow places show it without the year so nothing is cut off. Saving restarts the GUI.",
			id(self.menuBg): "A drawn background in the theme colours behind the main menu, its submenus and the plugin list (no photos), or off to see the TV picture. 'Image style' picks the look that goes with the image on this receiver. Saving restarts the GUI.",
			id(self.osdFit): "On: the screen position of the receiver is set to full, so pictures reach every edge of the TV. Off: the position that was set before is put back. Takes effect at once.",
			id(self.menuAnim): "Honeycomb background only: cells light up and small lights fall between them, on the right side of the menu. Saving restarts the GUI.",
			id(self.epgEnglish): "Many Arabic channels send each programme's title in Arabic and in English. Yes: posters and ratings are looked up with the English title (much more exact), the Arabic one is tried after it. What you read on screen does not change.",
			id(self.ibMeterColor): "Colour of the SNR and AGC bars in the infobars and the second infobar. Saving restarts the GUI.",
			id(self.ibMeterShape): "Shape of the SNR and AGC bars in the infobars and the second infobar: a line, blocks, dots or rising bars - each piece stands apart. Saving restarts the GUI.",
			id(self.ibLed): "A glowing line along the top of the infobar that lights up once, like an LED strip, each time the bar appears. Saving restarts the GUI.",
			id(self.ibBackdrop): "The programme's backdrop at the top of the screen while the infobar is shown (every infobar style): a wide band, a box in the middle, left or right, or off. Saving restarts the GUI.",
			id(self.fitScreens): "Plugin windows that have no design in this skin get one in the skin's style automatically; windows with pictures keep their own look, enlarged to the screen. Works after the next GUI restart.",
			id(self.logoStyle): "What a channel with no programme or no poster shows: a 3D card, its logo filling the whole place over its own colours, or the logo on a dark background.",
			id(self.posterStore): "In memory: posters are fetched again after every restart (nothing is written to the box). Kept: they are saved on the hard disk or USB stick and shown at once next time.",
			id(self.eventColor): "Colour of the programme name next to each channel in the channel list. Saving restarts the GUI.",
			id(self.chPreview): "Posters: the programme poster. Live TV picture: the channel playing now, as big as the style allows. Saving restarts the GUI.",
			id(self.ibChan): "Size of the channel logo, number and name above the compact capsule infobar. It grows upwards, never into the bar. Saving restarts the GUI.",
		}
		Y, N = True, False
		self.valuehint = {  # what the chosen value does: shown under the preview while LEFT / RIGHT change it
			id(self.menuBg): {"off": "No picture: the TV stays visible behind the menu.", "orbit": "Satellites on their orbits and a dish sending its signal.",
				"waves": "Glowing signal waves running across the screen.", "aurora": "Soft northern lights in the theme colours.", "honeycomb": "A honeycomb of glowing cells, a few of them lit.",
				"auto": "The look that goes with the image on this receiver.", "deco": "Art deco: fans of fine lines and a diamond pattern.", "carbon": "Carbon fibre with a sweep of light.",
				"bokeh": "Soft glowing circles, like a night city out of focus.", "prism": "Glass facets that catch the light."},
			id(self.menuAnim): {Y: "Cells light up and small lights fall between them.", N: "A still picture."},
			id(self.ibBackdrop): {"band": "A wide strip across the top of the screen.", "center": "A framed picture at the top, in the middle.",
				"left": "A framed picture at the top left.", "right": "A framed picture at the top right.", "off": "No backdrop: only the infobar."},
			id(self.ibLed): {Y: "The line lights up from the middle outwards each time the bar opens, then stays softly lit.", N: "No light line on the infobar."},
			id(self.ibMeterShape): {"line": "One smooth rounded line.", "blocks": "Separate rounded blocks with a gap between each.",
				"dots": "Separate round dots.", "steps": "Bars that rise from left to right, like a phone's signal."},
			id(self.ibMeterColor): {"classic": "Red at the start, blue when the signal is strong.", "theme": "The colour of the skin theme you chose.",
				"amber": "Orange to yellow.", "signal": "Red when weak, yellow in the middle, green when strong.", "green": "Green.", "blue": "Blue.", "white": "White and silver."},
			id(self.fitScreens): {Y: "Plugins without a design here get the skin's look, at full screen size.", N: "Plugins keep their own small windows."},
			id(self.rating): {Y: "Stars, rating, year and genre of films and series.", N: "No stars, rating, year or genre."},
			id(self.posters): {Y: "Programme posters in the infobars and channel list.", N: "No posters: the channel logo is shown instead."},
			id(self.backdrops): {Y: "Backdrop and scenes of the programme behind the second infobar.", N: "No backdrops or scenes."},
			id(self.logo3d): {Y: "No poster: the channel logo is shown in its place.", N: "No poster: the place stays empty."},
			id(self.epgEnglish): {Y: "English title first, then the Arabic one (more exact posters).", N: "Only the title shown on screen is used."},
			id(self.posterStore): {"ram": "Nothing is written to the box; fetched again after a restart.", "disk": "Saved on the hard disk or USB: shown at once next time."},
			id(self.arPosters): {"auto": "Arabic poster on Nilesat, Arabsat and Badr channels.", "always": "Arabic poster on every channel when there is one.", "off": "Always the English poster."},
			id(self.translate): {Y: "Titles and descriptions are translated to the language below.", N: "Everything stays in the language the channel sends."},
			id(self.trService): {"auto": "Free, no key needed.", "microsoft": "Uses your own Microsoft key (set below).", "deepl": "Uses your own DeepL key (set below)."},
			id(self.smooth): {"smooth": "The seconds hand glides.", "tick": "The seconds hand jumps once a second (lighter for slow boxes)."},
			id(self.weather): {Y: "Weather card in the infobars.", N: "No weather."},
			id(self.weatherLoc): {"auto": "Found from your internet connection.", "list": "The city you picked from the list (press OK).", "city": "The city you typed below."},
			id(self.chPreview): {"poster": "The programme poster next to the list.", "live": "The channel playing now, live, next to the list."},
			id(self.plLayout): {"grid": "Tiles side by side.", "list": "One plugin under the other."},
			id(self.adult): {"off": "Nothing is hidden.", "normal": "Adult and erotic titles are hidden.", "strict": "Also nudity, R and TV-MA titles."},
		}
		E = lambda label, cfg: (t(label), cfg)
		self.groups = [
			[E("Skin colour theme", self.theme), E("Menu style", self.menuStyle), E("Main menu background", self.menuBg), E("Menu animation", self.menuAnim), E("Fill the whole screen", self.osdFit), E("Arabic text font", self.arText), E("Arabic title font", self.arTitle),
				E("Fit plugin windows to the screen", self.fitScreens)],
			[E("Infobar style", self.ibxStyle), E("Infobar transparency", self.ibAlpha), E("Channel logo and name size", self.ibChan), E("Backdrop above the infobar", self.ibBackdrop), E("Light line on the infobar", self.ibLed), E("Infobar texts language", self.labelLang), E("Date format", self.dateFormat), E("Signal bars colour", self.ibMeterColor), E("Dark backing behind signal bars", self.meterBack), E("Signal bars shape", self.ibMeterShape), E("Second infobar style", self.sibStyle),
				E("Classic infobar poster", self.ibStyle), E("Show rating stars", self.rating), E("3D channel logo when no poster", self.logo3d)],
			[E("Channel list style", self.chStyle), E("Channel list text size", self.chFont), E("Channel list rows", self.chRows), E("Channel list picture", self.chPreview), E("Programme name colour", self.eventColor),
				E("Plugin list layout", self.plLayout), E("Plugin list text size", self.plFont)],
			[E("Infobar clock", self.clock), E("Clock seconds hand", self.smooth)],
			[E("Show weather", self.weather), E("Weather position", self.weatherPos), E("Weather location", self.weatherLoc),
				E("Weather city (typed)", self.weatherCity), E("Weather units", self.weatherUnits), E("Weather language", self.weatherLang), E("Weather forecast (4 days)", self.weatherForecast)],
			[E("Show posters", self.posters), E("Show backdrops", self.backdrops)] + ([E("Hide adult posters", self.adult)] if U.is_owner() else []) +
				[E("Arabic posters", self.arPosters), E("English EPG titles for posters", self.epgEnglish), E("Channel logo style", self.logoStyle), E("Store posters", self.posterStore), E("Search language", self.language)],
			[E("Translate events", self.translate), E("Translate to", self.trLang), E("Translation service", self.trService),
				E("Translation key", self.trKey), E("Microsoft key region", self.trRegion)],
			[E("TMDB API key", self.tmdb), E("OMDb API key", self.omdb), E("Fanart.tv API key", self.fanart)],
			[E("Setup language", self.uiLang)],
		]
		self.cat = 1
		self.inList = False
		self["config"] = SettingList(L)
		try:
			self["config"].acc2 = int((self.themes.get(self.startTheme) or {}).get("accent2", "#FF5A4E").lstrip("#"), 16)
		except Exception:
			pass
		for i, c in enumerate(CATS):
			self["cat%d" % i] = StaticText(t(c))
		self["catsel"] = Pixmap()
		self["help"] = StaticText("")
		self["preview"] = Pixmap()
		self["themename"] = StaticText("")
		self["themehint"] = StaticText("")
		self["key_red"] = StaticText(t("Cancel"))
		self["key_green"] = StaticText(t("Save"))
		self["key_yellow"] = StaticText(t("Clear cache"))
		self["key_blue"] = StaticText(t("Update"))
		self["actions"] = ActionMap(["SetupActions", "ColorActions", "DirectionActions"], {
			"ok": self.keyOK,
			"save": self.keySave,
			"green": self.keySave,
			"cancel": self.keyBack,
			"red": self.keyCancel,
			"yellow": self.clearCache,
			"blue": self.checkUpdate,
			"up": self.keyUp,
			"down": self.keyDown,
			"left": self.keyLeft,
			"right": self.keyRight,
		}, -2)
		self["config"].onSelectionChanged.append(self.selectionMoved)
		self.picload = ePicLoad()
		try:
			self.picload.PictureData.get().append(self.picReady)
		except AttributeError:
			self.picload_conn = self.picload.PictureData.connect(self.picReady)
		self.previewPath = None
		self.onLayoutFinish.append(self.layoutDone)
		self.updating = False
		self.container = None
		self.latestFound = ""
		self.onLayoutFinish.append(self.autoUpdate)
		for c in (self.theme, self.clock, self.menuStyle, self.chStyle, self.sibStyle, self.ibxStyle, self.ibStyle,
				self.ibAlpha, self.chFont, self.chRows, self.plFont, self.arText, self.arTitle, self.weatherLang, self.weatherPos, self.plLayout):
			c.addNotifier(self.themeChanged, initial_call=False)

	# ------------------------------------------------------------ categories and the list of one category

	def layoutDone(self):
		self.showCategory()
		self.initPreview()
		self.noticeTries = 0
		try:
			from enigma import eTimer
			self.noticeTimer = eTimer()
			try:
				self.noticeTimer.callback.append(self.showNotice)
			except AttributeError:
				self.noticeConn = self.noticeTimer.timeout.connect(self.showNotice)
			self.noticeTimer.start(800, True)
		except Exception as e:
			print("[MohammedSkin] notice timer: %s" % e)

	def showNotice(self):
		if U.settings().get("notice_solid"):
			return
		if not self.isTop():
			self.noticeTries += 1
			if self.noticeTries < 10:
				self.noticeTimer.start(800, True)
			return
		try:
			d = dict(U.settings())
			d["notice_solid"] = True
			U.save_settings(d)
		except Exception:
			pass
		self.openNotice(lambda *a: None, self.m(
			u"تنبيه مهم\n\n"
			u"نستسمحكم عذراً، تم حذف مفاتيح البوسترات من السكن لأسباب تقنية، وتم حذف البوسترات المخزّنة.\n\n"
			u"والمطوّر يبرئ ذمته أمام الله من استخدام أي مفاتيح لعرض البوسترات أو تنزيل صور النساء أو العري، وذلك لمخالفته تعاليم الشريعة الإسلامية.\n\n"
			u"فإذا وضعت مفتاحك الخاص فإنك تتحمل المسؤولية الكاملة عنه، والمطوّر غير مسؤول عنك ولا عن تصرفاتك واستخدامك.\n\n"
			u"بدون مفتاح يعمل السكن كالمعتاد ويعرض شعارات القنوات.",
			"Important notice\n\n"
			"We apologize: the poster keys were removed from the skin for technical reasons, and the stored posters were deleted.\n\n"
			"The developer declares himself free before God of any use of keys to show posters or download pictures of women or nudity, because that goes against the teachings of Islamic Sharia.\n\n"
			"If you enter your own key, you take full responsibility for it, and the developer is not responsible for you, your actions or how you use it.\n\n"
			"Without a key the skin works as usual and shows the channel logos."), False)

	def valueText(self, cfg):
		if isinstance(cfg, ConfigYesNo):
			return self.t("Yes") if cfg.value else self.t("No")
		if isinstance(cfg, ConfigText):
			return cfg.value
		try:
			return cfg.getText()
		except Exception:
			return str(cfg.value)

	def showCategory(self):
		y = 160 + self.cat * 78
		x = 1920 - 64 - 360 if self.lang in RTL else 64
		try:
			from enigma import ePoint
			self["catsel"].instance.move(ePoint(x, y))
		except Exception as e:
			print("[MohammedSkin] category: %s" % e)
		self["config"].build(self.groups[self.cat], self.valueText, keep=0)
		self.setListFocus(self.inList)
		self.updateHelp()
		self.showPreview()

	def setListFocus(self, on):
		self.inList = on
		self["config"].focus = on
		self["config"].redraw()
		try:
			self["config"].instance.setSelectionEnable(1 if on else 0)
		except Exception:
			pass

	def selectionMoved(self):
		if getattr(self, "_moving", False):
			return
		self._moving = True
		try:
			self["config"].redraw()
		finally:
			self._moving = False
		self.updateHelp()
		self.showPreview()

	def keyUp(self):
		if self.inList:
			if self["config"].getSelectionIndex() == 0:
				return
			self["config"].up()
		else:
			self.cat = (self.cat - 1) % len(CATS)
			self.showCategory()

	def keyDown(self):
		if self.inList:
			if self["config"].getSelectionIndex() >= len(self["config"].items) - 1:
				return
			self["config"].down()
		else:
			self.cat = (self.cat + 1) % len(CATS)
			self.showCategory()

	def changeValue(self, key):
		cur = self["config"].getCurrent()
		if not cur or isinstance(cur[1], ConfigText):
			return
		cur[1].handleKey(key)
		self["config"].redraw()
		if cur[1] is self.uiLang:
			self.updateHelp()
		self.showPreview()

	def keyLeft(self):
		if not self.inList:
			self.setListFocus(True)
			return
		self.changeValue(KEY_LEFT)

	def keyRight(self):
		if not self.inList:
			self.setListFocus(True)
			return
		self.changeValue(KEY_RIGHT)

	def keyBack(self):
		if self.inList:
			self.setListFocus(False)
			return
		self.keyCancel()

	def initPreview(self):

		# same picture loader as the OpenViX skin selector previews
		size = self["preview"].instance.size()
		self.picload.setPara((size.width(), size.height(), 1, 1, 1, 1, "#00000000"))
		self.showPreview()

	def picReady(self, picInfo=None):
		ptr = self.picload.getData()
		if ptr is not None and self["preview"].instance:
			try:
				self["preview"].instance.setPixmap(ptr.__deref__())
			except AttributeError:
				self["preview"].instance.setPixmap(ptr)
			self["preview"].instance.show()

	def themeChanged(self, cfg=None):
		self.showPreview()

	def showPreview(self):
		"""Clock line: preview of that clock in the chosen colours. Any other line: the colour theme."""
		cur = self["config"].getCurrent()
		theme = self.theme.value
		if cur and cur[1] is self.menuStyle:
			path = U.style_preview("menu", self.menuStyle.value, theme)
			self["themename"].text = dict(self.menuStyles).get(self.menuStyle.value, "")
			self["themehint"].text = self.t("LEFT / RIGHT to change")
		elif cur and cur[1] is self.chStyle:
			path = U.style_preview("channels", self.chStyle.value, theme)
			self["themename"].text = dict(self.chStyles).get(self.chStyle.value, "")
			self["themehint"].text = self.t("LEFT / RIGHT to change")
		elif cur and cur[1] is self.ibxStyle:
			path = U.style_preview("infobar", self.ibxStyle.value, theme)
			self["themename"].text = dict(self.ibxStyles).get(self.ibxStyle.value, "")
			self["themehint"].text = self.t("LEFT / RIGHT to change")
		elif cur and cur[1] is self.sibStyle:
			path = U.style_preview("sib", self.sibStyle.value, theme)
			self["themename"].text = dict(self.sibStyles).get(self.sibStyle.value, "")
			self["themehint"].text = self.t("LEFT / RIGHT to change")
		elif cur and cur[1] is self.ibStyle:
			path = U.style_preview("ibposter", self.ibStyle.value, theme)
			self["themename"].text = dict(self.ibStyles).get(self.ibStyle.value, "")
			self["themehint"].text = self.t("LEFT / RIGHT to change")
		elif cur and (cur[1] is self.clock or cur[1] is self.smooth):
			name = self.clock.value
			path = U.clock_preview(name, theme)
			self["themename"].text = self.clock.getText()
			self["themehint"].text = self.t("LEFT / RIGHT to change")
		elif cur and id(cur[1]) in self.extraPreviews():
			kind, name, hint = self.extraPreviews()[id(cur[1])]
			path = U.extra_preview(kind, name) or U.theme_preview(theme)
			self["themename"].text = self.valueText(cur[1])
			self["themehint"].text = self.t("LEFT / RIGHT to change")
		else:
			path = U.theme_preview(theme)
			self["themename"].text = self.valueText(cur[1]) if cur else self.theme.getText()
			self["themehint"].text = self.t("LEFT / RIGHT to change")
		if cur and id(cur[1]) in self.valuehint:  # what this choice does
			hint = self.valuehint[id(cur[1])].get(cur[1].value)
			if hint:
				self["themehint"].text = self.t(hint)
		if path == self.previewPath:
			return
		self.previewPath = path
		try:
			if self.picload.startDecode(path) != 0:
				print("[MohammedSkin] preview: cannot decode %s" % path)
		except Exception as e:
			print("[MohammedSkin] preview: %s" % e)

	def extraPreviews(self):
		"""Option -> (preview folder, picture name, hint) for the size, font, transparency and weather lines."""
		ib, ch = self.ibxStyle.value, self.chStyle.value
		th = self.theme.value if self.theme.value in U.SHIPPED_THEMES else "red"
		mc, ms = self.ibMeterColor.value, self.ibMeterShape.value
		meters = ("meters", "theme_%s_%s" % (ms, th) if mc == "theme" else "%s_%s" % (mc, ms), "")
		yn = lambda c: "yes" if c.value else "no"
		lang = ("ar" if self.weatherLang.value == "ar" else "en") if self.weatherPos.value == "top_right" else "ar"  # previews exist in Arabic and English
		weather = ("weather", "%s_%s_%s" % (ib, lang, self.weatherPos.value), "Weather in the first infobar")
		logo = ("logo3d", ib, "Channels with no event, no poster or a hidden poster show a 3D channel logo")
		return {
			id(self.ibAlpha): ("alpha", "%s_%s" % (ib, self.ibAlpha.value), "LEFT / RIGHT: from very transparent to very dark"),
			id(self.ibChan): ("ibchan", self.ibChan.value, "LEFT / RIGHT to change the size"),
			id(self.chFont): ("chfont", "%s_%s" % (ch, self.chFont.value), "LEFT / RIGHT to change the channel list text size"),
			id(self.chRows): ("chrows", "%s_%s" % (ch, self.chRows.value), "LEFT / RIGHT to change the channel list rows"),
			id(self.plFont): ("plgrid" if self.plLayout.value == "grid" else "plfont", self.plFont.value, "LEFT / RIGHT to change the plugin list size"),
			id(self.plLayout): ("plgrid" if self.plLayout.value == "grid" else "plfont", self.plFont.value, "LEFT / RIGHT: tiles or list"),
			id(self.arText): ("artext", self.arText.value, "LEFT / RIGHT to see each Arabic text font"),
			id(self.arTitle): ("artitle", self.arTitle.value, "LEFT / RIGHT to see each Arabic title font"),
			id(self.weather): weather, id(self.weatherLoc): weather, id(self.weatherPos): weather, id(self.weatherCity): weather, id(self.weatherUnits): weather, id(self.weatherLang): weather, id(self.weatherForecast): weather, id(self.meterBack): meters, id(self.labelLang): ("rating", "yes", ""),
			id(self.adult): logo, id(self.logo3d): logo,
			id(self.logoStyle): ("logostyle", self.logoStyle.value, "LEFT / RIGHT to change"),
			id(self.arPosters): ("arposter", "sample", "Arabic poster from TMDB on Arabic channels"),
			id(self.menuBg): ("menubg", "%s_%s" % (U.menu_bg_name(self.menuBg.value), th), ""),
			id(self.menuAnim): ("menubg", "%s_%s" % (U.menu_bg_name(self.menuBg.value), th), ""),
			id(self.ibBackdrop): ("backdrop", "%s_%s" % (ib, self.ibBackdrop.value), ""),
			id(self.ibLed): ("led", "%s_%s" % (ib, yn(self.ibLed)), ""),
			id(self.ibMeterColor): meters, id(self.ibMeterShape): meters,
			id(self.fitScreens): ("fit", yn(self.fitScreens), ""),
			id(self.rating): ("rating", yn(self.rating), ""),
			id(self.posters): ("posters", "posters_" + yn(self.posters), ""),
			id(self.backdrops): ("posters", "backdrops_" + yn(self.backdrops), ""),
			id(self.chPreview): ("chpreview", "%s_%s" % (ch, self.chPreview.value), ""),
			id(self.eventColor): ("evcolor", self.eventColor.value, ""),
			id(self.dateFormat): ("rating", "yes", ""), id(self.epgEnglish): ("posters", "posters_yes", ""), id(self.posterStore): ("posters", "posters_yes", ""),
			id(self.language): ("posters", "posters_yes", ""),
			id(self.translate): ("rating", "yes", ""), id(self.trLang): ("rating", "yes", ""), id(self.trService): ("rating", "yes", ""),
			id(self.trKey): ("rating", "yes", ""), id(self.trRegion): ("rating", "yes", ""),
			id(self.tmdb): ("posters", "backdrops_yes", ""), id(self.omdb): ("posters", "posters_yes", ""), id(self.fanart): ("posters", "backdrops_yes", ""),
		}

	def isTop(self):
		"""Only open a window from this screen while it is the one on top (enigma2 crashes otherwise)."""
		try:
			return bool(self.instance) and self.session.current_dialog is self
		except Exception:
			return False

	def status(self, text):
		"""Progress shown in the help line of the setup itself: no extra window, so nothing can crash."""
		try:
			self["help"].text = text
		except Exception:
			pass

	def restartNow(self):
		self.status(self.m(u"جاري تطبيق الشكل وإعادة تشغيل الواجهة ...", "Applying, the GUI restarts now ..."))
		from enigma import eTimer
		self.restartTimer = eTimer()
		try:
			self.restartTimer.callback.append(lambda: self.session.open(TryQuitMainloop, 3))
		except AttributeError:
			self.restartConn = self.restartTimer.timeout.connect(lambda: self.session.open(TryQuitMainloop, 3))
		self.restartTimer.start(300, True)

	def updateHelp(self):
		if self.updating:
			return
		cur = self["config"].getCurrent()
		self["help"].text = self.t(self.helptext.get(id(cur[1]), "")) if cur else ""

	def locChoices(self):
		p = getattr(self, "pick", {}) or {}
		t = getattr(self, "t", lambda x: x)
		place = (p.get("ar") or p.get("en")) and (u"%s  -  %s" % (p.get("ar") or "", p.get("en") or "")).strip(" -")
		return [("auto", t("Automatic (from the internet)")),
			("list", place or t("Choose country and city (press OK)")),
			("city", t("The city typed below"))]

	def chooseCountry(self):
		from Screens.ChoiceBox import ChoiceBox
		places = U.weather_places()
		if not places:
			return
		items = [(u"%s   %s" % (c["ar"], c["en"]) if c["ar"] != c["en"] else c["en"], i) for i, c in enumerate(places)]
		self.session.openWithCallback(self.countryChosen, ChoiceBox, title=self.m(u"اختر الدولة", "Choose the country"), list=items)

	def countryChosen(self, choice):
		if not choice:
			return
		from Screens.ChoiceBox import ChoiceBox
		self.country = U.weather_places()[choice[1]]
		items = [(u"%s   %s" % (c[1], c[0]) if c[1] != c[0] else c[0], i) for i, c in enumerate(self.country["cities"])]
		self.session.openWithCallback(self.cityChosen, ChoiceBox, title=self.m(u"اختر المدينة (%s)", "Choose the city (%s)") % self.country["en"], list=items)

	def cityChosen(self, choice):
		if not choice:
			return
		en, ar, lat, lon = self.country["cities"][choice[1]]
		self.pick = {"lat": lat, "lon": lon, "en": en, "ar": ar}
		self.weatherLoc.setChoices(self.locChoices(), default="list")
		self.weatherLoc.value = "list"
		self["config"].invalidateCurrent()

	def keyOK(self):
		if not self.inList:
			self.setListFocus(True)
			return
		cur = self["config"].getCurrent()
		if cur and cur[1] is self.weatherLoc:
			self.chooseCountry()
			return
		if cur and cur[1] in (self.tmdb, self.omdb, self.fanart) and not U.settings().get("terms_ok") and not getattr(self, "termsOk", False):
			self.openNotice(self.keyTermsAnswer, self.termsText(), True)
			return
		if cur and isinstance(cur[1], ConfigText):
			self.session.openWithCallback(lambda text, c=cur[1]: self.gotText(c, text), VirtualKeyBoard, title=cur[0], text=cur[1].value)

	def gotText(self, cfg, text):
		if text is not None:
			cfg.value = text.strip()
			self["config"].invalidateCurrent()

	def setPluginLayout(self):
		"""OpenATV and images based on it have their own list / grid switch: follow our choice."""
		try:
			from Components.config import config
			if hasattr(config.usage, "pluginListLayout"):
				choices = [c[0] if isinstance(c, tuple) else c for c in config.usage.pluginListLayout.choices.choices]
				want = 1 if self.plLayout.value == "grid" else 0
				if want in choices and config.usage.pluginListLayout.value != want:
					config.usage.pluginListLayout.value = want
					config.usage.pluginListLayout.save()
		except Exception as e:
			print("[MohammedSkin] plugin layout: %s" % e)

	def makeTheme(self):
		"""New colours are made on the box from the red one the first time they are chosen."""
		import threading
		name = self.theme.value
		self.updating = True
		self.status(self.m(u"جاري تجهيز اللون الجديد، انتظر دقيقة أو دقيقتين ...", "Preparing the %s colour, please wait ..." % self.themes.get(name, {}).get("label", name)))

		def work():
			ok = False
			try:
				ok = U.make_theme(name)
			except Exception as e:
				print("[MohammedSkin] make theme: %s" % e)
			try:
				from twisted.internet import reactor
				reactor.callFromThread(self.themeMade, ok)
			except Exception:
				pass
		th = threading.Thread(target=work)
		th.daemon = True
		th.start()

	def themeMade(self, ok):
		self.updating = False
		if ok:
			self.keySave()
		else:
			self.status("This colour needs python3-pillow. Update the skin (it installs it) and try again.")

	def openNotice(self, callback, text, asks):
		title, _, body = text.partition("\n\n")
		hint = self.m(u"OK = أوافق وأتعهد          EXIT = لا أوافق", "OK = I agree          EXIT = I do not agree") if asks else self.m(u"OK = متابعة", "OK = Continue")
		self.session.openWithCallback(callback, MohammedNotice, title, body, hint, asks)

	def termsText(self):
		return self.m(
			u"تعهد وإخلاء مسؤولية\n\n"
			u"السكن لا يحتوي على أي مفتاح بوسترات. أنت من يسجّل في موقع المصدر (TMDB وغيره) ويأخذ مفتاحك الخاص ويضعه هنا، فهو باسمك وتحت مسؤوليتك.\n\n"
			u"بوضعك المفتاح تقرّ وتتعهد بأنك المسؤول مسؤولية كاملة أمام الله ثم أمام القانون عن كل ما يجلبه مفتاحك ويظهر على جهازك، بما في ذلك أي صور أو محتوى محرّم أو مخلّ بالآداب، مثل صور النساء والعري وما شابهها. وأشهد الله على ذلك، وصاحب السكن بريء أمام الله سبحانه وتعالى من ذلك كله، ولا يتحمل أي مسؤولية عن المحتوى القادم من تلك المصادر ولا عن استخدامك لمفتاحك.\n\n"
			u"هل توافق وتتعهد؟",
			"Pledge and disclaimer\n\n"
			"The skin comes with no poster key. You register with the source website (TMDB or others), get your own key and enter it here, so it is in your name and your responsibility.\n\n"
			"By entering a key you confirm that you alone are fully responsible, before God and before the law, for everything your key fetches and shows on your receiver, including any forbidden or immoral pictures or content, such as pictures of women, nudity and the like. I call God as my witness, and the skin owner is free of all of it before God Almighty and takes no responsibility for the content that comes from those sources or for how you use your key.\n\n"
			"Do you agree and accept?")

	def acceptTerms(self):
		"""The pledge is shown once: the acceptance is kept at once, not only when the settings are saved."""
		self.termsOk = True
		try:
			d = dict(U.settings())
			d["terms_ok"] = True
			U.save_settings(d)
		except Exception as e:
			print("[MohammedSkin] pledge: %s" % e)

	def keyTermsAnswer(self, answer):
		if answer:
			self.acceptTerms()
			self.keyOK()

	def termsAnswer(self, answer):
		if answer:
			self.acceptTerms()
		else:
			for cfg in (self.tmdb, self.omdb, self.fanart):
				cfg.value = ""
			self.status(self.m(u"ما انحفظت المفاتيح لأنك ما وافقت على التعهد.", "The keys were not saved because the pledge was not accepted."))
		self.keySave()

	def keySave(self):
		if self.updating:
			return
		if (self.tmdb.value.strip() or self.omdb.value.strip() or self.fanart.value.strip()) and not U.settings().get("terms_ok") and not getattr(self, "termsOk", False):
			self.openNotice(self.termsAnswer, self.termsText(), True)
			return
		if self.theme.value != self.startTheme and U.theme_missing(self.theme.value):
			self.makeTheme()
			return
		try:
			data = dict(U.settings())
			data.update({
				"tmdb": self.tmdb.value.strip(), "omdb": self.omdb.value.strip(), "fanart": self.fanart.value.strip(),
				"terms_ok": bool(U.settings().get("terms_ok") or getattr(self, "termsOk", False)),
				"language": self.language.value, "posters": self.posters.value, "backdrops": self.backdrops.value,
				"translate": self.translate.value, "clock_smooth": self.smooth.value == "smooth", "rating": self.rating.value,
				"ch_font": self.chFont.value, "ch_rows": self.chRows.value, "pl_font": self.plFont.value,
				"ib_alpha": self.ibAlpha.value, "ib_chan": self.ibChan.value, "ch_preview": self.chPreview.value, "event_color": self.eventColor.value, "adult_filter": self.adult.value if U.is_owner() else "strict",
				"ar_text_font": self.arText.value, "ar_title_font": self.arTitle.value,
				"weather": self.weather.value, "weather_city": self.weatherCity.value.strip(), "weather_units": self.weatherUnits.value,
				"weather_mode": self.weatherLoc.value, "weather_lat": self.pick.get("lat"), "weather_lon": self.pick.get("lon"),
				"weather_place_en": self.pick.get("en") or "", "weather_place_ar": self.pick.get("ar") or "",
				"weather_lang": self.weatherLang.value, "arabic_posters": self.arPosters.value, "logo3d": self.logo3d.value, "fit_screens": self.fitScreens.value, "ib_backdrop": self.ibBackdrop.value, "ib_led": self.ibLed.value, "ib_meter_color": self.ibMeterColor.value, "ib_meter_shape": self.ibMeterShape.value, "menu_bg": self.menuBg.value, "menu_anim": self.menuAnim.value, "osd_fit": self.osdFit.value, "menu_bg_v2": True, "date_format": self.dateFormat.value, "label_lang": self.labelLang.value, "ib_meter_back": self.meterBack.value, "weather_forecast": self.weatherForecast.value, "epg_english": self.epgEnglish.value,
				"weather_pos": self.weatherPos.value, "pl_layout": self.plLayout.value, "logo_style": self.logoStyle.value, "poster_store": self.posterStore.value,
				"ui_lang": self.uiLang.value, "tr_lang": self.trLang.value, "tr_service": self.trService.value, "tr_key": self.trKey.value.strip(), "tr_region": self.trRegion.value.strip()})
			self.setPluginLayout()
			U.reset_weather()
			U._tr_failed.clear()  # new translation settings: try everything again at once
			U._tr_block.clear()
			U.save_settings(data)
			try:
				if self.osdFit.value != U.osd_is_full():
					U.fit_osd(restore=not self.osdFit.value)
			except Exception as e:
				print("[MohammedSkin] screen position: %s" % e)
			U.set_cache_dir()  # RAM or disk, as chosen now
			U.clear_cache() if data.get("poster_store") != "disk" else None
			newTheme = self.theme.value != self.startTheme
			newClock = self.clock.value != self.startClock
			if newTheme and not U.apply_theme(self.theme.value):
				raise Exception("theme files are missing")
			if newClock and not U.apply_clock(self.clock.value):
				raise Exception("clock files are missing")
			newMenu = self.menuStyle.value != self.startMenu
			newChannels = self.chStyle.value != self.startChannels
			if newMenu and not U.apply_style("menu", self.menuStyle.value):
				raise Exception("menu style files are missing")
			if newChannels and not U.apply_style("channels", self.chStyle.value):
				raise Exception("channel list style files are missing")
			newSib = self.sibStyle.value != self.startSib
			newIb = self.ibStyle.value != self.startIb
			if newSib and not U.apply_style("sib", self.sibStyle.value):
				raise Exception("second infobar style files are missing")
			if newIb:
				s2 = dict(U.settings())
				s2["ibposter_style"] = self.ibStyle.value
				U.save_settings(s2)  # used by the classic infobar (now or when it is chosen later)
				U.apply_style("ibposter", self.ibStyle.value)
			newIbx = self.ibxStyle.value != self.startIbx
			if newIbx and not U.apply_infobar(self.ibxStyle.value):
				raise Exception("infobar style files are missing")
			newTune = (self.chFont.value, self.chRows.value, self.plFont.value, self.ibAlpha.value) != self.startTune \
				or (self.weatherPos.value, self.plLayout.value, self.ibChan.value, self.chPreview.value, self.eventColor.value) != self.startPlace \
				or (self.ibBackdrop.value, self.ibLed.value, self.ibMeterColor.value, self.ibMeterShape.value, self.menuBg.value, self.menuAnim.value, self.dateFormat.value, self.labelLang.value, self.weatherForecast.value, self.meterBack.value) != self.startBackdrop
			if newTune or newTheme:
				U.apply_tuning()  # also re-makes the tuned pictures in the new colour theme
			newFonts = (self.arText.value, self.arTitle.value) != self.startFonts
			if newFonts:
				U.apply_arabic_fonts()
			newCjk = U.apply_cjk_font()  # Chinese / Japanese letters need their font loaded at start
			newTheme = newTheme or newClock or newMenu or newChannels or newSib or newIb or newIbx or newTune or newFonts or newCjk
		except Exception as e:
			self.session.open(MessageBox, "Could not save settings: %s" % e, MessageBox.TYPE_ERROR)
			return
		if newTheme:
			self.updating = True
			self.restartNow()  # the new look needs a GUI restart: do it straight away
		elif self.uiLang.value != self.lang:
			self.close("reopen")  # the setup opens again in the new language
		else:
			self.close()

	def restartAnswer(self, answer):
		if answer:
			self.session.open(TryQuitMainloop, 3)
		else:
			self.close()

	def keyCancel(self):
		if self.updating:
			return  # never close the setup in the middle of an update
		self.close()

	def clearCache(self):
		U.clear_cache()
		self.session.open(MessageBox, self.t("Poster cache cleared."), MessageBox.TYPE_INFO, timeout=3)


	# ------------------------------------------------------------ online update

	def checkUpdate(self):
		if self.updating:
			return
		self["key_blue"].setText(self.t("Checking..."))
		U.check_update(self.updateChecked)

	def updateChecked(self, latest, newer):
		try:
			self["key_blue"].setText(self.t("Update"))
		except Exception:
			return  # screen already closed
		if not self.isTop():
			return
		if not latest:
			self.session.open(MessageBox, self.t("Could not reach the update server.\nCheck the internet connection and try again."), MessageBox.TYPE_ERROR, timeout=6)
		elif newer:
			self.latestFound = latest
			if U.version_tuple(latest) > U.version_tuple(U.SKIN_VERSION):
				text = self.m(u"يوجد تحديث جديد لسكن MohammedSkin\n\nالمثبت: %s\nالجديد: %s\n\nهل تريد التحديث الآن؟",
					"A new version of MohammedSkin is available.\n\nInstalled: %s\nNew: %s\n\nUpdate now?") % (U.SKIN_VERSION, latest)
			else:
				text = self.m(u"آخر تحديث للسكن ما اكتمل (%s)\n\nهل تريد إكماله الآن؟",
					"The last MohammedSkin update did not finish (%s).\n\nFinish it now?") % latest
			self.startAutoUpdate(latest)
		else:
			self.latestFound = latest
			self.session.openWithCallback(self.updateAnswer, MessageBox,
				self.m(u"السكن محدث لآخر إصدار (%s)\n\nإعادة التثبيت تصلح أي ملفات ناقصة. تبي تعيد التثبيت الحين؟",
				"MohammedSkin is up to date (%s).\n\nReinstall it now (repairs missing files)?") % U.SKIN_VERSION,
				MessageBox.TYPE_YESNO, default=False)

	# ------------------------------------------------------------ automatic update when the setup opens

	def autoUpdate(self):
		"""Look on GitHub quietly when the setup opens; only the blue button label changes. Updating is the user's choice."""
		U.check_update(self.autoUpdateChecked)

	def autoUpdateChecked(self, latest, newer):
		if not newer or self.updating:
			return
		try:
			if not self.instance:
				return  # screen already closed
		except Exception:
			return
		if U.version_tuple(latest) > U.version_tuple(U.SKIN_VERSION) and self.session.current_dialog is self:
			self.startAutoUpdate(latest)  # a newer version is installed at once, no questions
			return
		self["key_blue"].setText(u"%s %s" % (self.t("Update"), latest))

	def startAutoUpdate(self, latest):
		"""Run the online installer in a console window, so the progress is visible.
		The installer restarts the GUI by itself when it is done."""
		from Screens.Console import Console
		self.updating = True
		self["key_blue"].setText(self.t("Updating..."))
		self.status(self.m(u"جاري التحديث إلى %s ...", "Updating to %s ...") % latest)
		title = self.m(u"تحديث MohammedSkin إلى %s - انتظر، الواجهة تعيد التشغيل بنفسها", "Updating MohammedSkin to %s - please wait, the GUI restarts by itself") % latest
		self.session.openWithCallback(self.consoleClosed, Console, title=title, cmdlist=[U.UPDATE_CMD])

	def consoleClosed(self, *args):
		"""Only reached when the installer did not restart the GUI (the update failed)."""
		self.updating = False
		try:
			self["key_blue"].setText(self.t("Update"))
		except Exception:
			pass
		self.status(self.m(u"لم يكتمل التحديث، جرّب مرة ثانية بالزر الأزرق.", "The update did not finish - try again with the blue button."))

	def autoUpdateData(self, data):
		try:
			self.updateLog.append(data.decode("utf-8", "ignore") if isinstance(data, bytes) else data)
		except Exception:
			pass

	def autoUpdateDone(self, retval):
		self.container = None
		log = "".join(self.updateLog)
		if retval == 0 and "installed successfully" in log:
			self.restartNow()
			return
		self.updating = False
		try:
			self["key_blue"].setText(self.t("Update"))
		except Exception:
			pass
		tail = " / ".join(log.strip().splitlines()[-3:])
		self.status("The update did not finish: %s  -  try again with the blue button." % tail)

	def updateAnswer(self, answer):
		if answer:
			self.startAutoUpdate(self.latestFound or "")

	def updateDone(self, *args):
		self.updating = True
		self.restartNow()


def main(session, **kwargs):
	def closed(answer=None, *args):
		if answer == "reopen":
			session.openWithCallback(closed, MohammedSkinSetup)
	session.openWithCallback(closed, MohammedSkinSetup)


def runtime_family():
	"""Window-style colour names of the running enigma2: 'vix' (OpenViX, OpenBH) or 'atv' (OpenATV, PurE2, EGAMI)."""
	try:
		from enigma import eWindowStyleSkinned
		if hasattr(eWindowStyleSkinned, "colLabelForeground"):
			return "vix"
		if hasattr(eWindowStyleSkinned, "colForeground"):
			return "atv"
	except Exception:
		pass
	return ""


_restartTimer = []


def askRestart(session, name):
	def ask():
		try:
			session.openWithCallback(lambda answer: answer and session.open(TryQuitMainloop, 3), MessageBox,
				"MohammedSkin has been adapted to %s.\nRestart the GUI now to load it?" % (name or "this image"), MessageBox.TYPE_YESNO, timeout=20)
		except Exception as e:
			print("[MohammedSkin] restart question: %s" % e)
	try:
		from enigma import eTimer
		t = eTimer()
		try:
			t.callback.append(ask)
		except AttributeError:
			t.conn = t.timeout.connect(ask)
		t.start(8000, True)
		_restartTimer[:] = [t]
	except Exception as e:
		print("[MohammedSkin] restart timer: %s" % e)


def sessionstart(reason, session=None, **kwargs):
	"""With MohammedSkin active:
	- make sure skin.xml matches this image (window-style names differ between OpenViX/OpenBH and OpenATV/PurE2/EGAMI);
	  if it had to be changed, offer a GUI restart
	- first start only: turn on picons in the channel list (the user can switch them off again; we never touch it twice)."""
	try:
		from Components.config import config
		if not config.skin.primary_skin.value.startswith("MohammedSkin/"):
			return
	except Exception as e:
		print("[MohammedSkin] sessionstart: %s" % e)
		return
	try:
		U.auto_fit_osd()  # a reduced screen position of the image leaves gaps around full-screen pictures: set it to full, once
	except Exception as e:
		print("[MohammedSkin] screen position: %s" % e)
	try:
		U.install_auto_windows()  # plugin windows without a design here get one in the skin's style
		U.install_screen_fitter()  # the rest (pictures, own list layouts) scaled up to full HD
	except Exception as e:
		print("[MohammedSkin] fitter: %s" % e)
	try:
		U.refresh_blocklist()
		U.weather()  # ready before the first infobar
	except Exception:
		pass
	try:
		key, fam, changed = U.adapt_image()
		live = runtime_family()
		if live and U.current_family() != live:
			changed = U.apply_style("image", live) or changed
		if changed:
			print("[MohammedSkin] adapted skin.xml to %s (%s)" % (U.image_name() or "unknown image", live or fam))
			if session is not None:
				askRestart(session, U.image_name())
	except Exception as e:
		print("[MohammedSkin] adapt: %s" % e)
	try:
		s = U.settings()
		if s.get("picons_enabled_once"):
			return
		if not config.usage.service_icon_enable.value:
			config.usage.service_icon_enable.value = True
			config.usage.service_icon_enable.save()
		s = dict(s)
		s["picons_enabled_once"] = True
		U.save_settings(s)
	except Exception as e:
		print("[MohammedSkin] sessionstart: %s" % e)


def Plugins(**kwargs):
	return [
		PluginDescriptor(name="MohammedSkin Setup", description="Colour themes, infobar styles, ratings, Arabic translation and poster options",
			where=PluginDescriptor.WHERE_PLUGINMENU, icon="plugin.png", fnc=main),
		PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=sessionstart),
	]
