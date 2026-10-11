# -*- coding: utf-8 -*-
# MohammedSkin bitrate of the channel playing now (video and audio), measured by the image's bitrate module.
#
#   <widget source="session.CurrentService" render="Label" ...><convert type="MohammedBitrate">Both</convert></widget>
#
#   Video   8.4 Mb/s
#   Audio   192 kb/s
#   Both    8.4 Mb/s · 192 kb/s
# Shows nothing when the image has no bitrate module (bitratecalc, from the Bitrate viewer plugin) or for streams.

from Components.Converter.Converter import Converter
from Components.Element import cached
from enigma import iPlayableService, iServiceInformation, eTimer

try:
	from bitratecalc import eBitrateCalculator
except Exception:
	eBitrateCalculator = None


def _fmt(kbit):
	if not kbit:
		return ""
	return "%.1f Mb/s" % (kbit / 1000.0) if kbit >= 1000 else "%d kb/s" % kbit


class MohammedBitrate(Converter):
	def __init__(self, type):
		Converter.__init__(self, type)
		self.type = type.strip()
		self.video = 0
		self.audio = 0
		self.calcs = []
		self.timer = eTimer()
		try:
			self.timer.callback.append(self.start)
		except AttributeError:
			self.timer_conn = self.timer.timeout.connect(self.start)

	def _calc(self, pid, info, ref, buf, cb):
		"""Both kinds of the module: (pid, namespace, tsid, onid, refresh, buffer) and (pid, reference, refresh, buffer)."""
		try:
			c = eBitrateCalculator(pid, "%x" % info.getInfo(iServiceInformation.sNamespace), info.getInfo(iServiceInformation.sTSID),
				info.getInfo(iServiceInformation.sONID), 1000, buf)
		except Exception:
			try:
				c = eBitrateCalculator(pid, ref, 1000, buf)
			except Exception:
				return None
		try:
			c.callback.append(cb)
		except Exception:
			return None
		return c

	def start(self):
		self.stop()
		if eBitrateCalculator is None:
			return
		service = self.source.service
		info = service and service.info()
		if not info:
			return
		ref = info.getInfoString(iServiceInformation.sServiceref)
		if not ref or "%3a//" in ref.lower() or "://" in ref:
			return  # streams: nothing to measure
		vpid = info.getInfo(iServiceInformation.sVideoPID)
		apid = info.getInfo(iServiceInformation.sAudioPID)
		if vpid > 0:
			c = self._calc(vpid, info, ref, 1024 * 1024, self.gotVideo)
			c and self.calcs.append(c)
		if apid > 0:
			c = self._calc(apid, info, ref, 64 * 1024, self.gotAudio)
			c and self.calcs.append(c)

	def stop(self):
		self.calcs = []
		self.video = self.audio = 0

	def gotVideo(self, value, status=1):
		self.video = value if status else 0
		Converter.changed(self, (self.CHANGED_POLL,))

	def gotAudio(self, value, status=1):
		self.audio = value if status else 0
		Converter.changed(self, (self.CHANGED_POLL,))

	@cached
	def getText(self):
		if self.type == "Video":
			return _fmt(self.video)
		if self.type == "Audio":
			return _fmt(self.audio)
		parts = [x for x in (_fmt(self.video), _fmt(self.audio)) if x]
		return u"  ·  ".join(parts)

	text = property(getText)

	def changed(self, what):
		if what[0] == self.CHANGED_SPECIFIC and (what[1] == iPlayableService.evStart or (what[1] == iPlayableService.evUpdatedInfo and not self.calcs)):
			self.timer.start(800, True)
		elif what[0] == self.CHANGED_SPECIFIC and what[1] == iPlayableService.evEnd:
			self.stop()
		Converter.changed(self, what)
