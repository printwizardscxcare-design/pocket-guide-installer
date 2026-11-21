"""Windows desktop setup and selective installation."""

import contextlib
import ctypes
import os
import queue
import shutil
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

BG = "#f1f2ee"
PAPER = "#ffffff"
INK = "#182420"
MUTED = "#52645c"
GREEN = "#175c45"
LINE = "#cad3ca"


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


def detected_cards():
    found = []
    mask = ctypes.windll.kernel32.GetLogicalDrives()
    for i in range(26):
        if not mask & (1 << i):
            continue
        drive = Path(chr(65 + i) + ":/")
        if ctypes.windll.kernel32.GetDriveTypeW(str(drive)) not in (2, 3):
            continue
        try:
            if (drive / "Analogue_Pocket.json").is_file():
                found.append(str(drive))
        except OSError:
            pass
    return found


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
        root.geometry("1000x690")
        root.minsize(820, 590)
        root.configure(bg=BG)
        self.style = ttk.Style(root)
        self.style.theme_use("clam")
        self.style.configure(
            "Treeview",
            font=("Segoe UI", 10),
            rowheight=28,
            background=PAPER,
            fieldbackground=PAPER,
            foreground=INK,
            borderwidth=0,
        )
        self.style.configure(
            "Treeview.Heading",
            font=("Segoe UI", 9, "bold"),
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
        self.card_info = tk.StringVar()
        self.groups = {}
        self.expanded = set()
        head = tk.Frame(root, bg=INK)
        head.pack(fill="x")
        tk.Label(
            head,
            text="Pocket Guide Installer",
            font=("Segoe UI", 22, "bold"),
            fg=PAPER,
            bg=INK,
        ).pack(side="left", padx=22, pady=13)
        tk.Label(
            head,
            text="openFPGA  /  microSD setup",
            font=("Segoe UI", 10),
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
                font=("Segoe UI", size, "bold" if bold else "normal"),
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
        table = tk.Frame(left, bg=PAPER)
        table.pack(fill="both", expand=True)
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
                font=("Segoe UI", 10, "bold"),
            ).pack(anchor="w")
            label(right, detail, 9).pack(anchor="w", padx=22)
        section("Your game files")
        tk.Checkbutton(
            right,
            text="Import compatible games",
            variable=self.import_games,
            bg=PAPER,
            activebackground=PAPER,
            font=("Segoe UI", 10),
            fg=INK,
        ).pack(anchor="w")
        label(right, "Scan the card and an optional PC folder.", 9).pack(anchor="w")
        ttk.Entry(right, textvariable=self.folder).pack(fill="x", pady=(6, 3))
        ttk.Button(right, text="Choose game folder…", command=self.browse_games).pack(
            anchor="w"
        )
        tk.Label(
            right,
            text="Both modes preserve cartridge play, firmware, saves, and Memories.",
            wraplength=238,
            justify="left",
            anchor="w",
            font=("Segoe UI", 10),
            bg=PAPER,
            fg=MUTED,
        ).pack(fill="x", pady=(16, 0))
        footer = tk.Frame(root, bg=BG)
        footer.pack(fill="x", padx=18, pady=(0, 14))
        bar = tk.Frame(footer, bg=BG)
        bar.pack(fill="x")
        tk.Label(
            bar, textvariable=self.summary, fg=INK, bg=BG, font=("Segoe UI", 11, "bold")
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
            font=("Segoe UI", 10, "bold"),
        )
        self.action.pack(side="right")
        self.report_button = ttk.Button(
            bar, text="Open report", command=self.open_report
        )
        self.progress = ttk.Progressbar(footer, mode="determinate")
        self.progress.pack(fill="x", pady=(7, 3))
        tk.Label(footer, textvariable=self.status, bg=BG, fg=MUTED, anchor="w").pack(
            fill="x"
        )
        self.status.set("Ready. Expand a category to choose individual items.")
        self.refresh()
        root.protocol("WM_DELETE_WINDOW", self.close)

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
        self.tree.tag_configure(
            "group", font=("Segoe UI", 10, "bold"), foreground=GREEN
        )
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
        if not cores:
            messagebox.showinfo(
                "Choose a core", "Select at least one core or game download."
            )
            return
        if self.mode.get() == "overwrite" and not messagebox.askokcancel(
            "Overwrite matching files", f"Replace selected files that differ on {card}?"
        ):
            return
        folder = (
            Path(self.folder.get())
            if self.folder.get() and self.import_games.get()
            else None
        )
        args = (card, folder, self.mode.get(), cores, assets, self.import_games.get())
        self.running = True
        self.stop.clear()
        self.action.configure(text="Stop safely")
        self.report_button.pack_forget()
        self.progress.configure(
            mode="determinate", value=0, maximum=max(1, len(cores) + len(assets))
        )
        self.core_count = 0
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
                    result = self.install(*args)
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
        while not self.events.empty():
            kind, value = self.events.get_nowait()
            if kind == "log":
                self.status.set(value)
                if value.startswith(("Processed ", "Skipped ")):
                    self.core_count += 1
                    self.progress.configure(value=self.core_count)
                if value.startswith("Verified game and system assets:"):
                    self.progress.configure(
                        value=self.core_count + int(value.split(":")[1].split("/")[0])
                    )
                if value.startswith("Installing games..."):
                    self.progress.configure(mode="indeterminate")
                    self.progress.start()
            else:
                self.running = False
                self.progress.stop()
                self.progress.configure(mode="determinate")
                self.action.configure(text="Install selection", state="normal")
                if kind == "done":
                    self.progress.configure(value=self.progress["maximum"])
                    self.report_button.pack(side="right", padx=8)
                    self.status.set(
                        f"Finished. {len(value['processed_cores'])} cores processed, {value['verified_game_and_system_assets']} assets verified, {value['game_files'].get('written', 0)} local game files written. See report for exceptions."
                    )
                else:
                    self.status.set(value)
                return
        self.root.after(100, self.poll)

    def open_report(self):
        os.startfile(self.reportdir / "Install report.txt")

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
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except OSError:
        pass
    root = tk.Tk()
    Installer(root, catalog, install, stop, reportdir)
    root.mainloop()
