# Pocket Guide Installer

A desktop installer for Windows, macOS, and Linux for Analogue Pocket openFPGA cores and games, based on the [Time Extension guide](https://www.timeextension.com/guides/all-analogue-pocket-openfpga-cores-and-where-to-download-them).

## Credits

This installer relies on the work of openFPGA developers, port maintainers, and tool authors. The full credits list identifies **89 repositories and every one of the 137 core builds**, including source projects, pinned releases, and GitHub-reported license information. [Read all credits and upstream sources](CREDITS.md).

## Use the installer

1. Download the package for your operating system from [the latest release](https://github.com/printwizardscxcare-design/pocket-guide-installer/releases/latest).
2. Connect an initialized Pocket microSD card to your computer. A card reader is fastest. For USB, use **Tools → Developer → USB SD Access** on the Pocket.
3. Open the installer and check the selected drive. All **137 cores and 365 game and system files** start selected. Expand a category or search for an item. **All** and **None** apply to the visible search results. Selecting a game selects its core. Removing a core removes downloads that depend exclusively on it.
4. Choose **Add missing files** (default) to keep differing files already on the card. Choose **Overwrite matching files** to replace differing files at selected destinations. Both modes retain unrelated files.
5. Leave **Import compatible games** selected to unpack games already on the card and optionally import a PC game folder. Click **Install selection**. Use **Stop safely** if you need to interrupt the transfer, then wait for the stopped message before ejecting.
6. Review the completion report and safely eject the card. On Pocket, select **openFPGA** for installed cores or **Play Cartridge** for physical cartridges.

Core and game installation writes under **Assets**, **Cores**, and **Platforms**. Selecting firmware also places the official firmware update at the card root. Downloaded core archives are pinned with SHA-256. Game and system assets are checked against their archive checksums. Each new or replacement file is verified before it becomes the destination file.

## What is included

The checklist links to developer core releases and indexed game and system assets. The full asset selection is **2.10 GiB**, in addition to core downloads and unpacked local games. Repeated and regional game listings can share a core. Core packages may contain bundled launchers or sample files. Individual game-download checkboxes control separately downloaded assets.

The optional game importer recognizes GB, GBC, GBA, NES, SFC, SMC, MD, GEN, SMD, GG, SMS, PCE, WS, WSC, LNX, A26, and A78 game files. It also recognizes loose Genesis BIN files inside a folder named **genesis**. It handles loose files and supported ZIP members for selected platforms. It keeps the source files.

The guide lists **Bandit**, **Birdie Try**, and **Ganbare! Marine Kun**. This release has no matched playable download for those three listings. The included Coin-Op Collection builds for **Mortal Kombat**, **NARC**, and **Smash TV** require a publisher license to play. Some systems also need user-supplied games or disc images.

## Reports and sharing

**Open report** shows a text summary of the most recent install. This report, a JSON version, and reusable download caches are under **%LOCALAPPDATA%\Pocket Guide Installer** on Windows, **~/Library/Application Support/Pocket Guide Installer** on macOS, or **~/.local/share/pocket-guide-installer** on Linux (respecting XDG_DATA_HOME). Game files, BIOS downloads, and card data are excluded from the standalone executable and repository.

People with repository access can use the private release link. You can also share the executable directly. Windows builds are unsigned. Mac builds are ad-hoc signed and are not Apple-notarized.

## Build from source on Windows

Use Python 3.15 x64 with Tk and PyInstaller 6.22.3.

```powershell
python -m pip install pyinstaller==6.22.3
python -m PyInstaller --onefile --windowed --name PocketGuideInstaller --icon "assets/pocket.ico" --add-data "assets:assets" --add-data "manifest.json:." pocket.py
```

The output is **dist/PocketGuideInstaller.exe**. For a full selection from the command line, run **python pocket.py --card E:/ --mode add**. Optional arguments include **--mode overwrite** and **--games "C:/My Games"**. Use the actual card drive.

Core metadata comes from the [openFPGA core inventory](https://openfpga-cores-inventory.github.io/analogue-pocket/) and [JT binary releases](https://github.com/jotego/jtbin). The game and system asset index uses the openFPGA-Files archive referenced by [Pupdate](https://github.com/mattpannella/pupdate).

## Optional firmware update

Firmware 2.7 is available in the checklist and starts selected. It requires confirmation. Cores, downloads, and local game imports run first. Firmware preparation runs last. The installer verifies the official checksum and skips preparation when the device reports 2.7 or newer. Overwrite mode backs up older Pocket update files to the PC.

After completion, safely eject, fully power off the Pocket, then power on with the card inserted. Allow 3-4 minutes and keep power on until it restarts. Choose None, then check Pocket firmware for firmware alone. Command-line runs require --firmware to include firmware.

Selecting firmware adds the official firmware file to the card root. Cartridge play remains available. Official instructions https://www.analogue.co/support/resource/updating-firmware


The Firmware only button selects just the firmware update and turns off local game imports.


## Platform downloads

| Platform | Download | Install |
| --- | --- | --- |
| Windows x64 | EXE | Open the executable |
| macOS Apple Silicon | arm64 DMG or ZIP | Copy the app to Applications |
| macOS Intel | x64 DMG or ZIP | Copy the app to Applications |
| Debian / Ubuntu x64 | DEB | Open with your package manager |
| Fedora x64 | RPM | Open with your package manager |
| Arch Linux x64 | pkg.tar.gz | Install with pacman |
| Linux x64 portable | tar.gz | Extract and run PocketGuideInstaller |

The release workflow builds and checks each platform natively and installs the Linux packages in Debian, Fedora, and Arch containers. Linux portable builds need an X11-compatible desktop and standard X11/font libraries. Intel and Apple Silicon macOS builds are separate. Physical Pocket transfers on macOS and Linux still need user testing.

The workflow supports Python 3.13 and PyInstaller 6.22.3. Build a native release with **python build_release.py 1.2.0** on the corresponding OS. Linux package builds also use FPM. Downloads contain the same checklist and firmware option. Choose the root of the mounted Pocket card when browsing manually.

See the release's **SHA256SUMS** file for each platform's download checksums.
