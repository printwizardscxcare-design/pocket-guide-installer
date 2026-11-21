"""Build native release archives on the corresponding operating system."""

import hashlib
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile

version = sys.argv[1].removeprefix("v") if len(sys.argv) > 1 else "1.2.0"
arch = "arm64" if platform.machine().lower() in ("arm64", "aarch64") else "x64"
target = (
    "windows"
    if sys.platform == "win32"
    else ("macos" if sys.platform == "darwin" else "linux")
)
out = Path("release")
out.mkdir(exist_ok=True)
name = f"PocketGuideInstaller-{version}-{target}-{arch}"
command = [
    sys.executable,
    "-m",
    "PyInstaller",
    "--noconfirm",
    "--clean",
    "--windowed",
    "--name",
    "PocketGuideInstaller",
    "--add-data",
    "manifest.json:.",
    "--add-data",
    "assets:assets",
    "--add-data",
    "CREDITS.md:.",
    "--add-data",
    "README.md:.",
]
if target == "macos":
    command += [
        "--onedir",
        "--icon",
        "assets/pocket.icns",
        "--osx-bundle-identifier",
        "com.printwizardscxcare.pocketguideinstaller",
    ]
else:
    command += ["--onefile", "--icon", "assets/pocket.ico"]
if target == "linux":
    # Use the distribution's font libraries with its own font configuration.
    # Bundling the older build host's fontconfig breaks current Arch configs.
    makespec = [shutil.which("pyi-makespec")] + [
        arg for arg in command[3:] if arg not in ("--noconfirm", "--clean")
    ]
    subprocess.run(makespec + ["pocket.py"], check=True)
    spec = Path("PocketGuideInstaller.spec")
    text = spec.read_text()
    text = text.replace(
        "pyz = PYZ",
        'a.binaries = [entry for entry in a.binaries if not entry[0].startswith(("libfontconfig.so", "libfreetype.so"))]\npyz = PYZ',
    )
    spec.write_text(text)
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", str(spec)],
        check=True,
    )
else:
    subprocess.run(command + ["pocket.py"], check=True)
if target == "windows":
    binary = Path("dist/PocketGuideInstaller.exe")
elif target == "macos":
    binary = Path("dist/PocketGuideInstaller.app/Contents/MacOS/PocketGuideInstaller")
else:
    binary = Path("dist/PocketGuideInstaller")
report = out / "smoke-check.txt"
subprocess.run(
    [str(binary.resolve()), "--smoke-test", "--smoke-report", str(report.resolve())],
    check=True,
    timeout=120,
)
assert report.is_file(), "Packaged startup check did not write its report"
print(report.read_text())
if target == "windows":
    shutil.copy2(binary, out / (name + ".exe"))
elif target == "macos":
    app = Path("dist/PocketGuideInstaller.app")
    subprocess.run(["codesign", "--verify", "--deep", "--strict", str(app)], check=True)
    subprocess.run(
        [
            "ditto",
            "-c",
            "-k",
            "--sequesterRsrc",
            "--keepParent",
            str(app),
            str(out / (name + ".zip")),
        ],
        check=True,
    )
    dmg = Path("build/dmg")
    dmg.mkdir(exist_ok=True)
    shutil.copytree(app, dmg / app.name, dirs_exist_ok=True)
    (dmg / "Applications").symlink_to("/Applications")
    subprocess.run(
        [
            "hdiutil",
            "create",
            "-volname",
            "Pocket Guide Installer",
            "-srcfolder",
            str(dmg),
            "-ov",
            "-format",
            "UDZO",
            str(out / (name + ".dmg")),
        ],
        check=True,
    )
else:
    stage = Path("build/linux-package")
    app = stage / "opt/pocket-guide-installer"
    app.mkdir(parents=True, exist_ok=True)
    shutil.copy2(binary, app / "PocketGuideInstaller")
    desktop = stage / "usr/share/applications"
    desktop.mkdir(parents=True, exist_ok=True)
    (desktop / "pocket-guide-installer.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=Pocket Guide Installer\nExec=/opt/pocket-guide-installer/PocketGuideInstaller\nIcon=pocket-guide-installer\nCategories=Utility;Game;\nTerminal=false\n",
        encoding="utf8",
    )
    icons = stage / "usr/share/icons/hicolor/256x256/apps"
    icons.mkdir(parents=True, exist_ok=True)
    from PIL import Image

    Image.open("assets/pocket.png").resize((256, 256)).save(
        icons / "pocket-guide-installer.png"
    )
    docs = stage / "usr/share/doc/pocket-guide-installer"
    docs.mkdir(parents=True, exist_ok=True)
    for doc in ("README.md", "CREDITS.md"):
        shutil.copy2(doc, docs / doc)
    for kind, suffix in (("deb", "deb"), ("rpm", "rpm"), ("pacman", "pkg.tar.gz")):
        cmd = [
            "fpm",
            "-s",
            "dir",
            "-t",
            kind,
            "-n",
            "pocket-guide-installer",
            "-v",
            version,
            "--architecture",
            "amd64",
            "--maintainer",
            "printwizardscxcare-design",
            "--description",
            "Selective Analogue Pocket openFPGA and firmware installer",
            "--url",
            "https://github.com/printwizardscxcare-design/pocket-guide-installer",
            "--package",
            str((out / (name + "." + suffix)).resolve()),
            "-C",
            str(stage),
            ".",
        ]
        if kind == "pacman":
            cmd[1:1] = ["--pacman-compression", "gz"]
        dependencies = {
            "deb": [
                "fonts-dejavu-core",
                "libx11-6",
                "libxext6",
                "libxrender1",
                "libxft2",
                "libxcb1",
                "fontconfig",
                "xdg-utils",
            ],
            "rpm": [
                "dejavu-sans-fonts",
                "libX11",
                "libXext",
                "libXrender",
                "libXft",
                "libxcb",
                "fontconfig",
                "xdg-utils",
            ],
            "pacman": [
                "ttf-dejavu",
                "libx11",
                "libxext",
                "libxrender",
                "libxft",
                "libxcb",
                "fontconfig",
                "xdg-utils",
            ],
        }
        for dependency in dependencies[kind]:
            cmd[1:1] = ["--depends", dependency]
        subprocess.run(cmd, check=True)
    with tarfile.open(out / (name + ".tar.gz"), "w:gz") as archive:
        archive.add(binary, arcname="PocketGuideInstaller")
        for doc in ("README.md", "CREDITS.md"):
            archive.add(doc, arcname=doc)
files = [p for p in out.iterdir() if p.name.startswith(name)]
(out / (name + "-SHA256SUMS.txt")).write_text(
    "".join(
        hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.name + "\n"
        for p in sorted(files)
    ),
    encoding="utf8",
)
