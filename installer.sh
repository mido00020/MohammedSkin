#!/bin/sh
# MohammedSkin online installer / updater
# Works on OpenViX, OpenBlackHole, OpenATV, PurE2 and EGAMI (Enigma2).
#   wget -q --no-check-certificate "https://raw.githubusercontent.com/mido00020/MohammedSkin/main/installer.sh" -O - | /bin/sh

BASE="https://raw.githubusercontent.com/mido00020/MohammedSkin/main"

# colours only on a real terminal (plain text when the output is piped or logged)
if [ -t 1 ]; then
	E=$(printf '\033')
	R="$E[1;31m"; G="$E[1;32m"; Y="$E[1;33m"; B="$E[1;34m"; M="$E[1;35m"; C="$E[1;36m"; W="$E[1;37m"; N="$E[0m"
else
	R=""; G=""; Y=""; B=""; M=""; C=""; W=""; N=""
fi
ok() { echo "${G}[ OK ]${N} $*"; }
info() { echo "${C}[ .. ]${N} $*"; }
warn() { echo "${Y}[ !! ]${N} $*"; }
err() { echo "${R}[ERR ]${N} $*"; }

echo ""
printf '%s\n' "$R"'  __  __       _                                          _ '"$N"
printf '%s\n' "$Y"' |  \/  | ___ | |__   __ _ _ __ ___  _ __ ___   ___  __| |'"$N"
printf '%s\n' "$G"' | |\/| |/ _ \| '\''_ \ / _` | '\''_ ` _ \| '\''_ ` _ \ / _ \/ _` |'"$N"
printf '%s\n' "$C"' | |  | | (_) | | | | (_| | | | | | | | | | |  __/ (_| |'"$N"
printf '%s\n' "$B"' |_|  |_|\___/|_| |_|\__,_|_| |_| |_|_| |_| |_|\___|\__,_|'"$N"
printf '%s\n' "$M"'           ____  _  _____ _   _ '"$N"
printf '%s\n' "$M"'          / ___|| |/ /_ _| \ | |'"$N"
printf '%s\n' "$M"'          \___ \| '\'' / | ||  \| |'"$N"
printf '%s\n' "$M"'           ___) | . \ | || |\  |'"$N"
printf '%s\n' "$M"'          |____/|_|\_\___|_| \_|'"$N"
echo ""
echo "${W}        MohammedSkin - online installer${N}"
echo "${C}  ----------------------------------------------${N}"

# ---------------------------------------------------------------- which image is this?
value() {
	# value <file> <key>  ->  value of key=... without quotes
	[ -f "$1" ] || return 1
	sed -n "s/^$2[ ]*=[ ]*//p" "$1" | head -n 1 | tr -d "'\"\r"
}

DISTRO=$(value /usr/lib/enigma.info distro)
[ -z "$DISTRO" ] && DISTRO=$(value /etc/image-version distro)
[ -z "$DISTRO" ] && DISTRO=$(value /etc/image-version creator)
[ -z "$DISTRO" ] && [ -f /etc/issue ] && DISTRO=$(head -n 1 /etc/issue | sed 's/Welcome to //' | awk '{print $1}')
[ -z "$DISTRO" ] && [ -f /etc/bhversion ] && DISTRO=openbh
VERSION=$(value /usr/lib/enigma.info imageversion)
[ -z "$VERSION" ] && VERSION=$(value /etc/image-version version)

case "$(echo "$DISTRO" | tr 'A-Z' 'a-z' | tr -d ' _-')" in
	openvix*|vix) IMAGE="OpenViX" ;;
	openbh*|openblackhole*|blackhole*) IMAGE="OpenBlackHole" ;;
	openatv*) IMAGE="OpenATV" ;;
	pure2*) IMAGE="PurE2" ;;
	egami*) IMAGE="EGAMI" ;;
	*) IMAGE="" ;;
esac

if [ -n "$IMAGE" ]; then
	ok "Image: ${W}$IMAGE ${VERSION}${N}  (supported)"
else
	info "Image: ${DISTRO:-unknown} ${VERSION}"
	echo "This image is not on the tested list. The skin adapts itself anyway,"
	echo "the image name in the infobar is left out."
fi

if [ ! -d /usr/lib/enigma2/python ] || ! command -v opkg >/dev/null 2>&1; then
	err "this does not look like an Enigma2 receiver (no enigma2 python or opkg)."
	exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
	err "python3 not found. MohammedSkin needs a Python 3 image."
	exit 1
fi

# ---------------------------------------------------------------- room for the download
# The poster cache lives in RAM (/tmp): empty it first so the receiver has memory for the update.
rm -rf /tmp/MohammedSkin/* /tmp/enigma2-skin-mohammedskin*.ipk 2>/dev/null
sync
echo 3 > /proc/sys/vm/drop_caches 2>/dev/null

free_kb() {
	df -Pk "$1" 2>/dev/null | awk 'NR==2 {print $4}'
}

# download and unpack where there is room: RAM first, then a hard disk or USB stick
WORK=""
for d in /tmp /media/hdd /media/usb /media/mmc; do
	[ -d "$d" ] && [ -w "$d" ] || continue
	f=$(free_kb "$d")
	[ -n "$f" ] && [ "$f" -gt 100000 ] && { WORK="$d"; break; }
done
if [ -z "$WORK" ]; then
	err "not enough free memory or disk space to download the update (about 100 MB needed)."
	echo "Free some space (or plug in a USB stick) and try again."
	exit 1
fi
IPK="$WORK/enigma2-skin-mohammedskin.ipk"
OPKG_TMP="$WORK/mohammedskin-opkg"
mkdir -p "$OPKG_TMP"

FLASH=$(free_kb /usr/share/enigma2)
info "Free space: download area $(free_kb "$WORK") kB, receiver flash ${FLASH:-?} kB"
if [ -n "$FLASH" ] && [ "$FLASH" -lt 30000 ]; then
	warn "little free space on the receiver (${FLASH} kB). The update may not fit."
fi

# ---------------------------------------------------------------- download

FMODE=""
fetch() {
	rm -f "$2"
	# remember which way worked, so the next files do not repeat the ones that failed
	if [ "$FMODE" != "nocheck" ] && wget -q -T 30 "$1" -O "$2" 2>/dev/null && [ -s "$2" ]; then
		FMODE="check"
		return 0
	fi
	if wget -q -T 30 --no-check-certificate "$1" -O "$2" 2>/dev/null && [ -s "$2" ]; then
		FMODE="nocheck"
		return 0
	fi
	if command -v curl >/dev/null 2>&1 && curl -kfsSL --max-time 120 "$1" -o "$2" && [ -s "$2" ]; then
		return 0
	fi
	rm -f "$2"
	return 1
}

VER=""
if fetch "$BASE/version.txt" /tmp/mohammedskin_version.txt; then
	VER=$(head -n 1 /tmp/mohammedskin_version.txt | tr -d '\r\n ')
	rm -f /tmp/mohammedskin_version.txt
fi
info "Latest version: ${W}${VER:-unknown}${N}"

# ---------------------------------------------------------------- quick update
# An installed skin keeps the list of its files (.manifest.json). Only the files that changed since
# then are downloaded and replaced; the whole package is fetched only for a first install or a big change.
SK=/usr/share/enigma2/MohammedSkin
quick_update() {
	[ -f "$SK/.installed" ] && [ -f "$SK/.manifest.json" ] || return 1
	fetch "$BASE/ipk/manifest.json.gz?t=$(date +%s)" "$WORK/mohammedskin_manifest.json.gz" || return 1
	python3 -E - "$WORK/mohammedskin_manifest.json.gz" "$WORK/mohammedskin-quick" "$SK/.manifest.json" <<'PY'
import gzip, hashlib, http.client, json, os, re, shutil, ssl, sys, time
new = json.loads(gzip.open(sys.argv[1]).read().decode("utf-8"))
stage, local = sys.argv[2], sys.argv[3]
old = json.load(open(local)).get("files", {})
files = new["files"]
ROOT = os.environ.get("MS_ROOT", "")  # only for testing
regen = re.compile(r"usr/share/enigma2/MohammedSkin/clocks/[^/]+/(?!red/|common/)[^/]+/")  # remade on the box when needed


def present(p):
	a = ROOT + "/" + p
	return os.path.exists(a) or (p.endswith(".py") and os.path.exists(a + "c"))


get = []
for p, (size, sha) in files.items():
	if p.startswith("CONTROL/"):
		get.append(p)
	elif old.get(p) != [size, sha]:
		get.append(p)
	elif not present(p) and not regen.match(p) and not p.endswith("/preview.png"):
		get.append(p)
gone = [p for p in old if p not in files and not p.startswith("CONTROL/")]
total = sum(files[p][0] for p in get)
print("Changed files: %d (%d kB), removed: %d" % (len(get) - 1, total // 1024, len(gone)))
if len(get) > 2500 or total > 40 * 1024 * 1024:
	print("Big update: the whole package is downloaded instead.")
	sys.exit(2)
shutil.rmtree(stage, ignore_errors=True)
os.makedirs(stage)
host = os.environ.get("MS_HOST", "raw.githubusercontent.com")
path0 = "/mido00020/MohammedSkin/%s/" % new["commit"]
import threading
TL = threading.local()


def connect(verify):
	if os.environ.get("MS_HOST"):
		return http.client.HTTPConnection(host, timeout=30)
	ctx = ssl.create_default_context() if verify else ssl._create_unverified_context()
	return http.client.HTTPSConnection(host, timeout=30, context=ctx)


def slow_get(url):
	import urllib.request
	ctx = ssl._create_unverified_context()
	return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "MohammedSkin"}), timeout=30, context=None if url.startswith("http:") else ctx).read()


def fetch_one(p):
	from urllib.parse import quote
	for attempt in range(5):
		try:
			if attempt >= 3:  # plain request that follows redirects
				data = slow_get(("http://" if os.environ.get("MS_HOST") else "https://") + host + path0 + quote(p))
				if hashlib.sha1(data).hexdigest() == files[p][1]:
					return data
				continue
			if getattr(TL, "c", None) is None:
				TL.c = connect(attempt < 2)
			TL.c.request("GET", path0 + quote(p), headers={"Connection": "keep-alive", "User-Agent": "MohammedSkin"})
			r = TL.c.getresponse()
			data = r.read()
			if r.status == 200 and hashlib.sha1(data).hexdigest() == files[p][1]:
				return data
		except Exception:
			pass
		try:
			TL.c.close()
		except Exception:
			pass
		TL.c = None
		time.sleep(1)
	raise RuntimeError("download failed: " + p)


def grab(p):
	data = fetch_one(p)
	d = os.path.join(stage, p)
	os.makedirs(os.path.dirname(d), exist_ok=True)
	open(d, "wb").write(data)


from concurrent.futures import ThreadPoolExecutor
done = 0
try:
	with ThreadPoolExecutor(max_workers=6) as ex:
		for _ in ex.map(grab, get):
			done += 1
			if done % 50 == 0:
				print("  %d / %d" % (done, len(get)))
except Exception as e:
	raise SystemExit(str(e))
# everything is here and checked: put it in place
for p in get:
	if p.startswith("CONTROL/"):
		continue
	a = ROOT + "/" + p
	os.makedirs(os.path.dirname(a), exist_ok=True)
	tmp = a + ".msnew"
	shutil.copyfile(os.path.join(stage, p), tmp)
	os.replace(tmp, a)
	if p.endswith(".py") and os.path.exists(a + "c"):
		os.remove(a + "c")
for p in gone:
	for a in (ROOT + "/" + p, ROOT + "/" + p + "c" if p.endswith(".py") else None):
		if a and os.path.isfile(a):
			os.remove(a)
PY
	rc=$?
	[ $rc -eq 0 ] || { rm -rf "$WORK/mohammedskin-quick"; return $rc; }
	rm -f "$SK/.installed"
	sh "$WORK/mohammedskin-quick/CONTROL/postinst" configure
	rm -rf "$WORK/mohammedskin-quick"
	[ -f "$SK/.installed" ] || return 1
	python3 -E -c "import gzip,json,sys;m=json.loads(gzip.open(sys.argv[1]).read());json.dump({'version':m['version'],'files':m['files']},open(sys.argv[2],'w'))" "$WORK/mohammedskin_manifest.json.gz" "$SK/.manifest.json"
	rm -f "$WORK/mohammedskin_manifest.json.gz"
	return 0
}

if quick_update; then
	echo "${G}  ----------------------------------------------${N}"
	echo "${G}  MohammedSkin ${VER} updated (changed files only)${N}"
	echo "${G}  ----------------------------------------------${N}"
	info "Restarting the GUI ..."
	sync
	sleep 1
	killall -9 enigma2 >/dev/null 2>&1
	pkill -9 -f /usr/bin/enigma2 >/dev/null 2>&1
	[ -x /etc/init.d/enigma2 ] && /etc/init.d/enigma2 restart >/dev/null 2>&1 &
	exit 0
fi
rm -rf "$WORK/mohammedskin-quick"

info "Downloading the package ..."
if ! fetch "$BASE/ipk/enigma2-skin-mohammedskin_all.ipk" "$IPK"; then
	err "download failed. Check the internet connection."
	exit 1
fi

# ---------------------------------------------------------------- install

info "Checking the download ..."
# the package must match the checksum published with it (a changed or broken file is refused)
if fetch "$BASE/ipk/enigma2-skin-mohammedskin_all.ipk.sha256" /tmp/mohammedskin.sha256; then
	WANT=$(head -c 64 /tmp/mohammedskin.sha256)
	rm -f /tmp/mohammedskin.sha256
	GOT=$(python3 -E -c "import hashlib,sys;h=hashlib.sha256();f=open(sys.argv[1],'rb');[h.update(b) for b in iter(lambda:f.read(1<<20),b'')];print(h.hexdigest())" "$IPK")
	if [ "$WANT" != "$GOT" ]; then
		rm -f "$IPK"
		err "the downloaded package does not match its checksum. Try the update again in a few minutes."
		exit 1
	fi
	ok "Checksum OK"
fi
# the download must be a whole package (a cut connection leaves half a file); the checksum above already proves it
if [ -z "$GOT" ] && ! python3 -E - "$IPK" <<'PY'
import sys, tarfile
f = open(sys.argv[1], "rb")
if f.read(8) != b"!<arch>\n":
	sys.exit(1)
names = []
while True:
	h = f.read(60)
	if len(h) < 60:
		break
	name, size = h[:16].decode().strip().rstrip("/"), int(h[48:58])
	names.append(name)
	if name.startswith("data.tar"):
		with tarfile.open(fileobj=f, mode="r|gz") as t:
			for m in t:
				pass
		break
	f.seek(size + (size & 1), 1)
if "control.tar.gz" not in names or not any(n.startswith("data.tar") for n in names):
	sys.exit(1)
PY
then
	rm -f "$IPK"
	err "the download is incomplete (connection cut). Try the update again."
	exit 1
fi

# unpack the package straight into place with python (fallback when opkg fails)
python_install() {
	python3 -E - "$IPK" <<'PY'
import os, sys, tarfile
f = open(sys.argv[1], "rb")
f.read(8)
ctl = None
while True:
	h = f.read(60)
	if len(h) < 60:
		break
	name, size = h[:16].decode().strip().rstrip("/"), int(h[48:58])
	if name.startswith("control.tar"):
		import io
		ctl = tarfile.open(fileobj=io.BytesIO(f.read(size)), mode="r:gz")
		if size & 1:
			f.read(1)
		continue
	if name.startswith("data.tar"):
		with tarfile.open(fileobj=f, mode="r|gz") as t:
			for m in t:
				if m.name.lstrip("./").startswith("usr/") and not m.isdir():
					t.extract(m, "/")
		break
	f.seek(size + (size & 1), 1)
if ctl:
	for m in ctl.getmembers():
		if m.name.endswith("postinst"):
			open("/tmp/mohammedskin_postinst", "wb").write(ctl.extractfile(m).read())
PY
	[ -f /tmp/mohammedskin_postinst ] && sh /tmp/mohammedskin_postinst configure
	rm -f /tmp/mohammedskin_postinst
	[ -f /usr/share/enigma2/MohammedSkin/.installed ]
}

# free room on the receiver first: colours and clock frames made on the box are made again when needed
SK=/usr/share/enigma2/MohammedSkin
if [ -d "$SK" ]; then
	for t in purple emerald orange rose sky; do rm -rf "$SK/themes/$t" "$SK/themes/$t.part"; done
	for c in "$SK"/clocks/*/; do
		for d in "$c"*/; do
			case "$(basename "$d")" in red|common) ;; *) find "$d" -type f ! -name 'preview.*' -exec rm -f {} + 2>/dev/null ;; esac
		done
	done
	rm -rf "$SK/img/tune" "$SK"/themes/*.part
	find "$SK" -name '*.part' -o -name '.opkg*' 2>/dev/null | xargs rm -rf 2>/dev/null
fi
sync
INODES=$(df -Pi /usr/share/enigma2 2>/dev/null | awk 'NR==2 {print $4}')
echo "Free files (inodes) on the receiver: ${INODES:-?}"
if [ -n "$INODES" ] && [ "$INODES" -lt 6000 ] 2>/dev/null; then
	warn "the receiver can hold only $INODES more files (disk full of small files)."
	echo "Delete old images / plugins / picons you do not use, then try again."
fi

info "Installing ..."
LOG=/tmp/mohammedskin_update.log
rm -f /usr/share/enigma2/MohammedSkin/.installed
if opkg install --force-reinstall --force-overwrite --tmp-dir "$OPKG_TMP" "$IPK" >"$LOG" 2>&1 && [ -f /usr/share/enigma2/MohammedSkin/.installed ]; then
	cat "$LOG"
else
	cat "$LOG"
	echo "opkg could not finish - installing the files directly ..."
	if ! python_install >>"$LOG" 2>&1; then
		tail -n 5 "$LOG"
		rm -rf "$IPK" "$OPKG_TMP"
		err "installation failed. Free space now: $(free_kb /usr/share/enigma2) kB"
		echo "Details: $LOG"
		exit 1
	fi
	ok "Installed directly (opkg was skipped)."
fi
rm -rf "$IPK" "$OPKG_TMP"

# keep the list of installed files: the next update fetches only what changed
rm -f "$SK/.manifest.json"
if fetch "$BASE/ipk/manifest.json.gz?t=$(date +%s)" "$WORK/mohammedskin_manifest.json.gz"; then
	python3 -E -c "import gzip,json,sys;m=json.loads(gzip.open(sys.argv[1]).read());v=open(sys.argv[2]).read().strip();m['version']==v and json.dump({'version':m['version'],'files':m['files']},open(sys.argv[3],'w'))" "$WORK/mohammedskin_manifest.json.gz" "$SK/.installed" "$SK/.manifest.json" 2>/dev/null
	rm -f "$WORK/mohammedskin_manifest.json.gz"
fi

# Pillow is optional (used for the clock and theme tools); try to add it quietly.
opkg list-installed 2>/dev/null | grep -q '^python3-pillow ' || opkg install python3-pillow >/dev/null 2>&1

echo "${G}  ----------------------------------------------${N}"
echo "${G}  MohammedSkin ${VER} installed successfully${N}"
[ -n "$IMAGE" ] && echo "${C}  adapted to $IMAGE${N}"
echo "${G}  ----------------------------------------------${N}"

# Restart the GUI here, also when the setup plugin started the update (NORESTART=1): older
# versions of the plugin could crash while finishing the update, so we never hand back to them.
info "Restarting the GUI ..."
sync
sleep 1
killall -9 enigma2 >/dev/null 2>&1
pkill -9 -f /usr/bin/enigma2 >/dev/null 2>&1
[ -x /etc/init.d/enigma2 ] && /etc/init.d/enigma2 restart >/dev/null 2>&1 &
exit 0
