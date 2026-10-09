# -*- coding: utf-8 -*-
# MohammedSkin: event text translated to Arabic online (free endpoints, no key).
#
#   <widget source="session.Event_Now" render="Label" ...>
#       <convert type="MohammedTranslate">Name</convert>          translated title
#   </widget>
#   <convert type="MohammedTranslate">Description</convert>        translated short + extended description
#   <convert type="MohammedTranslate">OriginalName</convert>       original title, only shown when a translation is on screen
#   <convert type="MohammedTranslate">NextName</convert>           next event title (ServiceEvent in the channel list)
#   <convert type="MohammedTranslate">NextDescription</convert>    next event description (ServiceEvent in the channel list)
#
# While the translation is being fetched the original text is shown, then it switches to Arabic.
# Turn it off in MohammedSkin Setup ("Translate events to Arabic").

from Components.Converter.Converter import Converter
from Components.Element import cached

from Components import MohammedSkinUtils as U


def _s(x):
	if x is None:
		return ""
	try:
		return x.decode("utf-8", "ignore")
	except AttributeError:
		return x


class MohammedTranslate(Converter):
	def __init__(self, type):
		Converter.__init__(self, type)
		self.type = type.strip()

	def _event(self):
		if self.type.startswith("Next"):
			service = getattr(self.source, "service", None)
			try:
				from enigma import eEPGCache, eServiceReference
				if isinstance(service, eServiceReference):
					return eEPGCache.getInstance().lookupEventTime(service, -1, 1)
			except Exception:
				pass
			return None
		return getattr(self.source, "event", None)

	def _original(self, event):
		if self.type in ("Name", "OriginalName", "NextName"):
			return _s(event.getEventName()).strip()
		short = _s(event.getShortDescription()).strip()
		ext = _s(event.getExtendedDescription()).strip()
		if short and ext and not ext.startswith(short):
			return short + "\n" + ext
		return ext or short

	def _refresh(self):
		self.changed((self.CHANGED_ALL,))

	@cached
	def getText(self):
		event = self._event()
		if event is None:
			return ""
		text = self._original(event)
		on = U.settings().get("translate", True)
		if self.type == "OriginalName":
			if not on or not text or (U.tr_target() == "ar" and U.is_arabic(text)):
				return ""
			return text if U.translated(text, self._refresh) not in (None, text) else ""
		if not on or not text:
			return text
		res = U.translated(text, self._refresh)
		return text if res is None else res

	text = property(getText)
