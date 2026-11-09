# -*- coding: utf-8 -*-
# MohammedSkin: a picture behind every channel in the channel list.
#
#   <widget source="ServiceEvent" render="MohammedRowsArt" row="/usr/share/enigma2/MohammedSkin/img/cl3_picrows_row.png"
#           rowheight="100" position="<same as the list>" size="<same as the list>" alphatest="blend" zPosition="2" />
#
# Placed exactly behind the (transparent) list, it draws one picture of the visible page: each
# channel's programme picture (backdrop, else poster) in its own row, fading into the skin's dark
# colour under the channel name. A channel with no picture gets its logo (picon) the same way, and
# a channel without either gets the skin's plain row. Pictures are remembered, so a page shows at
# once when you come back to it, and they are made again when the programme changes.
# Needs python3-pillow; without it the widget stays empty and the list looks like a plain list.

import os
import hashlib

from Components.Renderer.Renderer import Renderer
from enigma import ePixmap, eTimer, eEPGCache, eServiceReference
from Tools.LoadPixmap import LoadPixmap

from Components import MohammedSkinUtils as U


def _timer(fn):
	t = eTimer()
	try:
		t.callback.append(fn)
	except Exception:
		t.conn = t.timeout.connect(fn)
	return t


class MohammedRowsArt(Renderer):
	GUI_WIDGET = ePixmap

	def __init__(self):
		Renderer.__init__(self)
		self.row = ""
		self.rowheight = 0
		self.delay = 250
		self.items = {}      # service -> (programme key, picture or "") once known
		self.busy = {}       # service -> programme key being made
		self.page = None  # (width, row height, rows, [services])
		self.sig = None      # page currently shown
		self.making = None   # page being made
		self.timer = _timer(self.refresh)
		self.drawTimer = _timer(self.compose)

	def applySkin(self, desktop, parent):
		attribs = []
		for (attrib, value) in self.skinAttributes:
			if attrib == "row":
				self.row = value.strip()
			elif attrib == "rowheight":
				try:
					self.rowheight = int(value)
				except ValueError:
					pass
			elif attrib == "delay":
				try:
					self.delay = max(0, int(value))
				except ValueError:
					pass
			else:
				attribs.append((attrib, value))
		self.skinAttributes = attribs
		return Renderer.applySkin(self, desktop, parent)

	def postWidgetCreate(self, instance):
		self.sig = None
		self.changed((self.CHANGED_DEFAULT,))

	def preWidgetRemove(self, instance):
		self.timer.stop()
		self.drawTimer.stop()
		self.sig = None

	def changed(self, what):
		if self.instance:
			self.timer.start(self.delay, True)

	# ------------------------------------------------------------ the list

	def serviceList(self):
		try:
			from Screens.InfoBar import InfoBar
			cs = InfoBar.instance and InfoBar.instance.servicelist
			lst = getattr(cs, "servicelist", None)
			if lst is not None and getattr(lst, "instance", None) is not None:
				return lst
		except Exception:
			pass
		return None

	def layout(self, lst):
		h = 0
		for name in ("ItemHeight", "itemHeight"):
			try:
				h = int(getattr(lst, name, 0) or 0)
			except Exception:
				h = 0
			if h > 0:
				break
		h = h or self.rowheight
		size = self.instance.size()
		w, total = size.width(), size.height()
		if h <= 0 or w <= 0:
			return None
		n = max(1, total // h)
		try:
			idx = int(lst.getCurrentIndex())
		except Exception:
			idx = 0
		top = None
		try:
			top = int(lst.instance.getTopIndex())  # OpenATV: the list says where its page starts
		except Exception:
			top = None
		if top is None or top < 0 or not (top <= idx < top + n):
			top = idx - idx % n  # the list turns whole pages (enigma2's own rule)
		return w, h, n, top

	def refresh(self):
		if not self.instance:
			return
		lst = self.serviceList()
		if lst is None:
			return
		lay = self.layout(lst)
		if lay is None:
			return
		w, h, n, top = lay
		try:
			refs = lst.getList()[top:top + n]
		except Exception:
			return
		self.page = (w, h, n, refs)
		if len(self.items) > 600:
			self.items = {}
		for ref in refs:
			self.want(ref, w, h)
		self.compose()

	# ------------------------------------------------------------ one channel

	def theme(self):
		t = U.load_themes().get(U.settings().get("theme", "red")) or {}
		return t.get("accent", "#C8102E"), t.get("ink", "#060304")

	def want(self, ref, w, h):
		try:
			key = ref.toString()
		except Exception:
			return
		if ref.flags & (eServiceReference.isMarker | eServiceReference.isDirectory):
			self.items[key] = ("", "")
			return
		name = ""
		try:
			from ServiceReference import ServiceReference
			name = ServiceReference(ref).getServiceName() or ""
		except Exception:
			pass
		event = None
		try:
			event = eEPGCache.getInstance().lookupEventTime(ref, -1)
		except Exception:
			event = None
		q = None
		s = U.settings()
		if s.get("posters", True) or s.get("backdrops", True):
			try:
				if not U.adult_event(event, name):
					q = U.event_query(event, ref, name)
			except Exception:
				q = None
		pkey = "%s|%dx%d" % (q["key"] if q else "logo", w, h)
		have = self.items.get(key)
		if (have and have[0] == pkey) or self.busy.get(key) == pkey:
			return
		self.busy[key] = pkey
		if q is None:
			self.useLogo(key, pkey, ref, w, h)
			return
		entry = U.cached(q["key"])
		if entry is None or entry.get("partial"):
			got = U.request(q["title"], q["year"], q["kind"], lambda e, k=key, p=pkey, r=ref: self.onEntry(k, p, r, e, w, h),
				arabic=q.get("arabic", False), extra=q.get("extra", ()), hint=q.get("hint"))
			entry = got or entry
		if entry is not None:
			self.onEntry(key, pkey, ref, entry, w, h)

	def onEntry(self, key, pkey, ref, entry, w, h):
		if self.busy.get(key) != pkey and (self.items.get(key) or ("",))[0] != pkey:
			return
		s = U.settings()
		path = (s.get("backdrops", True) and entry.get("backdrop")) or (s.get("posters", True) and entry.get("poster")) or None
		if not path:
			if entry.get("partial"):
				return  # the poster or backdrop is still coming
			self.useLogo(key, pkey, ref, w, h)
			return
		acc, ink = self.theme()
		U.in_background(lambda: U.row_art(path, w, h, acc, ink, frame=False),
			lambda res, k=key, p=pkey, r=ref: self.made(k, p, r, res, w, h, entry.get("partial")))

	def useLogo(self, key, pkey, ref, w, h):
		picon = U.picon_path(ref)
		if not picon:
			self.made(key, pkey, ref, "", w, h)
			return
		acc, ink = self.theme()
		U.in_background(lambda: U.picon_art(picon, w, h, acc, ink),
			lambda res, k=key, p=pkey, r=ref: self.made(k, p, r, res or "", w, h))

	def made(self, key, pkey, ref, path, w, h, partial=False):
		if path is None:
			path = ""
		if not path and not partial:
			if self.busy.get(key) == pkey and (self.items.get(key) or ("",))[0] != pkey + "+logo":
				# nothing from the picture: the logo instead
				self.items[key] = (pkey + "+logo", "")
				self.useLogo(key, pkey, ref, w, h)
				return
		self.items[key] = (pkey, path)
		if not partial:
			self.busy.pop(key, None)
		self.drawTimer.start(120, True)

	# ------------------------------------------------------------ the page

	def defaultRow(self, h):
		path = self.row
		if path and self.rowheight and h != self.rowheight:
			tuned = os.path.join(os.path.dirname(path), U.TUNE_DIR, "%s_h%d.png" % (os.path.splitext(os.path.basename(path))[0], h))
			if os.path.exists(tuned):
				path = tuned
		return path

	def compose(self):
		if not self.instance or not self.page:
			return
		w, h, n, refs = self.page
		arts = []
		for ref in refs:
			try:
				arts.append((self.items.get(ref.toString()) or ("", ""))[1])
			except Exception:
				arts.append("")
		row = self.defaultRow(h)
		sig = "%d|%d|%d|%s|%s|%d" % (w, h, n, row, "|".join(arts), len(refs))
		if sig == self.sig or sig == self.making:
			return
		out = os.path.join(U.CACHE_DIR, "rows_%s.png" % hashlib.md5(sig.encode("utf-8")).hexdigest())
		if os.path.exists(out):
			self.showPage(sig, out)
			return
		self.making = sig
		U.in_background(lambda: U.rows_page(arts, w, h, n, row, out), lambda res, s=sig: self.pageMade(s, res))

	def pageMade(self, sig, path):
		if self.making == sig:
			self.making = None
		if path and self.instance:
			self.showPage(sig, path)
		self.drawTimer.start(50, True)  # something may have arrived while this page was made

	def showPage(self, sig, path):
		try:
			ptr = LoadPixmap(U.to_s(path), cached=False)
		except Exception:
			ptr = None
		if ptr is None:
			return
		self.instance.setPixmap(ptr)
		self.instance.show()
		self.sig = sig
