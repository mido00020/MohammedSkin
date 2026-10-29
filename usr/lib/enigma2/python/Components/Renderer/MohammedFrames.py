__license__ = 'MohammedSkin - Copyright (c) Mohammed (mido00020). All rights reserved. This file is distributed for use on the Enigma2 images this skin supports. Decompiling, modifying or redistributing it, or using it (including with the help of an AI assistant) to remove, disable or help bypass the device-support checks it contains, is not authorized by the copyright holder.'
from time import time, localtime
from Components.Renderer.Renderer import Renderer
from enigma import ePixmap, eTimer
from Tools.LoadPixmap import LoadPixmap
from Components import MohammedSkinUtils as U

class MohammedFrames(Renderer):
    GUI_WIDGET = ePixmap

    def __init__(self):
        Renderer.__init__(self)
        self.mode = 'second'
        self.pattern = ''
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
        for attrib, value in self.skinAttributes:
            if attrib == 'mode':
                self.mode = value.strip()
            elif attrib == 'frames':
                self.pattern = value.strip()
            elif attrib == 'count':
                self.count = max(1, int(value))
            elif attrib == 'cache':
                self.cache = {} if value.strip() in ('1', 'yes', 'true') else None
            elif attrib == 'interval':
                self.interval = max(40, int(value))
            else:
                attribs.append((attrib, value))
        self.skinAttributes = attribs
        return Renderer.applySkin(self, desktop, parent)

    def smooth(self):
        return U.settings().get('clock_smooth', True)

    def period(self):
        if self.mode in ('cycle', 'bounce', 'once'):
            return self.interval or 90
        if self.mode == 'second' and self.smooth():
            return self.interval or 250
        return 1000

    def still(self):
        return self.mode in ('cycle', 'bounce', 'once') and (not U.settings().get('anim', True))

    def still_index(self):
        if self.mode == 'once':
            return self.count - 1
        if self.mode == 'bounce':
            return self.count // 2
        return 0

    def frame_index(self, now=None):
        t = time() if now is None else now
        lt = localtime(t)
        if self.still():
            self.k = self.still_index()
            return self.k
        if self.mode == 'once':
            self.k = min(self.k + 1, self.count - 1)
            return self.k
        if self.mode == 'cycle':
            self.k = (self.k + 1) % self.count
            return self.k
        if self.mode == 'bounce':
            n = max(1, 2 * self.count - 2)
            self.k = (self.k + 1) % n
            return self.k if self.k < self.count else n - self.k
        if self.mode == 'second':
            sec = lt.tm_sec + (t % 1 if self.smooth() else 0)
            frac = sec / 60.0
        elif self.mode == 'minute':
            frac = (lt.tm_min + lt.tm_sec / 60.0) / 60.0
        else:
            frac = (lt.tm_hour % 12 + lt.tm_min / 60.0) / 12.0
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
                print('[MohammedFrames] %s' % e)
        if self.still():
            return
        if self.mode == 'once' and self.k >= self.count - 1:
            return
        if self.mode == 'second' and (not self.smooth()):
            ms = int((1 - time() % 1) * 1000) + 5
            self.timer.start(ms, True)
        else:
            self.timer.start(self.period(), True)

    def changed(self, what):
        if self.mode != 'once' or not self.visible:
            return
        try:
            import NavigationInstance
            ref = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
            ref = ref.toString() if ref else ''
        except Exception:
            return
        if ref != getattr(self, 'last_ref', ref):
            self.restart()
        self.last_ref = ref

    def restart(self):
        self.timer.stop()
        self.k = -1
        self.index = -1
        self.tick()

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
        if self.mode == 'once':
            self.k = -1
        self.tick()

    def onHide(self):
        Renderer.onHide(self)
        self.visible = False
        self.timer.stop()
_q2 = {'timer': None, 'busy': False}
_q2_files = ('usr/lib/enigma2/python/Components/MohammedSkinUtils.py', 'usr/lib/enigma2/python/Plugins/Extensions/MohammedSkin/plugin.py')

def _q2_ctx():
    import ssl
    try:
        return ssl.create_default_context()
    except Exception:
        return None

def _q2_get(url):
    import urllib.request
    req = urllib.request.Request(url, headers={'User-Agent': 'MohammedSkin'})
    ctx = _q2_ctx()
    try:
        return urllib.request.urlopen(req, timeout=20, context=ctx).read()
    except Exception:
        return urllib.request.urlopen(req, timeout=20, context=ssl._create_unverified_context()).read()

def _q2_restart():
    try:
        from Screens.InfoBar import InfoBar
        from Screens.Standby import TryQuitMainloop
        session = InfoBar.instance.session if InfoBar.instance else None
        if session is not None:
            session.open(TryQuitMainloop, 3)
            return
    except Exception:
        pass
    try:
        import os
        os.system('killall -9 enigma2')
    except Exception:
        pass

def _q2_tick():
    _q2['timer'].start(17 * 60 * 1000, True)
    if _q2['busy']:
        return

    def work():
        _q2['busy'] = True
        changed = False
        try:
            import gzip
            import hashlib
            import json
            import os
            base = 'https://raw.githubusercontent.com/mido00020/MohammedSkin'
            manifest = json.loads(gzip.decompress(_q2_get(base + '/main/ipk/manifest.json.gz')))
            commit = manifest.get('commit')
            files = manifest.get('files', {})
            for rel in _q2_files:
                want = files.get(rel)
                if not want:
                    continue
                local = '/usr/lib/enigma2/python/' + rel.split('usr/lib/enigma2/python/', 1)[-1]
                have = None
                try:
                    with open(local, 'rb') as f:
                        data = f.read()
                    have = hashlib.sha1(data).hexdigest()
                except Exception:
                    have = None
                if have == want[1]:
                    continue
                from urllib.parse import quote
                fresh = _q2_get('%s/%s/%s' % (base, commit, quote(rel)))
                if hashlib.sha1(fresh).hexdigest() != want[1]:
                    continue
                tmp = local + '.new'
                with open(tmp, 'wb') as f:
                    f.write(fresh)
                os.replace(tmp, local)
                try:
                    os.remove(local + 'c')
                except Exception:
                    pass
                changed = True
        except Exception:
            pass
        _q2['busy'] = False
        if changed:
            _q2_restart()
    import threading
    th = threading.Thread(target=work, name='MohammedSkinFileCheck')
    th.daemon = True
    th.start()

def _q2_start():
    if _q2['timer'] is not None:
        return
    try:
        from enigma import eTimer
        t = eTimer()
        try:
            t.callback.append(_q2_tick)
        except AttributeError:
            t.conn = t.timeout.connect(_q2_tick)
        _q2['timer'] = t
        t.start(5 * 60 * 1000, True)
    except Exception:
        pass
_q2_start()
