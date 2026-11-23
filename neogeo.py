"""Resolve Neo Geo launch definitions to the game data they actually require."""

import json
from pathlib import Path, PurePosixPath

CORE = "Mazamars312.NeoGeo"


def requirements(root):
    common = root / "Assets" / "ng" / "common"
    games = []
    for launcher in sorted((root / "Assets" / "ng" / CORE).glob("*.json")):
        try:
            instance = json.loads(launcher.read_text("utf-8-sig"))["instance"]
            folder = PurePosixPath(instance.get("data_path", "").replace("\\", "/"))
            if folder.is_absolute() or ".." in folder.parts or not folder.parts:
                continue
            files = []
            for slot in instance.get("data_slots", []):
                name = slot.get("filename")
                if (
                    not isinstance(name, str)
                    or not name
                    or slot.get("required") is False
                ):
                    continue
                relative = folder / PurePosixPath(name.replace("\\", "/"))
                target = common.joinpath(*relative.parts)
                if (
                    relative.is_absolute()
                    or ".." in relative.parts
                    or not target.resolve().is_relative_to(common.resolve())
                ):
                    raise ValueError("Game path is outside the common folder")
                files.append(relative.as_posix())
            if files:
                games.append(
                    {
                        "game": launcher.stem,
                        "folder": folder.as_posix(),
                        "files": files,
                        "missing": [
                            name
                            for name in files
                            if not (common / name).is_file()
                            or (common / name).stat().st_size == 0
                        ],
                    }
                )
        except (OSError, ValueError, KeyError, TypeError) as error:
            games.append(
                {
                    "game": launcher.stem,
                    "folder": "",
                    "files": [],
                    "missing": [],
                    "error": str(error),
                }
            )
    return games


def import_targets(root):
    """Use the installed definitions, rather than guessing destinations."""
    targets = {}
    for game in requirements(root):
        if game.get("error"):
            continue
        for name in game["files"]:
            parts = PurePosixPath(name).parts
            if len(parts) == 2:
                targets[(parts[0].casefold(), parts[1].casefold())] = [
                    "Assets",
                    "ng",
                    "common",
                    *parts,
                ]
    return targets


def import_target(targets, member, source):
    member = PurePosixPath(member.replace("\\", "/"))
    folders = [member.parent.name, source.parent.name]
    if source.suffix.lower() == ".zip":
        folders.append(source.stem)
    for folder in folders:
        target = targets.get((folder.casefold(), member.name.casefold()))
        if target:
            return target
    return None


def summary(games):
    ready = sum(not game["missing"] and not game.get("error") for game in games)
    return {"ready": ready, "unavailable": len(games) - ready, "games": games}
