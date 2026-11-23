# Installation guide

These instructions cover Pocket Guide Installer **1.3.2**. Download files from the [1.3.2 release](https://github.com/printwizardscxcare-design/pocket-guide-installer/releases/tag/v1.3.2). The repository and release downloads are public. A GitHub account is optional.

## Choose your download

| Computer | File |
| --- | --- |
| Windows x64 | PocketGuideInstaller-1.3.2-windows-x64.exe |
| Mac with Apple Silicon | PocketGuideInstaller-1.3.2-macos-arm64.dmg or .zip |
| Mac with Intel processor | PocketGuideInstaller-1.3.2-macos-x64.dmg or .zip |
| Debian or Ubuntu x64 | PocketGuideInstaller-1.3.2-linux-x64.deb |
| Fedora x64 | PocketGuideInstaller-1.3.2-linux-x64.rpm |
| Arch Linux x64 | PocketGuideInstaller-1.3.2-linux-x64.pkg.tar.gz |
| Other Linux x64 desktops | PocketGuideInstaller-1.3.2-linux-x64.tar.gz |

On a Mac, open **Apple menu → About This Mac**. Choose **arm64** if it lists an Apple chip such as M1, M2, M3, or M4. Choose **x64** if it lists an Intel processor. Linux packages and the Windows build target x64 computers.

The **SHA256SUMS.txt** files contain checksums. GitHub's **Source code** ZIP and TAR.GZ downloads contain the project source. Choose a named platform package above to run the prebuilt app.

## Windows

1. Download **PocketGuideInstaller-1.3.2-windows-x64.exe** to a local folder such as Downloads.
2. Double-click the file to open it. The executable runs directly and includes its Python runtime.
3. Continue with [Connect your Pocket](#connect-your-pocket).

The Windows executable is unsigned, so Windows may ask you to confirm the publisher or opening the downloaded app. Check that the file came from this release before approving a prompt.

To compare its checksum, open PowerShell in Downloads and run the command below. Compare the result with the Windows **SHA256SUMS.txt** file from the same release.

```powershell
Get-FileHash .\PocketGuideInstaller-1.3.2-windows-x64.exe -Algorithm SHA256
```

## macOS

### Install from a DMG

1. Download the **arm64** or **x64** DMG for your Mac.
2. Double-click the DMG to mount it.
3. Drag **PocketGuideInstaller** onto **Applications** in the opened disk window.
4. Eject the installer disk in Finder.
5. Open **Applications → PocketGuideInstaller**.
6. Continue with [Connect your Pocket](#connect-your-pocket).

### Install from a ZIP

1. Download the **arm64** or **x64** ZIP for your Mac.
2. Double-click it in Finder to extract **PocketGuideInstaller.app**.
3. Move the app to **Applications**, then open it.
4. Continue with [Connect your Pocket](#connect-your-pocket).

### First launch on macOS

The Mac app is ad-hoc signed and has not been notarized by Apple. If macOS blocks it because the developer cannot be verified, first confirm that you downloaded the expected release. After trying to open it, go to **System Settings → Privacy & Security**, find the app's message, choose **Open Anyway**, and confirm **Open**. Managed Macs may restrict this choice. Apple documents this per-app exception in its opening instructions. [Apple's instructions](https://support.apple.com/en-us/102445)

If macOS asks the app for access to removable volumes or the selected game folder, allow access to the locations you intend to use.

To verify a DMG or ZIP, download the matching Mac **SHA256SUMS.txt** file into the same folder. Open Terminal in that folder and run the appropriate command.

```bash
# Apple Silicon
shasum -a 256 -c PocketGuideInstaller-1.3.2-macos-arm64-SHA256SUMS.txt

# Intel
shasum -a 256 -c PocketGuideInstaller-1.3.2-macos-x64-SHA256SUMS.txt
```

The checksum list includes both the DMG and ZIP. A missing-file message for a format you did not download is expected. The file you did download should report **OK**.

## Debian and Ubuntu

1. Download **PocketGuideInstaller-1.3.2-linux-x64.deb**.
2. Open Terminal in the folder containing the download.
3. Install the package and its dependencies.

```bash
sudo apt install ./PocketGuideInstaller-1.3.2-linux-x64.deb
```

4. Open **Pocket Guide Installer** from your application menu. To launch from Terminal, run the command below as your normal user.
5. Continue with [Connect your Pocket](#connect-your-pocket).

```bash
/opt/pocket-guide-installer/PocketGuideInstaller
```

The package was installed and checked in Debian 13. The desktop build was also checked on Ubuntu 22.04. [Ubuntu local-package documentation](https://documentation.ubuntu.com/project/contributors/bug-fix/install-built-packages/)

## Fedora

1. Download **PocketGuideInstaller-1.3.2-linux-x64.rpm**.
2. Open Terminal in the download folder and install the package.

```bash
sudo dnf install ./PocketGuideInstaller-1.3.2-linux-x64.rpm
```

3. Open **Pocket Guide Installer** from your application menu, or run the command below as your normal user.
4. Continue with [Connect your Pocket](#connect-your-pocket).

```bash
/opt/pocket-guide-installer/PocketGuideInstaller
```

The RPM was installed and checked in Fedora 43.

## Arch Linux

1. Download **PocketGuideInstaller-1.3.2-linux-x64.pkg.tar.gz**.
2. Open Terminal in the download folder and install it with pacman.

```bash
sudo pacman -U ./PocketGuideInstaller-1.3.2-linux-x64.pkg.tar.gz
```

3. Open **Pocket Guide Installer** from your application menu, or run the command below as your normal user.
4. Continue with [Connect your Pocket](#connect-your-pocket).

```bash
/opt/pocket-guide-installer/PocketGuideInstaller
```

The package was installed and checked in the current Arch base container. [Arch local-package documentation](https://wiki.archlinux.org/title/Pacman)

## Portable Linux download

1. Download **PocketGuideInstaller-1.3.2-linux-x64.tar.gz**.
2. Extract it into its own folder and start the app.

```bash
mkdir -p PocketGuideInstaller-1.3.2
tar -xzf PocketGuideInstaller-1.3.2-linux-x64.tar.gz -C PocketGuideInstaller-1.3.2
cd PocketGuideInstaller-1.3.2
chmod +x PocketGuideInstaller
./PocketGuideInstaller
```

3. Continue with [Connect your Pocket](#connect-your-pocket).

Use a graphical desktop with X11 support, or a Wayland desktop with XWayland. The app includes its Python and Tk runtimes. The host supplies X11, fontconfig, FreeType, and fonts. If these are missing, install the dependencies for your distribution before opening the app.

```bash
# Debian / Ubuntu
sudo apt install libx11-6 libxext6 libxrender1 libxft2 libxcb1 fontconfig fonts-dejavu-core xdg-utils

# Fedora
sudo dnf install libX11 libXext libXrender libXft libxcb fontconfig dejavu-sans-fonts xdg-utils

# Arch
sudo pacman -S --needed libx11 libxext libxrender libxft libxcb fontconfig ttf-dejavu xdg-utils
```

The portable executable is built on Ubuntu 22.04. Compatibility with additional Linux distributions needs testing.

To verify Linux downloads, place the Linux **SHA256SUMS.txt** beside your downloaded packages and run the command below.

```bash
sha256sum -c PocketGuideInstaller-1.3.2-linux-x64-SHA256SUMS.txt
```

The list covers all four Linux formats. Missing-file messages for formats you did not download are expected. Check that your downloaded file reports **OK**.

## Connect your Pocket

1. Use a microSD card that the Pocket has already initialized. The app recognizes the device-generated **Analogue_Pocket.json** file at the card root. If that file is missing, let your Pocket initialize the card before trying again.
2. Connect the card through a microSD reader, or connect the Pocket with a USB-C data cable and enable **Tools → Developer → USB SD Access**. A reader is faster for a large installation. [Analogue USB SD documentation](https://www.analogue.co/developer/docs/openfpga/debugging-aids)
3. Open the app. When exactly one Pocket card is found, it is selected automatically. Check the card path and available space.
4. If it is missing from the list, click **Browse** and select the root of the mounted card. On Windows this is a drive such as **E:\**. On macOS it is normally under **/Volumes**. On Linux it is commonly under **/media**, **/run/media**, or **/mnt**. Mount it in your file manager first.

Run the app as your normal desktop user with write access to the card. The operating system may request administrator authorization to install a Linux package. The app itself uses the card permissions of the user running it.

## Choose what to install

All cores, indexed game and system downloads, and the firmware entry start checked.

1. Expand the checklist categories or search for a system or title. **All** and **None** apply to the visible search results. Selecting a game selects a core it depends on. Unchecking a core removes downloads that depend exclusively on that core.
2. Choose **Add missing files** to preserve differing files already on the card. Choose **Overwrite matching files** to replace selected files that differ. Unrelated files are kept.
3. Leave **Import compatible games** checked to unpack supported ZIP files already on the card. Use **Choose game folder** to add compatible files from a folder on your computer. Turn it off to skip local imports.
4. Check the card path once more, then click **Install selection**. Confirm overwrite or firmware prompts if those options were selected.
5. Leave the card connected until the completion message appears. For an interruption, choose **Stop safely** and wait for the stopped message before disconnecting.
6. Open the report and review any skipped files, missing assets, or license requirements.

The full indexed asset selection uses approximately **2.10 GiB** on the card, plus cores and imported games. The computer also needs space for cached downloads. A complete USB transfer can take hours.

**Play Cartridge** remains available. The core and game install works in the card's **Assets**, **Cores**, and **Platforms** folders. Saves and Memories are preserved.

## Firmware only

1. Click **Firmware only**. This selects the official Pocket **2.7** update and turns off local game imports.
2. Confirm the card and click **Install selection**.
3. Read the firmware confirmation. The app verifies Analogue's published checksum and skips preparation when the device reports 2.7 or newer.
4. In Add mode, a conflicting firmware file is kept and reported. In Overwrite mode, older Pocket update files are backed up to the computer before replacement.
5. When the report says the update is ready, safely eject the card or USB connection.
6. Fully power off the Pocket, insert the card if necessary, and power it on. Allow **3–4 minutes** and keep power on until it finishes and restarts.

For a combined install, cores and games are processed first and the firmware file is prepared last. The Pocket performs the actual firmware update at the next full power-on. [Analogue firmware instructions](https://www.analogue.co/support/resource/updating-firmware)

## Reports and help

Click **Open report** after a completed run. Reports and reusable download caches are stored in these folders.

| Platform | Folder |
| --- | --- |
| Windows | %LOCALAPPDATA%\Pocket Guide Installer |
| macOS | ~/Library/Application Support/Pocket Guide Installer |
| Linux | ~/.local/share/pocket-guide-installer, or $XDG_DATA_HOME/pocket-guide-installer |

**Install report.txt** is the readable summary. **Last install.json** contains the structured result. A stopped run can be resumed by rerunning the selection with **Add missing files**.

If you need help, open an [issue](https://github.com/printwizardscxcare-design/pocket-guide-installer/issues) with your OS, app version, the package you downloaded, and the relevant report message.

Core availability and compatibility vary. Some arcade builds need publisher-issued licenses. Some systems need separately supplied games, BIOS files, or disc images. Check the [project overview](README.md#availability-and-testing) and [upstream credits](CREDITS.md) for the included sources and known exceptions.

## Following installation progress

The **Installation activity** tab opens when installation starts. Active files appear above the completed history. Select a file to read its full path or any error.

The first progress bar counts files finished in the current step. During game and system downloads, a second bar shows bytes downloaded or found in the verified cache, with average download speed and the number of active transfers. Reaching the end of the download bar can still leave verification and card copying to finish. Items needing attention count as finished attempts and are clearly marked.

Local imports count game files and archives checked. A ZIP may contain several games. **Open report** shows a saved record of file outcomes after installation finishes.

The time estimate appears after a short measurement period and applies to the current step. It uses file progress for core and local imports, and byte progress with an allowance for verification and card writes for downloads. It updates as the speed changes and pauses when no progress is observed. Later steps are estimated when they begin.

## Understanding items to review

A core can be installed while its game content is absent. Donkey Kong Junior and Radar Scope need their own compatible game files. Neo Geo needs game data in per-game folders under `Assets/ng/common`; its BIOS and support files alone do not supply games. PC Engine CD needs a game CUE/BIN image. The filenames in `image_template.json` are examples.

Some bundled Coin-Op Collection core builds need the developer's beta access key. See the [upstream access instructions](https://github.com/Coin-OpCollection/Distribution-OpenFPGA#beta-access--pocket-updater). A core beta key and the game files are separate requirements.

Legacy `.smd` filenames can sometimes contain raw Genesis data. The importer accepts structurally recognizable raw images without altering their bytes, or decodes supported interleaved SMD images, and imports the result as `.md`. Unrecognized images are reported rather than guessed.

## Neo Geo: SROM missing / ID 3

**No file for SROM ID [3]** means the selected launch definition cannot find that game's SROM file. The game names in the core's menu are launch presets; they do not prove the game data is installed.

For this Neo Geo core, games use the compatible per-game folder format described in the [core developer's instructions](https://github.com/Mazamars312/Analogue_Pocket_Neogeo#installation-and-usage). Each game folder usually contains `srom`, `prom`, `crom0`, `m1rom` and `vroma0`, with additional files for some games. A generic MAME ZIP or a `.neo` image is not automatically the same format.

For example, Galaxy Fight Universal Warriors uses `Assets/ng/common/galaxyfg/`. Its five game files belong inside that folder. The three shared BIOS/support files stay directly under `Assets/ng/common`. Renaming `sfix.sfix` to `srom` does not supply Galaxy Fight's game data.

To import a compatible pack, choose your card, select the Neo Geo core, enable **Import compatible games**, and choose the computer folder containing the per-game directories or ZIPs. Use **Add missing files** to preserve existing different files. The installer imports recognized components and reports which launch definitions still have missing game files. It does not obtain missing Neo Geo games for you.

The JSON report includes the exact missing filenames for each game under `neo_geo`. Readiness means required game files are present and nonempty; it does not verify their contents against a known ROM dump or prove successful playback on a physical Pocket.
