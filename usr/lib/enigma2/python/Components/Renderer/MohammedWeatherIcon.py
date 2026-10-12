# -*- coding: utf-8 -*-
# MohammedSkin weather icon.
#
#   <widget source="global.CurrentTime" render="MohammedWeatherIcon" icons="/usr/share/enigma2/MohammedSkin/weather/84/%s.png"
#           position="..." size="84,84" alphatest="blend" />
#
# Hidden while the weather is unknown or switched off in the setup.

from Components.Renderer.Renderer import Renderer
from enigma import ePixmap
from Tools.LoadPixmap import LoadPixmap

from Components import MohammedSkinUtils as U


class MohammedWeatherIcon(Renderer):
	GUI_WIDGET = ePixmap

	def __init__(self):
		Renderer.__init__(self)
		self.pattern = "/usr/share/enigma2/MohammedSkin/weather/84/%s.png"
		self.shown = None
		self.day = 0
		self.cb = self.weatherReady

	def applySkin(self, desktop, parent):
		attribs = []
		for (attrib, value) in self.skinAttributes:
			if attrib == "icons":
				self.pattern = value.strip()
			elif attrib == "day":  # 1..4: the forecast days after today
				try:
					self.day = int(value)
				except Exception:
					self.day = 0
			else:
				attribs.append((attrib, value))
		self.skinAttributes = attribs
		return Renderer.applySkin(self, desktop, parent)

	def postWidgetCreate(self, instance):
		self.shown = None
		self.changed((self.CHANGED_DEFAULT,))

	def weatherReady(self):
		try:
			self.changed((self.CHANGED_ALL,))
		except Exception:
			pass

	def changed(self, what):
		if not self.instance:
			return
		data = U.weather(self.cb)
		if not data:
			self.shown = None
			self.instance.hide()
			return
		icon = data.get("icon", "cloudy")
		if self.day:
			try:
				icon = data["fc"][self.day - 1][0]
			except Exception:
				self.shown = None
				self.instance.hide()
				return
		path = self.pattern % icon
		if path != self.shown:
			try:
				self.instance.setPixmap(LoadPixmap(path))
				self.shown = path
			except Exception:
				self.instance.hide()
				return
		self.instance.show()
