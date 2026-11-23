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
        # Raw dumps with legacy SMD extensions can lack Sega's standard header.
        raw = bytearray(16384)
        raw[4:8] = (512).to_bytes(4, "big")
        for stack in (0xFFFFFE, 0xFFFEFE, 0x1000000, 0xFFFFFFF8):
            raw[:4] = stack.to_bytes(4, "big")
            assert engine.decode_smd(bytes(raw)) == bytes(raw)
        raw[256:260] = b"SEGA"
        smd = bytes(512) + bytes(raw[1::2]) + bytes(raw[0::2])
        assert engine.decode_smd(smd) == bytes(raw)
        try:
            engine.decode_smd(b"invalid image")
            raise AssertionError("Invalid SMD was accepted")
        except ValueError:
            pass
        with patch.object(
            engine,
            "CAT",
            {
                "asset_gaps": [
                    "Assets/ng/common/crom0",
                    "Assets/pcecd/common/image.cue",
                    "Assets/pcecd/common/image (Track 01).bin",
                ]
            },
        ):
            requirements = engine.content_requirements(card, {"ng", "pcecd"})
            assert len(requirements) == 2 and "examples" in requirements[1]
            ng_game = card / "Assets/ng/common/fixture/crom0"
            ng_game.parent.mkdir(parents=True)
            ng_game.write_bytes(b"game")
            ng_definition = card / "Assets/ng/Mazamars312.NeoGeo/Fixture.json"
            ng_definition.parent.mkdir(parents=True)
            ng_definition.write_text(
                json.dumps(
                    {
                        "instance": {
                            "data_path": "fixture",
                            "data_slots": [
                                {"id": 3, "filename": "srom"},
                                {"id": 5, "filename": "crom0"},
                            ],
                        }
                    }
                )
            )
            assert any(
                "missing game data" in line
                for line in engine.content_requirements(card, {"ng"})
            )
            (ng_game.parent / "srom").write_bytes(b"game srom")
            cd_game = card / "Assets/pcecd/common/fixture/game.CUE"
            cd_game.parent.mkdir(parents=True)
            cd_game.write_text('FILE "game.bin" BINARY')
            assert not engine.content_requirements(card, {"ng", "pcecd"})
        # The video's SROM error: a menu definition without its game data is not ready.
        import neogeo

        neo_card = base / "neo-card"
        launch = neo_card / "Assets/ng/Mazamars312.NeoGeo/Galaxy Fight.json"
        launch.parent.mkdir(parents=True)
        components = ["srom", "prom", "crom0", "m1rom", "vroma0"]
        launch.write_text(
            json.dumps(
                {
                    "instance": {
                        "data_path": "galaxyfg",
                        "data_slots": [
                            {"id": i + 3, "filename": name}
                            for i, name in enumerate(components)
                        ],
                    }
                }
            )
        )
        assert neogeo.summary(neogeo.requirements(neo_card))["ready"] == 0
        assert "galaxyfg/srom" in neogeo.requirements(neo_card)[0]["missing"]
        neo_source = base / "neo-import"
        pack = neo_source / "galaxyfg"
        pack.mkdir(parents=True)
        for component in components:
            (pack / component).write_bytes(("fixture " + component).encode())
        neo_issues = []
        result = engine.games(neo_card, neo_source, neo_issues, False, {"ng"})
        assert result["written"] == 5 and not neo_issues
        assert neogeo.summary(neogeo.requirements(neo_card))["ready"] == 1
        for component in components:
            assert (
                neo_card / "Assets/ng/common/galaxyfg" / component
            ).read_bytes() == (pack / component).read_bytes()
        zip_source = base / "neo-zips"
        zip_source.mkdir()
        with zipfile.ZipFile(zip_source / "galaxyfg.zip", "w") as archive:
            for component in components:
                archive.writestr(component, (pack / component).read_bytes())
        result = engine.games(neo_card, zip_source, neo_issues, False, {"ng"})
        assert result.get("written", 0) == 0 and result["present"] == 5
        unsafe = launch.parent / "Unsafe.json"
        unsafe.write_text(
            json.dumps(
                {
                    "instance": {
                        "data_path": "../outside",
                        "data_slots": [{"filename": "srom"}],
                    }
                }
            )
        )
        assert not any(key[0] == "outside" for key in neogeo.import_targets(neo_card))
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
        # Cached bytes must not make a slow network transfer look almost finished.
        app.stage_id = "assets"
        app.stage_total = 2
        app.stage_sizes = {"cached": 900, "network": 100}
        app.stage_items = {
            "cached": {"received": 900, "finished": True},
            "network": {"received": 10},
        }
        app.stage_started = app.estimate_started = 90
        app.network_bytes = 10
        with patch.object(interface.time, "monotonic", return_value=100):
            app.update_metrics()
            assert "About 2 min left in this step" in app.eta.get()
            app.network_bytes = 0
            app.update_metrics()
            assert "Estimating" in app.eta.get()
        with patch.object(interface.time, "monotonic", return_value=125):
            app.update_metrics()
            assert "paused" in app.eta.get()
        app.stage_items["network"]["received"] = 100
        app.network_bytes = 100
        with patch.object(interface.time, "monotonic", return_value=126):
            app.update_metrics()
            assert "Finishing verification" in app.eta.get()
        app.stage_items["network"]["finished"] = True
        with patch.object(interface.time, "monotonic", return_value=127):
            app.update_metrics()
            assert app.eta.get() == "This step is finished"
        icon = engine.BUNDLE / "assets" / "pocket.png"
        root.iconphoto(True, tk.PhotoImage(file=str(icon)))
        root.update()
        root.destroy()
    if report:
        Path(report).write_text(
            "PASS — startup, GUI, selection, isolated card writes, Add/Overwrite, save preservation, firmware version check, icon, live download/cached progress, cancellation, conflicts, game import outcomes, activity history and time estimates (cache, stalls, verification, finish).\n",
            encoding="utf8",
        )


if __name__ == "__main__":
    run()
    print("Platform smoke checks passed")
