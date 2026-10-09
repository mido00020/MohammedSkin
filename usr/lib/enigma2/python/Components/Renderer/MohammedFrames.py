# -*- coding: utf-8 -*-
# MohammedSkin frame renderer: shows one of a numbered set of pre-rendered PNG frames.
#
#   mode="second"  frame follows the clock seconds (smooth sweep or one step per second)
#   mode="minute"  frame follows minutes + seconds
#   mode="hour"    frame follows hours + minutes
#   mode="cycle"   frames play in a loop (running lights)
#   mode="bounce"  frames play forwards then backwards (0 1 2 3 2 1 0 ...): a soft glow up and down
#   cache="1"      keep the decoded frames in memory (only for a few small frames): no decoding while it plays
#
#   frames="/usr/share/enigma2/MohammedSkin/clock/sec_%03d.png"  count="240"
#   interval="250"   ms between updates (second / cycle modes)
#
# The timer only runs while the screen is shown. Frames are read from disk without
# caching so memory use stays flat.

from time import time, localtime

from Components.Renderer.Renderer import Renderer
from enigma import ePixmap, eTimer
from Tools.LoadPixmap import LoadPixmap

from Components import MohammedSkinUtils as U


class MohammedFrames(Renderer):
	GUI_WIDGET = ePixmap

	def __init__(self):
		Renderer.__init__(self)
		self.mode = "second"
		self.pattern = ""
		self.count = 1
		self.interval = 0
		self.index = -1
		self.k = 0
		self.visible = False
		self.cache = None
		self.timer = eTimer()
		try:
			self.timer.callback.append(self.tick)
		except AttributeError:
			self.timer_conn = self.timer.timeout.connect(self.tick)

	def applySkin(self, desktop, parent):
		attribs = []
		for (attrib, value) in self.skinAttributes:
			if attrib == "mode":
				self.mode = value.strip()
			elif attrib == "frames":
				self.pattern = value.strip()
			elif attrib == "count":
				self.count = max(1, int(value))
			elif attrib == "cache":
				self.cache = {} if value.strip() in ("1", "yes", "true") else None
			elif attrib == "interval":
				self.interval = max(40, int(value))
			else:
				attribs.append((attrib, value))
		self.skinAttributes = attribs
		return Renderer.applySkin(self, desktop, parent)

	# ------------------------------------------------------------ timing

	def smooth(self):
		return U.settings().get("clock_smooth", True)

	def period(self):
		if self.mode in ("cycle", "bounce"):
			return self.interval or 90
		if self.mode == "second" and self.smooth():
			return self.interval or 250
		return 1000

	def frame_index(self, now=None):
		t = time() if now is None else now
		lt = localtime(t)
		if self.mode == "cycle":
			self.k = (self.k + 1) % self.count
			return self.k
		if self.mode == "bounce":
			n = max(1, 2 * self.count - 2)
			self.k = (self.k + 1) % n
			return self.k if self.k < self.count else n - self.k
		if self.mode == "second":
			sec = lt.tm_sec + ((t % 1) if self.smooth() else 0)
			frac = sec / 60.0
		elif self.mode == "minute":
			frac = (lt.tm_min + lt.tm_sec / 60.0) / 60.0
		else:
			frac = ((lt.tm_hour % 12) + lt.tm_min / 60.0) / 12.0
		return int(frac * self.count) % self.count

	def tick(self):
		if not self.instance or not self.visible:
			return
		idx = self.frame_index()
		if idx != self.index:
			self.index = idx
			try:
				if self.cache is not None:
					ptr = self.cache.get(idx)
					if ptr is None:
						ptr = self.cache[idx] = LoadPixmap(self.pattern % idx, cached=False)
				else:
					ptr = LoadPixmap(self.pattern % idx, cached=False)
				if ptr is not None:
					self.instance.setPixmap(ptr)
			except Exception as e:
				print("[MohammedFrames] %s" % e)
		if self.mode == "second" and not self.smooth():
			ms = int((1 - (time() % 1)) * 1000) + 5  # line up with the start of the next second
			self.timer.start(ms, True)
		else:
			self.timer.start(self.period(), True)

	# ------------------------------------------------------------ lifecycle

	def changed(self, what):
		pass  # driven by our own timer

	def postWidgetCreate(self, instance):
		self.index = -1

	def preWidgetRemove(self, instance):
		self.visible = False
		self.timer.stop()
		if self.cache is not None:
			self.cache = {}

	def onShow(self):
		Renderer.onShow(self)
		self.visible = True
		self.index = -1
		self.tick()

	def onHide(self):
		Renderer.onHide(self)
		self.visible = False
		self.timer.stop()
