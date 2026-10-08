#!/bin/sh
# MohammedSkin online installer / updater
# Works on OpenViX, OpenBlackHole, OpenATV, PurE2 and EGAMI (Enigma2).
#   wget -q --no-check-certificate "https://raw.githubusercontent.com/mido00020/MohammedSkin/main/installer.sh" -O - | /bin/sh

BASE="https://raw.githubusercontent.com/mido00020/MohammedSkin/main"

echo "=============================================="
echo "        MohammedSkin - online installer"
echo "=============================================="

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
	echo "Image: $IMAGE ${VERSION}  (supported)"
else
	echo "Image: ${DISTRO:-unknown} ${VERSION}"
	echo "This image is not on the tested list. The skin adapts itself anyway,"
	echo "the image name in the infobar is left out."
fi

if [ ! -d /usr/lib/enigma2/python ] || ! command -v opkg >/dev/null 2>&1; then
	echo "ERROR: this does not look like an Enigma2 receiver (no enigma2 python or opkg)."
	exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
	echo "ERROR: python3 not found. MohammedSkin needs a Python 3 image."
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
	echo "ERROR: not enough free memory or disk space to download the update (about 100 MB needed)."
	echo "Free some space (or plug in a USB stick) and try again."
	exit 1
fi
IPK="$WORK/enigma2-skin-mohammedskin.ipk"
OPKG_TMP="$WORK/mohammedskin-opkg"
mkdir -p "$OPKG_TMP"

FLASH=$(free_kb /usr/share/enigma2)
echo "Free space: download area $(free_kb "$WORK") kB, receiver flash ${FLASH:-?} kB"
if [ -n "$FLASH" ] && [ "$FLASH" -lt 30000 ]; then
	echo "WARNING: little free space on the receiver (${FLASH} kB). The update may not fit."
fi

# ---------------------------------------------------------------- download

fetch() {
	rm -f "$2"
	# with certificate check first; older boxes without certificates fall back
	if wget -q "$1" -O "$2" 2>/dev/null && [ -s "$2" ]; then
		return 0
	fi
	if wget -q --no-check-certificate "$1" -O "$2" 2>/dev/null && [ -s "$2" ]; then
		return 0
	fi
	if command -v curl >/dev/null 2>&1 && curl -kfsSL "$1" -o "$2" && [ -s "$2" ]; then
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
echo "Latest version: ${VER:-unknown}"

echo "Downloading ..."
if ! fetch "$BASE/ipk/enigma2-skin-mohammedskin_all.ipk" "$IPK"; then
	echo "ERROR: download failed. Check the internet connection."
	exit 1
fi

# ---------------------------------------------------------------- install

echo "Checking the download ..."
# the package must match the checksum published with it (a changed or broken file is refused)
if fetch "$BASE/ipk/enigma2-skin-mohammedskin_all.ipk.sha256" /tmp/mohammedskin.sha256; then
	WANT=$(head -c 64 /tmp/mohammedskin.sha256)
	rm -f /tmp/mohammedskin.sha256
	GOT=$(python3 -E -c "import hashlib,sys;h=hashlib.sha256();f=open(sys.argv[1],'rb');[h.update(b) for b in iter(lambda:f.read(1<<20),b'')];print(h.hexdigest())" "$IPK")
	if [ "$WANT" != "$GOT" ]; then
		rm -f "$IPK"
		echo "ERROR: the downloaded package does not match its checksum. Try the update again in a few minutes."
		exit 1
	fi
	echo "Checksum OK"
fi
# the download must be a whole package (a cut connection leaves half a file)
if ! python3 -E - "$IPK" <<'PY'
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
	echo "ERROR: the download is incomplete (connection cut). Try the update again."
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
	echo "WARNING: the receiver can hold only $INODES more files (disk full of small files)."
	echo "Delete old images / plugins / picons you do not use, then try again."
fi

echo "Installing ..."
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
		echo "ERROR: installation failed. Free space now: $(free_kb /usr/share/enigma2) kB"
		echo "Details: $LOG"
		exit 1
	fi
	echo "Installed directly (opkg was skipped)."
fi
rm -rf "$IPK" "$OPKG_TMP"

# Pillow is optional (used for the clock and theme tools); try to add it quietly.
opkg list-installed 2>/dev/null | grep -q '^python3-pillow ' || opkg install python3-pillow >/dev/null 2>&1

echo "=============================================="
echo "  MohammedSkin ${VER} installed successfully"
[ -n "$IMAGE" ] && echo "  adapted to $IMAGE"
echo "=============================================="

# Restart the GUI here, also when the setup plugin started the update (NORESTART=1): older
# versions of the plugin could crash while finishing the update, so we never hand back to them.
echo "Restarting the GUI ..."
sync
sleep 1
killall -9 enigma2 >/dev/null 2>&1
exit 0
