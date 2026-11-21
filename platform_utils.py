"""Host paths and mounted Pocket cards for Windows, macOS, and Linux."""

import ctypes
import os
from pathlib import Path
import subprocess
import sys


def app_data_dir():
    if sys.platform == "win32":
        return (
            Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
            / "Pocket Guide Installer"
        )
    if sys.platform == "darwin":
        return (
            Path.home() / "Library" / "Application Support" / "Pocket Guide Installer"
        )
    return (
        Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        / "pocket-guide-installer"
    )


def is_card_root(root):
    root = root.absolute()
    if sys.platform == "win32":
        return root == Path(root.anchor) and root != Path(
            os.environ.get("SystemDrive", "C:") + "/"
        )
    return root.resolve() != Path("/") and os.path.ismount(root)


def detected_cards():
    candidates = []
    if sys.platform == "win32":
        mask = ctypes.windll.kernel32.GetLogicalDrives()
        candidates = [Path(chr(65 + i) + ":/") for i in range(26) if mask & (1 << i)]
    else:
        parents = (
            [Path("/Volumes")]
            if sys.platform == "darwin"
            else [Path("/media"), Path("/run/media"), Path("/mnt")]
        )
        for parent in parents:
            try:
                for child in parent.iterdir():
                    if child.is_dir():
                        candidates.append(child)
                        if not os.path.ismount(child):
                            candidates.extend(p for p in child.iterdir() if p.is_dir())
            except OSError:
                continue
        if sys.platform.startswith("linux"):
            try:
                for line in Path("/proc/self/mountinfo").read_text().splitlines():
                    mount = line.split()[4]
                    for old, new in [(r"\040", " "), (r"\011", "\t"), (r"\134", "\\")]:
                        mount = mount.replace(old, new)
                    candidates.append(Path(mount))
            except OSError:
                pass
    found = []
    for card in candidates:
        try:
            if is_card_root(card) and (card / "Analogue_Pocket.json").is_file():
                found.append(str(card))
        except OSError:
            continue
    return sorted(set(found))


def open_file(path):
    if sys.platform == "win32":
        os.startfile(path)
    else:
        subprocess.Popen(
            ["open" if sys.platform == "darwin" else "xdg-open", str(path)]
        )
