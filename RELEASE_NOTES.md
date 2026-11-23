Neo Geo game-pack import and readiness checks

- Import compatible per-game Neo Geo folders or ZIPs, including extensionless srom/prom/crom0/m1rom/vroma0 files.
- Use installed game definitions to resolve destination folders and retain Add/Overwrite behavior.
- Audit every game definition after import. A present crom0 alone no longer passes the game-data check.
- Show ready versus incomplete definitions in the saved report and label the core as needing separate game data.
- Preserve existing game files, saves and original imports.

This update fixes four legacy Genesis imports and clarifies missing-content reports.

- Recognizes raw Genesis dumps mislabeled as SMD, including early games without the usual SEGA header, after checking reset vectors and image layout. Original files stay untouched.
- Replaces generic Neo Geo component names and PC Engine CD example tracks with clear game-data requirements.
- Names Coin-Op Collection beta access separately from game content.

Game installation now has live progress and a persistent activity history.

- See the current stage, files finished, percentage and elapsed time.
- See the approximate time left in the current step after a short speed sample; estimates pause during stalls.
- Track game downloads by bytes, average speed and active transfers, including verified cached files.
- Watch each file move through download, verification and copying to the card.
- Review installed files, existing matches, preserved conflicts and failures in the activity tab. Select a row for full details.
- Local game imports show archives checked and the game being copied.
- File outcomes are saved in both installation reports. Stop safely also interrupts active downloads between chunks.

The Pocket Guide logo now uses an 8-bit Gruvbox design across the executable, Mac app, Linux packages, and project page.

Pocket Guide Installer 1.3.2 supports Windows, Intel and Apple Silicon macOS, and Linux. It includes the selective core and game checklist, Add and Overwrite modes, and a firmware-only option.

## Start here

Read the [project overview](https://github.com/printwizardscxcare-design/pocket-guide-installer#readme) and [full installation guide](https://github.com/printwizardscxcare-design/pocket-guide-installer/blob/main/INSTALL.md) before your first run. An offline copy of the guide is attached below as **INSTALL.md**.

| Download | Setup instructions |
| --- | --- |
| Windows x64 EXE | [Windows](https://github.com/printwizardscxcare-design/pocket-guide-installer/blob/main/INSTALL.md#windows) |
| macOS arm64 or x64 DMG / ZIP | [macOS, including first launch](https://github.com/printwizardscxcare-design/pocket-guide-installer/blob/main/INSTALL.md#macos) |
| Debian / Ubuntu DEB | [Debian / Ubuntu](https://github.com/printwizardscxcare-design/pocket-guide-installer/blob/main/INSTALL.md#debian-and-ubuntu) |
| Fedora RPM | [Fedora](https://github.com/printwizardscxcare-design/pocket-guide-installer/blob/main/INSTALL.md#fedora) |
| Arch pkg.tar.gz | [Arch Linux](https://github.com/printwizardscxcare-design/pocket-guide-installer/blob/main/INSTALL.md#arch-linux) |
| Linux portable tar.gz | [Portable Linux](https://github.com/printwizardscxcare-design/pocket-guide-installer/blob/main/INSTALL.md#portable-linux-download) |

All native builds passed startup and isolated installation checks. Linux packages also passed installation checks in Debian, Fedora, and Arch.

Windows builds are unsigned. Mac builds are ad-hoc signed and have not been notarized by Apple. Physical Pocket transfers on macOS and Linux still need user testing.

Firmware preparation runs last. After completion, safely eject and fully restart the Pocket to apply the update. [Firmware instructions](https://github.com/printwizardscxcare-design/pocket-guide-installer/blob/main/INSTALL.md#firmware-only)

## Credits

This project relies on the work of the openFPGA core developers and port maintainers, openFPGA Cores Inventory, JOTEGO, Pupdate, Analogue, Time Extension, and the asset collection contributors. [Full source and release credits](https://github.com/printwizardscxcare-design/pocket-guide-installer/blob/main/CREDITS.md).
