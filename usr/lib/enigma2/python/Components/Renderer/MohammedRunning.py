# -*- coding: utf-8 -*-
# MohammedSkin running text: a label whose text glides through when it is wider than the box.
#
#   <widget source="ServiceEvent" render="MohammedRunning" position="..." size="..." font="ArTitle;46"
#           foregroundColor="#00140C0A" backgroundColor="#00F0E6D0" transparent="1" halign="center" zPosition="7">
#       <convert type="MohammedTranslate">Name</convert>
#   </widget>
#
# Text that fits stays still (aligned with halign). Text that is too long waits a moment at its start,
# then glides out of one side and comes back in from the other, round and round.
# Latin text runs to the left; Arabic text runs to the right, so it is read from its start.
# direction="up": a block of text taller than the box (a description) rolls upwards instead, like credits:
# it waits at its first line, rolls up until it has left the box, then comes back in from the bottom.
# Extra attributes: speed="75" (pixels per second), step="40" (ms between frames), pause="1800" (ms before it moves).
# The place of the text is worked out from the clock, not counted per step, so a late frame never makes it stall.

from time import time

from Components.Renderer.Renderer import Renderer
from enigma import eLabel, eWidget, eTimer, ePoint, eSize, gFont

try:
	from skin import parseColor, parseFont
except ImportError:
	parseColor = parseFont = None

GAP = 80  # space between the end of the text and its start coming round again


def _rtl(text):
	try:
		t = text if isinstance(text, type(u"")) else text.decode("utf-8", "ignore")
	except Exception:
		return False
	for ch in t:
		o = ord(ch)
		if 0x0590 <= o <= 0x08FF or 0xFB1D <= o <= 0xFEFC:
			return True
		if ch.isalpha():
			return False
	return False


class MohammedRunning(Renderer):
	GUI_WIDGET = eWidget

	def __init__(self):
		Renderer.__init__(self)
		self.label = None
		self.font = None
		self.fg = None
		self.halign = "left"
		self.up = False
		self.speed = 75
		self.step = 40
		self.pause = 1800
		self.t0 = 0
		self.x0 = 0
		self.text = ""
		self.tw = 0
		self.x = 0
		self.rtl = False
		self.moving = False
		self.timer = eTimer()
		try:
			self.timer.callback.append(self.tick)
		except AttributeError:
			self.timer_conn = self.timer.timeout.connect(self.tick)

	def applySkin(self, desktop, parent):
		keep = []
		for (attrib, value) in self.skinAttributes:
			if attrib == "font":
				try:
					self.font = parseFont(value, ((1, 1), (1, 1)))
				except Exception:
					self.font = None
			elif attrib == "foregroundColor":
				try:
					self.fg = parseColor(value)
				except Exception:
					self.fg = None
			elif attrib == "direction":
				self.up = value.strip().lower() == "up"
			elif attrib == "halign":
				self.halign = value.strip()
			elif attrib == "speed":
				self.speed = max(20, int(value))
			elif attrib == "step":
				self.step = max(15, int(value))
			elif attrib == "pause":
				self.pause = max(0, int(value))
			elif attrib in ("valign", "noWrap"):
				pass
			else:
				keep.append((attrib, value))
		self.skinAttributes = keep
		if self.up and self.speed == 75 and "speed" not in [a for a, v in self.skinAttributes]:
			self.speed = 26  # reading speed for a description
		ret = Renderer.applySkin(self, desktop, parent)
		self.setup()
		return ret

	def postWidgetCreate(self, instance):
		self.label = eLabel(instance)

	def preWidgetRemove(self, instance):
		self.timer.stop()
		self.label = None

	def setup(self):
		if not self.label:
			return
		if self.font is not None:
			self.label.setFont(self.font)
		if self.fg is not None:
			self.label.setForegroundColor(self.fg)
		self.label.setTransparent(1)
		self.label.setVAlign(eLabel.alignTop if self.up else eLabel.alignCenter)
		try:
			self.label.setNoWrap(0 if self.up else 1)
		except Exception:
			pass
		self.layout()

	def box(self):
		s = self.instance.size()
		return s.width(), s.height()

	def layout(self):
		if not self.label or not self.instance:
			return
		self.timer.stop()
		self.moving = False
		w, h = self.box()
		if self.up:
			return self.layout_up(w, h)
		self.label.resize(eSize(4000, h))
		self.label.setText(self.text)
		try:
			self.tw = self.label.calculateSize().width()
		except Exception:
			self.tw = 0
		self.rtl = _rtl(self.text)
		if self.tw <= w or self.tw == 0:  # fits: no movement
			self.label.resize(eSize(w, h))
			self.label.setHAlign({"center": eLabel.alignCenter, "right": eLabel.alignRight}.get(self.halign, eLabel.alignLeft))
			self.label.move(ePoint(0, 0))
			return
		self.label.resize(eSize(self.tw + 4, h))
		self.label.setHAlign(eLabel.alignRight if self.rtl else eLabel.alignLeft)
		# start with the beginning of the text in view
		self.x = (w - self.tw - 4) if self.rtl else 0
		self.label.move(ePoint(self.x, 0))
		self.x0 = self.x
		self.moving = True
		self.t0 = time() + self.pause / 1000.0
		self.timer.start(self.pause, True)

	def layout_up(self, w, h):
		self.label.setHAlign({"center": eLabel.alignCenter, "right": eLabel.alignRight}.get(self.halign, eLabel.alignLeft))
		self.label.resize(eSize(w, 4000))
		self.label.setText(self.text)
		try:
			self.tw = self.label.calculateSize().height()  # here: the height of the text
		except Exception:
			self.tw = 0
		self.x = self.x0 = 0
		if self.tw <= h or self.tw == 0:
			self.label.resize(eSize(w, h))
			self.label.move(ePoint(0, 0))
			return
		self.label.resize(eSize(w, self.tw + 6))
		self.label.move(ePoint(0, 0))
		self.moving = True
		self.t0 = time() + self.pause / 1000.0
		self.timer.start(self.pause, True)

	def tick(self):
		if not self.moving or not self.label:
			return
		w, h = self.box()
		if self.up:  # rolls up, comes back in from the bottom
			gap = 40
			cycle = float(h + self.tw + 6 + gap)
			y = -max(0.0, (time() - self.t0) * self.speed)
			if y < -self.tw - 6 - gap:
				y = h - ((-self.tw - 6 - gap - y) % cycle)
			y = int(round(y))
			if y != self.x:
				self.x = y
				self.label.move(ePoint(0, y))
			self.timer.start(self.step, True)
			return
		cycle = float(w + self.tw + 4 + GAP)
		run = max(0.0, (time() - self.t0) * self.speed)
		if self.rtl:  # glides to the right, comes back in from the left
			x = self.x0 + run
			if x > w + GAP:
				x = -self.tw - 4 + ((x - (w + GAP)) % cycle)
				if x > w + GAP:
					x -= cycle
		else:  # glides to the left, comes back in from the right
			x = self.x0 - run
			if x < -self.tw - 4 - GAP:
				x = w - ((-self.tw - 4 - GAP - x) % cycle)
		x = int(round(x))
		if x != self.x:
			self.x = x
			self.label.move(ePoint(x, 0))
		self.timer.start(self.step, True)

	def changed(self, what):
		if what[0] == self.CHANGED_CLEAR:
			text = ""
		else:
			text = self.source.text or ""
		if text != self.text:
			self.text = text
			self.layout()

	def onShow(self):
		Renderer.onShow(self)
		if self.moving:
			self.t0 = time() + self.pause / 1000.0
			self.x = self.x0
			self.label.move(ePoint(0, self.x) if self.up else ePoint(self.x, 0))
			self.timer.start(self.pause, True)

	def onHide(self):
		Renderer.onHide(self)
		self.timer.stop()
