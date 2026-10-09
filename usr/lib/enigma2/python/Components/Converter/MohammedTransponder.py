# -*- coding: utf-8 -*-
# MohammedSkin: transponder details of the current channel, one field per widget.
#
#   <widget source="session.CurrentService" render="Label" ...>
#       <convert type="MohammedTransponder">Frequency</convert>
#   </widget>
#
#   Orbital      13.0°E / 7.0°W   (CABLE, TERR., IPTV for other sources)
#   Frequency    11900            (MHz)
#   Polarization H / V / L / R
#   SymbolRate   27500            (bandwidth for DVB-T)
#   FEC          2/3
#   Modulation   8PSK
#   System       S2 / S / C / T / T2
#   SatName      Nilesat/Eutelsat 7W
#   Line         11900 V 27500 2/3 8PSK
#   Caption:SR   caption that fits the tuner type ("SR", "BW", ...), empty when there is no data
#   HasData      boolean: tuned from a frontend (not IPTV / file)

from Components.Converter.Converter import Converter
from Components.Converter.Poll import Poll
from Components.Element import cached

try:
	from enigma import iServiceInformation
except ImportError:  # tests
	iServiceInformation = None

SAT_POL = {0: "H", 1: "V", 2: "L", 3: "R"}
SAT_FEC = {0: "Auto", 1: "1/2", 2: "2/3", 3: "3/4", 4: "5/6", 5: "7/8", 6: "8/9", 7: "3/5", 8: "4/5", 9: "9/10", 10: "6/7", 15: ""}
SAT_MOD = {0: "Auto", 1: "QPSK", 2: "8PSK", 3: "QAM16", 4: "16APSK", 5: "32APSK"}
SAT_SYS = {0: "S", 1: "S2"}
CAB_MOD = {0: "Auto", 1: "QAM16", 2: "QAM32", 3: "QAM64", 4: "QAM128", 5: "QAM256"}
CAB_FEC = {0: "Auto", 1: "1/2", 2: "2/3", 3: "3/4", 4: "5/6", 5: "7/8", 6: "8/9", 7: "3/5", 8: "4/5", 9: "9/10", 10: "6/7", 15: ""}
TER_BW = {0: "8MHz", 1: "7MHz", 2: "6MHz", 3: "Auto", 4: "5MHz", 5: "1.7MHz", 6: "10MHz"}
TER_MOD = {0: "QPSK", 1: "QAM16", 2: "QAM64", 3: "Auto", 4: "QAM256"}
TER_FEC = {0: "1/2", 1: "2/3", 2: "3/4", 3: "5/6", 4: "7/8", 5: "Auto", 6: "6/7", 7: "8/9", 8: "3/5", 9: "4/5"}

CAPTIONS = {
	"DVB-S": {"Orbital": "SAT", "Frequency": "FREQ", "SymbolRate": "SR", "FEC": "FEC", "Modulation": "MOD", "System": "SYS"},
	"DVB-C": {"Orbital": "SRC", "Frequency": "FREQ", "SymbolRate": "SR", "FEC": "FEC", "Modulation": "MOD", "System": "SYS"},
	"DVB-T": {"Orbital": "SRC", "Frequency": "FREQ", "SymbolRate": "BW", "FEC": "FEC", "Modulation": "MOD", "System": "SYS"},
	"ATSC": {"Orbital": "SRC", "Frequency": "FREQ", "SymbolRate": "", "FEC": "", "Modulation": "MOD", "System": "SYS"},
}


def orbital(pos):
	try:
		pos = int(pos)
	except (TypeError, ValueError):
		return ""
	if pos < 0 or pos > 3600:
		return ""
	if pos > 1800:
		return "%.1f\xb0W" % ((3600 - pos) / 10.0)
	return "%.1f\xb0E" % (pos / 10.0)


def mhz(freq, tuner):
	try:
		f = int(freq)
	except (TypeError, ValueError):
		return ""
	if f <= 0:
		return ""
	if tuner == "DVB-S":
		return str(int(round(f / 1000.0)))  # kHz
	if tuner == "DVB-C":
		return str(int(round(f / 1000.0))) if f < 10000000 else str(int(round(f / 1000000.0)))
	return str(int(round(f / 1000000.0)))  # Hz


def tuner_of(tp):
	t = str(tp.get("tuner_type", "") or "")
	for k in ("DVB-S", "DVB-C", "DVB-T", "ATSC"):
		if k in t:
			return k
	return ""


def fields(tp):
	"""Return a dict of display strings from raw transponder data (enigma's sTransponderData)."""
	out = dict.fromkeys(("Orbital", "Frequency", "Polarization", "SymbolRate", "FEC", "Modulation", "System", "SatName", "Tuner"), "")
	if not tp or not isinstance(tp, dict):
		return out
	tuner = tuner_of(tp)
	out["Tuner"] = tuner
	out["Frequency"] = mhz(tp.get("frequency"), tuner)
	if tuner == "DVB-S":
		out["Orbital"] = orbital(tp.get("orbital_position"))
		out["Polarization"] = SAT_POL.get(tp.get("polarization"), "")
		sr = tp.get("symbol_rate") or 0
		out["SymbolRate"] = str(int(sr) // 1000) if sr else ""
		out["FEC"] = SAT_FEC.get(tp.get("fec_inner"), "")
		out["Modulation"] = SAT_MOD.get(tp.get("modulation"), "")
		out["System"] = SAT_SYS.get(tp.get("system"), "S")
	elif tuner == "DVB-C":
		out["Orbital"] = "CABLE"
		sr = tp.get("symbol_rate") or 0
		out["SymbolRate"] = str(int(sr) // 1000) if sr else ""
		out["FEC"] = CAB_FEC.get(tp.get("fec_inner"), "")
		out["Modulation"] = CAB_MOD.get(tp.get("modulation"), "")
		out["System"] = "C2" if tp.get("system") == 1 else "C"
	elif tuner == "DVB-T":
		out["Orbital"] = "TERR."
		bw = tp.get("bandwidth")
		out["SymbolRate"] = TER_BW.get(bw, "") if isinstance(bw, int) and bw < 10 else ("%dMHz" % (bw // 1000000) if bw else "")
		out["FEC"] = TER_FEC.get(tp.get("code_rate_hp", tp.get("code_rate_lp")), "")
		out["Modulation"] = TER_MOD.get(tp.get("constellation"), "")
		out["System"] = "T2" if tp.get("system") == 1 else "T"
	elif tuner == "ATSC":
		out["Orbital"] = "ATSC"
		out["Modulation"] = {0: "Auto", 1: "QAM16", 2: "QAM32", 3: "QAM64", 4: "QAM128", 5: "QAM256", 6: "8VSB", 7: "16VSB"}.get(tp.get("modulation"), "")
		out["System"] = "ATSC"
	if out["FEC"] == "Auto" and tuner != "DVB-S":
		out["FEC"] = ""
	return out


class MohammedTransponder(Poll, Converter):
	def __init__(self, type):
		Converter.__init__(self, type)
		Poll.__init__(self)
		self.type = type.strip()
		self.poll_interval = 2000
		self.poll_enabled = True

	def _service_info(self):
		service = getattr(self.source, "service", None)
		if service is None:
			return None
		try:
			return service.info()
		except Exception:
			return None

	def _data(self):
		info = self._service_info()
		if info is None:
			return None, None
		tp = None
		try:
			tp = info.getInfoObject(iServiceInformation.sTransponderData)
		except Exception:
			tp = None
		return info, tp

	def _is_stream(self, info):
		try:
			ref = info.getInfoString(iServiceInformation.sServiceref) or ""
		except Exception:
			return False
		return "%3a//" in ref.lower() or "://" in ref

	@cached
	def getText(self):
		info, tp = self._data()
		if info is None:
			return ""
		f = fields(tp)
		if not f["Tuner"]:
			if self.type == "Orbital" and self._is_stream(info):
				return "IPTV"
			return ""
		if self.type.startswith("Caption:"):
			key = self.type.split(":", 1)[1]
			return CAPTIONS.get(f["Tuner"], {}).get(key, key)
		if self.type == "SatName":
			if f["Tuner"] != "DVB-S":
				return {"DVB-C": "Cable", "DVB-T": "Terrestrial"}.get(f["Tuner"], f["Tuner"])
			try:
				from Components.NimManager import nimmanager
				name = nimmanager.getSatName(int(tp.get("orbital_position")))
			except Exception:
				name = ""
			return name or f["Orbital"]
		if self.type == "Line":
			parts = [f["Frequency"], f["Polarization"], f["SymbolRate"], f["FEC"], f["Modulation"]]
			return " ".join(p for p in parts if p)
		return f.get(self.type, "")

	text = property(getText)

	@cached
	def getBoolean(self):
		info, tp = self._data()
		return bool(info is not None and fields(tp)["Tuner"])

	boolean = property(getBoolean)
