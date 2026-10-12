# -*- coding: utf-8 -*-
# MohammedSkin info converter.
#
# With session.CurrentService:
#   Resolution  -> "1080p"          IsHD / IsUHD / IsDolby / IsCrypted / IsWide (boolean)
#   IsSD / Is720 / Is1080 / Is4K / IsHDR -> boolean, the quality row of the infobars
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
from Components import MohammedLabels as L

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
		return U.event_entry(getattr(self.source, "event", None), self._ready, U.source_ref(self.source))

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

	_hdr_lists = None

	def _hdr_list(self):
		"""The HDR transponders and channel-name words: the skin's own list plus the user's (/etc/enigma2/mohammedskin_hdr.json)."""
		if MohammedInfo._hdr_lists is not None:
			return MohammedInfo._hdr_lists
		import json
		import os
		tps, names = [], []
		for path in ("/usr/share/enigma2/MohammedSkin/hdr.json", "/etc/enigma2/mohammedskin_hdr.json"):
			try:
				if os.path.exists(path):
					d = json.load(open(path))
					for t in d.get("transponders", []):
						tps.append((int(t[0]), int(t[1]), str(t[2]).upper()[:1]))
					for n in d.get("names", []):
						names.append(str(n).upper())
			except Exception:
				pass
		MohammedInfo._hdr_lists = (tps, names)
		return MohammedInfo._hdr_lists

	def _hdr_by_list(self, info):
		"""True when the playing satellite transponder is on the HDR list, or the channel name has one of the listed words."""
		tps, names = self._hdr_list()
		try:
			name = " " + (info.getName() or "").upper().replace("-", " ").replace("_", " ") + " "
		except Exception:
			name = ""
		for n in names:
			if (" " + n + " ") in name:
				return True
		if not tps:
			return False
		try:
			from Components.Converter.MohammedTransponder import tuner_of, mhz, SAT_POL
			tp = info.getInfoObject(iServiceInformation.sTransponderData)
			if not tp or tuner_of(tp) != "DVB-S":
				return False
			orb = int(tp.get("orbital_position"))
			f = int(mhz(tp.get("frequency"), "DVB-S") or 0)
			pol = SAT_POL.get(tp.get("polarization"), "")
		except Exception:
			return False
		for o, fr, pl in tps:
			if o == orb and abs(fr - f) <= 2 and pl == pol:
				return True
		return False

	def _hdr(self):
		"""HDR10 / HLG / Dolby Vision of the playing picture: the decoder's gamma where the image reports it, otherwise the
		HDR transponder / channel list (an image such as the Vu+ OpenViX gives no HDR information at all)."""
		info = self._info()
		if not info:
			return False
		g = -1
		key = getattr(iServiceInformation, "sGamma", None)
		if key is not None:
			try:
				g = info.getInfo(key)
			except Exception:
				g = -1
		if g is not None and g > 0 and self._height() > 0:
			return True
		return self._hdr_by_list(info) and self._height() >= 1072

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
		if t in ("IsSD", "Is720", "Is1080", "Is4K"):  # the quality row: exactly one of them lights up
			h = self._height()
			if h <= 0:
				return False
			if t == "Is4K":
				return h >= 2152
			if t == "Is1080":
				return 1072 <= h < 2152
			if t == "Is720":
				return 712 <= h < 1072
			return h < 712
		if t == "IsHDR":
			return self._hdr()
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
			return L.label(t[5:]) if getattr(self.source, "event", None) is not None else ""
		if t.startswith("NoEventText:"):
			return L.label(t[12:]) if getattr(self.source, "event", None) is None else ""
		if t.startswith("NextText:"):
			return L.label(t[9:]) if self._next_event() is not None else ""
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
			return L.label({"film": "Film", "series": "Series"}.get(k, ""))
		try:
			begin, dur = event.getBeginTime(), event.getDuration()
		except Exception:
			return ""
		if t == "Duration":
			return L.minutes(dur // 60) if dur > 0 else ""
		if t == "Remaining":
			left = begin + dur - int(time())
			if dur <= 0 or left <= 0:
				return ""
			if left > dur:  # not started yet
				return L.minutes(dur // 60)
			return L.minutes_left((left + 59) // 60)
		return ""

	text = property(getText)

	def changed(self, what):
		Converter.changed(self, what)
