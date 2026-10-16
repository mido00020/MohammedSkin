# -*- coding: utf-8 -*-
# MohammedSkin weather text (Open-Meteo, no key). Location from the setup, or from the box's internet address.
#
#   <widget source="global.CurrentTime" render="Label" ...><convert type="MohammedWeather">Temp</convert></widget>
#
# DayName:1..4 | DayTemp:1..4 (forecast, the days after today)
# Temp | Condition | City | MinMax | Humidity | Wind | Line (condition and city)
# City:<width>:<font>:<size>:<1|2|3> -> the city name that fits the box: the full size, a smaller one, or shortened (three boxes, one shows it)
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
		if self.type.startswith("City:"):
			return self.cityFit(U.weather_text("City", data))
		return U.weather_text(self.type, data)

	def cityFit(self, name):
		"""The name in the box of its size tier: full size when it fits, 80% when it does not, else 66% and shortened with dots."""
		try:
			_, w, font, size, tier = self.type.split(":")
			w, size, tier = int(w), int(size), int(tier)
			from Components import MohammedLabels as L
		except Exception:
			return name
		if not name:
			return ""
		sizes = (size, int(round(size * 0.8)), int(round(size * 0.66)))
		pick = 3
		for i in (0, 1):
			if L.text_width(name, font, sizes[i]) <= w:
				pick = i + 1
				break
		if pick != tier:
			return ""
		if pick == 3 and L.text_width(name, font, sizes[2]) > w:
			while len(name) > 1 and L.text_width(name + u"\u2026", font, sizes[2]) > w:
				name = name[:-1].rstrip()
			name += u"\u2026"
		return name

	text = property(getText)

	@cached
	def getBoolean(self):
		return bool(U.weather(self.cb))

	boolean = property(getBoolean)
