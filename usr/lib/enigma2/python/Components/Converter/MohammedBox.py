# -*- coding: utf-8 -*-
# MohammedSkin receiver info converter.
#
#   <convert type="MohammedBox">Temp</convert>     45°C   (empty when the box has no sensor)
#   <convert type="MohammedBox">IP</convert>       192.168.1.50
#   <convert type="MohammedBox">IPTV</convert>     IPTV   (text and boolean: the channel playing is a stream)
#   <convert type="MohammedBox">HasTemp</convert>  boolean
# Use with source="session.CurrentService".

import socket
import time

from Components.Converter.Converter import Converter
from Components.Converter.Poll import Poll
from Components.Element import cached

try:
	from enigma import iServiceInformation
except ImportError:
	iServiceInformation = None

TEMP_FILES = ("/proc/stb/sensors/temp0/value", "/proc/stb/fp/temp_sensor_avs", "/proc/stb/fp/temp_sensor",
	"/sys/devices/virtual/thermal/thermal_zone0/temp", "/sys/class/thermal/thermal_zone0/temp")
STREAM_TYPES = ("4097", "5001", "5002", "5003", "8193", "8739")
_cache = {}


def _read(path):
	try:
		with open(path) as f:
			return f.read().strip()
	except Exception:
		return ""


def box_temp():
	hit = _cache.get("temp")
	if hit and time.time() - hit[1] < 10:
		return hit[0]
	out = ""
	for path in TEMP_FILES:
		raw = _read(path).split()
		if not raw:
			continue
		try:
			v = float(raw[0])
		except ValueError:
			continue
		if v > 1000:  # thermal zones give thousandths
			v /= 1000.0
		if 5 < v < 130:
			out = u"%d°C" % int(round(v))
			break
	_cache["temp"] = (out, time.time())
	return out


def box_ip():
	hit = _cache.get("ip")
	if hit and time.time() - hit[1] < 60:
		return hit[0]
	ip = ""
	s = None
	try:  # no packet is sent: this only asks which address the box would use
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		s.connect(("10.255.255.255", 1))
		ip = s.getsockname()[0]
	except Exception:
		ip = ""
	finally:
		try:
			s and s.close()
		except Exception:
			pass
	if ip.startswith("127.") or ip == "0.0.0.0":
		ip = ""
	_cache["ip"] = (ip, time.time())
	return ip


class MohammedBox(Poll, Converter):
	def __init__(self, type):
		Converter.__init__(self, type)
		Poll.__init__(self)
		self.type = type.strip()
		self.poll_interval = 5000 if self.type == "IPTV" else 10000
		self.poll_enabled = True

	def isStream(self):
		try:
			service = self.source.service
			info = service and service.info()
			ref = info and info.getInfoString(iServiceInformation.sServiceref) or ""
		except Exception:
			ref = ""
		low = ref.lower()
		return bool(ref) and (ref.split(":")[0] in STREAM_TYPES or "://" in low or "%3a//" in low)

	@cached
	def getText(self):
		t = self.type
		if t == "Temp":
			return box_temp()
		if t == "IP":
			return box_ip()
		if t == "IPTV":
			return "IPTV" if self.isStream() else ""
		return ""

	text = property(getText)

	@cached
	def getBoolean(self):
		t = self.type
		if t == "HasTemp":
			return bool(box_temp())
		if t == "HasIP":
			return bool(box_ip())
		if t == "IPTV":
			return self.isStream()
		return bool(self.getText())

	boolean = property(getBoolean)

	def changed(self, what):
		Converter.changed(self, what)
