# -*- coding: utf-8 -*-
# MohammedSkin rating stars: five stars filled in half-star steps from the event's rating (0-10).
#
#   <widget source="session.Event_Now" render="MohammedStars" frames="/usr/share/enigma2/MohammedSkin/img/stars_200_%02d.png"
#           position="..." size="200,36" alphatest="blend" />
#   event = now | next   (only for ServiceEvent in the channel list)
#
# The rating comes from the same online lookup as the posters (TMDB, TVmaze, OMDb or IMDb).
# The widget stays hidden while there is no rating, or when ratings are switched off in the setup.

from Components.Renderer.Renderer import Renderer
from enigma import ePixmap, eEPGCache
from Tools.LoadPixmap import LoadPixmap

from Components import MohammedSkinUtils as U


class MohammedStars(Renderer):
	GUI_WIDGET = ePixmap

	def __init__(self):
		Renderer.__init__(self)
		self.pattern = "/usr/share/enigma2/MohammedSkin/img/stars_200_%02d.png"
		self.which = "now"
		self.shown = None

	def applySkin(self, desktop, parent):
		attribs = []
		for (attrib, value) in self.skinAttributes:
			if attrib == "frames":
				self.pattern = value.strip()
			elif attrib == "event":
				self.which = "next" if value.strip().lower() == "next" else "now"
			else:
				attribs.append((attrib, value))
		self.skinAttributes = attribs
		return Renderer.applySkin(self, desktop, parent)

	def postWidgetCreate(self, instance):
		self.shown = None
		self.changed((self.CHANGED_DEFAULT,))

	def getEvent(self):
		src = self.source
		event = getattr(src, "event", None)
		if self.which == "next":
			service = getattr(src, "service", None)
			if service is not None:
				try:
					event = eEPGCache.getInstance().lookupEventTime(service, -1, 1)
				except Exception:
					event = None
		return event

	def changed(self, what):
		if not self.instance:
			return
		if what[0] == self.CHANGED_CLEAR or not U.settings().get("rating", True):
			self.hideStars()
			return
		entry = U.event_entry(self.getEvent(), self.ready)
		self.showEntry(entry)

	def ready(self):
		if self.instance:
			self.showEntry(U.event_entry(self.getEvent()))

	def showEntry(self, entry):
		rating = U.rating_of(entry) if entry else 0
		if rating <= 0:
			self.hideStars()
			return
		idx = max(1, min(10, int(round(rating))))  # 0-10 rating = 0-10 half stars of five stars
		path = self.pattern % idx
		if path != self.shown:
			try:
				ptr = LoadPixmap(path, cached=True)
			except Exception:
				ptr = None
			if ptr is None:
				self.hideStars()
				return
			self.instance.setPixmap(ptr)
			self.shown = path
		self.instance.show()

	def hideStars(self):
		if self.instance:
			self.instance.hide()
