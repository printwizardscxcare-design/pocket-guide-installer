"""Desktop setup and selective installation."""

import contextlib
import ctypes
import math
import os
import queue
import shutil
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from platform_utils import detected_cards, open_file

BG = "#f1f2ee"
PAPER = "#ffffff"
INK = "#182420"
MUTED = "#52645c"
GREEN = "#175c45"
LINE = "#cad3ca"
UI_FONT = (
    "Segoe UI"
    if sys.platform == "win32"
    else ("Helvetica" if sys.platform == "darwin" else "DejaVu Sans")
)


class Checklist:
    def __init__(self, catalog):
        self.catalog = catalog
        self.items = {}
        categories = {
            "Console": "Home console cores",
            "Handheld": "Handheld cores",
            "Computer": "Computer cores",
            "Arcade": "Arcade cores",
            "Arcade Multi": "Arcade cores",
        }
        for key, info in catalog["core_info"].items():
            self.items[key] = (
                categories.get(info["category"], "Other cores"),
                info["name"],
                key + (" · license required" if key in catalog["licenses"] else ""),
            )
        for path, info in catalog["asset_info"].items():
            self.items[path] = (
                info["kind"],
                info["name"],
                path.split("/")[1] + " / " + path.split("/")[-1],
            )
        self.items["firmware"] = (
            "Pocket firmware",
            "Official firmware 2.7",
            "Apply on next full power-on",
        )
        self.selected = set(self.items)

    def change(self, keys, on):
        keys = set(keys)
        if on:
            self.selected.update(keys)
            for key in keys.intersection(self.catalog["assets"]):
                owners = self.catalog["asset_info"][key]["owners"]
                if not self.selected.intersection(owners):
                    self.selected.add(owners[0])
        else:
            self.selected.difference_update(keys)
            for name, meta in self.catalog["asset_info"].items():
                if not self.selected.intersection(meta["owners"]):
                    self.selected.discard(name)


class Installer:
    def __init__(self, root, catalog, install, stop, reportdir):
        self.root = root
        self.cat = catalog
        self.install = install
        self.stop = stop
        self.reportdir = reportdir
        self.model = Checklist(catalog)
        self.events = queue.Queue()
        self.running = False
        root.title("Pocket Guide Installer")
        root.geometry("1080x780")
        root.minsize(860, 680)
        root.configure(bg=BG)
        self.style = ttk.Style(root)
        self.style.theme_use("clam")
        self.style.configure(
            "Treeview",
            font=(UI_FONT, 10),
            rowheight=28,
            background=PAPER,
            fieldbackground=PAPER,
            foreground=INK,
            borderwidth=0,
        )
        self.style.configure(
            "Treeview.Heading",
            font=(UI_FONT, 9, "bold"),
            background=BG,
            foreground=MUTED,
        )
        self.style.map(
            "Treeview",
            background=[("selected", "#dcece2")],
            foreground=[("selected", INK)],
        )
        self.style.configure(
            "TProgressbar", background="#47a16e", troughcolor="#d7dfd7", borderwidth=0
        )
        self.card = tk.StringVar()
        self.folder = tk.StringVar()
        self.mode = tk.StringVar(value="add")
        self.import_games = tk.BooleanVar(value=True)
        self.search = tk.StringVar()
        self.summary = tk.StringVar()
        self.status = tk.StringVar()
        self.phase = tk.StringVar(value="Installation progress")
        self.progress_text = tk.StringVar(value="Ready")
        self.transfer_text = tk.StringVar()
        self.eta = tk.StringVar()
        self.stage_id = None
        self.stage_items = {}
        self.activity_rows = {}
        self.stage_total = 0
        self.stage_sizes = {}
        self.started_at = None
        self.card_info = tk.StringVar()
        self.groups = {}
        self.expanded = set()
        head = tk.Frame(root, bg=INK)
        head.pack(fill="x")
        tk.Label(
            head,
            text="Pocket Guide Installer",
            font=(UI_FONT, 22, "bold"),
            fg=PAPER,
            bg=INK,
        ).pack(side="left", padx=22, pady=13)
        tk.Label(
            head,
            text="openFPGA  /  microSD setup",
            font=(UI_FONT, 10),
            fg="#c4d7c9",
            bg=INK,
        ).pack(side="right", padx=22)
        body = tk.Frame(root, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)
        left = tk.Frame(body, bg=PAPER, padx=14, pady=10)
        left.grid(row=0, column=0, sticky="nsew")
        right = tk.Frame(body, bg=PAPER, width=290, padx=14, pady=10)
        right.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        right.grid_propagate(False)

        def label(parent, text, size=10, bold=False):
            return tk.Label(
                parent,
                text=text,
                font=(UI_FONT, size, "bold" if bold else "normal"),
                fg=INK,
                bg=PAPER,
                anchor="w",
            )

        label(left, "Install checklist", 15, True).pack(fill="x")
        top = tk.Frame(left, bg=PAPER)
        top.pack(fill="x", pady=(6, 8))
        label(top, "Search").pack(side="left", padx=(0, 6))
        ttk.Entry(top, textvariable=self.search).pack(
            side="left", expand=True, fill="x"
        )
        for text, value in [("All", True), ("None", False)]:
            ttk.Button(
                top, text=text, width=5, command=lambda v=value: self.bulk(v)
            ).pack(side="left", padx=(4, 0))
        self.tabs = ttk.Notebook(left)
        self.tabs.pack(fill="both", expand=True)
        table = tk.Frame(self.tabs, bg=PAPER)
        self.tabs.add(table, text="Choose items")
        self.tree = ttk.Treeview(
            table, columns=("detail",), show="tree headings", selectmode="browse"
        )
        self.tree.heading("#0", text="Selection", anchor="w")
        self.tree.heading("detail", text="Core or file", anchor="w")
        self.tree.column("#0", width=260, minwidth=130)
        self.tree.column("detail", width=160, minwidth=80)
        scroll = ttk.Scrollbar(table, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<ButtonRelease-1>", self.click)
        self.tree.bind("<space>", self.keyboard)
        self.search.trace_add("write", lambda *_: self.refresh())
        activity = tk.Frame(self.tabs, bg=PAPER)
        self.tabs.add(activity, text="Installation activity")
        tk.Label(
            activity,
            text="Active files appear first. Finished work stays below.",
            bg=PAPER,
            fg=MUTED,
            anchor="w",
            font=(UI_FONT, 9),
        ).pack(fill="x", pady=6)
        activity_table = tk.Frame(activity, bg=PAPER)
        activity_table.pack(fill="both", expand=True)
        self.activity = ttk.Treeview(
            activity_table, columns=("state", "detail"), show="tree headings"
        )
        self.activity.heading("#0", text="Game, core or file", anchor="w")
        self.activity.heading("state", text="Status", anchor="w")
        self.activity.heading("detail", text="Details", anchor="w")
        self.activity.column("#0", width=240, minwidth=130)
        self.activity.column("state", width=155, minwidth=100)
        self.activity.column("detail", width=230, minwidth=100)
        activity_scroll = ttk.Scrollbar(activity_table, command=self.activity.yview)
        self.activity.configure(yscrollcommand=activity_scroll.set)
        activity_scroll.pack(side="right", fill="y")
        self.activity.pack(fill="both", expand=True)
        self.activity_detail = tk.StringVar(
            value="Select a file to see its full details."
        )
        tk.Label(
            activity,
            textvariable=self.activity_detail,
            bg=PAPER,
            fg=MUTED,
            anchor="w",
            justify="left",
            wraplength=650,
            font=(UI_FONT, 9),
        ).pack(fill="x", pady=(6, 0))
        self.activity.bind("<<TreeviewSelect>>", self.show_activity_detail)
        self.activity.tag_configure("finished", foreground=GREEN)
        self.activity.tag_configure("attention", foreground="#a33c21")

        def section(text):
            label(right, text, 12, True).pack(fill="x", pady=(10, 4))

        section("Pocket microSD card")
        row = tk.Frame(right, bg=PAPER)
        row.pack(fill="x")
        choices = detected_cards()
        self.drives = ttk.Combobox(
            row, textvariable=self.card, values=choices, width=18
        )
        self.drives.pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Browse", command=self.browse_card).pack(
            side="left", padx=(5, 0)
        )
        ttk.Button(right, text="Firmware only", command=self.firmware_only).pack(
            anchor="w", pady=(6, 0)
        )
        self.card.trace_add("write", lambda *_: self.storage())
        tk.Label(
            right, textvariable=self.card_info, bg=PAPER, fg=MUTED, anchor="w"
        ).pack(fill="x", pady=(4, 2))
        if len(choices) == 1:
            self.card.set(choices[0])
        else:
            self.storage()
        section("Existing files")
        for val, title, detail in [
            ("add", "Add missing files", "Keep files already on the card."),
            (
                "overwrite",
                "Overwrite matching files",
                "Replace selected files that differ.",
            ),
        ]:
            tk.Radiobutton(
                right,
                text=title,
                value=val,
                variable=self.mode,
                bg=PAPER,
                fg=INK,
                activebackground=PAPER,
                selectcolor=PAPER,
                font=(UI_FONT, 10, "bold"),
            ).pack(anchor="w")
            label(right, detail, 9).pack(anchor="w", padx=22)
        section("Your game files")
        tk.Checkbutton(
            right,
            text="Import compatible games",
            variable=self.import_games,
            bg=PAPER,
            activebackground=PAPER,
            font=(UI_FONT, 10),
            fg=INK,
        ).pack(anchor="w")
        label(right, "Scan the card and an optional PC folder.", 9).pack(anchor="w")
        ttk.Entry(right, textvariable=self.folder).pack(fill="x", pady=(6, 3))
        ttk.Button(right, text="Choose game folder…", command=self.browse_games).pack(
            anchor="w"
        )
        tk.Label(
            right,
            text="Cartridge play, saves, and Memories are preserved. Firmware updates apply on the Pocket after a full power-on.",
            wraplength=238,
            justify="left",
            anchor="w",
            font=(UI_FONT, 10),
            bg=PAPER,
            fg=MUTED,
        ).pack(fill="x", pady=(16, 0))
        footer = tk.Frame(root, bg=BG)
        footer.pack(fill="x", padx=18, pady=(0, 14))
        bar = tk.Frame(footer, bg=BG)
        bar.pack(fill="x")
        tk.Label(
            bar, textvariable=self.summary, fg=INK, bg=BG, font=(UI_FONT, 11, "bold")
        ).pack(side="left")
        self.action = tk.Button(
            bar,
            text="Install selection",
            command=self.start,
            fg="white",
            bg=GREEN,
            activebackground="#104932",
            activeforeground="white",
            relief="flat",
            padx=18,
            pady=5,
            font=(UI_FONT, 10, "bold"),
        )
        self.action.pack(side="right")
        self.report_button = ttk.Button(
            bar, text="Open report", command=self.open_report
        )
        progress_heading = tk.Frame(footer, bg=BG)
        progress_heading.pack(fill="x", pady=(9, 0))
        tk.Label(
            progress_heading,
            textvariable=self.phase,
            bg=BG,
            fg=INK,
            font=(UI_FONT, 10, "bold"),
        ).pack(side="left")
        tk.Label(
            progress_heading,
            textvariable=self.progress_text,
            bg=BG,
            fg=INK,
            font=(UI_FONT, 10),
        ).pack(side="right")
        self.progress = ttk.Progressbar(footer, mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=(7, 3))
        self.transfer_panel = tk.Frame(footer, bg=BG)
        self.byte_progress = ttk.Progressbar(
            self.transfer_panel, mode="determinate", maximum=100
        )
        self.byte_progress.pack(fill="x", pady=(2, 3))
        tk.Label(
            self.transfer_panel,
            textvariable=self.transfer_text,
            bg=BG,
            fg=MUTED,
            anchor="w",
            font=(UI_FONT, 9),
        ).pack(fill="x")
        self.status_label = tk.Label(
            footer, textvariable=self.status, bg=BG, fg=MUTED, anchor="w"
        )
        self.status_label.pack(fill="x")
        tk.Label(
            footer, textvariable=self.eta, bg=BG, fg=INK, anchor="w", font=(UI_FONT, 9)
        ).pack(fill="x")
        self.status.set("Ready. Expand a category to choose individual items.")
        self.refresh()
        root.protocol("WM_DELETE_WINDOW", self.close)

    def firmware_only(self):
        if self.running:
            return
        self.search.set("")
        self.model.selected = {"firmware"}
        self.import_games.set(False)
        self.refresh()
        self.status.set(
            "Firmware only selected. Click Install selection to prepare the update."
        )

    def storage(self):
        try:
            card = Path(self.card.get())
            assert self.card.get() and (card / "Analogue_Pocket.json").is_file()
            self.card_info.set(
                f"{shutil.disk_usage(card).free / 2**30:.1f} GiB available"
            )
        except (OSError, AssertionError):
            self.card_info.set("Choose an initialized Pocket card.")

    def browse_card(self):
        if self.running:
            return
        value = filedialog.askdirectory(title="Choose the root of the Pocket card")
        if value:
            self.card.set(value)

    def browse_games(self):
        if self.running:
            return
        value = filedialog.askdirectory(title="Choose your game folder")
        if value:
            self.folder.set(value)
            self.import_games.set(True)

    def refresh(self):
        if self.running:
            return
        if self.tree.get_children():
            self.expanded = {
                g
                for g in self.groups
                if self.tree.exists(g) and self.tree.item(g, "open")
            }
        self.tree.delete(*self.tree.get_children())
        self.groups = {}
        query = self.search.get().strip().casefold()
        for key, (group, name, detail) in sorted(
            self.model.items.items(), key=lambda x: tuple(v.casefold() for v in x[1])
        ):
            if query and query not in " ".join((group, name, detail, key)).casefold():
                continue
            self.groups.setdefault(group, []).append(key)
        for group, keys in self.groups.items():
            n = sum(k in self.model.selected for k in keys)
            mark = "☑" if n == len(keys) else ("◩" if n else "☐")
            self.tree.insert(
                "",
                "end",
                iid=group,
                text=f"{mark}  {group}",
                values=(f"{n} / {len(keys)}",),
                open=bool(query) or group in self.expanded,
                tags=("group",),
            )
            for k in keys:
                _, name, detail = self.model.items[k]
                self.tree.insert(
                    group,
                    "end",
                    iid=k,
                    text=("☑  " if k in self.model.selected else "☐  ") + name,
                    values=(detail,),
                )
        self.tree.tag_configure("group", font=(UI_FONT, 10, "bold"), foreground=GREEN)
        cores = self.model.selected.intersection(self.cat["packages"])
        assets = self.model.selected.intersection(self.cat["assets"])
        size = sum(self.cat["assets"][i][2] for i in assets)
        self.summary.set(
            f"{len(cores)} cores   ·   {len(assets)} game and system files   ·   {size / 2**30:.2f} GiB in assets"
        )

    def bulk(self, value):
        if self.running:
            return
        self.model.change([k for keys in self.groups.values() for k in keys], value)
        self.refresh()

    def click(self, e):
        if "indicator" in self.tree.identify_element(e.x, e.y):
            return
        self.toggle(self.tree.identify_row(e.y))

    def keyboard(self, e):
        self.toggle(self.tree.focus())
        return "break"

    def toggle(self, item):
        if not item or self.running:
            return
        keys = self.groups.get(item, [item])
        on = not all(k in self.model.selected for k in keys)
        position = self.tree.yview()[0]
        self.model.change(keys, on)
        self.refresh()
        if self.tree.exists(item):
            self.tree.focus(item)
            self.tree.selection_set(item)
        self.tree.yview_moveto(position)

    def start(self):
        if self.running:
            self.stop.set()
            self.action.configure(state="disabled")
            self.status.set("Stopping safely after the current file…")
            return
        card = Path(self.card.get())
        if not self.card.get() or not (card / "Analogue_Pocket.json").is_file():
            messagebox.showinfo(
                "Choose a Pocket card",
                "Select the root of your initialized Pocket microSD card.",
            )
            return
        cores = self.model.selected.intersection(self.cat["packages"])
        assets = self.model.selected.intersection(self.cat["assets"])
        firmware = "firmware" in self.model.selected
        if not cores and not firmware:
            messagebox.showinfo(
                "Choose an item", "Select a core, game download, or firmware."
            )
            return
        if self.mode.get() == "overwrite" and not messagebox.askokcancel(
            "Overwrite matching files", f"Replace selected files that differ on {card}?"
        ):
            return
        if firmware and not messagebox.askokcancel(
            "Prepare Pocket firmware 2.7",
            "Download and verify official firmware 2.7 on the card? The Pocket will apply it after a full power-off and power-on. Allow 3–4 minutes and keep power on until it restarts. Older update files are backed up to this PC when Overwrite is selected.",
        ):
            return
        folder = (
            Path(self.folder.get())
            if self.folder.get() and self.import_games.get()
            else None
        )
        args = (
            card,
            folder,
            self.mode.get(),
            cores,
            assets,
            self.import_games.get(),
            firmware,
        )
        self.running = True
        self.started_at = time.monotonic()
        self.stage_id = None
        self.stage_items = {}
        self.activity_rows = {}
        self.activity.delete(*self.activity.get_children())
        self.activity_detail.set("Select a file to see its full details.")
        self.tabs.select(1)
        self.stop.clear()
        self.action.configure(text="Stop safely")
        self.report_button.pack_forget()
        self.progress.configure(mode="determinate", value=0, maximum=100)
        self.progress_text.set("Preparing…")
        self.phase.set("Checking the card")
        self.eta.set("Estimating time remaining…")
        self.status.set("Checking the card and preparing downloads…")
        events = self.events

        class Log:
            pending = ""

            def write(self, line):
                self.pending += line
                while "\n" in self.pending:
                    line, self.pending = self.pending.split("\n", 1)
                    if line:
                        events.put(("log", line))

            def flush(self):
                pass

        def run():
            try:
                with contextlib.redirect_stdout(Log()):
                    result = self.install(
                        *args, progress=lambda event: events.put(("progress", event))
                    )
                events.put(("done", result))
            except BaseException as e:
                events.put(
                    (
                        "error",
                        "Stopped safely. You can resume with Add missing files."
                        if self.stop.is_set()
                        else str(e),
                    )
                )

        threading.Thread(target=run, daemon=True).start()
        self.root.after(80, self.poll)

    def poll(self):
        # Keep the window responsive even when several downloads finish together.
        for _ in range(300):
            if self.events.empty():
                break
            kind, value = self.events.get_nowait()
            if kind == "progress":
                self.show_progress(value)
            elif kind == "log":
                if self.stage_id is None:
                    self.status.set(value)
            else:
                self.running = False
                self.progress.stop()
                self.progress.configure(mode="determinate")
                self.action.configure(text="Install selection", state="normal")
                if kind == "done":
                    self.eta.set("Installation finished")
                    self.progress.configure(value=self.progress["maximum"])
                    issues = len(value.get("needs_attention", []))
                    self.phase.set(
                        "Finished"
                        if not issues
                        else "Finished · some items need attention"
                    )
                    self.progress_text.set(
                        f"{issues} items to review" if issues else "All tasks finished"
                    )
                    if (
                        value.get("firmware")
                        and "not selected" not in value["firmware"]
                    ):
                        messagebox.showinfo("Pocket firmware", value["firmware"])
                    self.report_button.pack(side="right", padx=8)
                    self.status.set(
                        f"Finished. {len(value['processed_cores'])} cores processed, {value['verified_game_and_system_assets']} assets verified, {value['game_files'].get('written', 0)} local game files written. See report for exceptions."
                    )
                else:
                    self.eta.set("Time estimate paused")
                    self.status.set(value)
                    self.phase.set(
                        "Stopped safely"
                        if self.stop.is_set()
                        else "Installation interrupted"
                    )
                    for row in self.activity.get_children():
                        if not self.activity.item(row, "tags"):
                            values = self.activity.item(row, "values")
                            self.activity.item(
                                row,
                                values=(
                                    "Stopped" if self.stop.is_set() else "Interrupted",
                                    values[1],
                                ),
                            )
                return
        if self.stage_id:
            self.update_metrics()
        self.root.after(100, self.poll)

    def show_progress(self, event):
        stage = event["stage"]
        if event["type"] == "stage":
            if stage != self.stage_id:
                self.stage_items = {}
                self.stage_sizes = {}
                self.stage_started = time.monotonic()
                self.network_bytes = 0
            self.stage_id = stage
            self.stage_total = event.get("total")
            self.estimate_started = time.monotonic()
            self.last_work = 0
            self.last_work_at = self.estimate_started
            self.stage_sizes = event.get("sizes", self.stage_sizes)
            titles = {
                "cores": "Core installation",
                "assets": "Game and system files",
                "games": "Importing your games",
                "firmware": "Pocket firmware",
            }
            if "step" in event:
                self.phase.set(
                    f"Step {event['step']} of {event['steps']} · {titles[stage]}"
                )
            self.progress.stop()
            self.progress.configure(
                mode="indeterminate" if self.stage_total is None else "determinate",
                value=0,
            )
            if self.stage_total is None:
                self.progress.start()
            if stage == "assets":
                self.transfer_panel.pack(fill="x", before=self.status_label)
            else:
                self.transfer_panel.pack_forget()
            self.status.set(event.get("detail", "Preparing files…"))
            self.update_metrics()
            return
        if stage != self.stage_id:
            return
        key = event["key"]
        old = self.stage_items.get(key, {})
        if event.get("status") in ("Downloading", "Verifying download"):
            self.network_bytes += max(
                0, event.get("received", 0) - old.get("received", 0)
            )
        item = {**old, **event}
        self.stage_items[key] = item
        meta = self.cat["asset_info"].get(key) or self.cat["core_info"].get(key) or {}
        name = meta.get(
            "name", "Official firmware 2.7" if key == "firmware" else Path(key).name
        )
        detail = item.get("detail", "")
        if stage == "assets":
            received, size = item.get("received", 0), item.get("size", 0)
            if not item.get("finished") and size:
                detail = f"{received / 2**20:.1f} / {size / 2**20:.1f} MiB · {key}"
            elif not detail:
                detail = key
        tags = (
            ("attention",)
            if item.get("error")
            else ("finished",)
            if item.get("finished")
            else ()
        )
        row_key = (stage, key)
        if row_key not in self.activity_rows:
            self.activity_rows[row_key] = self.activity.insert("", 0, text=name)
        row = self.activity_rows[row_key]
        self.activity.item(row, values=(item["status"], detail), tags=tags)
        if item.get("finished") and not old.get("finished"):
            self.activity.move(row, "", "end")
        if not self.stop.is_set():
            self.status.set(f"{item['status']} · {name}")
        self.update_metrics()

    def show_activity_detail(self, _event=None):
        selected = self.activity.selection()
        if selected:
            item = self.activity.item(selected[0])
            self.activity_detail.set(
                f"{item['text']} · {item['values'][0]}\n{item['values'][1]}"
            )

    def update_metrics(self):
        items = list(self.stage_items.values())
        finished = sum(bool(i.get("finished")) for i in items)
        errors = sum(bool(i.get("error")) for i in items)
        active = sum(not i.get("finished", False) for i in items)
        elapsed = int(time.monotonic() - self.started_at) if self.started_at else 0
        clock = f"{elapsed // 60}:{elapsed % 60:02d} elapsed"
        if self.stage_total is None:
            self.progress_text.set(f"Finding game files · {clock}")
        else:
            percent = 100 * finished / self.stage_total if self.stage_total else 100
            self.progress.configure(value=percent)
            self.progress_text.set(
                f"{finished} / {self.stage_total} files finished · {percent:.0f}% · {clock}"
                + (f" · {errors} to review" if errors else "")
            )
        if self.stage_id == "assets":
            total = sum(self.stage_sizes.values())
            received = sum(
                min(i.get("received", 0), self.stage_sizes.get(k, 0))
                for k, i in self.stage_items.items()
            )
            self.byte_progress.configure(value=100 * received / total if total else 100)
            duration = max(0.1, time.monotonic() - self.stage_started)
            speed = self.network_bytes / duration / 2**20
            self.transfer_text.set(
                f"Downloaded or cached: {received / 2**20:.1f} / {total / 2**20:.1f} MiB"
                f"   ·   {speed:.1f} MiB/s average   ·   {active} active"
            )
            # Leave a small allowance for verification and card writes after bytes arrive.
            work = sum(
                self.stage_sizes.get(k, 0)
                if i.get("finished")
                else min(i.get("received", 0), self.stage_sizes.get(k, 0)) * 0.95
                for k, i in self.stage_items.items()
            )
            remaining_bytes = sum(
                max(0, size - self.stage_items.get(key, {}).get("received", 0))
                for key, size in self.stage_sizes.items()
                if not self.stage_items.get(key, {}).get("finished")
            )
            # Cached bytes never inflate the measured network speed.
            remaining = (
                remaining_bytes * duration / self.network_bytes * 1.05
                if self.network_bytes
                else None
            )
            self.update_estimate(
                work,
                total,
                remaining=remaining,
                file_rate=False,
                finishing=not remaining_bytes and finished < self.stage_total,
            )
        else:
            self.update_estimate(finished, self.stage_total)

    def update_estimate(
        self, work, total, remaining=None, file_rate=True, finishing=False
    ):
        now = time.monotonic()
        if work != self.last_work:
            self.last_work, self.last_work_at = work, now
        duration = now - self.estimate_started
        if self.stop.is_set():
            text = "Stopping safely…"
        elif total is not None and work >= total:
            text = "This step is finished"
        elif now - self.last_work_at > 20:
            text = "Waiting for progress · time estimate paused"
        elif finishing:
            text = "Finishing verification and card copies…"
        elif (
            total
            and work > 0
            and duration >= 5
            and (file_rate or remaining is not None)
        ):
            seconds = duration * max(0, total - work) / work if file_rate else remaining
            if seconds < 60:
                remaining = "Under a minute"
            else:
                minutes = math.ceil(seconds / 60)
                remaining = (
                    f"About {minutes} min"
                    if minutes < 60
                    else f"About {minutes // 60} hr {minutes % 60} min"
                )
            text = f"{remaining} left in this step · approximate"
        else:
            text = "Estimating time remaining for this step…"
        self.eta.set(text)

    def open_report(self):
        open_file(self.reportdir / "Install report.txt")

    def close(self):
        if self.running:
            if messagebox.askyesno(
                "Stop installation?", "Stop safely after the current file?"
            ):
                self.stop.set()
                self.status.set("Stopping safely…")
        else:
            self.root.destroy()


def launch(catalog, install, stop, reportdir):
    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except OSError:
            pass
    root = tk.Tk()
    icon = (
        Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "assets" / "pocket.ico"
    )
    if sys.platform == "win32" and icon.is_file():
        root.iconbitmap(str(icon))
    else:
        root.app_icon = tk.PhotoImage(file=str(icon.with_suffix(".png")))
        root.iconphoto(True, root.app_icon)
    Installer(root, catalog, install, stop, reportdir)
    root.mainloop()
