"""ETS2 Mod Synchronizer — bilingual FR/EN desktop tool."""

import os
import shutil
import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

from decrypt import decrypt_file
from mod_reader import (
    entry_id, get_default_mod_dir, get_default_profiles_dir,
    parse_entry, read_mod_folder,
)
from sii_parser import extract_active_mods, replace_active_mods

# ---------------------------------------------------------------------------
# Localisation
# ---------------------------------------------------------------------------

_S = {
    # Common
    "title":         {"fr": "ETS2 Mod Synchronizer",                          "en": "ETS2 Mod Synchronizer"},
    "tab_sync":      {"fr": "Synchroniser",                                    "en": "Synchronize"},
    "tab_manager":   {"fr": "Gestionnaire de mods",                            "en": "Mod Manager"},
    "browse":        {"fr": "Parcourir…",                                      "en": "Browse…"},
    "log_title":     {"fr": "Journal",                                         "en": "Log"},
    "err_title":     {"fr": "Erreur",                                          "en": "Error"},
    "ok_title":      {"fr": "Succès",                                          "en": "Success"},
    # Sync tab
    "sync_sub":      {"fr": "Copiez la liste de mods de l'hôte vers votre profil.",
                      "en": "Copy the host's mod list to your profile."},
    "sync_my":       {"fr": "Votre profile.sii :",                             "en": "Your profile.sii:"},
    "sync_host":     {"fr": "profile.sii de l'Hôte :",                        "en": "Host's profile.sii:"},
    "sync_hint":     {"fr": "Fichier : Documents/Euro Truck Simulator 2/profiles/{profil}/profile.sii",
                      "en": "File: Documents/Euro Truck Simulator 2/profiles/{profile}/profile.sii"},
    "sync_btn":      {"fr": "  Synchroniser les Mods  ",                       "en": "  Synchronize Mods  "},
    "err_fields":    {"fr": "Veuillez sélectionner les deux fichiers.",        "en": "Please select both files."},
    "err_notfound":  {"fr": "Fichier introuvable :\n{}",                       "en": "File not found:\n{}"},
    "err_nomods_h":  {"fr": "active_mods introuvable dans le fichier hôte.",
                      "en": "active_mods not found in host file."},
    "err_nomods_m":  {"fr": "active_mods introuvable dans votre fichier.",
                      "en": "active_mods not found in your file."},
    "ok_sync":       {"fr": "{} mod(s) copiés depuis le profil hôte.\n\nBackup :\n{}",
                      "en": "{} mod(s) copied from host profile.\n\nBackup:\n{}"},
    "log_read_h":    {"fr": "Lecture du fichier hôte…",                        "en": "Reading host file…"},
    "log_mods_h":    {"fr": "{} mod(s) trouvé(s) chez l'hôte.",               "en": "{} mod(s) found on host."},
    "log_autodet":   {"fr": "Fichier détecté automatiquement : {}",            "en": "File auto-detected: {}"},
    "log_read_m":    {"fr": "Lecture de votre fichier…",                       "en": "Reading your file…"},
    "log_backup":    {"fr": "Backup créé : {}",                                "en": "Backup created: {}"},
    "log_done":      {"fr": "Synchronisation réussie — {} mod(s) copiés.",    "en": "Sync complete — {} mod(s) copied."},
    # Manager tab
    "mgr_profile":   {"fr": "Profil (profile.sii) :",                         "en": "Profile (profile.sii):"},
    "mgr_moddir":    {"fr": "Dossier mods :",                                  "en": "Mods folder:"},
    "mgr_load":      {"fr": "Charger",                                         "en": "Load"},
    "mgr_avail":     {"fr": "Disponibles dans mod/",                           "en": "Available in mod/"},
    "mgr_active":    {"fr": "Actifs dans le profil",                           "en": "Active in profile"},
    "mgr_apply":     {"fr": "  Appliquer au profil  ",                         "en": "  Apply to Profile  "},
    "mgr_missing":   {"fr": " ⚠",                                              "en": " ⚠"},
    "log_loading":   {"fr": "Chargement des mods…",                            "en": "Loading mods…"},
    "log_avail":     {"fr": "{} mod(s) disponible(s), {} déjà actif(s).",     "en": "{} mod(s) available, {} already active."},
    "log_applied":   {"fr": "Profil mis à jour — {} mod(s) actif(s).",        "en": "Profile updated — {} mod(s) active."},
    "ok_applied":    {"fr": "{} mod(s) actif(s) enregistrés.\n\nBackup :\n{}","en": "{} mod(s) active saved.\n\nBackup:\n{}"},
    "err_no_profile":{"fr": "Sélectionnez d'abord un profile.sii.",            "en": "Please select a profile.sii first."},
    "err_no_moddir": {"fr": "Dossier mods introuvable :\n{}",                  "en": "Mods folder not found:\n{}"},
    "err_noactive":  {"fr": "La liste des mods actifs est vide.",              "en": "Active mod list is empty."},
}


class L10n:
    def __init__(self):
        self.lang = "fr"
        self._cbs: list = []

    def t(self, key: str, *args) -> str:
        text = _S[key][self.lang]
        return text.format(*args) if args else text

    def toggle(self):
        self.lang = "en" if self.lang == "fr" else "fr"
        for cb in self._cbs:
            cb()

    def on_change(self, cb):
        self._cbs.append(cb)


# ---------------------------------------------------------------------------
# Sync helpers
# ---------------------------------------------------------------------------

def find_mods_file(path: str, log=None) -> tuple:
    """Return (actual_path, plaintext_content, was_autodetected)."""
    def _log(msg, tag=""):
        if log:
            log(msg, tag)

    try:
        content = decrypt_file(path)
    except Exception as e:
        raise ValueError(str(e))

    if extract_active_mods(content) is not None:
        return path, content, False

    _log("active_mods absent de {} — scan des fichiers voisins…".format(
        os.path.basename(path)), "warn")

    parent = os.path.dirname(path)
    for fname in sorted(os.listdir(parent)):
        if not fname.lower().endswith(".sii"):
            continue
        sibling = os.path.join(parent, fname)
        if os.path.normcase(sibling) == os.path.normcase(path):
            continue
        try:
            c = decrypt_file(sibling)
            if extract_active_mods(c) is not None:
                return sibling, c, True
            _log("{} — pas de active_mods".format(fname), "warn")
        except NotImplementedError:
            _log("{} — format non supporté".format(fname), "warn")
        except Exception as e:
            _log("{} — erreur : {}".format(fname, e), "warn")

    raise ValueError(
        "Liste de mods introuvable dans ce dossier.\n\n"
        "Le fichier à utiliser est :\n"
        "Documents/Euro Truck Simulator 2/profiles/{profil}/profile.sii\n\n"
        "⚠ Ne pas utiliser les fichiers game.sii du dossier save/ —\n"
        "ils ne contiennent pas la liste des mods."
    )


# ---------------------------------------------------------------------------
# Scrollable Listbox widget
# ---------------------------------------------------------------------------

class ScrollListbox(ttk.Frame):
    def __init__(self, parent, **kw):
        super().__init__(parent)
        self.lb = tk.Listbox(self, selectmode="single",
                             activestyle="none", **kw)
        sb = ttk.Scrollbar(self, command=self.lb.yview)
        self.lb.configure(yscrollcommand=sb.set)
        self.lb.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    # Delegate common Listbox methods
    def insert(self, idx, *items):    self.lb.insert(idx, *items)
    def delete(self, first, last=None): self.lb.delete(first, last)
    def get(self, first, last=None):  return self.lb.get(first, last)
    def size(self):                   return self.lb.size()
    def curselection(self):           return self.lb.curselection()
    def selection_clear(self, first, last=None): self.lb.selection_clear(first, last)
    def selection_set(self, first, last=None):   self.lb.selection_set(first, last)
    def see(self, idx):               self.lb.see(idx)
    def bind(self, *a, **kw):         return self.lb.bind(*a, **kw)


# ---------------------------------------------------------------------------
# Main App
# ---------------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.l10n = L10n()
        self.l10n.on_change(self._refresh_labels)

        # Sync tab state
        self.my_path   = tk.StringVar()
        self.host_path = tk.StringVar()

        # Manager tab state
        self.mgr_profile_path = tk.StringVar()
        self.mgr_mod_dir      = tk.StringVar(value=get_default_mod_dir())
        self._all_mods: list  = []   # [{id, display_name, entry, path}]
        self._active_entries: list = []  # ordered list of "id|name" strings

        self.title("ETS2 Mod Synchronizer")
        self.minsize(660, 520)
        self._build_ui()

    # ================================================================ build UI

    def _build_ui(self):
        # ── Top bar ──────────────────────────────────────────────────────────
        top = ttk.Frame(self)
        top.pack(fill="x", padx=14, pady=(12, 6))
        self._lbl_title = ttk.Label(top, font=("Segoe UI", 13, "bold"))
        self._lbl_title.pack(side="left")
        self._btn_lang = ttk.Button(top, width=4, command=self.l10n.toggle)
        self._btn_lang.pack(side="right")

        ttk.Separator(self).pack(fill="x", padx=14, pady=(0, 6))

        # ── Notebook ─────────────────────────────────────────────────────────
        self._nb = ttk.Notebook(self)
        self._nb.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        self._sync_frame = ttk.Frame(self._nb, padding=10)
        self._mgr_frame  = ttk.Frame(self._nb, padding=10)
        self._nb.add(self._sync_frame, text="")
        self._nb.add(self._mgr_frame,  text="")

        self._build_sync_tab()
        self._build_manager_tab()
        self._refresh_labels()

    # ──────────────────────────────────────────────────────── Sync tab

    def _build_sync_tab(self):
        f = self._sync_frame

        self._sync_sub = ttk.Label(f, font=("Segoe UI", 9), foreground="#777")
        self._sync_sub.pack(anchor="w")

        self._sync_hint = tk.Label(f, font=("Segoe UI", 8), fg="#aaa",
                                   bg=self["bg"], justify="left", wraplength=580)
        self._sync_hint.pack(anchor="w", pady=(2, 8))

        ttk.Separator(f).pack(fill="x", pady=(0, 8))

        fields = ttk.Frame(f)
        fields.pack(fill="x")
        fields.columnconfigure(1, weight=1)

        self._lbl_my = ttk.Label(fields)
        self._lbl_my.grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(fields, textvariable=self.my_path, width=50).grid(
            row=0, column=1, padx=8, sticky="ew")
        self._btn_bmy = ttk.Button(fields,
                                   command=lambda: self._browse_file(self.my_path))
        self._btn_bmy.grid(row=0, column=2)

        self._lbl_host = ttk.Label(fields)
        self._lbl_host.grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(fields, textvariable=self.host_path, width=50).grid(
            row=1, column=1, padx=8, sticky="ew")
        self._btn_bhost = ttk.Button(fields,
                                     command=lambda: self._browse_file(self.host_path))
        self._btn_bhost.grid(row=1, column=2)

        ttk.Separator(f).pack(fill="x", pady=10)

        self._btn_sync = ttk.Button(f, command=self._do_sync)
        self._btn_sync.pack()

        ttk.Separator(f).pack(fill="x", pady=(10, 6))

        self._sync_log_frame = ttk.LabelFrame(f, padding=4)
        self._sync_log_frame.pack(fill="both", expand=True)
        self._sync_log = self._make_log(self._sync_log_frame)

    # ──────────────────────────────────────────────────────── Manager tab

    def _build_manager_tab(self):
        f = self._mgr_frame

        # ── Paths row ────────────────────────────────────────────────────────
        paths = ttk.Frame(f)
        paths.pack(fill="x")
        paths.columnconfigure(1, weight=1)

        self._lbl_mgr_profile = ttk.Label(paths)
        self._lbl_mgr_profile.grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(paths, textvariable=self.mgr_profile_path, width=44).grid(
            row=0, column=1, padx=6, sticky="ew")
        self._btn_mgr_profile = ttk.Button(
            paths, command=self._browse_mgr_profile)
        self._btn_mgr_profile.grid(row=0, column=2)

        self._lbl_mgr_moddir = ttk.Label(paths)
        self._lbl_mgr_moddir.grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(paths, textvariable=self.mgr_mod_dir, width=44).grid(
            row=1, column=1, padx=6, sticky="ew")
        frame_btns = ttk.Frame(paths)
        frame_btns.grid(row=1, column=2)
        self._btn_mgr_moddir = ttk.Button(
            frame_btns, command=self._browse_mgr_moddir)
        self._btn_mgr_moddir.pack(side="left")
        self._btn_mgr_load = ttk.Button(frame_btns, command=self._load_mods)
        self._btn_mgr_load.pack(side="left", padx=(4, 0))

        ttk.Separator(f).pack(fill="x", pady=(8, 6))

        # ── Two listboxes + controls ─────────────────────────────────────────
        cols = ttk.Frame(f)
        cols.pack(fill="both", expand=True)
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(2, weight=1)

        # Left: available
        self._lbl_avail = ttk.Label(cols, font=("Segoe UI", 9, "bold"))
        self._lbl_avail.grid(row=0, column=0, pady=(0, 4))
        self._lb_avail = ScrollListbox(cols, height=12, font=("Segoe UI", 9))
        self._lb_avail.grid(row=1, column=0, sticky="nsew")
        self._lb_avail.bind("<Double-Button-1>", lambda e: self._activate())

        # Centre: arrow buttons
        ctrl = ttk.Frame(cols)
        ctrl.grid(row=1, column=1, padx=8)
        self._btn_add    = ttk.Button(ctrl, text="→", width=3, command=self._activate)
        self._btn_remove = ttk.Button(ctrl, text="←", width=3, command=self._deactivate)
        self._btn_up     = ttk.Button(ctrl, text="↑", width=3, command=self._move_up)
        self._btn_down   = ttk.Button(ctrl, text="↓", width=3, command=self._move_down)
        for i, btn in enumerate((self._btn_add, self._btn_remove,
                                  self._btn_up, self._btn_down)):
            btn.pack(pady=3)

        # Right: active
        self._lbl_active = ttk.Label(cols, font=("Segoe UI", 9, "bold"))
        self._lbl_active.grid(row=0, column=2, pady=(0, 4))
        self._lb_active = ScrollListbox(cols, height=12, font=("Segoe UI", 9))
        self._lb_active.grid(row=1, column=2, sticky="nsew")
        self._lb_active.bind("<Double-Button-1>", lambda e: self._deactivate())

        ttk.Separator(f).pack(fill="x", pady=(8, 6))

        # Apply + log
        self._btn_apply = ttk.Button(f, command=self._apply_mods)
        self._btn_apply.pack()

        self._mgr_log_frame = ttk.LabelFrame(f, padding=4)
        self._mgr_log_frame.pack(fill="both", expand=True, pady=(6, 0))
        self._mgr_log = self._make_log(self._mgr_log_frame)

    # ──────────────────────────────────────────────────────── log widget

    def _make_log(self, parent) -> tk.Text:
        box = tk.Text(parent, height=5, state="disabled", wrap="word",
                      font=("Consolas", 9), bg="#1e1e1e", fg="#d4d4d4",
                      relief="flat")
        sb = ttk.Scrollbar(parent, command=box.yview)
        box.configure(yscrollcommand=sb.set)
        box.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        box.tag_config("ok",   foreground="#4ec9b0")
        box.tag_config("err",  foreground="#f44747")
        box.tag_config("warn", foreground="#dcdcaa")
        return box

    def _log(self, box: tk.Text, msg: str, tag: str = ""):
        ts = datetime.now().strftime("%H:%M:%S")
        box.configure(state="normal")
        box.insert("end", f"[{ts}] {msg}\n", tag)
        box.configure(state="disabled")
        box.see("end")

    def _slog(self, msg, tag=""): self._log(self._sync_log, msg, tag)
    def _mlog(self, msg, tag=""): self._log(self._mgr_log,  msg, tag)

    # ────────────────────────────────────────────────── label refresh / i18n

    def _refresh_labels(self):
        L = self.l10n
        self._lbl_title.configure(text=L.t("title"))
        self._btn_lang.configure(text="EN" if L.lang == "fr" else "FR")
        self._nb.tab(0, text=L.t("tab_sync"))
        self._nb.tab(1, text=L.t("tab_manager"))
        # Sync
        self._sync_sub.configure(text=L.t("sync_sub"))
        self._sync_hint.configure(text=L.t("sync_hint"))
        self._lbl_my.configure(text=L.t("sync_my"))
        self._lbl_host.configure(text=L.t("sync_host"))
        self._btn_bmy.configure(text=L.t("browse"))
        self._btn_bhost.configure(text=L.t("browse"))
        self._btn_sync.configure(text=L.t("sync_btn"))
        self._sync_log_frame.configure(text=L.t("log_title"))
        # Manager
        self._lbl_mgr_profile.configure(text=L.t("mgr_profile"))
        self._lbl_mgr_moddir.configure(text=L.t("mgr_moddir"))
        self._btn_mgr_profile.configure(text=L.t("browse"))
        self._btn_mgr_moddir.configure(text=L.t("browse"))
        self._btn_mgr_load.configure(text=L.t("mgr_load"))
        self._lbl_avail.configure(text=L.t("mgr_avail"))
        self._lbl_active.configure(text=L.t("mgr_active"))
        self._btn_apply.configure(text=L.t("mgr_apply"))
        self._mgr_log_frame.configure(text=L.t("log_title"))

    # ─────────────────────────────────────────────────────── file browsing

    def _browse_file(self, var: tk.StringVar):
        path = filedialog.askopenfilename(
            initialdir=get_default_profiles_dir(),
            filetypes=[("SII files", "*.sii"), ("All files", "*.*")],
        )
        if path:
            var.set(path)

    def _browse_mgr_profile(self):
        path = filedialog.askopenfilename(
            initialdir=get_default_profiles_dir(),
            filetypes=[("profile.sii", "profile.sii"), ("SII files", "*.sii")],
        )
        if path:
            self.mgr_profile_path.set(path)

    def _browse_mgr_moddir(self):
        path = filedialog.askdirectory(initialdir=get_default_mod_dir())
        if path:
            self.mgr_mod_dir.set(path)

    # ================================================================ Sync logic

    def _do_sync(self):
        L = self.l10n
        my   = self.my_path.get().strip()
        host = self.host_path.get().strip()

        if not my or not host:
            messagebox.showerror(L.t("err_title"), L.t("err_fields"))
            return
        for p in (my, host):
            if not os.path.isfile(p):
                messagebox.showerror(L.t("err_title"), L.t("err_notfound", p))
                return

        self._slog(L.t("log_read_h"))
        try:
            host_actual, host_content, detected = find_mods_file(host, self._slog)
        except Exception as e:
            self._slog(str(e), "err")
            messagebox.showerror(L.t("err_title"), str(e))
            return
        if detected:
            self._slog(L.t("log_autodet", os.path.basename(host_actual)), "warn")

        host_mods = extract_active_mods(host_content)
        if host_mods is None:
            self._slog(L.t("err_nomods_h"), "err")
            messagebox.showerror(L.t("err_title"), L.t("err_nomods_h"))
            return
        self._slog(L.t("log_mods_h", len(host_mods)))

        self._slog(L.t("log_read_m"))
        try:
            my_actual, my_content, detected = find_mods_file(my, self._slog)
        except Exception as e:
            self._slog(str(e), "err")
            messagebox.showerror(L.t("err_title"), str(e))
            return
        if detected:
            self._slog(L.t("log_autodet", os.path.basename(my_actual)), "warn")

        new_content = replace_active_mods(my_content, host_mods)
        if new_content is None:
            self._slog(L.t("err_nomods_m"), "err")
            messagebox.showerror(L.t("err_title"), L.t("err_nomods_m"))
            return

        backup = my_actual + ".backup"
        shutil.copy2(my_actual, backup)
        self._slog(L.t("log_backup", os.path.basename(backup)))

        with open(my_actual, "w", encoding="utf-8") as fh:
            fh.write(new_content)

        self._slog(L.t("log_done", len(host_mods)), "ok")
        messagebox.showinfo(L.t("ok_title"), L.t("ok_sync", len(host_mods), backup))

    # ================================================================ Manager logic

    def _load_mods(self):
        L = self.l10n
        profile = self.mgr_profile_path.get().strip()
        mod_dir = self.mgr_mod_dir.get().strip()

        if not profile:
            messagebox.showerror(L.t("err_title"), L.t("err_no_profile"))
            return
        if not os.path.isdir(mod_dir):
            messagebox.showerror(L.t("err_title"), L.t("err_no_moddir", mod_dir))
            return

        self._mlog(L.t("log_loading"))
        self._btn_mgr_load.configure(state="disabled")

        def worker():
            try:
                # Read profile active mods
                _, content, _ = find_mods_file(profile, self._mlog)
                active = extract_active_mods(content) or []

                # Read available mods from folder
                all_mods = read_mod_folder(mod_dir)

                self.after(0, lambda: self._populate_lists(all_mods, active))
            except Exception as e:
                self.after(0, lambda: self._mlog(str(e), "err"))
            finally:
                self.after(0, lambda: self._btn_mgr_load.configure(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    def _populate_lists(self, all_mods: list, active_entries: list):
        L = self.l10n
        self._all_mods = all_mods
        self._active_entries = list(active_entries)

        # Index available mods by ID
        avail_by_id = {m["id"]: m for m in all_mods}
        active_ids  = {entry_id(e) for e in active_entries}

        # Clear listboxes
        self._lb_avail.delete(0, "end")
        self._lb_active.delete(0, "end")

        # Fill available: mods in folder but not yet active
        for mod in all_mods:
            if mod["id"] not in active_ids:
                self._lb_avail.insert("end", mod["display_name"])

        # Fill active: preserve order, mark missing mods with ⚠
        for entry in active_entries:
            mid, name = entry_id(entry), entry.split("|", 1)[-1] if "|" in entry else entry
            if mid not in avail_by_id:
                name += L.t("mgr_missing")
            self._lb_active.insert("end", name)

        already_active = sum(1 for e in active_entries if entry_id(e) in avail_by_id)
        self._mlog(L.t("log_avail", len(all_mods), already_active), "ok")

    def _activate(self):
        """Move selected available mod → active list."""
        sel = self._lb_avail.curselection()
        if not sel:
            return
        idx = sel[0]
        display = self._lb_avail.get(idx)

        # Find the matching mod entry
        mod = next((m for m in self._all_mods if m["display_name"] == display), None)
        if mod is None:
            return

        self._lb_avail.delete(idx)
        self._lb_active.insert("end", display)
        self._active_entries.append(mod["entry"])

        # Keep selection visible
        new_size = self._lb_avail.size()
        if new_size > 0:
            self._lb_avail.selection_set(min(idx, new_size - 1))

    def _deactivate(self):
        """Move selected active mod → available list (sorted position)."""
        sel = self._lb_active.curselection()
        if not sel:
            return
        idx = sel[0]
        entry = self._active_entries[idx]
        mid   = entry_id(entry)

        self._lb_active.delete(idx)
        del self._active_entries[idx]

        # Re-insert in available list at sorted position (if .scs exists)
        mod = next((m for m in self._all_mods if m["id"] == mid), None)
        if mod:
            # Find insertion point (alphabetical by display_name)
            names = list(self._lb_avail.get(0, "end"))
            pos   = next((i for i, n in enumerate(names)
                          if n.lower() > mod["display_name"].lower()), len(names))
            self._lb_avail.insert(pos, mod["display_name"])

        new_size = self._lb_active.size()
        if new_size > 0:
            self._lb_active.selection_set(min(idx, new_size - 1))

    def _move_up(self):
        sel = self._lb_active.curselection()
        if not sel or sel[0] == 0:
            return
        i = sel[0]
        self._swap_active(i, i - 1)
        self._lb_active.selection_clear(0, "end")
        self._lb_active.selection_set(i - 1)
        self._lb_active.see(i - 1)

    def _move_down(self):
        sel = self._lb_active.curselection()
        if not sel or sel[0] >= self._lb_active.size() - 1:
            return
        i = sel[0]
        self._swap_active(i, i + 1)
        self._lb_active.selection_clear(0, "end")
        self._lb_active.selection_set(i + 1)
        self._lb_active.see(i + 1)

    def _swap_active(self, i: int, j: int):
        # Swap in data
        self._active_entries[i], self._active_entries[j] = (
            self._active_entries[j], self._active_entries[i])
        # Swap in listbox
        a, b = self._lb_active.get(i), self._lb_active.get(j)
        self._lb_active.delete(i)
        self._lb_active.insert(i, b)
        self._lb_active.delete(j)
        self._lb_active.insert(j, a)

    def _apply_mods(self):
        L = self.l10n
        profile = self.mgr_profile_path.get().strip()

        if not profile:
            messagebox.showerror(L.t("err_title"), L.t("err_no_profile"))
            return
        if not self._active_entries:
            messagebox.showerror(L.t("err_title"), L.t("err_noactive"))
            return

        try:
            actual, content, _ = find_mods_file(profile, self._mlog)
        except Exception as e:
            self._mlog(str(e), "err")
            messagebox.showerror(L.t("err_title"), str(e))
            return

        new_content = replace_active_mods(content, self._active_entries)
        if new_content is None:
            self._mlog(L.t("err_nomods_m"), "err")
            messagebox.showerror(L.t("err_title"), L.t("err_nomods_m"))
            return

        backup = actual + ".backup"
        shutil.copy2(actual, backup)
        self._mlog(L.t("log_backup", os.path.basename(backup)))

        with open(actual, "w", encoding="utf-8") as fh:
            fh.write(new_content)

        self._mlog(L.t("log_applied", len(self._active_entries)), "ok")
        messagebox.showinfo(
            L.t("ok_title"),
            L.t("ok_applied", len(self._active_entries), backup),
        )


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = App()
    app.mainloop()
