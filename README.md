<p align="center"><img src="assets/pocket.png" width="144" alt="Smiling handheld with a download chip"></p>

# Pocket Guide Installer

Set up your Analogue Pocket from Windows, macOS, or Linux. Choose the openFPGA cores and game assets you want, import your existing games, or prepare an official firmware update from one checklist.

[Download version 1.3.0](https://github.com/printwizardscxcare-design/pocket-guide-installer/releases/tag/v1.3.0) · [Installation guide](INSTALL.md) · [Full credits](CREDITS.md) · [Get help](https://github.com/printwizardscxcare-design/pocket-guide-installer/issues)

## What it does

- Offers **137 core builds and 365 indexed game and system files**, organized into a searchable checklist.
- Starts with everything checked so you can install a full selection or choose individual items.
- Adds missing files or overwrites matching files, with verification before each replacement.
- Imports compatible loose game files and ZIP members from the card or a folder on your computer.
- Provides a **Firmware only** button for official Pocket firmware **2.7**.
- Shows live download sizes and speed, per-stage file counts, and an activity history of downloads, verification, card copies, cached files, and items needing attention.
- Saves the file activity in the installation report for later review.

Your physical cartridges still work through **Play Cartridge**. Core and game files are installed into the card's **Assets**, **Cores**, and **Platforms** folders. Selecting firmware prepares an update file at the card root. Saves and Memories are preserved.

## Download and install

Choose the package that matches your computer. The linked instructions cover installation and first launch for each format.

| Platform | Version 1.3.0 download | Instructions |
| --- | --- | --- |
| Windows x64 | [EXE](https://github.com/printwizardscxcare-design/pocket-guide-installer/releases/download/v1.3.0/PocketGuideInstaller-1.3.0-windows-x64.exe) | [Windows setup](INSTALL.md#windows) |
| macOS Apple Silicon | [DMG](https://github.com/printwizardscxcare-design/pocket-guide-installer/releases/download/v1.3.0/PocketGuideInstaller-1.3.0-macos-arm64.dmg) · [ZIP](https://github.com/printwizardscxcare-design/pocket-guide-installer/releases/download/v1.3.0/PocketGuideInstaller-1.3.0-macos-arm64.zip) | [Mac setup](INSTALL.md#macos) |
| macOS Intel | [DMG](https://github.com/printwizardscxcare-design/pocket-guide-installer/releases/download/v1.3.0/PocketGuideInstaller-1.3.0-macos-x64.dmg) · [ZIP](https://github.com/printwizardscxcare-design/pocket-guide-installer/releases/download/v1.3.0/PocketGuideInstaller-1.3.0-macos-x64.zip) | [Mac setup](INSTALL.md#macos) |
| Debian / Ubuntu x64 | [DEB](https://github.com/printwizardscxcare-design/pocket-guide-installer/releases/download/v1.3.0/PocketGuideInstaller-1.3.0-linux-x64.deb) | [Debian / Ubuntu setup](INSTALL.md#debian-and-ubuntu) |
| Fedora x64 | [RPM](https://github.com/printwizardscxcare-design/pocket-guide-installer/releases/download/v1.3.0/PocketGuideInstaller-1.3.0-linux-x64.rpm) | [Fedora setup](INSTALL.md#fedora) |
| Arch Linux x64 | [pkg.tar.gz](https://github.com/printwizardscxcare-design/pocket-guide-installer/releases/download/v1.3.0/PocketGuideInstaller-1.3.0-linux-x64.pkg.tar.gz) | [Arch setup](INSTALL.md#arch-linux) |
| Linux x64 portable | [tar.gz](https://github.com/printwizardscxcare-design/pocket-guide-installer/releases/download/v1.3.0/PocketGuideInstaller-1.3.0-linux-x64.tar.gz) | [Portable Linux setup](INSTALL.md#portable-linux-download) |

Windows builds are unsigned. Mac builds use ad-hoc signing and have not been notarized by Apple. The installation guide explains first-launch prompts. Checksums for every package are on the release page.

This repository is public. Anyone can view the project and download a release without a GitHub account. You can share the project page, release link, or a downloaded installer file directly.

## Your first install

1. Connect a microSD card already initialized by the Pocket. Use a card reader, or enable **Tools → Developer → USB SD Access** on the connected Pocket.
2. Open the app and confirm the detected card. Click **Browse** if you need to select it manually.
3. Adjust the checklist, choose **Add missing files** or **Overwrite matching files**, and optionally choose a folder of your games.
4. Click **Install selection** and leave the card connected until it finishes.
5. Open the report, review any exceptions, and safely eject.

The complete indexed asset selection uses about **2.10 GiB**, plus cores and imported games. Downloads are cached on the computer. A card reader is faster for large installations.

Firmware is prepared **after** selected cores and games. To apply it, safely eject, fully power off the Pocket, then power on with the card inserted. Allow **3–4 minutes** and keep power on until it restarts. [Firmware-only instructions](INSTALL.md#firmware-only)

## Built on the community's work

The FPGA cores, their ports, release catalogs, and existing updater tools make this project possible. Their developers and contributors deserve the credit for the systems and games this installer helps set up.

- **Spiritualized1997, agg23, budude2, Mazamars312, JOTEGO, obsidian-dot-dev, OpenGateware, Coin-Op Collection, and the other developers listed in the full credits** provide the core projects and release builds.
- **openFPGA Cores Inventory** supplies the core catalog and release metadata. [Catalog repository](https://github.com/openfpga-cores-inventory/analogue-pocket)
- **Matt Pannella's Pupdate** informed the updater and asset-layout approach. [Pupdate repository](https://github.com/mattpannella/pupdate)
- **JOTEGO** maintains source cores and Pocket binary distributions. [Source cores](https://github.com/jotego/jtcores) · [Binary releases](https://github.com/jotego/jtbin)
- **Damien McFerran and Time Extension** created the guide used to select the systems and arcade titles. [Original guide](https://www.timeextension.com/guides/all-analogue-pocket-openfpga-cores-and-where-to-download-them)
- **Analogue** develops Pocket, Analogue OS, and openFPGA, and publishes the firmware. [Developer documentation](https://www.analogue.co/developer/docs)
- **Internet Archive and the openFPGA-Files contributors** host the indexed game and system assets. [Collection](https://archive.org/details/openFPGA-Files)

**[Read the complete credits for every core build, source repository, pinned download, and packaging tool.](CREDITS.md)** The credits include GitHub-reported licenses and links to each project's own contributor history and terms.

The app interface and installer code were created for this project. The smiling handheld artwork was generated with OpenAI's image-generation tool. Python, Tcl/Tk, PyInstaller, Pillow, FPM, and GitHub Actions support the desktop builds.

## Availability and testing

The source and packaged app passed automated checks on Windows, Intel Mac, Apple Silicon Mac, and Linux. Linux packages were also installed and checked inside Debian 13, Fedora 43, and Arch containers. Physical Pocket transfers on macOS and Linux still need user testing.

Some arcade builds require a publisher-issued license. The selected **Mortal Kombat**, **NARC**, and **Smash TV** builds have that requirement. **Bandit**, **Birdie Try**, and **Ganbare! Marine Kun** have no matched playable download in this release. Some systems need separately supplied games, BIOS files, or disc images. The completion report lists items requiring attention.

The game importer supports GB, GBC, GBA, NES, SFC, SMC, MD, GEN, SMD, GG, SMS, PCE, WS, WSC, LNX, A26, and A78 files. Loose Genesis BIN files are recognized inside a folder named **genesis**. Supported game files in ZIP archives can be unpacked for selected platforms.

## Reports and support

Use **Open report** after an install. Reports and cached downloads live in the app's data folder on each platform. [Report locations and help](INSTALL.md#reports-and-help)

For a problem report, include your operating system, installer version, download format, and the relevant message from **Install report.txt**. [Open an issue](https://github.com/printwizardscxcare-design/pocket-guide-installer/issues)

## Build from source

Native builds use Python 3.13, PyInstaller 6.22.3, and Pillow 12.0.0. Linux package generation also uses FPM 1.17.0 and the system build tools listed in the workflow.

```bash
python -m pip install pyinstaller==6.22.3 pillow==12.0.0
python build_release.py 1.3.0
```

Build on the target operating system. The workflow creates Intel and Apple Silicon Mac releases separately. Build outputs and checksums are written to **release/**. [Native build and distribution checks](.github/workflows/desktop.yml)

To run from source, use **python pocket.py** with a Python installation that includes Tk. The command-line entry point accepts **--card**, **--mode add**, **--mode overwrite**, **--games**, and the optional **--firmware** flag. [Source code](pocket.py)
