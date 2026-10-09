# -*- coding: utf-8 -*-
# MohammedSkin info converter.
#
# With session.CurrentService:
#   Resolution  -> "1080p"          IsHD / IsUHD / IsDolby / IsCrypted / IsWide (boolean)
#   Aspect      -> "16:9" / "4:3"
#   Number      -> channel number of the playing service
# With session.Event_Now / Event_Next / ServiceEvent:
#   Kind        -> "Film" / "Series" / ""
#   Remaining   -> "78 min left"
#   Duration    -> "145 min"
#   Text:Now playing      -> the text only when there is an event
#   NoEventText:No guide  -> the text only when there is no event
#   NextText:Then at      -> the text only when a next event exists
#   HasEvent / HasNext    -> boolean, pair with ConditionalShowHide
#   HasRating   -> boolean: the event has an online rating (and ratings are switched on)
#   RatingText  -> "7.8"            RatingSource -> "IMDb" / "TMDB" / "TVmaze"
#   Meta        -> "2024  •  Drama, Mystery"   (year and up to two genres)
# With any source:
#   Provider    -> provider of the service (also safe in the channel list)
#   ImageName   -> "OpenATV Moh", "OpenBlackHole Moh", ... (the image this box runs; "Moh" when unknown)
#   NextTime    -> "18:00 - 19:45" of the next programme (ServiceEvent in the channel list)
#   ImageIs:openatv -> boolean: the box runs that image (openvix, openbh, openatv, pure2, egami; moh = unknown)
#   AlwaysTrue  -> True
#   Blink       -> toggles every 650 ms (pair with ConditionalShowHide); independent of the box blink setting

from time import time

from Components.Converter.Converter import Converter
from Components.Converter.Poll import Poll
from Components.Element import cached
from enigma import iServiceInformation

from Components import MohammedSkinUtils as U

WIDESCREEN = (3, 4, 7, 8, 0xB, 0xC, 0xF, 0x10)

_image_label = []


def image_label():
	if not _image_label:
		try:
			_image_label.append(U.image_label())
		except Exception:
			_image_label.append("Moh")
	return _image_label[0]


_image_key = []


def image_is(t):
	"""ImageIs:openatv -> True on that image; ImageIs:moh -> True when the image is not known"""
	if not _image_key:
		try:
			_image_key.append(U.image_key() or "moh")
		except Exception:
			_image_key.append("moh")
	return t.split(":", 1)[1].strip().lower() == _image_key[0]


DOLBY = ("AC3", "AC-3", "E-AC3", "EAC3", "AC4", "DOLBY", "DD+", "DD ")


class MohammedInfo(Poll, Converter):
	def __init__(self, type):
		Converter.__init__(self, type)
		Poll.__init__(self)
		self.type = type.strip()
		if self.type == "Remaining":
			self.poll_interval = 30000
			self.poll_enabled = True
		elif self.type == "Blink":
			self.poll_interval = 650
			self.poll_enabled = True
		self.dead = False

	# ------------------------------------------------------------ online info (rating, year, genres)

	def _entry(self):
		if not U.settings().get("rating", True):
			return None
		return U.event_entry(getattr(self.source, "event", None), self._ready)

	def _ready(self):
		if not self.dead:
			try:
				Converter.changed(self, (self.CHANGED_POLL,))
			except Exception:
				pass

	def destroy(self):
		self.dead = True
		Poll.destroy(self)  # same as before this override (Poll comes first in the MRO)

	def _provider(self):
		"""Provider name for the playing service (iServiceInformation) and for the channel list
		(iStaticServiceInformation needs the reference too; some images call it wrongly)."""
		info = getattr(self.source, "info", None)
		if info is None:
			return ""
		ref = getattr(self.source, "service", None)
		try:
			if ref is not None:
				return info.getInfoString(ref, iServiceInformation.sProvider) or ""
		except Exception:
			pass
		try:
			return info.getInfoString(iServiceInformation.sProvider) or ""
		except Exception:
			return ""

	def _meta(self):
		e = self._entry()
		if not e or not e.get("poster"):  # only for a real match (one with a poster)
			return ""
		parts = []
		if e.get("year"):
			parts.append(str(e["year"]))
		if e.get("genres"):
			parts.append(", ".join(e["genres"][:2]))
		return u"  \u2022  ".join(parts)

	def _service(self):
		return getattr(self.source, "service", None)

	def _info(self):
		s = self._service()
		try:
			return s and s.info()
		except Exception:
			return None

	def _height(self):
		info = self._info()
		if not info:
			return -1
		try:
			return info.getInfo(iServiceInformation.sVideoHeight)
		except Exception:
			return -1

	def _dolby(self):
		s = self._service()
		try:
			tracks = s and s.audioTracks()
			if not tracks:
				return False
			for i in range(tracks.getNumberOfTracks()):
				d = (tracks.getTrackInfo(i).getDescription() or "").upper() + " "
				if any(x in d for x in DOLBY):
					return True
		except Exception:
			pass
		return False

	def _next_event(self):
		service = getattr(self.source, "service", None)
		try:
			from enigma import eServiceReference, eEPGCache
			if isinstance(service, eServiceReference):
				return eEPGCache.getInstance().lookupEventTime(service, -1, 1)
		except Exception:
			pass
		return None

	@cached
	def getBoolean(self):
		t = self.type
		if t == "HasEvent":
			return getattr(self.source, "event", None) is not None
		if t == "HasNext":
			return self._next_event() is not None
		if t == "AlwaysTrue":
			return True
		if t.startswith("ImageIs:"):
			return image_is(t)
		if t == "HasRating":
			return U.rating_of(self._entry() or {}) > 0
		if t == "Blink":
			return int(time() * 1000 / 650) % 2 == 0
		if t in ("IsHD", "IsUHD"):
			h = self._height()
			return h >= 2160 if t == "IsUHD" else 720 <= h < 2160
		if t == "IsDolby":
			return self._dolby()
		info = self._info()
		if not info:
			return False
		try:
			if t == "IsCrypted":
				return info.getInfo(iServiceInformation.sIsCrypted) == 1
			if t == "IsWide":
				return info.getInfo(iServiceInformation.sAspect) in WIDESCREEN
		except Exception:
			pass
		return False

	boolean = property(getBoolean)

	def _number(self):
		ref = None
		try:
			import NavigationInstance
			ref = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
		except Exception:
			ref = None
		if ref is None:
			ref = getattr(self.source, "serviceref", None)
		try:
			num = ref.getChannelNum() if ref is not None else 0
		except Exception:
			num = 0
		return str(num) if num and num > 0 else ""

	@cached
	def getText(self):
		t = self.type
		if t == "Number":
			return self._number()
		if t == "ImageName":
			return image_label()
		if t == "Provider":
			return self._provider()
		if t == "RatingText":
			r = U.rating_of(self._entry() or {})
			return ("%.1f" % r) if r > 0 else ""
		if t == "RatingSource":
			e = self._entry() or {}
			return e.get("rating_src", "") if U.rating_of(e) > 0 else ""
		if t == "Meta":
			return self._meta()
		if t.startswith("Text:"):
			return t[5:] if getattr(self.source, "event", None) is not None else ""
		if t.startswith("NoEventText:"):
			return t[12:] if getattr(self.source, "event", None) is None else ""
		if t.startswith("NextText:"):
			return t[9:] if self._next_event() is not None else ""
		if t == "NextTime":  # "18:00 - 19:45" of the next programme
			ev = self._next_event()
			try:
				from time import localtime, strftime
				begin, dur = ev.getBeginTime(), ev.getDuration()
				return "%s - %s" % (strftime("%H:%M", localtime(begin)), strftime("%H:%M", localtime(begin + dur)))
			except Exception:
				return ""
		if t == "Resolution":
			h = self._height()
			if h <= 0:
				return ""
			for std in (2160, 1080, 720, 576, 480):
				if h >= std - 8:
					return "%dp" % std
			return "%dp" % h
		if t == "Aspect":
			info = self._info()
			try:
				a = info.getInfo(iServiceInformation.sAspect) if info else -1
			except Exception:
				a = -1
			if a < 0:
				return ""
			return "16:9" if a in WIDESCREEN else "4:3"
		event = getattr(self.source, "event", None)
		if event is None:
			return ""
		if t == "Kind":
			k = U.guess_kind(event)
			return {"film": "Film", "series": "Series"}.get(k, "")
		try:
			begin, dur = event.getBeginTime(), event.getDuration()
		except Exception:
			return ""
		if t == "Duration":
			return "%d min" % (dur // 60) if dur > 0 else ""
		if t == "Remaining":
			left = begin + dur - int(time())
			if dur <= 0 or left <= 0:
				return ""
			if left > dur:  # not started yet
				return "%d min" % (dur // 60)
			return "%d min left" % ((left + 59) // 60)
		return ""

	text = property(getText)

	def changed(self, what):
		Converter.changed(self, what)
