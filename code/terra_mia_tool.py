#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Terra Mia – Strumento di Gestione Sito Web
==========================================
Gestisci prodotti, immagini, anteprima locale del sito
e pubblica su GitHub in modo semplice e intuitivo.
"""

import os
import sys
import json
import shutil
import socket
import threading
import subprocess
import re
import webbrowser
import http.server
import socketserver
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from pathlib import Path
from PIL import Image, ImageTk

# ──────────────────────────────────────────────────────────────────────────────
# PERCORSI
# ──────────────────────────────────────────────────────────────────────────────
REPO_ROOT     = Path(__file__).parent.parent          # radice del repository
PRODUCTS_JSON = REPO_ROOT / "data" / "products.json"
REGIONS_JS    = REPO_ROOT / "js"   / "regions.js"
IMAGES_DIR    = REPO_ROOT / "images" / "regions"
CONFIG_FILE   = Path(__file__).parent / "config.json"

# ──────────────────────────────────────────────────────────────────────────────
# TEMA VISIVO
# ──────────────────────────────────────────────────────────────────────────────
C = {
    "bg":       "#1a1a18",
    "surface":  "#252520",
    "surface2": "#2e2e29",
    "border":   "#3a3a33",
    "accent":   "#c8963e",
    "accent2":  "#8a6b2e",
    "green":    "#4e9432",
    "green_bg": "#223819",
    "red":      "#a63838",
    "text":     "#e8e0d0",
    "sub":      "#a09880",
    "white":    "#ffffff",
}

FONT_T  = ("Segoe UI", 16, "bold")
FONT_H  = ("Segoe UI", 11, "bold")
FONT_B  = ("Segoe UI", 10)
FONT_S  = ("Segoe UI",  9)
FONT_BT = ("Segoe UI", 10, "bold")
FONT_BIG_BTN = ("Segoe UI", 12, "bold")


# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURAZIONE
# ──────────────────────────────────────────────────────────────────────────────
def load_config():
    default = {
        "import_folder":  str(Path.home() / "Pictures" / "import"),
        "git_commit_msg": "Aggiornamento sito Terra Mia",
        "server_port":    8000,
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
    # Ordina sempre le regioni in ordine alfabetico (A-Z)
    sorted_items = sorted(regions_dict.items(), key=lambda x: x[0].strip().lower())
    items_str = ",\n".join(f'    {{ name: "{n}", count: {c} }}' for n, c in sorted_items)
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
    nums = sorted(list(set(nums)))
    return nums


def max_image_num(region_name):
    nums = get_region_image_nums(region_name)
    return max(nums) if nums else 0


def get_image_files_for_num(folder, num):
    """
    Trova i percorsi effettivi per l'immagine num (default .jpeg, fallback .jpg).
    Restituisce (thumb_path, full_path).
    """
    thumb = None
    full  = None
    for ext in (".jpeg", ".jpg"):
        t = folder / f"{num}{ext}"
        if t.exists() and thumb is None:
            thumb = t
        f = folder / f"{num}@2x{ext}"
        if f.exists() and full is None:
            full = f
    if thumb is None:
        thumb = folder / f"{num}.jpeg"
    if full is None:
        full = folder / f"{num}@2x.jpeg"
    return thumb, full


def resize_and_copy(src_path, dst_thumb, dst_full, size=(500, 500)):
    dst_full.parent.mkdir(parents=True, exist_ok=True)
    dst_thumb.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src_path) as img:
        img = img.convert("RGB")
        # Salva sempre come vero JPEG (.jpg), anche se l'originale era PNG/WEBP
        img.save(dst_full, "JPEG", quality=92)
        w, h = img.size
        min_s = min(w, h)
        left  = (w - min_s) // 2
        top   = (h - min_s) // 2
        thumb = img.crop((left, top, left + min_s, top + min_s))
        thumb = thumb.resize(size, Image.LANCZOS)
        thumb.save(dst_thumb, "JPEG", quality=85)


# ──────────────────────────────────────────────────────────────────────────────
# SERVER HTTP LOCALE (SENZA CACHE PER ANTEPRIMA IMMEDIATA)
# ──────────────────────────────────────────────────────────────────────────────
class NoCacheHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

    def log_message(self, format, *args):
        # Silenzioso: non intasa i log di sistema
        pass

    def end_headers(self):
        # Disabilita la cache per mostrare subito le modifiche a foto e json
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()


class LocalServerManager:
    def __init__(self, root_dir):
        self.root_dir = root_dir
        self.server = None
        self.thread = None
        self.port = 8000
        self.is_running = False

    def start(self, preferred_port=8000):
        if self.is_running and self.server:
            return self.port

        # Cerca una porta libera
        ports = [preferred_port, 8080, 8081, 8888, 5500, 5000]
        selected_server = None
        selected_port = None

        for p in ports:
            try:
                class ReusableTCPServer(socketserver.TCPServer):
                    allow_reuse_address = True

                s = ReusableTCPServer(("127.0.0.1", p), NoCacheHTTPRequestHandler)
                selected_server = s
                selected_port = p
                break
            except OSError:
                continue

        if not selected_server:
            # Prova una porta casuale assegnata dal sistema operativo
            try:
                class ReusableTCPServer(socketserver.TCPServer):
                    allow_reuse_address = True

                s = ReusableTCPServer(("127.0.0.1", 0), NoCacheHTTPRequestHandler)
                selected_server = s
                selected_port = s.server_address[1]
            except Exception as ex:
                raise RuntimeError(f"Impossibile avviare il server web locale: {ex}")

        self.server = selected_server
        self.port = selected_port
        self.is_running = True

        def run_loop():
            try:
                self.server.serve_forever()
            except Exception:
                pass
            finally:
                self.is_running = False

        self.thread = threading.Thread(target=run_loop, daemon=True)
        self.thread.start()
        return self.port

    def stop(self):
        if self.server:
            try:
                self.server.shutdown()
                self.server.server_close()
            except Exception:
                pass
            self.server = None
            self.thread = None
            self.is_running = False


# ──────────────────────────────────────────────────────────────────────────────
# WIDGET HELPERS
# ──────────────────────────────────────────────────────────────────────────────
def btn(parent, text, cmd=None, variant="primary", font=FONT_BT, **kw):
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
                  relief="flat", font=font, padx=12, pady=5,
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
#  APPLICAZIONE PRINCIPALE
# ══════════════════════════════════════════════════════════════════════════════
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self.title("Terra Mia – Gestione Sito Web")
        self.geometry("1160x760")
        self.minsize(960, 640)
        self.configure(bg=C["bg"])

        self._products_data = []
        self._img_order = []
        self._thumb_cache = {}          # Cache miniature (path -> ImageTk.PhotoImage)
        self._large_preview_photo = None # Riferimento per anteprima grande
        self._current_preview_file = None

        # Server locale
        self.server_mgr = LocalServerManager(REPO_ROOT)

        self._setup_styles()
        self._build_header()
        self._build_tabs()
        self._build_statusbar()

        self._load_products()

        # Chiusura pulita della finestra
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        try:
            self.server_mgr.stop()
        except Exception:
            pass
        self.destroy()

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

        # Pulsanti scorciatoia a destra
        btn(hdr, "⚙ Impostazioni", cmd=self._settings,
            variant="neutral").pack(side="right", padx=12)
        btn(hdr, "🌐 Anteprima Sito", cmd=lambda: self.nb.select(self.tw),
            variant="primary").pack(side="right", padx=4)

    # ── Tabs ───────────────────────────────────────────────────────────────
    def _build_tabs(self):
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=10, pady=6)

        self.tp = tk.Frame(self.nb, bg=C["surface"])
        self.ti = tk.Frame(self.nb, bg=C["surface"])
        self.tw = tk.Frame(self.nb, bg=C["surface"])
        self.tg = tk.Frame(self.nb, bg=C["surface"])

        self.nb.add(self.tp, text="📦  1. Prodotti")
        self.nb.add(self.ti, text="🖼  2. Immagini Regioni")
        self.nb.add(self.tw, text="🌐  3. Anteprima Sito")
        self.nb.add(self.tg, text="🚀  4. Pubblica su GitHub")

        self._build_products_tab()
        self._build_images_tab()
        self._build_preview_tab()
        self._build_github_tab()

    # ── Status bar ─────────────────────────────────────────────────────────
    def _build_statusbar(self):
        sb = tk.Frame(self, bg=C["surface2"], pady=4)
        sb.pack(fill="x", side="bottom")
        self._status = tk.StringVar(value="Pronto.")
        tk.Label(sb, textvariable=self._status, font=FONT_S,
                 bg=C["surface2"], fg=C["sub"], anchor="w").pack(fill="x", padx=12)

    def status(self, msg):
        self._status.set(msg)
        self.update_idletasks()

    # ── Impostazioni ───────────────────────────────────────────────────────
    def _settings(self):
        d = tk.Toplevel(self)
        d.title("Impostazioni")
        d.configure(bg=C["bg"])
        d.geometry("580x210")
        d.grab_set()

        vi = tk.StringVar(value=self.cfg.get("import_folder", ""))
        vm = tk.StringVar(value=self.cfg.get("git_commit_msg", ""))

        def row(r, label, var, browse=False):
            lbl(d, label, bg=C["bg"]).grid(row=r, column=0, padx=14, pady=8, sticky="w")
            e = entry(d, var, width=40)
            e.grid(row=r, column=1, padx=6, pady=8, sticky="ew")
            if browse:
                def pick(v=var):
                    p = filedialog.askdirectory(title="Seleziona cartella import")
                    if p:
                        v.set(p)
                tk.Button(d, text="…", command=pick, bg=C["surface2"],
                          fg=C["text"], relief="flat", cursor="hand2").grid(
                    row=r, column=2, padx=4)

        row(0, "Cartella Import Foto:", vi, browse=True)
        row(1, "Messaggio Commit:", vm)
        d.columnconfigure(1, weight=1)

        def save():
            self.cfg["import_folder"]  = vi.get()
            self.cfg["git_commit_msg"] = vm.get()
            save_config(self.cfg)
            self.status("Impostazioni salvate.")
            d.destroy()

        btn(d, "💾 Salva Impostazioni", cmd=save).grid(row=2, column=0, columnspan=3, pady=16)

    # ══════════════════════════════════════════════════════════════════════
    #  TAB 1 – PRODOTTI (CON ORDINAMENTO ALFABETICO E MANUALE REGIONI)
    # ══════════════════════════════════════════════════════════════════════
    def _build_products_tab(self):
        p = self.tp

        # Pannello sinistro – lista e gestione regioni
        left = tk.Frame(p, bg=C["surface2"], width=230)
        left.pack(side="left", fill="y", padx=(6, 0), pady=6)
        left.pack_propagate(False)

        lbl(left, "📍 Regioni", bg=C["surface2"], font=FONT_H,
            fg=C["accent"]).pack(pady=(10, 4), padx=10, anchor="w")

        self._reg_lb = tk.Listbox(
            left, font=FONT_B, bg=C["surface"], fg=C["text"],
            selectbackground=C["accent"], selectforeground="#1a1a18",
            relief="flat", activestyle="none", bd=0
        )
        self._reg_lb.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self._reg_lb.bind("<<ListboxSelect>>", self._on_region)

        # Pulsante aggiunta nuova regione (in ordine alfabetico)
        btn(left, "+ Nuova Regione", cmd=self._add_region,
            variant="primary").pack(fill="x", padx=6, pady=(2, 4))

        # Pulsanti riordino manuale della regione selezionata
        ord_frame = tk.Frame(left, bg=C["surface2"])
        ord_frame.pack(fill="x", padx=6, pady=2)
        lbl(ord_frame, "Sposta regione:", font=FONT_S, bg=C["surface2"], fg=C["sub"]).pack(side="top", anchor="w")
        
        btn_ord = tk.Frame(ord_frame, bg=C["surface2"])
        btn_ord.pack(fill="x", pady=2)
        btn(btn_ord, "▲ Sposta Su", cmd=lambda: self._move_region(-1),
            variant="neutral", font=FONT_S).pack(side="left", fill="x", expand=True, padx=(0, 2))
        btn(btn_ord, "▼ Sposta Giù", cmd=lambda: self._move_region(+1),
            variant="neutral", font=FONT_S).pack(side="right", fill="x", expand=True, padx=(2, 0))

        # Pulsanti utilità regioni: Ordina A-Z ed Elimina
        util_frame = tk.Frame(left, bg=C["surface2"])
        util_frame.pack(fill="x", padx=6, pady=(4, 8))
        btn(util_frame, "🔤 Ordina Tutte A-Z", cmd=self._sort_regions_alpha,
            variant="neutral", font=FONT_S).pack(fill="x", pady=2)
        btn(util_frame, "🗑 Elimina Regione", cmd=self._del_region,
            variant="danger", font=FONT_S).pack(fill="x", pady=2)

        # Pannello destro – prodotti della regione selezionata
        right = tk.Frame(p, bg=C["surface"])
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)

        self._prod_hdr = lbl(right, "← Seleziona una regione dall'elenco",
                             font=FONT_H, fg=C["accent"])
        self._prod_hdr.pack(fill="x", padx=6, pady=(6, 2))

        tb = tk.Frame(right, bg=C["surface"])
        tb.pack(fill="x", padx=6, pady=4)
        btn(tb, "+ Aggiungi Prodotto", cmd=self._add_product).pack(side="left", padx=(0, 4))
        btn(tb, "✏ Modifica", cmd=self._edit_product, variant="neutral").pack(side="left", padx=3)
        btn(tb, "🗑 Elimina",  cmd=self._del_product,  variant="danger").pack(side="left", padx=3)
        btn(tb, "💾 Salva Modifiche", cmd=self._save_products, variant="success").pack(side="right")

        cols = ("nome", "descrizione", "quantita", "prezzo")
        self._tree = ttk.Treeview(right, columns=cols, show="headings", height=18)
        for c, l, w in [("nome", "Nome", 220), ("descrizione", "Descrizione", 300),
                        ("quantita", "Quantità", 100), ("prezzo", "Prezzo", 90)]:
            self._tree.heading(c, text=l)
            self._tree.column(c, width=w, anchor="w")
        self._tree.pack(fill="both", expand=True, padx=6, pady=4)

        ob = tk.Frame(right, bg=C["surface"])
        ob.pack(fill="x", padx=6, pady=3)
        lbl(ob, "Riordina prodotti selezionati:", font=FONT_S, fg=C["sub"]).pack(side="left")
        btn(ob, "▲ Su",  cmd=lambda: self._move_prod(-1), variant="neutral").pack(side="left", padx=4)
        btn(ob, "▼ Giù", cmd=lambda: self._move_prod(+1), variant="neutral").pack(side="left", padx=2)

    def _load_products(self):
        self._products_data = []
        if PRODUCTS_JSON.exists():
            try:
                with open(PRODUCTS_JSON, encoding="utf-8") as f:
                    self._products_data = json.load(f)
            except Exception as ex:
                messagebox.showerror("Errore lettura", f"Impossibile leggere products.json:\n{ex}")
        self._refresh_regions()

    def _refresh_regions(self):
        self._reg_lb.delete(0, tk.END)
        for r in self._products_data:
            self._reg_lb.insert(tk.END, r["name"])
        # Aggiorna anche il combobox della tab immagini
        if hasattr(self, "_img_combo"):
            vals = [r["name"] for r in self._products_data]
            self._img_combo["values"] = vals

    def _current_region(self):
        sel = self._reg_lb.curselection()
        if not sel:
            messagebox.showwarning("Attenzione", "Seleziona prima una regione dall'elenco a sinistra.")
            return None, None
        idx = sel[0]
        return idx, self._products_data[idx]

    def _on_region(self, _event=None):
        sel = self._reg_lb.curselection()
        if not sel:
            return
        reg = self._products_data[sel[0]]
        self._prod_hdr.config(text=f"📦 Prodotti per: {reg['name']}")
        self._refresh_tree(reg.get("items", []))

    def _refresh_tree(self, items):
        for row in self._tree.get_children():
            self._tree.delete(row)
        for it in items:
            self._tree.insert("", tk.END, values=(
                it.get("name", ""), it.get("description", ""),
                it.get("quantity", ""), it.get("price", "")))

    def _add_region(self):
        name = simpledialog.askstring("Nuova Regione", "Inserisci il nome della regione da aggiungere:", parent=self)
        if not name or not name.strip():
            return
        name = name.strip()

        # Verifica se già presente
        for i, r in enumerate(self._products_data):
            if r["name"].strip().lower() == name.lower():
                messagebox.showinfo("Regione esistente", f"La regione '{r['name']}' è già presente nell'elenco.")
                self._reg_lb.selection_clear(0, tk.END)
                self._reg_lb.selection_set(i)
                self._reg_lb.see(i)
                self._on_region()
                return

        rid = "tab-" + name.lower().replace(" ", "-").replace("'", "-")
        new_entry = {"id": rid, "name": name, "items": []}

        # Inserimento AUTOMATICO in ordine alfabetico A-Z
        insert_idx = len(self._products_data)
        for i, r in enumerate(self._products_data):
            if r["name"].strip().lower() > name.lower():
                insert_idx = i
                break

        self._products_data.insert(insert_idx, new_entry)
        self._refresh_regions()

        # Aggiorna anche regions.js mantenendo l'ordine alfabetico
        rd = load_regions_js()
        if name not in rd:
            rd[name] = 0
            save_regions_js(rd)

        # Seleziona la nuova regione appena inserita
        self._reg_lb.selection_clear(0, tk.END)
        self._reg_lb.selection_set(insert_idx)
        self._reg_lb.see(insert_idx)
        self._on_region()
        self.status(f"✅ Nuova regione '{name}' inserita in ordine alfabetico. Ricorda di Salvare.")

    def _move_region(self, direction):
        sel = self._reg_lb.curselection()
        if not sel:
            messagebox.showwarning("Attenzione", "Seleziona prima una regione da spostare.")
            return
        idx = sel[0]
        target = idx + direction
        if 0 <= target < len(self._products_data):
            self._products_data[idx], self._products_data[target] = (
                self._products_data[target],
                self._products_data[idx]
            )
            self._refresh_regions()
            self._reg_lb.selection_clear(0, tk.END)
            self._reg_lb.selection_set(target)
            self._reg_lb.see(target)
            self._on_region()
            self.status(f"Regione spostata. Ricorda di cliccare su 'Salva Modifiche'.")

    def _sort_regions_alpha(self):
        if not self._products_data:
            return
        if not messagebox.askyesno(
            "Ordina Tutte A-Z",
            "Vuoi riordinare tutte le regioni in ordine alfabetico da A a Z?"
        ):
            return
        self._products_data.sort(key=lambda r: r["name"].strip().lower())
        self._refresh_regions()
        if self._products_data:
            self._reg_lb.selection_clear(0, tk.END)
            self._reg_lb.selection_set(0)
            self._reg_lb.see(0)
            self._on_region()
        self.status("Tutte le regioni sono ora in ordine alfabetico A-Z. Clicca su 'Salva Modifiche'.")

    def _del_region(self):
        sel = self._reg_lb.curselection()
        if not sel:
            messagebox.showwarning("Attenzione", "Seleziona prima la regione da eliminare.")
            return
        idx = sel[0]
        reg = self._products_data[idx]
        items_count = len(reg.get("items", []))

        msg = f"Sei sicuro di voler eliminare la regione '{reg['name']}'?"
        if items_count > 0:
            msg += f"\n\n⚠️ Attenzione: contiene {items_count} prodotti che verranno rimossi!"
        if not messagebox.askyesno("Conferma eliminazione", msg):
            return

        del self._products_data[idx]
        self._refresh_regions()

        # Aggiorna anche regions.js
        rd = load_regions_js()
        if reg.get("name") in rd:
            del rd[reg["name"]]
            save_regions_js(rd)

        if self._products_data:
            new_idx = min(idx, len(self._products_data) - 1)
            self._reg_lb.selection_set(new_idx)
            self._reg_lb.see(new_idx)
            self._on_region()
        else:
            self._refresh_tree([])
            self._prod_hdr.config(text="← Seleziona una regione dall'elenco")
        self.status(f"Regione '{reg['name']}' eliminata. Ricorda di Salvare.")

    def _add_product(self):
        _, reg = self._current_region()
        if reg is None:
            return
        data = self._product_dlg()
        if data:
            if "items" not in reg:
                reg["items"] = []
            reg["items"].append(data)
            self._refresh_tree(reg["items"])
            self.status(f"Prodotto '{data['name']}' aggiunto. Clicca su 'Salva Modifiche'.")

    def _edit_product(self):
        _, reg = self._current_region()
        if reg is None:
            return
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("Attenzione", "Seleziona un prodotto dalla tabella.")
            return
        idx = self._tree.index(sel[0])
        data = self._product_dlg(reg["items"][idx])
        if data:
            reg["items"][idx] = data
            self._refresh_tree(reg["items"])
            self.status("Prodotto modificato. Clicca su 'Salva Modifiche'.")

    def _del_product(self):
        _, reg = self._current_region()
        if reg is None:
            return
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("Attenzione", "Seleziona un prodotto da eliminare.")
            return
        if not messagebox.askyesno("Conferma", "Vuoi davvero eliminare questo prodotto?"):
            return
        idx = self._tree.index(sel[0])
        del reg["items"][idx]
        self._refresh_tree(reg["items"])
        self.status("Prodotto rimosso. Clicca su 'Salva Modifiche'.")

    def _move_prod(self, d):
        _, reg = self._current_region()
        if reg is None:
            return
        sel = self._tree.selection()
        if not sel:
            return
        idx  = self._tree.index(sel[0])
        ni   = idx + d
        items = reg.get("items", [])
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
        d.title("Modifica Prodotto" if existing else "Nuovo Prodotto")
        d.configure(bg=C["bg"])
        d.geometry("520x300")
        d.grab_set()
        d.columnconfigure(1, weight=1)

        fields = [("Nome *", "name"), ("Descrizione", "description"),
                  ("Quantità", "quantity"), ("Prezzo", "price")]
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
                messagebox.showwarning("Attenzione", "Il nome del prodotto è obbligatorio.", parent=d)
                return
            for k, v in vs.items():
                result[k] = v.get().strip()
            confirmed[0] = True
            d.destroy()

        br = tk.Frame(d, bg=C["bg"])
        br.grid(row=len(fields), column=0, columnspan=2, pady=16)
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
            self.status("✅ products.json salvato con successo!")
            messagebox.showinfo("Salvato", "Lista prodotti salvata correttamente!")
        except Exception as ex:
            messagebox.showerror("Errore salvataggio", str(ex))

    # ══════════════════════════════════════════════════════════════════════
    #  TAB 2 – IMMAGINI REGIONI (CON MINIATURE E ANTEPRIMA VISIVA)
    # ══════════════════════════════════════════════════════════════════════
    def _build_images_tab(self):
        p = self.ti

        # Barra superiore di selezione regione e import
        top = tk.Frame(p, bg=C["surface2"])
        top.pack(fill="x", padx=8, pady=8)
        lbl(top, "Seleziona Regione:", bg=C["surface2"], font=FONT_H).pack(side="left", padx=8)

        self._img_region = tk.StringVar()
        self._img_combo  = ttk.Combobox(
            top, textvariable=self._img_region,
            values=[r["name"] for r in self._products_data],
            state="readonly", font=FONT_B, width=22
        )
        self._img_combo.pack(side="left", padx=4)
        self._img_combo.bind("<<ComboboxSelected>>", self._img_load)

        btn(top, "📥 Importa Foto da Cartella", cmd=self._import_images, variant="primary").pack(side="left", padx=12)
        btn(top, "🔄 Ricarica Elenco", cmd=self._img_load, variant="neutral").pack(side="left", padx=4)

        # Contenitore diviso: Lista a sinistra, Pannello Anteprima a destra
        main_split = tk.Frame(p, bg=C["surface"])
        main_split.pack(fill="both", expand=True, padx=8, pady=4)

        # ── Pannello Sinistro: Lista immagini con miniature ─────────────
        list_pane = tk.Frame(main_split, bg=C["surface"])
        list_pane.pack(side="left", fill="both", expand=True)

        # Intestazione colonne
        ch = tk.Frame(list_pane, bg=C["surface2"])
        ch.pack(fill="x")
        
        tk.Label(ch, text="#", font=FONT_H, bg=C["surface2"], fg=C["accent"], width=3, anchor="center").pack(side="left", padx=4, pady=4)
        tk.Label(ch, text="Foto", font=FONT_H, bg=C["surface2"], fg=C["accent"], width=8, anchor="center").pack(side="left", padx=4, pady=4)
        tk.Label(ch, text="File", font=FONT_H, bg=C["surface2"], fg=C["accent"], width=12, anchor="w").pack(side="left", padx=4, pady=4)
        tk.Label(ch, text="500px", font=FONT_H, bg=C["surface2"], fg=C["accent"], width=8, anchor="center").pack(side="left", padx=4, pady=4)
        tk.Label(ch, text="Alta Ris.", font=FONT_H, bg=C["surface2"], fg=C["accent"], width=8, anchor="center").pack(side="left", padx=4, pady=4)
        tk.Label(ch, text="Azioni", font=FONT_H, bg=C["surface2"], fg=C["accent"], anchor="e").pack(side="right", padx=18, pady=4)

        # Lista scorrevole
        self._img_sf = VScrollFrame(list_pane, bg=C["surface"])
        self._img_sf.pack(fill="both", expand=True)

        # ── Pannello Destro: Anteprima Ingrandita ────────────────────────
        prev_pane = tk.Frame(main_split, bg=C["surface2"], width=300)
        prev_pane.pack(side="right", fill="y", padx=(8, 0))
        prev_pane.pack_propagate(False)

        lbl(prev_pane, "🖼 Anteprima Immagine", font=FONT_H, fg=C["accent"],
            bg=C["surface2"]).pack(pady=(12, 4), padx=10, anchor="w")
        
        lbl(prev_pane, "Clicca su una riga per ingrandire:", font=FONT_S,
            fg=C["sub"], bg=C["surface2"]).pack(padx=10, anchor="w")

        # Contenitore immagine ingrandita (240x240)
        img_box = tk.Frame(prev_pane, bg=C["bg"], width=240, height=240,
                           highlightbackground=C["border"], highlightthickness=1)
        img_box.pack(pady=10, padx=10)
        img_box.pack_propagate(False)

        self._prev_lbl_img = tk.Label(img_box, bg=C["bg"], text="Nessuna immagine\nselezionata",
                                      fg=C["sub"], font=FONT_S)
        self._prev_lbl_img.pack(fill="both", expand=True)

        self._prev_info = tk.Label(prev_pane, text="", font=FONT_S,
                                   bg=C["surface2"], fg=C["text"], justify="left")
        self._prev_info.pack(fill="x", padx=10, pady=4)

        btn(prev_pane, "🔍 Apri a Schermo Intero", cmd=self._open_current_fullscreen,
            variant="neutral", font=FONT_S).pack(fill="x", padx=10, pady=8)

        lbl(prev_pane, "💡 Suggerimento:\nFai doppio clic su una riga\nper aprire la foto direttamente.",
            font=FONT_S, fg=C["sub"], bg=C["surface2"], justify="left").pack(padx=10, pady=(10, 0), anchor="w")

        # Barra inferiore per salvare / applicare modifiche immagini
        bot = tk.Frame(p, bg=C["surface2"])
        bot.pack(fill="x", padx=8, pady=(4, 6))

        self._img_info = tk.Label(bot, text="Seleziona una regione in alto.", font=FONT_S,
                                  bg=C["surface2"], fg=C["sub"])
        self._img_info.pack(side="left", padx=10)

        btn(bot, "💾 Applica e Rinumera Immagini",
            cmd=self._apply_image_changes, variant="success").pack(side="right", padx=8, pady=4)

    def _open_current_fullscreen(self):
        if self._current_preview_file and Path(self._current_preview_file).exists():
            try:
                os.startfile(str(self._current_preview_file))
            except Exception as ex:
                messagebox.showerror("Errore", f"Impossibile aprire il file:\n{ex}")
        else:
            messagebox.showinfo("Info", "Seleziona prima un'immagine valida.")

    def _get_thumbnail(self, img_path, size=(54, 54)):
        """Carica e ridimensiona l'immagine per la miniatura nella lista."""
        key = f"{img_path}_{size}"
        if key in self._thumb_cache:
            return self._thumb_cache[key]
        if not img_path.exists():
            return None
        try:
            with Image.open(img_path) as im:
                im = im.convert("RGB")
                im.thumbnail(size, Image.LANCZOS)
                photo = ImageTk.PhotoImage(im)
                self._thumb_cache[key] = photo
                return photo
        except Exception:
            return None

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
        
        # Reset anteprima
        self._prev_lbl_img.config(image="", text="Seleziona una foto")
        self._prev_info.config(text="")
        self._current_preview_file = None

        count = len(self._img_order)
        self._img_info.config(
            text=f"Regione: {region}  |  Totale immagini: {count}"
        )

        if not self._img_order:
            empty_lbl = tk.Label(inner, text="Nessuna immagine presente in questa regione.\nUsa il pulsante 'Importa Foto' per caricarne di nuove.",
                                 bg=C["surface"], fg=C["sub"], font=FONT_B, pady=30)
            empty_lbl.pack(fill="x")
            return

        for pos, num in enumerate(self._img_order):
            self._img_row(inner, pos, num, region)

        # Mostra la prima immagine nell'anteprima grande di default
        if self._img_order:
            self._show_preview(region, self._img_order[0])

    def _img_row(self, parent, pos, num, region):
        folder = IMAGES_DIR / region
        thumb_file, full_file = get_image_files_for_num(folder, num)
        ok_t = thumb_file.exists()
        ok_f = full_file.exists()

        row = tk.Frame(parent, bg=C["surface"],
                       highlightbackground=C["border"], highlightthickness=1)
        row.pack(fill="x", padx=2, pady=1)

        # Numero progressivo
        tk.Label(row, text=f"{pos+1}", width=3,
                 bg=C["surface"], fg=C["sub"], font=FONT_S, anchor="center").pack(side="left", padx=4)

        # Miniatura visiva 54x54 px
        thumb_img = self._get_thumbnail(thumb_file if ok_t else full_file)
        if thumb_img:
            lbl_img = tk.Label(row, image=thumb_img, bg=C["surface"], width=56, height=56, cursor="hand2")
            lbl_img.image = thumb_img # Mantieni riferimento
            lbl_img.pack(side="left", padx=4, pady=2)
            lbl_img.bind("<Button-1>", lambda e, n=num: self._show_preview(region, n))
            lbl_img.bind("<Double-Button-1>", lambda e, f=full_file: os.startfile(str(f)) if f.exists() else None)
        else:
            lbl_none = tk.Label(row, text="🖼\nNo Foto", bg=C["surface2"], fg=C["sub"],
                                font=FONT_S, width=7, height=3)
            lbl_none.pack(side="left", padx=4, pady=2)

        # Nome file
        display_name = thumb_file.name if ok_t else f"{num}.jpeg"
        lbl_name = tk.Label(row, text=display_name, width=12,
                            bg=C["surface"], fg=C["text"], font=FONT_B, anchor="w", cursor="hand2")
        lbl_name.pack(side="left", padx=4)

        # Stato 500px e Alta Risoluzione
        tk.Label(row, text="✅ 500px" if ok_t else "❌ Mancante", width=9,
                 bg=C["surface"], fg=C["green"] if ok_t else C["red"],
                 font=FONT_S, anchor="center").pack(side="left", padx=2)

        tk.Label(row, text="✅ 2x" if ok_f else "❌ Mancante", width=8,
                 bg=C["surface"], fg=C["green"] if ok_f else C["red"],
                 font=FONT_S, anchor="center").pack(side="left", padx=2)

        # Cliccando sulla riga si aggiorna l'anteprima
        def on_click(e, n=num):
            self._show_preview(region, n)

        def on_dbl_click(e, f=full_file):
            if f.exists():
                try:
                    os.startfile(str(f))
                except Exception:
                    pass

        row.bind("<Button-1>", on_click)
        lbl_name.bind("<Button-1>", on_click)
        row.bind("<Double-Button-1>", on_dbl_click)
        lbl_name.bind("<Double-Button-1>", on_dbl_click)

        # Pulsanti Sposta Su / Giù ed Elimina
        act = tk.Frame(row, bg=C["surface"])
        act.pack(side="right", padx=6)

        for text, cmd in [("▲ Su", lambda n=num: self._img_up(n)),
                          ("▼ Giù", lambda n=num: self._img_dn(n)),
                          ("🗑", lambda n=num: self._img_del(n))]:
            is_del = (text == "🗑")
            bg_col = C["red"] if is_del else C["surface2"]
            fg_col = C["white"] if is_del else C["text"]
            b = tk.Button(act, text=text, command=cmd, bg=bg_col, fg=fg_col,
                          relief="flat", cursor="hand2", font=FONT_S,
                          padx=6, pady=2)
            b.pack(side="left", padx=2)

    def _show_preview(self, region, num):
        folder = IMAGES_DIR / region
        thumb_file, full_file = get_image_files_for_num(folder, num)
        target = full_file if full_file.exists() else thumb_file

        if not target.exists():
            self._prev_lbl_img.config(image="", text="File non trovato")
            self._prev_info.config(text="")
            self._current_preview_file = None
            return

        try:
            with Image.open(target) as im:
                w, h = im.size
                im_copy = im.copy()
                im_copy.thumbnail((240, 240), Image.LANCZOS)
                self._large_preview_photo = ImageTk.PhotoImage(im_copy)
                self._prev_lbl_img.config(image=self._large_preview_photo, text="")
                
                size_kb = target.stat().st_size // 1024
                info_text = (
                    f"📁 File: {target.name}\n"
                    f"📐 Dimensioni: {w} × {h} px\n"
                    f"💾 Peso file: {size_kb} KB\n"
                    f"🔎 Risoluzione: {'Alta (2x)' if target == full_file else 'Bassa (500px)'}"
                )
                self._prev_info.config(text=info_text)
                self._current_preview_file = target
        except Exception as ex:
            self._prev_lbl_img.config(image="", text=f"Errore anteprima:\n{ex}")
            self._current_preview_file = None

    def _img_up(self, num):
        try:
            i = self._img_order.index(num)
        except ValueError:
            return
        if i > 0:
            self._img_order[i], self._img_order[i-1] = self._img_order[i-1], self._img_order[i]
            self._img_refresh()
            self._show_preview(self._img_region.get(), num)

    def _img_dn(self, num):
        try:
            i = self._img_order.index(num)
        except ValueError:
            return
        if i < len(self._img_order) - 1:
            self._img_order[i], self._img_order[i+1] = self._img_order[i+1], self._img_order[i]
            self._img_refresh()
            self._show_preview(self._img_region.get(), num)

    def _img_del(self, num):
        if not messagebox.askyesno("Conferma eliminazione",
                f"Eliminare l'immagine n.{num} dal disco?\n\nQuesta operazione non può essere annullata."):
            return
        region = self._img_region.get()
        folder = IMAGES_DIR / region
        for ext in (".jpg", ".jpeg"):
            for sfx in ("", "@2x"):
                p = folder / f"{num}{sfx}{ext}"
                try:
                    p.unlink(missing_ok=True)
                except Exception:
                    pass
        self._img_order.remove(num)
        self._img_refresh(region)
        self.status(f"Immagine {num} eliminata. Clicca su 'Applica e Rinumera' per riordinare la sequenza.")

    def _apply_image_changes(self):
        region = self._img_region.get()
        if not region:
            messagebox.showwarning("Attenzione", "Seleziona prima una regione in alto.")
            return
        folder = IMAGES_DIR / region
        if not folder.exists():
            messagebox.showerror("Errore", f"Cartella non trovata:\n{folder}")
            return

        order = self._img_order
        if not order:
            messagebox.showinfo("Info", "Nessuna immagine presente da riordinare.")
            return

        # 1. Sposta tutti i file correnti in nomi temporanei (.jpeg)
        for i, num in enumerate(order):
            for sfx in ("", "@2x"):
                src = None
                for ext in (".jpeg", ".jpg"):
                    cand = folder / f"{num}{sfx}{ext}"
                    if cand.exists():
                        src = cand
                        break
                if src:
                    dst = folder / f"__tmp_{i}{sfx}.jpeg"
                    shutil.copy2(src, dst)

        # 2. Rimuovi i file numerati originali (.jpeg e .jpg)
        for f in folder.iterdir():
            if f.suffix.lower() in (".jpeg", ".jpg") and not f.name.startswith("__tmp_"):
                try:
                    f.unlink()
                except Exception:
                    pass

        # 3. Rinomina sequenzialmente in 1.jpeg, 2.jpeg...
        for i in range(len(order)):
            for sfx in ("", "@2x"):
                src = folder / f"__tmp_{i}{sfx}.jpeg"
                dst = folder / f"{i+1}{sfx}.jpeg"
                if src.exists():
                    shutil.move(str(src), str(dst))

        # 4. Aggiorna conteggio in js/regions.js
        rd = load_regions_js()
        rd[region] = len(order)
        save_regions_js(rd)

        # Pulisci cache e ricarica
        self._thumb_cache.clear()
        self._img_order = list(range(1, len(order) + 1))
        self._img_refresh(region)
        self.status(f"✅ {region}: {len(order)} immagini rinumerate e regions.js aggiornato.")
        messagebox.showinfo("Operazione completata",
            f"Tutte le immagini di '{region}' sono state riordinate e rinumerate da 1 a {len(order)} in formato .jpeg!\n\n"
            f"Il file 'js/regions.js' è stato aggiornato correttamente.")

    def _import_images(self):
        region = self._img_region.get()
        if not region:
            messagebox.showwarning("Attenzione", "Seleziona prima una regione in alto.")
            return

        import_root   = Path(self.cfg.get("import_folder", Path.home() / "Pictures" / "import"))
        import_folder = import_root / region
        EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".heic", ".heif"}

        if import_folder.exists():
            src_files = [f for f in import_folder.iterdir() if f.suffix.lower() in EXTS]
        else:
            ans = messagebox.askyesno(
                "Cartella Import Automatica Non Trovata",
                f"La cartella automatica non esiste ancora:\n{import_folder}\n\n"
                "Vuoi scegliere manualmente le foto dal computer?"
            )
            if not ans:
                return
            raw = filedialog.askopenfilenames(
                title=f"Seleziona immagini per {region}",
                filetypes=[("Immagini", "*.jpg *.jpeg *.png *.webp *.bmp")]
            )
            if not raw:
                return
            src_files = [Path(f) for f in raw]

        if not src_files:
            messagebox.showinfo("Nessuna foto trovata", f"Nessun file immagine trovato in:\n{import_folder}")
            return

        if not messagebox.askyesno("Conferma Importazione",
                f"Trovate {len(src_files)} nuove immagini per '{region}'.\n\n"
                "Il programma creerà automaticamente:\n"
                "• La copia a risoluzione 500×500 px (.jpeg)\n"
                "• La copia ad alta risoluzione 2x (.jpeg)\n\n"
                "Vuoi procedere?"):
            return

        dst_folder = IMAGES_DIR / region
        dst_folder.mkdir(parents=True, exist_ok=True)
        next_n = max_image_num(region) + 1

        # Finestra di avanzamento facile
        pw = tk.Toplevel(self)
        pw.title("Importazione immagini in corso...")
        pw.configure(bg=C["bg"])
        pw.geometry("440x140")
        pw.grab_set()

        pl = lbl(pw, "Elaborazione immagini in corso...", bg=C["bg"])
        pl.pack(pady=12)
        pb = ttk.Progressbar(pw, length=380, maximum=len(src_files))
        pb.pack(padx=20)
        pc = lbl(pw, "", bg=C["bg"], fg=C["sub"], font=FONT_S)
        pc.pack(pady=4)

        errors = []
        imported_files = []

        def do():
            nonlocal next_n
            for i, src in enumerate(src_files):
                try:
                    dt = dst_folder / f"{next_n}.jpeg"
                    df = dst_folder / f"{next_n}@2x.jpeg"
                    pl.config(text=f"Elaboro ({i+1}/{len(src_files)}): {src.name}")
                    pc.config(text=f"Salvataggio in: {next_n}.jpeg")
                    pb["value"] = i + 1
                    pw.update_idletasks()
                    resize_and_copy(src, dt, df)
                    imported_files.append(src)
                    next_n += 1
                except Exception as ex:
                    errors.append(f"{src.name}: {ex}")

            # Aggiorna regions.js (automaticamente ordinato A-Z)
            rd = load_regions_js()
            rd[region] = next_n - 1
            save_regions_js(rd)
            pw.destroy()

            # Pulisci cache e ricarica
            self._thumb_cache.clear()
            msg = f"✅ Importate con successo {len(imported_files)} immagini per '{region}' in formato .jpeg."
            if errors:
                msg += f"\n\n⚠️ Errori riscontrati:\n" + "\n".join(errors[:5])
            messagebox.showinfo("Importazione completata", msg)
            self._img_load()
            self.status(f"✅ Importazione '{region}' completata. Totale foto: {next_n-1}")

            # Chiedi all'utente se vuole eliminare i file originali per evitare ricopie
            if imported_files:
                ask_del = messagebox.askyesno(
                    "Eliminazione File Originali",
                    f"Tutte le {len(imported_files)} immagini sono state copiate e salvate correttamente.\n\n"
                    "Vuoi eliminare i file originali dalla cartella di importazione?\n\n"
                    "💡 Consigliato: premi 'Sì' per svuotare la cartella ed evitare di ricopiare le stesse foto in futuro."
                )
                if ask_del:
                    del_count = 0
                    del_errs = []
                    for f in imported_files:
                        try:
                            f.unlink(missing_ok=True)
                            del_count += 1
                        except Exception as ex:
                            del_errs.append(f"{f.name}: {ex}")

                    if del_errs:
                        messagebox.showwarning(
                            "Attenzione",
                            f"Eliminati {del_count} file originali.\n"
                            f"Alcuni file non sono stati eliminati:\n" + "\n".join(del_errs[:5])
                        )
                    else:
                        self.status(f"✅ Importate {len(imported_files)} foto ed eliminati i file originali dalla cartella.")

        threading.Thread(target=do, daemon=True).start()

    # ══════════════════════════════════════════════════════════════════════
    #  TAB 3 – ANTEPRIMA SITO WEB (SERVER LOCALE INTEGRATO)
    # ══════════════════════════════════════════════════════════════════════
    def _build_preview_tab(self):
        p = self.tw

        tk.Label(p, text="🌐  Anteprima del Sito Web in Locale",
                 font=FONT_T, bg=C["surface"], fg=C["accent"]).pack(pady=(16, 4))
        
        tk.Label(p,
                 text="Visualizza il sito web sul tuo computer esattamente come lo vedranno i clienti,\n"
                      "verificando foto e modifiche PRIMA di pubblicarlo su internet.",
                 font=FONT_B, bg=C["surface"], fg=C["text"], justify="center").pack(pady=(0, 16))

        # Scheda stato del server
        self._srv_card = tk.LabelFrame(p, text=" Stato Server Locale ",
                                       font=FONT_H, bg=C["surface2"],
                                       fg=C["accent"], relief="flat", bd=2)
        self._srv_card.pack(fill="x", padx=60, pady=6)

        card_inner = tk.Frame(self._srv_card, bg=C["surface2"], pady=12, padx=16)
        card_inner.pack(fill="x")

        self._srv_badge = tk.Label(card_inner, text="⚪ SERVER INATTIVO", font=FONT_BT,
                                   bg=C["border"], fg=C["text"], padx=14, pady=6)
        self._srv_badge.pack(side="left")

        self._srv_url_lbl = tk.Label(card_inner, text="Il server locale non è ancora avviato.",
                                     font=FONT_B, bg=C["surface2"], fg=C["sub"])
        self._srv_url_lbl.pack(side="left", padx=16)

        # Pulsanti principali di controllo
        ctrl_frame = tk.Frame(p, bg=C["surface"])
        ctrl_frame.pack(fill="x", padx=60, pady=16)

        # Grande pulsante verde per avviare ed aprire il sito
        self._btn_launch = tk.Button(ctrl_frame, text="▶  AVVIA SERVER & APRI SITO NEL BROWSER",
                                     command=lambda: self._start_server_and_open("index.html"),
                                     bg=C["green"], fg=C["white"],
                                     activebackground=C["accent"], activeforeground=C["white"],
                                     font=FONT_BIG_BTN, relief="flat", padx=20, pady=12, cursor="hand2")
        self._btn_launch.pack(fill="x", pady=4)

        # Riga pulsanti rapidi per aprire pagine specifiche
        links_frame = tk.Frame(p, bg=C["surface"])
        links_frame.pack(fill="x", padx=60, pady=6)

        lbl(links_frame, "Collegamenti rapidi:", font=FONT_H, fg=C["accent"]).pack(side="left", padx=(0, 10))

        btn(links_frame, "🏠 Home Page (index.html)",
            cmd=lambda: self._open_page("index.html"), variant="neutral").pack(side="left", padx=4)

        btn(links_frame, "🍷 Pagina Prodotti (products.html)",
            cmd=lambda: self._open_page("products.html"), variant="neutral").pack(side="left", padx=4)

        btn(links_frame, "⏹ Ferma Server",
            cmd=self._stop_server_action, variant="danger").pack(side="right", padx=4)

        # Riquadro di guida passo-passo
        guide_box = tk.LabelFrame(p, text=" 💡 Come Funziona ",
                                  font=FONT_H, bg=C["surface"],
                                  fg=C["accent"], relief="flat", bd=1)
        guide_box.pack(fill="both", expand=True, padx=60, pady=16)

        guide_text = (
            "1. Clicca sul pulsante verde 'AVVIA SERVER & APRI SITO NEL BROWSER'.\n\n"
            "2. Si aprirà automaticamente il tuo navigatore internet abituale (Chrome, Edge, Firefox, ecc.).\n\n"
            "3. Il sito caricherà tutti i prodotti di 'products.json' e le foto aggiornate in tempo reale.\n\n"
            "4. Se fai nuove modifiche alle immagini o ai prodotti, basta premere F5 nel browser per ricaricare la pagina!\n\n"
            "5. Quando sei soddisfatto del risultato, vai nella scheda '4. Pubblica su GitHub' per metterlo online."
        )
        tk.Label(guide_box, text=guide_text, font=FONT_B,
                 bg=C["surface"], fg=C["text"], justify="left", padx=16, pady=14).pack(anchor="w")

    def _update_server_status_ui(self):
        if self.server_mgr.is_running:
            self._srv_badge.config(text="🟢 SERVER ATTIVO", bg=C["green_bg"], fg="#7ee658")
            self._srv_url_lbl.config(
                text=f"In esecuzione su: http://localhost:{self.server_mgr.port}  (Porta locale attiva)",
                fg=C["text"]
            )
            self._btn_launch.config(
                text="🌐  RIAPRI SITO NEL BROWSER (http://localhost:" + str(self.server_mgr.port) + ")",
                bg=C["accent2"]
            )
        else:
            self._srv_badge.config(text="⚪ SERVER INATTIVO", bg=C["border"], fg=C["sub"])
            self._srv_url_lbl.config(text="Il server locale non è attualmente in funzione.", fg=C["sub"])
            self._btn_launch.config(
                text="▶  AVVIA SERVER & APRI SITO NEL BROWSER",
                bg=C["green"]
            )

    def _start_server_and_open(self, page="index.html"):
        try:
            port = self.server_mgr.start(self.cfg.get("server_port", 8000))
            self._update_server_status_ui()
            self.status(f"✅ Server web attivo all'indirizzo: http://localhost:{port}")
            url = f"http://localhost:{port}/{page}"
            webbrowser.open(url)
        except Exception as ex:
            messagebox.showerror("Errore Avvio Server", f"Impossibile avviare il server locale:\n{ex}")

    def _open_page(self, page="index.html"):
        if not self.server_mgr.is_running:
            # Avvia automaticamente
            self._start_server_and_open(page)
        else:
            url = f"http://localhost:{self.server_mgr.port}/{page}"
            webbrowser.open(url)
            self.status(f"Aperto {page} nel browser.")

    def _stop_server_action(self):
        if self.server_mgr.is_running:
            self.server_mgr.stop()
            self._update_server_status_ui()
            self.status("Server web locale fermato.")
            messagebox.showinfo("Server fermato", "Il server locale è stato arrestato con successo.")
        else:
            messagebox.showinfo("Info", "Il server locale è già inattivo.")

    # ══════════════════════════════════════════════════════════════════════
    #  TAB 4 – PUBBLICA SU GITHUB
    # ══════════════════════════════════════════════════════════════════════
    def _build_github_tab(self):
        p = self.tg

        tk.Label(p, text="🚀  Pubblica Modifiche su GitHub",
                 font=FONT_T, bg=C["surface"], fg=C["accent"]).pack(pady=14)
        tk.Label(p,
            text="Invia tutte le modifiche al sito su GitHub Pages.\n"
                 "Le novità saranno visibili online sul sito pubblico entro pochi minuti.",
            font=FONT_B, bg=C["surface"], fg=C["text"], justify="center").pack(pady=2)

        sf = tk.LabelFrame(p, text=" Stato Repository ",
                           font=FONT_H, bg=C["surface"],
                           fg=C["accent"], relief="flat", bd=2)
        sf.pack(fill="x", padx=40, pady=10)
        self._git_st = tk.Text(sf, height=8,
                               bg=C["surface2"], fg=C["text"],
                               font=("Consolas", 10), relief="flat",
                               state="disabled", wrap="word")
        self._git_st.pack(fill="both", padx=8, pady=8)

        mf = tk.Frame(p, bg=C["surface"])
        mf.pack(fill="x", padx=40, pady=2)
        lbl(mf, "Descrizione modifiche:").pack(side="left", padx=4)
        self._commit_var = tk.StringVar(value=self.cfg.get("git_commit_msg", "Aggiornamento sito Terra Mia"))
        entry(mf, self._commit_var, width=50).pack(side="left", padx=8, fill="x", expand=True)

        br = tk.Frame(p, bg=C["surface"])
        br.pack(pady=12)
        btn(br, "🔍 Ricontrolla Modifiche", cmd=self._git_status, variant="neutral").pack(side="left", padx=8)
        btn(br, "🚀 Pubblica su GitHub", cmd=self._git_push, variant="primary").pack(side="left", padx=8)

        self._git_log = tk.Text(p, height=6,
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
            return -1, "", "Git non trovato nel sistema. Assicurati che Git sia installato."

    def _git_status(self):
        self._git_st.config(state="normal")
        self._git_st.delete("1.0", tk.END)
        code, out, err = self._git_run(["status", "--short"])
        if code == -1:
            self._git_st.insert(tk.END, f"❌ {err}")
        elif not out:
            self._git_st.insert(tk.END, "✅ Nessuna modifica in sospeso. Il sito è aggiornato con l'ultima versione.")
        else:
            self._git_st.insert(tk.END, "📝 File modificati pronti per la pubblicazione:\n\n" + out)
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
            messagebox.showwarning("Attenzione", "Inserisci una breve descrizione delle modifiche apportate.")
            return
        code, out, _ = self._git_run(["status", "--short"])
        if code == -1:
            messagebox.showerror("Errore", "Git non trovato nel sistema.")
            return
        if not out:
            messagebox.showinfo("Info", "Nessuna nuova modifica trovata da pubblicare.")
            return
        if not messagebox.askyesno("Pubblicazione Sito",
                f'Vuoi pubblicare le modifiche su GitHub?\n\nMessaggio: "{msg}"'):
            return

        self._git_log.config(state="normal")
        self._git_log.delete("1.0", tk.END)
        self._git_log.config(state="disabled")

        def do():
            self._git_write("▶ Aggiunta file modificati (git add -A)...", C["sub"])
            c, o, e = self._git_run(["add", "-A"])
            if c != 0:
                self._git_write(f"❌ {e}", C["red"]); return

            self._git_write(f'▶ Creazione salvataggio (git commit -m "{msg}")...', C["sub"])
            c, o, e = self._git_run(["commit", "-m", msg])
            if c != 0:
                self._git_write(f"❌ {e}", C["red"]); return
            self._git_write(o, C["green"])

            self._git_write("▶ Invio modifiche online su GitHub (git push)...", C["sub"])
            c, o, e = self._git_run(["push"])
            if c != 0:
                self._git_write(f"❌ {e or o}", C["red"])
                self._git_write("💡 Assicurati che il computer sia connesso a internet e che le credenziali GitHub siano valide.", C["accent"])
            else:
                self._git_write("✅ Pubblicato con successo su GitHub!", C["green"])
                self._git_write("🌐 Le modifiche saranno visibili sul sito pubblico entro pochi minuti.", C["accent"])
                self.status("✅ Sito pubblicato su GitHub!")
                self._git_status()

        threading.Thread(target=do, daemon=True).start()


# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()
