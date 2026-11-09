# -*- coding: utf-8 -*-
# MohammedSkin: the programme picture behind the channel you are standing on in the channel list.
#
#   <widget source="ServiceEvent" render="MohammedRowArt" event="now" delay="350"
#           selection="/usr/share/enigma2/MohammedSkin/img/cl3_premium_sel.png" position="0,0" size="1,1" />
#
# The widget itself shows nothing. The picture (backdrop, else poster) is made into a picture of one
# list row and set as the list's selection picture, so the list itself draws it behind the selected
# row, wherever the row is on the page. While there is no picture (no event, nothing found, still
# loading, no python3-pillow) the normal selection picture given in "selection" is used.

from Components.Renderer.MohammedPoster import MohammedPoster
from Tools.LoadPixmap import LoadPixmap

from Components import MohammedSkinUtils as U


class MohammedRowArt(MohammedPoster):

	def __init__(self):
		MohammedPoster.__init__(self)
		self.kind = "backdrop"
		self.logo = False
		self.selection = ""
		self.rowheight = 0
		self.art = None

	def applySkin(self, desktop, parent):
		attribs = []
		for (attrib, value) in self.skinAttributes:
			if attrib == "selection":
				self.selection = value.strip()
			elif attrib == "rowheight":
				try:
					self.rowheight = int(value)
				except ValueError:
					pass
			else:
				attribs.append((attrib, value))
		self.skinAttributes = attribs
		ret = MohammedPoster.applySkin(self, desktop, parent)
		self.kind = "backdrop"
		self.logo = False
		return ret

	def postWidgetCreate(self, instance):
		instance.hide()
		MohammedPoster.postWidgetCreate(self, instance)

	def preWidgetRemove(self, instance):
		MohammedPoster.preWidgetRemove(self, instance)
		self.art = None

	# ------------------------------------------------------------ the channel list

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

	def rowSize(self, lst):
		try:
			w = lst.instance.size().width()
		except Exception:
			w = 0
		h = 0
		for name in ("ItemHeight", "itemHeight", "item_height"):
			try:
				h = int(getattr(lst, name, 0) or 0)
			except Exception:
				h = 0
			if h > 0:
				break
		return w, (h or self.rowheight)

	def setSelection(self, ptr):
		lst = self.serviceList()
		if lst is None or ptr is None:
			return False
		for name in ("setSelectionPicture", "setSelectionPixmap"):
			fn = getattr(lst.instance, name, None)
			if fn is None:
				continue
			try:
				fn(ptr)
			except Exception:
				continue
			try:
				lst.instance.invalidate()
			except Exception:
				pass
			return True
		return False

	def restore(self):
		if self.art is None:
			return
		self.art = None
		path = self.selection
		if not path:
			return
		lst = self.serviceList()
		if lst is not None and self.rowheight:
			h = self.rowSize(lst)[1]
			if h and h != self.rowheight:
				# a changed row size uses the resized copy the skin made of the same picture
				import os
				tuned = os.path.join(os.path.dirname(path), U.TUNE_DIR, "%s_h%d.png" % (os.path.splitext(os.path.basename(path))[0], h))
				if os.path.exists(tuned):
					path = tuned
		try:
			self.setSelection(LoadPixmap(U.to_s(path), cached=True))
		except Exception:
			pass

	# ------------------------------------------------------------ MohammedPoster hooks

	def useLogo(self):
		return False

	def showLogo(self):
		self.current = None
		self.hide()

	def showEntry(self, entry, key):
		path = entry.get("backdrop") or (getattr(self, "arabic", False) and entry.get("poster_ar")) or entry.get("poster")
		if not path:
			if not entry.get("partial"):
				self.hide()
			return
		self.display(path)

	def display(self, path):
		lst = self.serviceList()
		if lst is None:
			self.hide()
			return
		w, h = self.rowSize(lst)
		if w <= 0 or h <= 0:
			self.hide()
			return
		theme = U.load_themes().get(U.settings().get("theme", "red")) or {}
		key = self.current
		ready = U.row_art_async(path, w, h, theme.get("accent", "#C8102E"), theme.get("ink", "#060304"),
			lambda p, k=key: self.onArt(k, p))
		if ready:
			self.setArt(ready)
		else:
			self.restore()  # never leave the previous channel's picture behind this row while this one is made

	def onArt(self, key, path):
		if self.instance and key == self.current:
			if path:
				self.setArt(path)
			else:
				self.restore()

	def setArt(self, path):
		if path == self.art:
			return
		try:
			ptr = LoadPixmap(U.to_s(path), cached=False)
		except Exception:
			ptr = None
		if ptr is not None and self.setSelection(ptr):
			self.art = path
			self.shown = path
		else:
			self.restore()

	def hide(self):
		self.shown = None
		self.want = None
		if self.instance:
			self.instance.hide()
		self.restore()
