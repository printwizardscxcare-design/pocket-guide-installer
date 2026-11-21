"""Offline checks run against source and the packaged application on each OS."""

import contextlib
import io
import json
from pathlib import Path
import tempfile
import tkinter as tk
from unittest.mock import patch
import zipfile


def run(report=None):
    import pocket
    import interface
    import platform_utils

    # Use the running __main__ module in frozen diagnostics so the checked
    # catalog and worker are the ones loaded by the packaged entry point.
    import sys

    engine = sys.modules.get("__main__")
    if not hasattr(engine, "install"):
        engine = pocket
    with tempfile.TemporaryDirectory() as folder:
        base = Path(folder)
        card = base / "card"
        card.mkdir()
        cache = base / "cache" / "Downloads"
        cache.mkdir(parents=True)
        marker = {
            "product": "Analogue Pocket",
            "firmware": {"runtime": {"name": "2.7"}},
        }
        (card / "Analogue_Pocket.json").write_text(json.dumps(marker))
        fixture = base / "fixture.zip"
        with zipfile.ZipFile(fixture, "w") as archive:
            archive.writestr(
                "Cores/Fixture.Test/core.json",
                '{"core":{"metadata":{"platform_ids":["gb"]}}}',
            )
            archive.writestr("Cores/Fixture.Test/fixture.rev", b"offline fixture")
            archive.writestr("Platforms/gb.json", '{"platform":{"name":"Fixture"}}')
        catalog = {
            "packages": {"Fixture.Test": "unused"},
            "core_info": {
                "Fixture.Test": {
                    "platforms": ["gb"],
                    "category": "Handheld",
                    "name": "Fixture",
                }
            },
            "assets": {},
            "asset_info": {},
            "licenses": [],
            "asset_gaps": [],
            "rows": [],
            "unavailable_games": [],
        }
        engine.STOP.clear()
        (card / "Saves").mkdir()
        sentinel = card / "Saves" / "preserve.sav"
        sentinel.write_bytes(b"save")
        assert not platform_utils.is_card_root(Path.home())
        assert not engine.clean("CON") and not engine.clean("../escape")
        for mode in ("add", "overwrite"):
            with (
                patch.object(engine, "CAT", catalog),
                patch.object(engine, "CACHE", cache),
                patch.object(engine, "is_card_root", lambda p: p == card),
                patch.object(engine, "fetch", lambda _: ("Fixture.Test", fixture)),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                result = engine.install(
                    card, None, mode, {"Fixture.Test"}, set(), False
                )
            assert result["processed_cores"] == ["Fixture.Test"]
            binary = card / "Cores" / "Fixture.Test" / "fixture.rev"
            assert binary.read_bytes() == b"offline fixture"
            binary.write_bytes(b"changed")
        assert sentinel.read_bytes() == b"save"
        # Existing files survive Add and are refreshed by Overwrite.
        dest = card / "Assets" / "gb" / "common" / "test.gb"
        assert engine.write_verified(dest, b"one", False) == "written"
        assert engine.write_verified(dest, b"two", False) == "conflict"
        assert dest.read_bytes() == b"one"
        assert engine.write_verified(dest, b"two", True) == "written"
        assert dest.read_bytes() == b"two"
        assert "skipped" in engine.prepare_firmware(card, False)
        root = tk.Tk()
        root.withdraw()
        app = interface.Installer(
            root, engine.CAT, engine.install, engine.STOP, cache.parent
        )
        app.firmware_only()
        assert app.model.selected == {"firmware"} and not app.import_games.get()
        app.search.set("SNES")
        root.update()
        assert any("SNES" in k for keys in app.groups.values() for k in keys)
        icon = engine.BUNDLE / "assets" / "pocket.png"
        root.iconphoto(True, tk.PhotoImage(file=str(icon)))
        root.update()
        root.destroy()
    if report:
        Path(report).write_text(
            "PASS — startup, GUI, selection, isolated card writes, Add/Overwrite, save preservation, firmware version check, and icon.\n",
            encoding="utf8",
        )


if __name__ == "__main__":
    run()
    print("Platform smoke checks passed")
