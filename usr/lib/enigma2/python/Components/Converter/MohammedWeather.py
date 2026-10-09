# -*- coding: utf-8 -*-
# MohammedSkin weather text (Open-Meteo, no key). Location from the setup, or from the box's internet address.
#
#   <widget source="global.CurrentTime" render="Label" ...><convert type="MohammedWeather">Temp</convert></widget>
#
# Temp | Condition | City | MinMax | Humidity | Wind | Line (condition and city)
# HasWeather (with ConditionalShowHide): weather switched on and known

from Components.Converter.Converter import Converter
from Components.Element import cached

from Components import MohammedSkinUtils as U


class MohammedWeather(Converter, object):
	def __init__(self, type):
		Converter.__init__(self, type)
		self.type = (type or "Temp").strip()
		self.cb = self.weatherReady

	def weatherReady(self):
		try:
			Converter.changed(self, (self.CHANGED_ALL,))
		except Exception:
			pass

	@cached
	def getText(self):
		data = U.weather(self.cb)
		if self.type == "HasWeather":
			return ""
		return U.weather_text(self.type, data)

	text = property(getText)

	@cached
	def getBoolean(self):
		return bool(U.weather(self.cb))

	boolean = property(getBoolean)
