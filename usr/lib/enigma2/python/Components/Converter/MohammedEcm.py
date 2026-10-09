# -*- coding: utf-8 -*-
# MohammedSkin softcam converter. Reads /tmp/ecm.info written by OSCam / NCam / CCcam.
#
#   <convert type="MohammedEcm">Cam</convert>          OSCam
#   <convert type="MohammedEcm">Server</convert>       cs.myserver.net
#   <convert type="MohammedEcm">Protocol</convert>     CCcam
#   <convert type="MohammedEcm">EcmTime</convert>      0.21 s
#   <convert type="MohammedEcm">Caid</convert>         0B00
#   <convert type="MohammedEcm">Line</convert>         cs.myserver.net  CCcam  0.21 s
#   <convert type="MohammedEcm">Short</convert>        0.21 s · 0B00 · cs.myserver.net
#   <convert type="MohammedEcm">Full</convert>         0.21 s · CCcam · CAID 0B00 · hop 1 · cs.myserver.net
#   <convert type="MohammedEcm">IsConnected</convert>  boolean (green / red dot)
#   <convert type="MohammedEcm">Keys</convert>         several lines: CAID / PID / provider, reader and protocol,
#                                                      ECM time and the control words (CW0 / CW1) as OSCam(-Emu) writes them
# Use with source="session.CurrentService".

import os
import re
import time

from Components.Converter.Converter import Converter
from Components.Converter.Poll import Poll
from Components.Element import cached

ECM_FILES = ("/tmp/ecm.info", "/tmp/ecm0.info")
STALE_SECONDS = 120
CAMS = (("oscam", "OSCam"), ("ncam", "NCam"), ("cccam", "CCcam"), ("gbox", "GBox"),
	("wicardd", "Wicardd"), ("mgcamd", "MGcamd"), ("cvs", "CVS"), ("vizcam", "VizCam"))
PROTOCOLS = {"cccam": "CCcam", "newcamd": "Newcamd", "camd35": "Camd35", "cs378x": "Camd35 TCP",
	"cs357x": "Camd35", "radegast": "Radegast", "gbox": "GBox", "mgcamd": "MGcamd",
	"internal": "Card", "emu": "Emu", "pcsc": "Card", "mouse": "Card", "smargo": "Card",
	"ghttp": "GHttp", "scam": "Scam", "constcw": "ConstCW"}

_cam_cache = ["", 0.0]


def running_cam():
	now = time.time()
	if now - _cam_cache[1] < 10:
		return _cam_cache[0]
	name = ""
	try:
		for pid in os.listdir("/proc"):
			if not pid.isdigit():
				continue
			try:
				with open("/proc/%s/comm" % pid) as f:
					comm = f.read().strip().lower()
			except Exception:
				continue
			for key, label in CAMS:
				if comm.startswith(key):
					name = label
					break
			if name:
				break
	except Exception:
		pass
	_cam_cache[0], _cam_cache[1] = name, now
	return name


def read_ecm():
	"""Return dict with server, protocol, time, caid, hops — or {} when nothing fresh."""
	for path in ECM_FILES:
		try:
			if time.time() - os.path.getmtime(path) > STALE_SECONDS:
				continue
			with open(path) as f:
				lines = f.read().splitlines()
		except Exception:
			continue
		d = {}
		for line in lines:
			if ":" not in line:
				continue
			k, v = line.split(":", 1)
			d[k.strip().lower()] = v.strip()
		out = {}
		# server
		server = d.get("from") or d.get("address") or d.get("reader") or ""
		src = d.get("source", "")
		m = re.search(r"\((\w+) at ([^)]+)\)", src)  # "net (cccam at host:port)"
		if m:
			out["protocol"] = m.group(1)
			server = server or m.group(2)
		server = re.sub(r"^\s*(?:net|emu)\s*", "", server)
		if server.lower() in ("local", "cache", "cache1", "cache2", "cache3"):
			server = server.capitalize()
		out["server"] = server.split(":")[0] if server.count(":") == 1 else server
		proto = d.get("protocol") or out.get("protocol") or d.get("using") or ""
		proto = proto.strip().lower()
		if proto.startswith("cccam"):
			proto = "cccam"
		first = proto.split()[0] if proto else ""
		out["protocol"] = PROTOCOLS.get(first, first.capitalize())
		# ecm time: "0.123" or "123 msec" or "0.123 s"
		t = d.get("ecm time", "")
		m = re.search(r"([\d.]+)\s*(msec|ms)?", t)
		if m:
			try:
				val = float(m.group(1))
				if m.group(2) or val > 20:
					val /= 1000.0
				out["time"] = "%.2f s" % val
			except ValueError:
				pass
		caid = d.get("caid", "")
		out["caid"] = caid.replace("0x", "").upper().zfill(4) if caid else ""
		out["hops"] = d.get("hops", "")
		if out.get("server") or out.get("time"):
			return out
	return {}


def read_keys():
	"""All of ecm.info in a few clear lines, with the control words (what OSCam-Emu users look at)."""
	for path in ECM_FILES:
		try:
			if time.time() - os.path.getmtime(path) > STALE_SECONDS:
				continue
			with open(path) as f:
				lines = f.read().splitlines()
		except Exception:
			continue
		d = {}
		for line in lines:
			if ":" in line:
				k, v = line.split(":", 1)
				d.setdefault(k.strip().lower(), v.strip())
		if not d:
			continue
		e = read_ecm()
		out = []
		ids = [("CAID", d.get("caid", "")), ("PID", d.get("pid", "")), ("Prov", d.get("prov", "") or d.get("provider", "")), ("ChID", d.get("chid", ""))]
		out.append("   ".join("%s %s" % (k, v.replace("0x", "").upper()) for k, v in ids if v))
		who = [d.get("reader", ""), e.get("protocol", "") or d.get("protocol", ""), d.get("from", "") or d.get("address", "")]
		out.append("   ".join(x for x in who if x))
		more = [("ECM", e.get("time", "")), ("hops", d.get("hops", ""))]
		out.append("   ".join("%s %s" % (k, v) for k, v in more if v))
		for k in ("cw0", "cw1"):
			if d.get(k):
				out.append("%s  %s" % (k.upper(), d[k]))
		return "\n".join(x for x in out if x.strip())
	return ""


class MohammedEcm(Poll, Converter):
	def __init__(self, type):
		Converter.__init__(self, type)
		Poll.__init__(self)
		self.type = type.strip()
		self.poll_interval = 2000
		self.poll_enabled = True

	@cached
	def getText(self):
		t = self.type
		if t == "Cam":
			return running_cam()
		if t == "Keys":
			return read_keys()
		e = read_ecm()
		if t == "Server":
			return e.get("server", "")
		if t == "Protocol":
			return e.get("protocol", "")
		if t == "EcmTime":
			return e.get("time", "")
		if t == "Caid":
			return e.get("caid", "")
		if t == "Line":
			return "  ".join(x for x in (e.get("server"), e.get("protocol"), e.get("time")) if x)
		if t == "Short":  # narrow places: time, CAID and server
			return u"  \u00b7  ".join(x for x in (e.get("time"), e.get("caid"), e.get("server")) if x)
		if t == "Full":  # everything in one clear line
			hops = e.get("hops", "")
			return u"  \u00b7  ".join(x for x in (e.get("time"), e.get("protocol"), "CAID " + e["caid"] if e.get("caid") else "",
				("hop " + hops) if hops and hops != "0" else "", e.get("server")) if x)  # server last: a long name is cut, never the time
		return ""

	text = property(getText)

	@cached
	def getBoolean(self):
		if self.type == "IsConnected":
			return bool(read_ecm())
		if self.type == "NotConnected":
			return not read_ecm()
		return bool(self.getText())

	boolean = property(getBoolean)

	def changed(self, what):
		Converter.changed(self, what)
