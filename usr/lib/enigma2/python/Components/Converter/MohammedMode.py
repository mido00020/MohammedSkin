# -*- coding: utf-8 -*-
# Which part of the channel list is open, read from its title (for the All / Satellites /
# Favourites / Providers tabs of the channel list styles).
#
#   <widget source="Title" render="Pixmap" pixmap="..."><convert type="MohammedMode">All</convert><convert type="ConditionalShowHide" /></widget>
#
# All | Satellites | Favourites | Providers  (boolean); Name: the mode as text

import re

from Components.Converter.Converter import Converter
from Components.Element import cached

_SAT = re.compile(u"satellit|\\d+(?:[.,]\\d)?\\s*°?\\s*[EW]\\b|قمر|أقمار|الأقمار", re.I | re.U)
_PROV = re.compile(u"provider|anbieter|fournisseur|مزود", re.I | re.U)
_ALL = re.compile(u"^\\s*all\\b|\\ball\\s*\\(|\\balle\\b|\\btous\\b|الكل|جميع", re.I | re.U)


def mode_of(title):
	t = title or ""
	if _PROV.search(t):
		return "Providers"
	if _SAT.search(t):
		return "Satellites"
	if _ALL.search(t):
		return "All"
	return "Favourites"


class MohammedMode(Converter, object):
	def __init__(self, type):
		Converter.__init__(self, type)
		self.type = (type or "Name").strip()

	def title(self):
		try:
			return self.source.text or ""
		except Exception:
			return ""

	@cached
	def getBoolean(self):
		return mode_of(self.title()) == self.type

	boolean = property(getBoolean)

	@cached
	def getText(self):
		return mode_of(self.title()) if self.type == "Name" else ""

	text = property(getText)
