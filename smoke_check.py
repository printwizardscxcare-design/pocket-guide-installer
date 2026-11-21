"""Offline checks run against source and the packaged application on each OS."""

import contextlib
import hashlib
import io
import json
import tempfile
import threading
import tkinter as tk
import zipfile
from pathlib import Path
from unittest.mock import patch


def run(report=None):
    # Use the running __main__ module in frozen diagnostics so the checked
    # catalog and worker are the ones loaded by the packaged entry point.
    import sys

    import interface
    import platform_utils
    import pocket

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
            progress_events = []
            with (
                patch.object(engine, "CAT", catalog),
                patch.object(engine, "CACHE", cache),
                patch.object(engine, "is_card_root", lambda p: p == card),
                patch.object(engine, "fetch", lambda _: ("Fixture.Test", fixture)),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                result = engine.install(
                    card,
                    None,
                    mode,
                    {"Fixture.Test"},
                    set(),
                    False,
                    progress=progress_events.append,
                )
            assert result["processed_cores"] == ["Fixture.Test"]
            assert progress_events[0]["stage"] == "cores"
            assert progress_events[-1]["finished"]
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
        # Chunked transfers report live bytes, cached files, write results and failures.
        import downloads

        asset_cache = base / "asset-cache"
        asset_cache.mkdir()
        data = b"asset" * 100000
        digest = hashlib.sha1(data).hexdigest()
        spec = ("fixture.bin", digest, len(data))
        events = []
        with patch.object(
            downloads.urllib.request, "urlopen", lambda *a, **kw: io.BytesIO(data)
        ):
            done, errors = downloads.transfer(
                {"one": spec},
                asset_cache,
                lambda name, local: "written",
                threading.Event(),
                events.append,
            )
        assert done == 1 and not errors
        assert any(
            e["status"] == "Downloading" and e.get("received", 0) > 0 for e in events
        )
        assert any(e["status"] == "Verifying download" for e in events)
        assert events[-1]["status"] == "Installed" and events[-1]["finished"]
        events.clear()
        with patch.object(
            downloads.urllib.request,
            "urlopen",
            side_effect=AssertionError("Cached file requested network"),
        ):
            done, errors = downloads.transfer(
                {"one": spec},
                asset_cache,
                lambda name, local: "present",
                threading.Event(),
                events.append,
            )
        assert done == 1 and not errors and events[-1]["status"] == "Already on card"
        assert any(e["status"] == "Verified cache" for e in events)
        events.clear()

        def conflict(*args):
            raise ValueError("Existing different file preserved")

        done, errors = downloads.transfer(
            {"one": spec}, asset_cache, conflict, threading.Event(), events.append
        )
        assert done == 0 and len(errors) == 1 and events[-1]["error"]
        cancelled = threading.Event()

        def cancel_during_download(**event):
            if event["status"] == "Downloading":
                cancelled.set()

        with patch.object(
            downloads.urllib.request, "urlopen", lambda *a, **kw: io.BytesIO(data)
        ):
            try:
                downloads.get_file(spec, base, cancel_during_download, cancelled)
                raise AssertionError("Cancelled download returned a file")
            except downloads.TransferStopped:
                pass
        assert not (base / digest).exists()
        # Imports count every archive, including an unreadable ZIP, and preserve outcomes.
        local_games = base / "games"
        local_games.mkdir()
        (local_games / "fixture.gb").write_bytes(b"fixture game")
        (local_games / "broken.zip").write_bytes(b"not a zip")
        events.clear()
        issues = []
        counts = engine.games(card, local_games, issues, False, {"gb"}, events.append)
        assert counts["written"] == 1 and issues
        assert len([e for e in events if e.get("finished")]) == events[0]["total"]
        assert any(e.get("error") for e in events)
        root = tk.Tk()
        root.withdraw()
        with patch.object(interface, "detected_cards", lambda: []):
            app = interface.Installer(
                root, engine.CAT, engine.install, engine.STOP, cache.parent
            )
        app.firmware_only()
        assert app.model.selected == {"firmware"} and not app.import_games.get()
        app.search.set("SNES")
        root.update()
        assert any("SNES" in k for keys in app.groups.values() for k in keys)
        import time

        app.started_at = time.monotonic()
        app.show_progress(
            {
                "type": "stage",
                "stage": "assets",
                "total": 2,
                "step": 2,
                "steps": 3,
                "sizes": {"one": 100, "two": 100},
            }
        )
        app.show_progress(
            {
                "type": "item",
                "stage": "assets",
                "key": "one",
                "status": "Downloading",
                "received": 50,
                "size": 100,
            }
        )
        assert app.byte_progress["value"] == 25 and app.progress["value"] == 0
        app.show_progress(
            {
                "type": "item",
                "stage": "assets",
                "key": "one",
                "status": "Installed",
                "received": 100,
                "finished": True,
            }
        )
        assert app.progress["value"] == 50
        app.show_progress(
            {
                "type": "item",
                "stage": "assets",
                "key": "two",
                "status": "Needs attention",
                "finished": True,
                "error": True,
            }
        )
        assert app.progress["value"] == 100 and "1 to review" in app.progress_text.get()
        app.show_progress(
            {"type": "stage", "stage": "games", "total": 0, "step": 3, "steps": 3}
        )
        assert app.progress["value"] == 100 and len(app.activity.get_children()) == 2
        icon = engine.BUNDLE / "assets" / "pocket.png"
        root.iconphoto(True, tk.PhotoImage(file=str(icon)))
        root.update()
        root.destroy()
    if report:
        Path(report).write_text(
            "PASS — startup, GUI, selection, isolated card writes, Add/Overwrite, save preservation, firmware version check, icon, live download/cached progress, cancellation, conflicts, game import outcomes and activity history.\n",
            encoding="utf8",
        )


if __name__ == "__main__":
    run()
    print("Platform smoke checks passed")
