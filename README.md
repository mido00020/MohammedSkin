# MohammedSkin

A cinematic Full HD skin for Enigma2 (1920x1080).

Works on **OpenViX**, **OpenBlackHole**, **OpenATV**, **PurE2** and **EGAMI**. The installer checks which image the receiver runs and the skin adapts itself to it, so the same command works on all of them.

- The image name glows in the middle of the infobar (OpenViX, OpenBlackHole, OpenATV, PurE2, EGAMI)
- Posters, backdrops and scenes fetched online (kept in RAM only, nothing saved to flash)
- Infobar styles: classic, four 3D poster designs (cinema, hologram, film reel, diagonal), four framed poster designs, two compact designs, the clock arch, a glass panel with a round channel badge, and a curved bar with a round poster and running lights in the theme colour
- Inside every infobar: date and day, receiver temperature, receiver IP, an IPTV mark for streams, and the softcam with its ECM time and server
- Second infobar styles: classic, backdrop with four scenes, or backdrop with two scenes
- Rating stars, rating, year and genre of films and series
- Infobar poster in the bar, or above the bar and larger
- Main menu styles: classic, black glass, ivory white, 3D tiles, neon glass
- Channel list styles: classic, 3D lists with a white, black glass or colour panel, seven 3D designs (premium glass, neon focus, cinema carousel, cover flow, vertical icons, futuristic, golden), glass designs with tabs, side picture, big logos, neon and featured card, cinema tickets with a lit marquee board (one big picture, or poster with details and the next programme), and neon glass over the programme's full picture
- Channel list text size (small to extra large) and row size (compact to extra large), for every channel list style
- Plugin list text size (small to extra large)
- First infobar transparency: very transparent, transparent, normal, dark, very dark
- Adult poster filter: hides posters, backdrops and scenes of adult and erotic titles and channels (off, on, strict)
- Weather (free, no key): card at the top right of every infobar style and in the second infobar; city found automatically or typed in the setup; Arabic or English, °C or °F
- Arabic fonts to choose from: Tajawal, Cairo, Almarai, Noto Kufi, IBM Plex Arabic, Amiri, DejaVu, and title fonts Lalezar, Cairo Black, Changa, El Messiri, Aref Ruqaa, Rakkas
- Arabic posters for channels on Nilesat, Arabsat and Badr (when TMDB has one)
- 3D channel logo card when a channel has no event, no poster was found, or the poster is hidden
- Every new option has a preview picture in the setup
- Ten colour themes: red, blue, turquoise, sky blue (fayrouzi), gold, black, purple, emerald green, orange and rose pink (the new ones are prepared on the receiver the first time you pick them)
- Five glass channel list styles: gold glass with All / Satellites / Favourites / Providers tabs, glass sidebar, sidebar with big logos, neon sidebar and featured channel card
- Plugin list as a grid of tiles (OpenViX / OpenBH with grid support, OpenATV) or as a list
- Weather position: top right, top centre, or above the infobar (right or left)
- Classic analog clocks with a smooth seconds hand, or no centre clock
- Arabic auto-translation of event titles and descriptions
- Pulsing transponder readout (frequency, polarisation, symbol rate, FEC, modulation)
- SNR in dB, signal meters and softcam server info

## Install / update

Run this in telnet/SSH on the receiver:

```
wget -q --no-check-certificate "https://raw.githubusercontent.com/mido00020/MohammedSkin/main/installer.sh" -O - | /bin/sh
```

The same command installs the skin the first time and updates it later. It shows the detected image, installs, and restarts the GUI.

When you open **Menu > Plugins > MohammedSkin Setup** and a newer version is on GitHub, the setup asks whether to update (Yes / No). Yes installs it and restarts the GUI by itself. You can also check by hand with the **blue** button.

## Activate

Open the skin selection of your image (on OpenViX: **Menu > Setup > User Interface > Skin**) and choose **MohammedSkin**.

## Setup

**Menu > Plugins > MohammedSkin Setup**: colour theme, menu and channel list style, channel list text and row size, plugin list text size, infobar style and transparency, second infobar style, infobar poster position, rating stars, clock, Arabic translation, adult poster filter and optional API keys. Each style has a preview.

## Files

| File | Purpose |
|---|---|
| `installer.sh` | Online installer / updater |
| `version.txt` | Latest published version |
| `ipk/enigma2-skin-mohammedskin_all.ipk` | Latest package |
| `blocklist.txt` | Titles and channels that never get a poster (read by every receiver) |

## Credits

Posters, scenes and ratings: [TMDB](https://www.themoviedb.org). This product uses the TMDB API but is not endorsed or certified by TMDB. Series data also from TVmaze.
