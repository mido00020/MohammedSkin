# -*- coding: utf-8 -*-
# MohammedSkin poster / backdrop renderer.
#
# Usage in skin.xml:
#   <widget source="session.Event_Now" render="MohammedPoster" kind="poster" position="..." size="..." />
#   <widget source="session.Event_Next" render="MohammedPoster" kind="poster" ... />
#   <widget source="ServiceEvent" render="MohammedPoster" kind="backdrop" event="now" ... />
#   <widget source="ServiceEvent" render="MohammedPoster" kind="poster" event="next" ... />
#
# kind  = poster | backdrop | scene  (scene: use index="0".."4")
# event = now | next   (only needed for ServiceEvent; Event_Now/Event_Next already say which)
# delay = ms to wait before looking up (debounce while scrolling), default 300
# fill  = background colour around the picture, e.g. "#00060304" (default transparent)
# cover = "1": crop the picture to the widget shape so it fills it (round posters); needs python3-pillow
# logo  = "0": no 3D channel logo when there is no picture (posters and backdrops show one by default)
#
# Channels on Nilesat / Arabsat / Badr (or with Arabic titles) get the Arabic poster when TMDB has one.
# With no event, no picture found, or a poster hidden by the adult filter, a 3D card with the
# channel logo is shown instead (needs python3-pillow; otherwise the widget hides as before).
#
# While no picture is shown the widget is hidden, so anything placed underneath it
# in the skin (a channel-logo card, for example) shows through as a fallback.

from Components.Renderer.Renderer import Renderer
from enigma import ePixmap, ePicLoad, eTimer, eEPGCache

from Components import MohammedSkinUtils as U


class MohammedPoster(Renderer):
	GUI_WIDGET = ePixmap

	def __init__(self):
		Renderer.__init__(self)
		self.kind = "poster"
		self.scene = 0
		self.which = "now"
		self.delay = 300
		self.fill = "#FF000000"
		self.cover = False
		self.logo = True
		self.current = None      # cache key currently wanted
		self.shown = None        # file currently displayed
		self.pending = None      # (title, year, kind, key)
		self.picload = ePicLoad()
		try:
			self.picload.PictureData.get().append(self.picReady)
		except Exception:
			self.picload_conn = self.picload.PictureData.connect(self.picReady)
		self.timer = eTimer()
		try:
			self.timer.callback.append(self.lookup)
		except Exception:
			self.timer_conn = self.timer.timeout.connect(self.lookup)

	def applySkin(self, desktop, parent):
		attribs = []
		for (attrib, value) in self.skinAttributes:
			if attrib == "kind":
				v = value.strip().lower()
				self.kind = v if v in ("backdrop", "scene") else "poster"
			elif attrib == "index":
				try:
					self.scene = max(0, int(value))
				except ValueError:
					pass
			elif attrib == "event":
				self.which = "next" if value.strip().lower() == "next" else "now"
			elif attrib == "fill":
				self.fill = value.strip()
			elif attrib == "logo":
				self.logo = value.strip().lower() not in ("0", "no", "false", "off")
			elif attrib == "cover":
				self.cover = value.strip().lower() in ("1", "yes", "true", "on")
			elif attrib == "delay":
				try:
					self.delay = max(0, int(value))
				except ValueError:
					pass
			else:
				attribs.append((attrib, value))
		self.skinAttributes = attribs
		return Renderer.applySkin(self, desktop, parent)

	def postWidgetCreate(self, instance):
		self.changed((self.CHANGED_DEFAULT,))

	def preWidgetRemove(self, instance):
		self.timer.stop()
		self.current = None

	# ------------------------------------------------------------ event

	def getEvent(self):
		src = self.source
		event = getattr(src, "event", None)
		if self.which == "next":
			service = getattr(src, "service", None)
			if service is not None:  # ServiceEvent in the channel list
				try:
					epg = eEPGCache.getInstance()
					event = epg.lookupEventTime(service, -1, 1)
				except Exception:
					event = None
		return event

	def channel(self):
		"""(service reference, name) of the channel this event belongs to (channel list or the one playing)."""
		src = self.source
		ref = getattr(src, "service", None)
		if ref is None:
			nav = getattr(src, "navcore", None)
			try:
				ref = nav.getCurrentlyPlayingServiceReference() if nav else None
			except Exception:
				ref = None
		if ref is None:
			return None, ""
		try:
			from ServiceReference import ServiceReference
			return ref, (ServiceReference(ref).getServiceName() or "").replace(u"\x86", "").replace(u"\x87", "")
		except Exception:
			return ref, ""

	def channelName(self):
		return self.channel()[1]

	def useLogo(self):
		return self.logo and self.kind in ("poster", "backdrop") and U.settings().get("logo3d", True)

	def showLogo(self):
		"""3D channel logo instead of a picture (made in the timer, so scrolling stays smooth)."""
		ref, name = self.channel()
		if not self.useLogo() or (ref is None and not name):
			self.hide()
			return
		key = "logo:%s:%s" % (ref.toString() if ref is not None and hasattr(ref, "toString") else "", name)
		if key == self.current and self.shown:
			return
		self.current = key
		self.hide()
		self.pending = ("logo", ref, name, key)
		self.timer.stop()
		self.timer.start(self.delay, True)

	def changed(self, what):
		if not self.instance:
			return
		setting = "posters" if self.kind == "poster" else "backdrops"
		if not U.settings().get(setting, True):
			self.hide()
			return
		if what[0] == self.CHANGED_CLEAR:
			self.showLogo()  # no guide data for this channel: its logo instead of an empty place
			return
		event = self.getEvent()
		ref, chname = self.channel()
		if self.which == "next" and getattr(self.source, "service", None) is not None:
			now = getattr(self.source, "event", None)
			try:
				now_name = now.getEventName() if now else ""
			except Exception:
				now_name = ""
			if U.no_event_title(U.clean_title(now_name)[0]) or U.no_event_title(now_name):
				self.showLogo()  # no guide for this channel now: the "next" programme is guesswork too
				return
		if U.adult_event(event, chname):
			self.showLogo()
			return
		name = event.getEventName() if event else ""
		title, year = U.clean_title(name)
		if U.no_event_title(title) or U.no_event_title(name):
			self.showLogo()
			return
		self.arabic = self.kind == "poster" and U.want_arabic_poster(ref, chname, title)
		self.arabic_ctx = U.arabic_channel(ref, chname) or bool(U._ARABIC.search(title))
		key = U.cache_key(title, year)
		if key == self.current and self.shown:
			return
		self.current = key
		entry = U.cached(key)
		if entry is not None:
			self.timer.stop()
			self.showEntry(entry, key)
			return
		self.hide()
		self.extra = (U.arabic_alt_title(event),) if self.arabic_ctx and not U._ARABIC.search(title) else ()
		self.pending = (title, year, U.guess_kind(event), key)
		self.timer.stop()
		self.timer.start(self.delay, True)

	def lookup(self):
		if not self.pending:
			return
		if self.pending[0] == "logo":
			_, ref, name, key = self.pending
			self.pending = None
			if key != self.current or not self.instance:
				return
			size = self.instance.size()
			path = U.picon3d_async(ref, name, size.width(), size.height(), lambda p, k=key: self.onLogo(k, p))
			if path:
				self.display(path)
			return
		title, year, kind, key = self.pending
		self.pending = None
		if key != self.current:
			return
		entry = U.request(title, year, kind, lambda e, k=key: self.onResult(k, e), arabic=getattr(self, "arabic_ctx", False), extra=getattr(self, "extra", ()))
		if entry is not None:
			self.showEntry(entry, key)

	def onLogo(self, key, path):
		if self.instance and key == self.current:
			if path:
				self.display(path)
			else:
				self.hide()

	def onResult(self, key, entry):
		if self.instance and key == self.current:
			self.showEntry(entry, key)

	# ------------------------------------------------------------ drawing

	def showEntry(self, entry, key):
		if self.kind == "scene":
			sc = entry.get("scenes") or []
			path = sc[self.scene] if self.scene < len(sc) else None
		elif self.kind == "backdrop":
			path = entry.get("backdrop")
		else:
			path = (getattr(self, "arabic", False) and entry.get("poster_ar")) or entry.get("poster")
		if not path:
			if self.kind in ("poster", "backdrop") and entry.get("t") is not None:
				self.current = None
				self.showLogo()
			else:
				self.hide()
			return
		self.display(path)

	def display(self, path):
		if self.cover:
			# the crop is made in the background: the GUI must not wait for it (it froze weak boxes on OK)
			size = self.instance.size()
			ready = U.cover_crop_async(path, size.width(), size.height(), lambda p, k=self.current: self.onCrop(k, p))
			if ready is None:
				self.hide()  # never leave the previous channel's picture up while this one is made
				return
			path = ready
		self.showPath(path)

	def onCrop(self, key, path):
		if self.instance and key == self.current and path:
			self.showPath(path)

	def showPath(self, path):
		self.want = path
		if path == self.shown:
			self.instance.show()
			return
		if getattr(self, "decoding", False):
			return  # one picture at a time: the newest wanted one is decoded when this one is done
		self.startDecode(path)

	def startDecode(self, path):
		size = self.instance.size()
		self.loading = path
		self.decoding = True
		self.picload.setPara([size.width(), size.height(), 1, 1, False, 1, self.fill])
		if self.picload.startDecode(path) != 0:
			self.decoding = False
			self.hide()

	def picReady(self, picInfo=None):
		self.decoding = False
		if not self.instance:
			return
		done = getattr(self, "loading", None)
		want = getattr(self, "want", None)
		if want and want != done:
			self.startDecode(want)  # the channel changed while this one was decoding: never show the old picture
			return
		ptr = self.picload.getData()
		if ptr is not None and want:
			self.instance.setPixmap(ptr)
			self.shown = done
			self.instance.show()
		else:
			self.hide()

	def hide(self):
		self.shown = None
		self.want = None
		if self.instance:
			self.instance.hide()
