import argparse
import concurrent.futures
import hashlib
import json
import ntpath
import os
import re
import shutil
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

import downloads
from platform_utils import app_data_dir, is_card_root

STOP = threading.Event()


class InstallStopped(BaseException):
    pass


def checkpoint():
    if STOP.is_set():
        raise InstallStopped()


BUNDLE = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
CAT = json.loads((BUNDLE / "manifest.json").read_text("utf-8-sig"))
CACHE = app_data_dir() / "Downloads"
ROOTS = {"assets": "Assets", "cores": "Cores", "platforms": "Platforms"}
EXT = {
    "gb": "gb",
    "gbc": "gbc",
    "gba": "gba",
    "nes": "nes",
    "sfc": "snes",
    "smc": "snes",
    "md": "genesis",
    "gen": "genesis",
    "smd": "genesis",
    "gg": "gg",
    "sms": "sms",
    "pce": "pce",
    "ws": "wonderswan",
    "wsc": "wonderswan",
    "lnx": "lynx",
    "a26": "2600",
    "a78": "7800",
}


def clean(name):
    return (
        name not in (".", "..", "")
        and not re.search(r'[<>:"/\\|?*\x00-\x1f]', name)
        and not name.endswith((".", " "))
        and not ntpath.isreserved(name)
    )


def output_path(root, parts):
    if not all(clean(p) for p in parts):
        raise ValueError("Invalid archive path " + str(parts))
    path = root.joinpath(*parts)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Path outside target")
    return path


def fetch(item):
    checkpoint()
    key, url = item
    url = urllib.parse.quote(url, safe=":/%?=&+")
    file = CACHE / (hashlib.sha256(url.encode()).hexdigest() + ".zip")
    expected = CAT["sha256"][key]
    if file.exists() and hashlib.sha256(file.read_bytes()).hexdigest() == expected:
        return key, file
    error = None
    for attempt in range(3):
        try:
            with (
                urllib.request.urlopen(
                    urllib.request.Request(
                        url, headers={"User-Agent": "PocketGuideInstaller"}
                    ),
                    timeout=50,
                ) as response,
                tempfile.NamedTemporaryFile(dir=CACHE, delete=False) as dest,
            ):
                tmp = Path(dest.name)
                try:
                    shutil.copyfileobj(response, dest)
                except BaseException:
                    dest.close()
                    tmp.unlink(missing_ok=True)
                    raise
            if (
                not zipfile.is_zipfile(tmp)
                or hashlib.sha256(tmp.read_bytes()).hexdigest() != expected
            ):
                tmp.unlink()
                raise ValueError("Invalid ZIP download")
            tmp.replace(file)
            return key, file
        except Exception as e:
            error = e
            time.sleep(attempt + 1)
    raise RuntimeError(str(error))


def write_verified(dest, data, replace):
    checkpoint()
    digest = hashlib.sha256(data).digest()
    if dest.is_file():
        if (
            dest.stat().st_size == len(data)
            and hashlib.sha256(dest.read_bytes()).digest() == digest
        ):
            return "present"
        if not replace:
            return "conflict"
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=dest.parent, delete=False) as f:
        tmp = Path(f.name)
        try:
            f.write(data)
        except BaseException:
            f.close()
            tmp.unlink(missing_ok=True)
            raise
    try:
        if hashlib.sha256(tmp.read_bytes()).digest() != digest:
            raise OSError("Verification failed " + str(dest))
        os.replace(tmp, dest)
    finally:
        tmp.unlink(missing_ok=True)
    return "written"


def install_core(root, key, archive, overwrite, report):
    platforms = {x.casefold() for x in CAT["core_info"][key]["platforms"]}
    with zipfile.ZipFile(archive) as z:
        files = []
        for info in z.infolist():
            parts = info.filename.replace("\\", "/").split("/")
            if info.is_dir() or any(
                p.startswith(".") or p == "__MACOSX" for p in parts
            ):
                continue
            pos = next((i for i, p in enumerate(parts) if p.lower() in ROOTS), None)
            if pos is None:
                continue
            parts = parts[pos:]
            parts[0] = ROOTS[parts[0].lower()]
            if len(parts) < 2:
                continue
            if parts[0] == "Cores" and parts[1].casefold() != key.casefold():
                continue
            if parts[0] == "Assets":
                if parts[1].casefold() not in platforms:
                    continue
                if (
                    len(parts) > 2
                    and "." in parts[2]
                    and len(parts) > 3
                    and parts[2].lower() != key.lower()
                ):
                    continue
            if (
                parts[0] == "Platforms"
                and Path(parts[-1]).stem.casefold() not in platforms
            ):
                continue
            files.append((info, output_path(root, parts), parts))
        if not any(
            len(p) == 3 and p[0] == "Cores" and p[2].lower() == "core.json"
            for _, _, p in files
        ):
            raise ValueError("Core manifest absent from package")
        if not any(
            p[0] == "Cores" and p[-1].lower().endswith((".rbf", ".rev", ".rbf_r"))
            for _, _, p in files
        ):
            raise ValueError("Core binary absent from package")
        for info, path, parts in files:
            state = write_verified(
                path,
                z.read(info),
                overwrite,
            )
            if state == "conflict":
                report.append("Kept existing file: " + str(path))


def decode_smd(data):
    """Decode copier blocks, or preserve an already raw cartridge image."""
    if data[256:260] == b"SEGA":
        return data
    # Some old sets label raw dumps as SMD. Early/unlicensed games need not
    # have a SEGA header; validate their 68000 reset vectors instead.
    if len(data) >= 16384 and len(data) % 16384 == 0:
        stack = int.from_bytes(data[:4], "big")
        entry = int.from_bytes(data[4:8], "big")
        valid_stack = stack == 0x1000000 or (
            stack >> 24 in (0, 255) and 0xFF0000 <= (stack & 0xFFFFFF) <= 0xFFFFFF
        )
        if valid_stack and 8 <= entry < len(data) and entry % 2 == 0:
            return data
    body = data[512:]
    if not body or len(body) % 16384:
        raise ValueError("Unsupported SMD layout")
    decoded = bytearray(len(body))
    for off in range(0, len(body), 16384):
        decoded[off : off + 16384 : 2] = body[off + 8192 : off + 16384]
        decoded[off + 1 : off + 16384 : 2] = body[off : off + 8192]
    if decoded[256:260] != b"SEGA":
        raise ValueError("Unrecognized SMD cartridge header")
    return bytes(decoded)


def content_requirements(root, platforms):
    """Separate missing game content from generic example slot filenames."""
    missing = []
    for name in CAT.get("asset_gaps", []):
        platform = name.split("/")[1].lower()
        if platform not in platforms or platform in {"ng", "pcecd"}:
            continue
        if not output_path(root, name.split("/")).is_file():
            missing.append("Additional game or system file: " + name)
    if "ng" in platforms:
        common = root / "Assets" / "ng" / "common"
        if not common.exists() or not any(
            p.name == "crom0" for p in common.rglob("crom0") if p.is_file()
        ):
            missing.append(
                "Neo Geo: no compatible game data was found. Games need their own folders under Assets/ng/common; BIOS/support files alone do not include games, and generic crom0/prom names are not standalone downloads."
            )
    if "pcecd" in platforms:
        common = root / "Assets" / "pcecd" / "common"
        if not common.exists() or not any(
            p.suffix.lower() == ".cue" for p in common.rglob("*") if p.is_file()
        ):
            missing.append(
                "PC Engine CD: no game CUE/BIN image was found under Assets/pcecd/common. The image.cue and 30 track names in image_template.json are examples, not 31 failed downloads."
            )
    return missing


def games(root, extra, report, overwrite, platforms, progress=None):
    assets = root / "Assets"
    sources = [assets] + (
        [extra] if extra and extra.resolve() != assets.resolve() else []
    )
    counts = Counter()
    sources_and_paths = []
    for source in sources:
        on_card = source == assets
        paths = [
            p
            for p in source.rglob("*")
            if p.is_file()
            and (
                p.suffix.lower() == ".zip"
                or (
                    p.suffix.lower()[1:] in EXT
                    or (
                        p.suffix.lower() == ".bin"
                        and "genesis" in [x.lower() for x in p.parts]
                    )
                )
                and (
                    not on_card
                    or len(p.relative_to(source).parts) > 2
                    and p.relative_to(source).parts[1].lower() != "common"
                    and "." not in p.relative_to(source).parts[1]
                )
            )
        ]
        sources_and_paths.append((source, on_card, paths))
    total = sum(len(paths) for _, _, paths in sources_and_paths)
    if progress:
        progress({"type": "stage", "stage": "games", "total": total})
    for source, on_card, paths in sources_and_paths:
        for idx, path in enumerate(paths, 1):
            checkpoint()
            before = counts.copy()
            issue_count = len(report)
            if progress:
                progress(
                    {
                        "type": "item",
                        "stage": "games",
                        "key": str(path),
                        "status": "Checking game archive"
                        if path.suffix.lower() == ".zip"
                        else "Importing game",
                    }
                )
            try:

                def place(name, data):
                    filename = Path(name.replace("\\", "/")).name
                    ext = Path(filename).suffix[1:].lower()
                    if ext == "bin" and "genesis" in [x.lower() for x in path.parts]:
                        platform = "genesis"
                    elif ext in EXT:
                        platform = EXT[ext]
                    else:
                        return
                    if platform not in platforms:
                        return
                    if ext == "smd":
                        data = decode_smd(data)
                        filename = Path(filename).stem + ".md"
                    if ext == "gen":
                        filename = Path(filename).stem + ".md"
                    if not filename:
                        return
                    if on_card:
                        rel = path.relative_to(source)
                        if rel.parts[0].lower() == platform:
                            sub = list(rel.parts[1:-1])
                            if sub and sub[0].lower() == "common":
                                sub = sub[1:]
                        else:
                            sub = ["Imported"]
                    else:
                        sub = ["Imported"] + list(path.relative_to(source).parts[:-1])
                    dest = output_path(
                        root, ["Assets", platform, "common"] + sub + [filename]
                    )
                    if progress:
                        progress(
                            {
                                "type": "item",
                                "stage": "games",
                                "key": str(path),
                                "status": "Copying game to card",
                                "detail": filename,
                            }
                        )
                    state = write_verified(dest, data, overwrite)
                    counts[state] += 1
                    if state == "conflict":
                        report.append("Game name conflict: " + str(dest))

                if path.suffix.lower() == ".zip":
                    with zipfile.ZipFile(path) as z:
                        for f in z.infolist():
                            if (
                                not f.is_dir()
                                and not any(
                                    part.startswith((".", "__MACOSX"))
                                    for part in f.filename.split("/")
                                )
                                and Path(f.filename).suffix[1:].lower() in EXT
                                and f.file_size <= 128 * 1024 * 1024
                            ):
                                place(f.filename, z.read(f))
                else:
                    place(path.name, path.read_bytes())
            except Exception as e:
                if not (root / "Analogue_Pocket.json").exists():
                    raise OSError("Pocket disconnected") from e
                report.append(str(path) + ": " + str(e))
            if progress:
                written = counts["written"] - before["written"]
                present = counts["present"] - before["present"]
                attention = len(report) > issue_count
                status = (
                    "Needs attention"
                    if attention
                    else "Imported"
                    if written
                    else "Already on card"
                    if present
                    else "No compatible games"
                )
                progress(
                    {
                        "type": "item",
                        "stage": "games",
                        "key": str(path),
                        "status": status,
                        "finished": True,
                        "error": attention,
                        "detail": f"{written} written, {present} already matched"
                        + (" · " + report[-1] if attention else ""),
                    }
                )
            if idx % 250 == 0:
                print("Game archives checked", idx, "of", len(paths), flush=True)
    return dict(counts)


def prepare_firmware(root, overwrite):
    version = "2.7"
    name = "pocket_firmware_2_7.bin"
    expected = "ac5848b97fa8272b2257a45d9c41dbe6"
    current = (
        json.loads((root / "Analogue_Pocket.json").read_text("utf-8-sig"))
        .get("firmware", {})
        .get("runtime", {})
        .get("name", "")
    )
    try:
        if tuple(map(int, current.split("."))) >= tuple(map(int, version.split("."))):
            return f"Pocket reports firmware {current}. Update file skipped."
    except ValueError:
        pass
    destination = root / name
    other = [
        f
        for f in root.iterdir()
        if f.is_file()
        and f.suffix.lower() == ".bin"
        and f.name.lower().startswith("pocket_firmware")
        and f.name.lower() != name
    ]
    if other and not overwrite:
        return "Firmware skipped. Other Pocket firmware files are on the card. Use Overwrite matching files to back them up and replace them."
    print("Preparing Pocket firmware 2.7…", flush=True)
    cache = CACHE.parent / "Firmware"
    cache.mkdir(exist_ok=True)
    local = cache / name
    if not local.is_file() or hashlib.md5(local.read_bytes()).hexdigest() != expected:
        with urllib.request.urlopen(
            "https://www.analogue.co/support/pocket/firmware/2.7/download", timeout=60
        ) as response:
            data = response.read()
        if len(data) != 54525952 or hashlib.md5(data).hexdigest() != expected:
            raise ValueError("Pocket firmware checksum mismatch")
        write_verified(local, data, True)
    data = local.read_bytes()
    if hashlib.md5(data).hexdigest() != expected:
        raise ValueError("Pocket firmware checksum mismatch")
    checkpoint()
    # Keep a verified PC backup before removing an older update from the SD root.
    for old in other:
        backup = (
            cache
            / "Previous updates"
            / (hashlib.sha256(old.read_bytes()).hexdigest() + "-" + old.name)
        )
        write_verified(backup, old.read_bytes(), False)
    state = write_verified(destination, data, overwrite)
    if state == "conflict":
        return "Firmware skipped. Existing firmware file differs. Select Overwrite matching files to replace it."
    for old in other:
        checkpoint()
        old.unlink()
    return "Firmware 2.7 is ready on the card. Safely eject, fully power off the Pocket, then power on with the card inserted. Allow 3–4 minutes and keep power on until the Pocket restarts."


def install(
    card,
    game_folder,
    mode,
    core_ids,
    asset_ids,
    import_games=True,
    firmware=False,
    progress=None,
):
    root = Path(card).absolute()
    overwrite = mode == "overwrite"
    if (
        not is_card_root(root)
        or not (root / "Analogue_Pocket.json").is_file()
        or json.loads((root / "Analogue_Pocket.json").read_text("utf-8-sig")).get(
            "product"
        )
        != "Analogue Pocket"
    ):
        raise ValueError("Select the root of an initialized Analogue Pocket card.")
    if game_folder and (
        not game_folder.is_dir()
        or game_folder.resolve().is_relative_to(root.resolve())
        or root.resolve().is_relative_to(game_folder.resolve())
    ):
        raise ValueError("Choose an existing game folder outside the card.")
    CACHE.mkdir(parents=True, exist_ok=True)
    report = []
    installed = []
    activity = []
    stages = [
        name
        for name, enabled in (
            ("cores", core_ids),
            ("assets", asset_ids),
            ("games", import_games),
            ("firmware", firmware),
        )
        if enabled
    ]

    def emit(event):
        if event.get("finished"):
            activity.append(event.copy())
        if progress:
            progress(event)

    def stage(name, total=None, **values):
        emit(
            {
                "type": "stage",
                "stage": name,
                "total": total,
                "step": stages.index(name) + 1,
                "steps": len(stages),
                **values,
            }
        )

    if core_ids:
        stage("cores", len(core_ids))

    def fetch_core(item):
        key = item[0]
        emit(
            {"type": "item", "stage": "cores", "key": key, "status": "Downloading core"}
        )
        return fetch(item)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = {
            pool.submit(fetch_core, item): item[0]
            for item in CAT["packages"].items()
            if item[0] in core_ids
        }
        for future in concurrent.futures.as_completed(futures):
            checkpoint()
            key = futures[future]
            try:
                key, file = future.result()
                emit(
                    {
                        "type": "item",
                        "stage": "cores",
                        "key": key,
                        "status": "Installing core",
                    }
                )
                before_issues = len(report)
                install_core(root, key, file, overwrite, report)
                installed.append(key)
                emit(
                    {
                        "type": "item",
                        "stage": "cores",
                        "key": key,
                        "status": "Existing files kept"
                        if len(report) > before_issues
                        else "Core installed",
                        "detail": f"{len(report) - before_issues} files to review"
                        if len(report) > before_issues
                        else "",
                        "finished": True,
                        "error": len(report) > before_issues,
                    }
                )
                print("Processed", key, flush=True)
            except Exception as e:
                if not (root / "Analogue_Pocket.json").exists():
                    raise OSError("Pocket disconnected") from e
                report.append(key + ": " + str(e))
                emit(
                    {
                        "type": "item",
                        "stage": "cores",
                        "key": key,
                        "status": "Needs attention",
                        "detail": str(e),
                        "finished": True,
                        "error": True,
                    }
                )
                print("Skipped", key, e, flush=True)
    print("Installing game and system assets...", flush=True)

    def copy_asset(name, local):
        dest = output_path(root, name.split("/"))
        state = write_verified(dest, local.read_bytes(), overwrite)
        if state == "conflict":
            raise ValueError("Existing different file preserved")
        return state

    plan = {
        i: CAT["assets"][i]
        for i in asset_ids
        if set(CAT["asset_info"][i]["owners"]).intersection(installed)
    }
    if asset_ids:
        stage(
            "assets", len(asset_ids), sizes={i: CAT["assets"][i][2] for i in asset_ids}
        )
        for name in asset_ids - plan.keys():
            emit(
                {
                    "type": "item",
                    "stage": "assets",
                    "key": name,
                    "status": "Needs attention",
                    "detail": "Required core was not installed",
                    "size": CAT["assets"][name][2],
                    "finished": True,
                    "error": True,
                }
            )
            report.append(name + ": required core was not installed")
    asset_count, issues = downloads.transfer(
        plan,
        CACHE.parent / "Assets",
        copy_asset,
        STOP,
        emit,
    )
    report.extend(issues)
    for core in set(CAT["licenses"]).intersection(installed):
        report.append(
            "Coin-Op Collection beta access/key may be required for this core build: "
            + core
        )
    platforms = {p.lower() for i in installed for p in CAT["core_info"][i]["platforms"]}
    report.extend(content_requirements(root, platforms))
    checkpoint()
    print("Installing games...", flush=True)
    if import_games:
        stage("games", detail="Finding compatible game files…")
    counts = (
        games(root, game_folder, report, overwrite, platforms, emit)
        if import_games
        else {}
    )
    for r in CAT["rows"]:
        if set(r["cores"]).intersection(core_ids) and not set(r["cores"]).intersection(
            installed
        ):
            report.append("Guide entry needs attention: " + r["title"])
    checkpoint()
    firmware_status = "Firmware update was not selected."
    if firmware:
        stage("firmware", 1)
        emit(
            {
                "type": "item",
                "stage": "firmware",
                "key": "firmware",
                "status": "Preparing firmware 2.7",
            }
        )
        try:
            firmware_status = prepare_firmware(root, overwrite)
        except Exception as exc:
            firmware_status = "Firmware preparation failed: " + str(exc)
            report.append(firmware_status)
        emit(
            {
                "type": "item",
                "stage": "firmware",
                "key": "firmware",
                "status": "Needs attention"
                if firmware_status.startswith("Firmware preparation failed")
                else "Firmware checked",
                "detail": firmware_status,
                "finished": True,
                "error": firmware_status.startswith("Firmware preparation failed"),
            }
        )
    result = {
        "firmware": firmware_status,
        "unavailable_guide_games": CAT["unavailable_games"],
        "card": str(root),
        "mode": mode,
        "processed_cores": sorted(installed),
        "verified_game_and_system_assets": asset_count,
        "game_files": counts,
        "needs_attention": report,
        "activity": activity,
    }
    out = CACHE.parent / "Last install.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf8")
    lines = [
        "Pocket installation report",
        f"Card {root}   |   Mode {mode}",
        "",
        f"{len(installed)} of {len(core_ids)} selected cores processed",
        f"{asset_count} of {len(asset_ids)} selected game and system files verified",
        f"{counts.get('written', 0)} local game files written; {counts.get('present', 0)} already matched",
        "",
        firmware_status,
        "",
        "Items to review",
        *(report or ["None"]),
        "",
        "Guide games without a matched playable download",
        *CAT["unavailable_games"],
        "",
        "Processed cores",
        *sorted(installed),
        "",
        "File activity",
        *(
            f"{item['status']}: {item['key']}"
            + (" — " + item["detail"] if item.get("detail") else "")
            for item in activity
        ),
    ]
    (CACHE.parent / "Install report.txt").write_text(
        "\n".join(lines), encoding="utf-8-sig"
    )
    print(
        "Processed cores:",
        len(installed),
        "Game files:",
        counts,
        "Report:",
        out,
        flush=True,
    )

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke-test", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--smoke-report", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--card", type=Path)
    parser.add_argument("--games", type=Path)
    parser.add_argument("--firmware", action="store_true")
    parser.add_argument("--mode", choices=["add", "overwrite"], default="add")
    args = parser.parse_args()
    if args.smoke_test:
        from smoke_check import run

        run(args.smoke_report)
        return
    if args.card is None:
        from interface import launch

        launch(CAT, install, STOP, CACHE.parent)
    else:
        install(
            args.card,
            args.games,
            args.mode,
            set(CAT["packages"]),
            set(CAT["assets"]),
            True,
            args.firmware,
        )


if __name__ == "__main__":
    main()
