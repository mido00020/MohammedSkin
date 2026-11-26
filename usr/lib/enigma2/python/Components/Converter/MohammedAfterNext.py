# -*- coding: utf-8 -*-
# MohammedSkin: the programme after the next one (now, next, then this one) of the playing channel.
#
#   <widget source="session.CurrentService" render="Label" ...>
#       <convert type="MohammedAfterNext">Name</convert>
#   </widget>
#   Name         title (translated like MohammedTranslate when the translation is on)
#   Time         "21:30"
#   Duration     "45 min"
#   Description  short description, or the start of the long one
#   Text:After that at   the word only when there is such a programme
#   Has          boolean, pair with ConditionalShowHide
#
# The guide is read again every 30 seconds and at every channel change.

from time import time, localtime, strftime

from Components.Converter.Converter import Converter
from Components.Converter.Poll import Poll
from Components.Element import cached

from Components import MohammedSkinUtils as U
from Components import MohammedLabels as L


def _s(x):
	if x is None:
		return ""
	try:
		return x.decode("utf-8", "ignore")
	except AttributeError:
		return x


class MohammedAfterNext(Poll, Converter):
	def __init__(self, type):
		Converter.__init__(self, type)
		Poll.__init__(self)
		self.type = type.strip()
		self.poll_interval = 30000
		self.poll_enabled = True

	def _event(self):
		"""(begin, duration, title, short, long) of the third programme from now, or None"""
		try:
			import NavigationInstance
			from enigma import eEPGCache
			ref = NavigationInstance.instance.getCurrentlyPlayingServiceOrGroup()
			if ref is None:
				return None
			evs = eEPGCache.getInstance().lookupEvent(["BDTSE", (ref.toString(), 0, -1, 24 * 60)]) or []
			now = time()
			evs = sorted([e for e in evs if e and e[0] and e[1] and e[0] + e[1] > now], key=lambda e: e[0])
			return evs[2] if len(evs) > 2 else None
		except Exception:
			return None

	def _refresh(self):
		self.changed((self.CHANGED_ALL,))

	@cached
	def getText(self):
		t = self.type
		ev = self._event()
		if ev is None:
			return ""
		if t.startswith("Text:"):
			return L.label(t[5:])
		if t == "Time":
			return strftime("%H:%M", localtime(ev[0]))
		if t == "Duration":
			return L.minutes(ev[1] // 60) if ev[1] > 0 else ""
		if t == "Description":
			d = _s(ev[3]).strip() or _s(ev[4]).strip()
			return d.replace("\n", " ")
		title = _s(ev[2]).strip()
		if not title or not U.settings().get("translate", True):
			return title
		try:
			res = U.translated(title, self._refresh)
		except Exception:
			res = None
		return title if res is None else res

	text = property(getText)

	@cached
	def getBoolean(self):
		return self._event() is not None

	boolean = property(getBoolean)

	def changed(self, what):
		Converter.changed(self, what)


# Python 2 images (VTi): enigma2 there only takes UTF-8 byte strings, a unicode text would crash the GUI.
import sys as _sys
if _sys.version_info[0] == 2:
	def _py2_bytes(get):
		def text(self):
			v = get(self)
			return v.encode("utf-8") if isinstance(v, unicode) else v
		return property(text)
	MohammedAfterNext.text = _py2_bytes(MohammedAfterNext.text.fget)
