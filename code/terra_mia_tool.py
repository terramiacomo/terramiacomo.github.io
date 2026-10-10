#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Terra Mia – Strumento di Gestione Sito Web
==========================================
Gestisci prodotti, immagini e pubblica su GitHub
in modo semplice e intuitivo.
"""

import os
import sys
import json
import shutil
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from pathlib import Path
from PIL import Image
import subprocess
import re

# ──────────────────────────────────────────────────────────────────────────────
# PERCORSI
# ──────────────────────────────────────────────────────────────────────────────
REPO_ROOT  = Path(__file__).parent.parent          # radice del repository
PRODUCTS_JSON = REPO_ROOT / "data" / "products.json"
REGIONS_JS    = REPO_ROOT / "js"   / "regions.js"
IMAGES_DIR    = REPO_ROOT / "images" / "regions"
CONFIG_FILE   = Path(__file__).parent / "config.json"

# ──────────────────────────────────────────────────────────────────────────────
# TEMA
# ──────────────────────────────────────────────────────────────────────────────
C = {
    "bg":       "#1a1a18",
    "surface":  "#252520",
    "surface2": "#2e2e29",
    "border":   "#3a3a33",
    "accent":   "#c8963e",
    "accent2":  "#8a6b2e",
    "green":    "#5a8a3a",
    "red":      "#9b3a3a",
    "text":     "#e8e0d0",
    "sub":      "#a09880",
    "white":    "#ffffff",
}

FONT_T  = ("Segoe UI", 17, "bold")
FONT_H  = ("Segoe UI", 11, "bold")
FONT_B  = ("Segoe UI", 10)
FONT_S  = ("Segoe UI",  9)
FONT_BT = ("Segoe UI", 10, "bold")


# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURAZIONE
# ──────────────────────────────────────────────────────────────────────────────
def load_config():
    default = {
        "import_folder":  str(Path.home() / "Pictures" / "import"),
        "git_commit_msg": "Aggiornamento sito Terra Mia",
    }
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                default.update(json.load(f))
        except Exception:
            pass
    return default


def save_config(cfg):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS – IMMAGINI / REGIONS.JS
# ──────────────────────────────────────────────────────────────────────────────
def load_regions_js():
    if not REGIONS_JS.exists():
        return {}
    with open(REGIONS_JS, encoding="utf-8") as f:
        content = f.read()
    result = {}
    for m in re.finditer(r'\{\s*name:\s*["\']([^"\']+)["\']\s*,\s*count:\s*(\d+)\s*\}', content):
        result[m.group(1)] = int(m.group(2))
    return result


def save_regions_js(regions_dict):
    if not REGIONS_JS.exists():
        return
    with open(REGIONS_JS, encoding="utf-8") as f:
        content = f.read()
    items_str = ",\n".join(f'    {{ name: "{n}", count: {c} }}' for n, c in regions_dict.items())
    new_array = "const regions = [\n" + items_str + "\n];"
    new_content = re.sub(r'const regions\s*=\s*\[.*?\];', new_array, content, flags=re.DOTALL)
    with open(REGIONS_JS, "w", encoding="utf-8") as f:
        f.write(new_content)


def get_region_image_nums(region_name):
    folder = IMAGES_DIR / region_name
    if not folder.exists():
        return []
    nums = []
    for f in folder.iterdir():
        if f.suffix.lower() in (".jpg", ".jpeg") and "@2x" not in f.name:
            try:
                nums.append(int(f.stem))
            except ValueError:
                pass
    nums.sort()
    return nums


def max_image_num(region_name):
    nums = get_region_image_nums(region_name)
    return max(nums) if nums else 0


def resize_and_copy(src_path, dst_thumb, dst_full, size=(500, 500)):
    dst_full.parent.mkdir(parents=True, exist_ok=True)
    dst_thumb.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_path, dst_full)
    with Image.open(src_path) as img:
        img = img.convert("RGB")
        w, h = img.size
        min_s = min(w, h)
        left  = (w - min_s) // 2
        top   = (h - min_s) // 2
        img   = img.crop((left, top, left + min_s, top + min_s))
        img   = img.resize(size, Image.LANCZOS)
        img.save(dst_thumb, "JPEG", quality=85)


# ──────────────────────────────────────────────────────────────────────────────
# WIDGET HELPERS
# ──────────────────────────────────────────────────────────────────────────────
def btn(parent, text, cmd=None, variant="primary", **kw):
    colors = {
        "primary": (C["accent"],   "#1a1a18"),
        "success": (C["green"],    C["white"]),
        "danger":  (C["red"],      C["white"]),
        "neutral": (C["surface2"], C["text"]),
    }
    bg, fg = colors.get(variant, colors["primary"])
    b = tk.Button(parent, text=text, command=cmd,
                  bg=bg, fg=fg,
                  activebackground=C["accent2"], activeforeground=C["white"],
                  relief="flat", font=FONT_BT, padx=14, pady=6,
                  cursor="hand2", **kw)
    b.bind("<Enter>", lambda e: b.config(bg=C["accent2"]))
    b.bind("<Leave>", lambda e: b.config(bg=bg))
    return b


def lbl(parent, text, **kw):
    defaults = dict(bg=C["surface"], fg=C["text"], font=FONT_B)
    defaults.update(kw)
    return tk.Label(parent, text=text, **defaults)


def entry(parent, var, **kw):
    defaults = dict(bg=C["surface2"], fg=C["text"], font=FONT_B,
                    insertbackground=C["accent"], relief="flat")
    defaults.update(kw)
    return tk.Entry(parent, textvariable=var, **defaults)


class VScrollFrame(tk.Frame):
    """Frame con scrollbar verticale"""
    def __init__(self, container, **kw):
        super().__init__(container, **kw)
        self.canvas = tk.Canvas(self, bg=C["surface"], highlightthickness=0)
        sb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=C["surface"])
        self.inner.bind("<Configure>",
                        lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfig(self._win, width=e.width))
        self.bind_all("<MouseWheel>",
                      lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))


# ══════════════════════════════════════════════════════════════════════════════
#  APPLICAZIONE
# ══════════════════════════════════════════════════════════════════════════════
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self.title("Terra Mia – Gestione Sito")
        self.geometry("1120x740")
        self.minsize(920, 620)
        self.configure(bg=C["bg"])
        self._products_data = []
        self._img_order = []

        self._setup_styles()
        self._build_header()
        self._build_tabs()
        self._build_statusbar()

        self._load_products()

    # ── Stili ──────────────────────────────────────────────────────────────
    def _setup_styles(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("TNotebook",     background=C["bg"],      borderwidth=0)
        s.configure("TNotebook.Tab", background=C["surface2"],
                     foreground=C["sub"], padding=[16, 8], font=FONT_B)
        s.map("TNotebook.Tab",
              background=[("selected", C["accent"])],
              foreground=[("selected", "#1a1a18")])
        s.configure("TScrollbar",    background=C["border"], troughcolor=C["bg"])
        s.configure("Treeview",      background=C["surface"], foreground=C["text"],
                     fieldbackground=C["surface"], font=FONT_B, rowheight=26)
        s.configure("Treeview.Heading", background=C["surface2"],
                     foreground=C["accent"], font=FONT_H)
        s.map("Treeview",
              background=[("selected", C["accent"])],
              foreground=[("selected", "#1a1a18")])
        s.configure("TCombobox", fieldbackground=C["surface2"],
                     background=C["surface2"], foreground=C["text"],
                     selectbackground=C["accent"])

    # ── Header ─────────────────────────────────────────────────────────────
    def _build_header(self):
        hdr = tk.Frame(self, bg=C["surface"], pady=8)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🌿  Terra Mia", font=FONT_T,
                 bg=C["surface"], fg=C["accent"]).pack(side="left", padx=18)
        tk.Label(hdr, text="Gestione Sito Web", font=FONT_B,
                 bg=C["surface"], fg=C["sub"]).pack(side="left", padx=2)
        btn(hdr, "⚙ Impostazioni", cmd=self._settings,
            variant="neutral").pack(side="right", padx=14)

    # ── Tabs ───────────────────────────────────────────────────────────────
    def _build_tabs(self):
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=10, pady=6)

        self.tp = tk.Frame(self.nb, bg=C["surface"])
        self.ti = tk.Frame(self.nb, bg=C["surface"])
        self.tg = tk.Frame(self.nb, bg=C["surface"])

        self.nb.add(self.tp, text="📦  Prodotti")
        self.nb.add(self.ti, text="🖼  Immagini Regioni")
        self.nb.add(self.tg, text="🚀  Pubblica su GitHub")

        self._build_products_tab()
        self._build_images_tab()
        self._build_github_tab()

    # ── Status bar ─────────────────────────────────────────────────────────
    def _build_statusbar(self):
        sb = tk.Frame(self, bg=C["surface2"], pady=3)
        sb.pack(fill="x", side="bottom")
        self._status = tk.StringVar(value="Pronto.")
        tk.Label(sb, textvariable=self._status, font=FONT_S,
                 bg=C["surface2"], fg=C["sub"], anchor="w").pack(fill="x", padx=10)

    def status(self, msg):
        self._status.set(msg)
        self.update_idletasks()

    # ── Impostazioni ───────────────────────────────────────────────────────
    def _settings(self):
        d = tk.Toplevel(self)
        d.title("Impostazioni")
        d.configure(bg=C["bg"])
        d.geometry("580x190")
        d.grab_set()

        vi = tk.StringVar(value=self.cfg.get("import_folder", ""))
        vm = tk.StringVar(value=self.cfg.get("git_commit_msg", ""))

        def row(r, label, var, browse=False):
            lbl(d, label, bg=C["bg"]).grid(row=r, column=0, padx=14, pady=8, sticky="w")
            e = entry(d, var, width=40)
            e.grid(row=r, column=1, padx=6, pady=8, sticky="ew")
            if browse:
                def pick(v=var):
                    p = filedialog.askdirectory(title="Seleziona cartella")
                    if p:
                        v.set(p)
                tk.Button(d, text="…", command=pick, bg=C["surface2"],
                          fg=C["text"], relief="flat", cursor="hand2").grid(
                    row=r, column=2, padx=4)

        row(0, "Cartella Import:", vi, browse=True)
        row(1, "Messaggio Commit:", vm)
        d.columnconfigure(1, weight=1)

        def save():
            self.cfg["import_folder"]   = vi.get()
            self.cfg["git_commit_msg"]  = vm.get()
            save_config(self.cfg)
            self.status("Impostazioni salvate.")
            d.destroy()

        btn(d, "💾 Salva", cmd=save).grid(row=2, column=0, columnspan=3, pady=14)

    # ══════════════════════════════════════════════════════════════════════
    #  TAB – PRODOTTI
    # ══════════════════════════════════════════════════════════════════════
    def _build_products_tab(self):
        p = self.tp

        # Pannello sinistro – lista regioni
        left = tk.Frame(p, bg=C["surface2"], width=195)
        left.pack(side="left", fill="y", padx=(6, 0), pady=6)
        left.pack_propagate(False)

        lbl(left, "Regione", bg=C["surface2"], font=FONT_H,
            fg=C["accent"]).pack(pady=(12, 3), padx=8, anchor="w")

        self._reg_lb = tk.Listbox(
            left, font=FONT_B, bg=C["surface"], fg=C["text"],
            selectbackground=C["accent"], selectforeground="#1a1a18",
            relief="flat", activestyle="none", bd=0
        )
        self._reg_lb.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self._reg_lb.bind("<<ListboxSelect>>", self._on_region)

        btn(left, "+ Aggiungi Regione", cmd=self._add_region,
            variant="neutral").pack(fill="x", padx=6, pady=4)

        # Pannello destro – prodotti
        right = tk.Frame(p, bg=C["surface"])
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)

        self._prod_hdr = lbl(right, "← Seleziona una regione",
                             font=FONT_H, fg=C["accent"])
        self._prod_hdr.pack(fill="x", padx=6, pady=(6, 2))

        tb = tk.Frame(right, bg=C["surface"])
        tb.pack(fill="x", padx=6, pady=3)
        btn(tb, "+ Aggiungi",  cmd=self._add_product).pack(side="left", padx=(0, 4))
        btn(tb, "✏ Modifica",  cmd=self._edit_product, variant="neutral").pack(side="left", padx=3)
        btn(tb, "🗑 Elimina",  cmd=self._del_product,  variant="danger").pack(side="left", padx=3)
        btn(tb, "💾 Salva",    cmd=self._save_products, variant="success").pack(side="right")

        cols = ("nome", "descrizione", "quantita", "prezzo")
        self._tree = ttk.Treeview(right, columns=cols, show="headings", height=18)
        for c, l, w in [("nome","Nome",230),("descrizione","Descrizione",300),
                        ("quantita","Quantità",100),("prezzo","Prezzo",80)]:
            self._tree.heading(c, text=l)
            self._tree.column(c, width=w, anchor="w")
        self._tree.pack(fill="both", expand=True, padx=6, pady=3)

        ob = tk.Frame(right, bg=C["surface"])
        ob.pack(fill="x", padx=6, pady=3)
        lbl(ob, "Riordina:", font=FONT_S, fg=C["sub"]).pack(side="left")
        btn(ob, "▲ Su",   cmd=lambda: self._move_prod(-1), variant="neutral").pack(side="left", padx=3)
        btn(ob, "▼ Giù",  cmd=lambda: self._move_prod(+1), variant="neutral").pack(side="left", padx=3)

    def _load_products(self):
        self._products_data = []
        if PRODUCTS_JSON.exists():
            with open(PRODUCTS_JSON, encoding="utf-8") as f:
                self._products_data = json.load(f)
        self._refresh_regions()

    def _refresh_regions(self):
        self._reg_lb.delete(0, tk.END)
        for r in self._products_data:
            self._reg_lb.insert(tk.END, r["name"])
        # Aggiorna anche combo immagini se esiste
        if hasattr(self, "_img_combo"):
            vals = [r["name"] for r in self._products_data]
            self._img_combo["values"] = vals

    def _current_region(self):
        sel = self._reg_lb.curselection()
        if not sel:
            messagebox.showwarning("Attenzione", "Seleziona prima una regione.")
            return None, None
        idx = sel[0]
        return idx, self._products_data[idx]

    def _on_region(self, _event=None):
        sel = self._reg_lb.curselection()
        if not sel:
            return
        reg = self._products_data[sel[0]]
        self._prod_hdr.config(text=f"📦  {reg['name']}")
        self._refresh_tree(reg["items"])

    def _refresh_tree(self, items):
        for row in self._tree.get_children():
            self._tree.delete(row)
        for it in items:
            self._tree.insert("", tk.END, values=(
                it.get("name",""), it.get("description",""),
                it.get("quantity",""), it.get("price","")))

    def _add_region(self):
        name = simpledialog.askstring("Nuova Regione", "Nome della regione:", parent=self)
        if not name:
            return
        rid = "tab-" + name.lower().replace(" ", "-")
        self._products_data.append({"id": rid, "name": name, "items": []})
        self._refresh_regions()
        self._reg_lb.selection_set(tk.END)
        self._on_region()

    def _add_product(self):
        _, reg = self._current_region()
        if reg is None:
            return
        data = self._product_dlg()
        if data:
            reg["items"].append(data)
            self._refresh_tree(reg["items"])

    def _edit_product(self):
        _, reg = self._current_region()
        if reg is None:
            return
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("Attenzione", "Seleziona un prodotto.")
            return
        idx  = self._tree.index(sel[0])
        data = self._product_dlg(reg["items"][idx])
        if data:
            reg["items"][idx] = data
            self._refresh_tree(reg["items"])

    def _del_product(self):
        _, reg = self._current_region()
        if reg is None:
            return
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("Attenzione", "Seleziona un prodotto.")
            return
        if not messagebox.askyesno("Conferma", "Eliminare il prodotto selezionato?"):
            return
        idx = self._tree.index(sel[0])
        del reg["items"][idx]
        self._refresh_tree(reg["items"])

    def _move_prod(self, d):
        _, reg = self._current_region()
        if reg is None:
            return
        sel = self._tree.selection()
        if not sel:
            return
        idx  = self._tree.index(sel[0])
        ni   = idx + d
        items = reg["items"]
        if 0 <= ni < len(items):
            items[idx], items[ni] = items[ni], items[idx]
            self._refresh_tree(items)
            ch = self._tree.get_children()
            if 0 <= ni < len(ch):
                self._tree.selection_set(ch[ni])
                self._tree.focus(ch[ni])

    def _product_dlg(self, existing=None):
        result = {}
        confirmed = [False]

        d = tk.Toplevel(self)
        d.title("Prodotto")
        d.configure(bg=C["bg"])
        d.geometry("520x300")
        d.grab_set()
        d.columnconfigure(1, weight=1)

        fields = [("Nome *","name"), ("Descrizione","description"),
                  ("Quantità","quantity"), ("Prezzo","price")]
        vs = {}
        for i, (label, key) in enumerate(fields):
            lbl(d, label, bg=C["bg"]).grid(row=i, column=0, padx=14, pady=7, sticky="w")
            v = tk.StringVar(value=(existing or {}).get(key, ""))
            vs[key] = v
            e = entry(d, v, width=38)
            e.grid(row=i, column=1, padx=8, pady=7, sticky="ew")
            if i == 0:
                e.focus_set()

        def ok():
            if not vs["name"].get().strip():
                messagebox.showwarning("Attenzione", "Il nome è obbligatorio.", parent=d)
                return
            for k, v in vs.items():
                result[k] = v.get().strip()
            confirmed[0] = True
            d.destroy()

        br = tk.Frame(d, bg=C["bg"])
        br.grid(row=len(fields), column=0, columnspan=2, pady=14)
        btn(br, "✅ Conferma", cmd=ok).pack(side="left", padx=8)
        btn(br, "Annulla", cmd=d.destroy, variant="neutral").pack(side="left")
        d.bind("<Return>", lambda e: ok())
        d.bind("<Escape>", lambda e: d.destroy())
        d.wait_window()
        return result if confirmed[0] else None

    def _save_products(self):
        try:
            with open(PRODUCTS_JSON, "w", encoding="utf-8") as f:
                json.dump(self._products_data, f, ensure_ascii=False, indent=2)
            self.status("✅ products.json salvato.")
            messagebox.showinfo("Salvato", "Lista prodotti salvata con successo!")
        except Exception as ex:
            messagebox.showerror("Errore", str(ex))

    # ══════════════════════════════════════════════════════════════════════
    #  TAB – IMMAGINI REGIONI
    # ══════════════════════════════════════════════════════════════════════
    def _build_images_tab(self):
        p = self.ti

        # Toolbar
        top = tk.Frame(p, bg=C["surface2"])
        top.pack(fill="x", padx=8, pady=8)
        lbl(top, "Regione:", bg=C["surface2"]).pack(side="left", padx=8)

        self._img_region = tk.StringVar()
        self._img_combo  = ttk.Combobox(
            top, textvariable=self._img_region,
            values=[r["name"] for r in self._products_data],
            state="readonly", font=FONT_B, width=22
        )
        self._img_combo.pack(side="left", padx=4)
        self._img_combo.bind("<<ComboboxSelected>>", self._img_load)

        btn(top, "📥 Importa da cartella", cmd=self._import_images).pack(side="left", padx=10)
        btn(top, "🔄 Aggiorna lista", cmd=self._img_load, variant="neutral").pack(side="left", padx=4)

        # Intestazione colonne
        ch = tk.Frame(p, bg=C["surface2"])
        ch.pack(fill="x", padx=8)
        for text, flex in [("#", False), ("Immagine", True), ("500px ✓", False),
                           ("Alta Res ✓", False), ("Azioni", False)]:
            tk.Label(ch, text=text, font=FONT_H, bg=C["surface2"],
                     fg=C["accent"], anchor="w",
                     width=(None if flex else 10)).pack(
                side="left", padx=8, pady=4, fill="x" if flex else "none")

        # Lista scorrevole
        self._img_sf = VScrollFrame(p, bg=C["surface"])
        self._img_sf.pack(fill="both", expand=True, padx=8)

        self._img_info = tk.Label(p, text="", font=FONT_S,
                                  bg=C["bg"], fg=C["sub"])
        self._img_info.pack(pady=2)

        bot = tk.Frame(p, bg=C["surface2"])
        bot.pack(fill="x", padx=8, pady=6)
        lbl(bot, "Dopo riordino/eliminazione:", bg=C["surface2"], fg=C["sub"],
            font=FONT_S).pack(side="left", padx=8)
        btn(bot, "💾 Applica modifiche immagini",
            cmd=self._apply_image_changes, variant="success").pack(side="right", padx=8)

    def _img_load(self, _=None):
        region = self._img_region.get()
        if not region:
            return
        self._img_order = get_region_image_nums(region)
        self._img_refresh(region)

    def _img_refresh(self, region=None):
        if region is None:
            region = self._img_region.get()
        inner = self._img_sf.inner
        for w in inner.winfo_children():
            w.destroy()
        self._img_info.config(
            text=f"Regione: {region}  |  Immagini: {len(self._img_order)}")
        for pos, num in enumerate(self._img_order):
            self._img_row(inner, pos, num, region)

    def _img_row(self, parent, pos, num, region):
        folder = IMAGES_DIR / region
        ok_t   = (folder / f"{num}.jpeg").exists()
        ok_f   = (folder / f"{num}@2x.jpeg").exists()

        row = tk.Frame(parent, bg=C["surface"],
                       highlightbackground=C["border"], highlightthickness=1)
        row.pack(fill="x", padx=2, pady=1)

        tk.Label(row, text=f"{pos+1}", width=4,
                 bg=C["surface"], fg=C["sub"], font=FONT_S).pack(side="left", padx=6)
        tk.Label(row, text=f"{num}.jpeg", width=14,
                 bg=C["surface"], fg=C["text"], font=FONT_B, anchor="w").pack(side="left", padx=4)
        tk.Label(row, text="✅" if ok_t else "❌", width=10,
                 bg=C["surface"], fg=C["green"] if ok_t else C["red"],
                 font=FONT_B).pack(side="left", padx=4)
        tk.Label(row, text="✅" if ok_f else "❌", width=10,
                 bg=C["surface"], fg=C["green"] if ok_f else C["red"],
                 font=FONT_B).pack(side="left", padx=4)

        act = tk.Frame(row, bg=C["surface"])
        act.pack(side="right", padx=6)

        for text, cmd in [("▲", lambda n=num: self._img_up(n)),
                           ("▼", lambda n=num: self._img_dn(n)),
                           ("🗑", lambda n=num: self._img_del(n))]:
            bg = C["red"] if text == "🗑" else C["surface2"]
            fg = C["white"] if text == "🗑" else C["text"]
            tk.Button(act, text=text, command=cmd, bg=bg, fg=fg,
                      relief="flat", cursor="hand2", font=FONT_S,
                      padx=5).pack(side="left", padx=2)

    def _img_up(self, num):
        try:
            i = self._img_order.index(num)
        except ValueError:
            return
        if i > 0:
            self._img_order[i], self._img_order[i-1] = self._img_order[i-1], self._img_order[i]
            self._img_refresh()

    def _img_dn(self, num):
        try:
            i = self._img_order.index(num)
        except ValueError:
            return
        if i < len(self._img_order) - 1:
            self._img_order[i], self._img_order[i+1] = self._img_order[i+1], self._img_order[i]
            self._img_refresh()

    def _img_del(self, num):
        if not messagebox.askyesno("Conferma",
                f"Eliminare l'immagine n.{num}?\n(Il file verrà cancellato dal disco)"):
            return
        region = self._img_region.get()
        folder = IMAGES_DIR / region
        for f in [folder / f"{num}.jpeg", folder / f"{num}@2x.jpeg"]:
            try:
                f.unlink(missing_ok=True)
            except Exception:
                pass
        self._img_order.remove(num)
        self._img_refresh(region)
        self.status(f"Immagine {num} eliminata. Premi 'Applica modifiche' per rinumerare.")

    def _apply_image_changes(self):
        region = self._img_region.get()
        if not region:
            messagebox.showwarning("Attenzione", "Seleziona una regione.")
            return
        folder = IMAGES_DIR / region
        if not folder.exists():
            messagebox.showerror("Errore", f"Cartella non trovata:\n{folder}")
            return

        order  = self._img_order
        if not order:
            messagebox.showinfo("Info", "Nessuna immagine da riordinare.")
            return

        # Sposta tutto in tmp
        for i, num in enumerate(order):
            for sfx in ("", "@2x"):
                src = folder / f"{num}{sfx}.jpeg"
                dst = folder / f"__tmp_{i}{sfx}.jpeg"
                if src.exists():
                    shutil.copy2(src, dst)

        # Rimuovi originali (non tmp)
        for f in folder.iterdir():
            if f.suffix.lower() == ".jpeg" and not f.name.startswith("__tmp_"):
                f.unlink()

        # Rinomina tmp → 1,2,3...
        for i in range(len(order)):
            for sfx in ("", "@2x"):
                src = folder / f"__tmp_{i}{sfx}.jpeg"
                dst = folder / f"{i+1}{sfx}.jpeg"
                if src.exists():
                    shutil.move(str(src), str(dst))

        # Aggiorna regions.js
        rd = load_regions_js()
        rd[region] = len(order)
        save_regions_js(rd)

        self._img_order = list(range(1, len(order)+1))
        self._img_refresh(region)
        self.status(f"✅ {region}: {len(order)} immagini rinumerate, regions.js aggiornato.")
        messagebox.showinfo("Fatto",
            f"Immagini di {region} riordinate e rinumerate!\n"
            f"Totale: {len(order)} immagini.\nregions.js aggiornato.")

    def _import_images(self):
        region = self._img_region.get()
        if not region:
            messagebox.showwarning("Attenzione", "Seleziona prima una regione.")
            return

        import_root   = Path(self.cfg.get("import_folder", Path.home() / "Pictures" / "import"))
        import_folder = import_root / region
        EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".heic", ".heif"}

        if import_folder.exists():
            src_files = [f for f in import_folder.iterdir() if f.suffix.lower() in EXTS]
        else:
            ans = messagebox.askyesno(
                "Cartella non trovata",
                f"Cartella non trovata:\n{import_folder}\n\n"
                "Vuoi selezionare le immagini manualmente?"
            )
            if not ans:
                return
            raw = filedialog.askopenfilenames(
                title="Seleziona immagini da importare",
                filetypes=[("Immagini", "*.jpg *.jpeg *.png *.webp *.bmp")]
            )
            if not raw:
                return
            src_files = [Path(f) for f in raw]

        if not src_files:
            messagebox.showinfo("Nessun file", "Nessuna immagine trovata.")
            return

        if not messagebox.askyesno("Importa",
                f"Trovate {len(src_files)} immagini per '{region}'.\n"
                "Verranno create versioni 500×500px (anteprima) e alta risoluzione.\n\n"
                "Procedere?"):
            return

        dst_folder = IMAGES_DIR / region
        dst_folder.mkdir(parents=True, exist_ok=True)
        next_n = max_image_num(region) + 1

        # Finestra progresso
        pw = tk.Toplevel(self)
        pw.title("Importazione...")
        pw.configure(bg=C["bg"])
        pw.geometry("400x130")
        pw.grab_set()
        pl = lbl(pw, "Elaborazione in corso...", bg=C["bg"])
        pl.pack(pady=14)
        pb = ttk.Progressbar(pw, length=340, maximum=len(src_files))
        pb.pack(padx=20)
        pc = lbl(pw, "", bg=C["bg"], fg=C["sub"], font=FONT_S)
        pc.pack(pady=4)

        errors = []

        def do():
            nonlocal next_n
            for i, src in enumerate(src_files):
                try:
                    dt = dst_folder / f"{next_n}.jpeg"
                    df = dst_folder / f"{next_n}@2x.jpeg"
                    pl.config(text=f"Elaboro: {src.name}")
                    pc.config(text=f"{i+1} / {len(src_files)}")
                    pb["value"] = i + 1
                    pw.update_idletasks()
                    resize_and_copy(src, dt, df)
                    next_n += 1
                except Exception as ex:
                    errors.append(f"{src.name}: {ex}")

            rd = load_regions_js()
            rd[region] = next_n - 1
            save_regions_js(rd)
            pw.destroy()

            msg = f"✅ Importate {len(src_files)-len(errors)} immagini in '{region}'."
            if errors:
                msg += f"\n⚠️ Errori:\n" + "\n".join(errors[:5])
            messagebox.showinfo("Completato", msg)
            self._img_load()
            self.status(f"✅ Importazione '{region}' completata. Totale: {next_n-1}")

        threading.Thread(target=do, daemon=True).start()

    # ══════════════════════════════════════════════════════════════════════
    #  TAB – PUBBLICA SU GITHUB
    # ══════════════════════════════════════════════════════════════════════
    def _build_github_tab(self):
        p = self.tg

        tk.Label(p, text="🚀  Pubblica Modifiche su GitHub",
                 font=FONT_T, bg=C["surface"], fg=C["accent"]).pack(pady=14)
        tk.Label(p,
            text="Invia tutte le modifiche al sito su GitHub Pages.\n"
                 "Le modifiche saranno visibili online entro pochi minuti.",
            font=FONT_B, bg=C["surface"], fg=C["text"], justify="center").pack(pady=2)

        sf = tk.LabelFrame(p, text=" Stato Repository ",
                           font=FONT_H, bg=C["surface"],
                           fg=C["accent"], relief="flat", bd=2)
        sf.pack(fill="x", padx=40, pady=12)
        self._git_st = tk.Text(sf, height=9,
                               bg=C["surface2"], fg=C["text"],
                               font=("Consolas", 10), relief="flat",
                               state="disabled", wrap="word")
        self._git_st.pack(fill="both", padx=8, pady=8)

        mf = tk.Frame(p, bg=C["surface"])
        mf.pack(fill="x", padx=40, pady=2)
        lbl(mf, "Messaggio commit:").pack(side="left", padx=4)
        self._commit_var = tk.StringVar(value=self.cfg.get("git_commit_msg", "Aggiornamento sito Terra Mia"))
        entry(mf, self._commit_var, width=50).pack(side="left", padx=8, fill="x", expand=True)

        br = tk.Frame(p, bg=C["surface"])
        br.pack(pady=14)
        btn(br, "🔍 Verifica modifiche", cmd=self._git_status, variant="neutral").pack(side="left", padx=8)
        btn(br, "🚀 Pubblica su GitHub", cmd=self._git_push).pack(side="left", padx=8)

        self._git_log = tk.Text(p, height=7,
                                bg=C["bg"], fg=C["text"],
                                font=("Consolas", 9), relief="flat",
                                state="disabled", wrap="word")
        self._git_log.pack(fill="x", padx=40, pady=6)
        self._git_status()

    def _git_run(self, args):
        try:
            r = subprocess.run(["git"] + args, cwd=str(REPO_ROOT),
                               capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            return r.returncode, r.stdout.strip(), r.stderr.strip()
        except FileNotFoundError:
            return -1, "", "Git non trovato. Installa Git da https://git-scm.com"

    def _git_status(self):
        self._git_st.config(state="normal")
        self._git_st.delete("1.0", tk.END)
        code, out, err = self._git_run(["status", "--short"])
        if code == -1:
            self._git_st.insert(tk.END, f"❌ {err}")
        elif not out:
            self._git_st.insert(tk.END, "✅ Nessuna modifica in sospeso. Il sito è aggiornato.")
        else:
            self._git_st.insert(tk.END, "📝 Modifiche da pubblicare:\n\n" + out)
        self._git_st.config(state="disabled")

    def _git_write(self, msg, color=None):
        self._git_log.config(state="normal")
        tag = f"c{color}" if color else "default"
        self._git_log.tag_config(tag, foreground=color or C["text"])
        self._git_log.insert(tk.END, msg + "\n", tag)
        self._git_log.see(tk.END)
        self._git_log.config(state="disabled")

    def _git_push(self):
        msg = self._commit_var.get().strip()
        if not msg:
            messagebox.showwarning("Attenzione", "Inserisci un messaggio di commit.")
            return
        code, out, _ = self._git_run(["status", "--short"])
        if code == -1:
            messagebox.showerror("Errore", "Git non trovato.")
            return
        if not out:
            messagebox.showinfo("Info", "Nessuna modifica da pubblicare.")
            return
        if not messagebox.askyesno("Pubblica",
                f'Pubblicare le modifiche su GitHub?\n\nMessaggio: "{msg}"'):
            return

        self._git_log.config(state="normal")
        self._git_log.delete("1.0", tk.END)
        self._git_log.config(state="disabled")

        def do():
            self._git_write("▶ git add -A ...", C["sub"])
            c, o, e = self._git_run(["add", "-A"])
            if c != 0:
                self._git_write(f"❌ {e}", C["red"]); return

            self._git_write(f'▶ git commit -m "{msg}" ...', C["sub"])
            c, o, e = self._git_run(["commit", "-m", msg])
            if c != 0:
                self._git_write(f"❌ {e}", C["red"]); return
            self._git_write(o, C["green"])

            self._git_write("▶ git push ...", C["sub"])
            c, o, e = self._git_run(["push"])
            if c != 0:
                self._git_write(f"❌ {e or o}", C["red"])
                self._git_write("💡 Assicurati di essere autenticato su GitHub.", C["accent"])
            else:
                self._git_write("✅ Pubblicato con successo!", C["green"])
                self._git_write("🌐 Modifiche visibili online tra qualche minuto.", C["accent"])
                self.status("✅ Sito pubblicato su GitHub!")
                self._git_status()

        threading.Thread(target=do, daemon=True).start()


# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()
