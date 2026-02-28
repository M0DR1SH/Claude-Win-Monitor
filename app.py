import customtkinter as ctk
import tkinter as tk
from PIL import Image
from curl_cffi import requests
import threading
import time
import json
import os
import sys
import webbrowser
import dateutil.parser
from http.server import HTTPServer, BaseHTTPRequestHandler

try:
    import pystray
    _HAVE_TRAY = True
except ImportError:
    _HAVE_TRAY = False

# --- CONSTANTES ---
BASE_URL = "https://claude.ai/api"
REFRESH_RATE_SECONDS = 300
CONFIG_FILE = "claude_monitor_config.json"
APP_NAME = "Claude Usage Monitor"
APP_AUTHOR = "🅻🅶 @ IA Mastery"
APP_VERSION = "v1.7.2"
APP_DATE = "27/02/2026"

# Palette de couleurs
COLOR_BG = "#141414"
COLOR_CARD = "#1c1c1c"
COLOR_CARD_WARN = "#1e1a12"
COLOR_CARD_CRIT = "#1e1212"
COLOR_SAFE = "#22c55e"
COLOR_SAFE_BG = "#0b2115"
COLOR_WARN = "#f59e0b"
COLOR_WARN_BG = "#1f1508"
COLOR_CRIT = "#ef4444"
COLOR_CRIT_BG = "#1f0808"
COLOR_BLUE = "#3b82f6"
COLOR_TITLEBAR = "#0e0e0e"

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")


def _apply_rounded_corners_to(window):
    """Coins arrondis Windows 11 via DWM pour n'importe quelle fenêtre."""
    try:
        import ctypes
        hwnd = window.winfo_id()
        DWMWCP_ROUND = 2
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 33,
            ctypes.byref(ctypes.c_int(DWMWCP_ROUND)),
            ctypes.sizeof(ctypes.c_int(DWMWCP_ROUND))
        )
    except Exception:
        pass


class Tooltip:
    """Infobulle légère au survol d'un widget (apparition différée)."""
    DELAY = 420

    def __init__(self, widget, text):
        self._w = widget
        self._text = text
        self._tip = None
        self._aid = None
        widget.bind("<Enter>", self._schedule)
        widget.bind("<Leave>", self._cancel)
        widget.bind("<ButtonPress>", self._cancel)

    def _schedule(self, _=None):
        self._cancel()
        self._aid = self._w.after(self.DELAY, self._show)

    def _cancel(self, _=None):
        if self._aid:
            self._w.after_cancel(self._aid)
            self._aid = None
        if self._tip:
            self._tip.destroy()
            self._tip = None

    def _show(self):
        self._tip = tk.Toplevel()
        self._tip.overrideredirect(True)
        self._tip.configure(bg="#1e1e1e")
        frame = tk.Frame(self._tip, bg="#1e1e1e",
                         highlightbackground="#484848", highlightthickness=1)
        frame.pack()
        tk.Label(frame, text=self._text, bg="#1e1e1e", fg="#ddd",
                 font=("Segoe UI", 10), padx=10, pady=5).pack()

        self._tip.update_idletasks()
        tw = self._tip.winfo_reqwidth()
        th = self._tip.winfo_reqheight()
        wx = self._w.winfo_rootx()
        wy = self._w.winfo_rooty()
        ww = self._w.winfo_width()
        wh = self._w.winfo_height()
        sh = self._w.winfo_screenheight()
        x = max(4, wx + (ww - tw) // 2)
        y = wy - th - 6 if wy + wh + th + 6 > sh - 50 else wy + wh + 6
        self._tip.geometry(f"+{x}+{y}")


# --- UTILITAIRES ---
def format_date_french(iso_date_str):
    if not iso_date_str:
        return "Date inconnue"
    try:
        dt = dateutil.parser.isoparse(iso_date_str).astimezone()
        days = ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"]
        months = ["", "janv", "fév", "mars", "avr", "mai", "juin",
                  "juil", "août", "sept", "oct", "nov", "déc"]
        return f"{days[dt.weekday()]} {dt.day} {months[dt.month]} à {dt.hour}h{dt.minute:02d}"
    except Exception:
        return "Erreur date"


class ConfigManager:
    @staticmethod
    def load():
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    @staticmethod
    def save(session_key, org_id=None):
        data = {"session_key": session_key}
        if org_id:
            data["org_id"] = org_id
        with open(CONFIG_FILE, 'w') as f:
            json.dump(data, f)


# --- ICÔNE DE STATUT (CERCLE + SYMBOLE) ---
class StatusIcon(tk.Canvas):
    """Cercle coloré affichant ✓ (normal/warn) ou ! (critique)."""

    def __init__(self, master, size=20, bg_color=COLOR_CARD, **kwargs):
        super().__init__(master, width=size, height=size,
                         bg=bg_color, highlightthickness=0, **kwargs)
        self.size = size
        self.draw(0.0, COLOR_SAFE)

    def draw(self, ratio, color):
        self.delete("all")
        s = self.size
        self.create_oval(1, 1, s - 1, s - 1, fill=color, outline="")
        lw = max(2, s // 11)
        if ratio < 0.85:
            pts = [s * 0.24, s * 0.52, s * 0.44, s * 0.72, s * 0.76, s * 0.28]
            self.create_line(*pts, fill="white", width=lw,
                             capstyle="round", joinstyle="round")
        else:
            cx = s / 2
            self.create_line(cx, s * 0.22, cx, s * 0.60,
                             fill="white", width=lw, capstyle="round")
            r = max(1.5, s // 12)
            cy = s * 0.76
            self.create_oval(cx - r, cy - r, cx + r, cy + r,
                             fill="white", outline="")


# --- FENÊTRES MODALES (base commune) ---
class _BaseDialog(ctk.CTkToplevel):
    """Fenêtre modale stylée : overrideredirect, titlebar custom, draggable."""

    def __init__(self, parent, title_text, width, height):
        super().__init__(parent)
        self.overrideredirect(True)
        # La couleur de fond de la fenêtre = couleur de bordure (1px gap autour du main)
        self.configure(fg_color="#484848")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self._dx = self._dy = 0
        self._parent = parent
        self.geometry(f"{width}x{height}")
        self.after(10, lambda: self._center_on(parent))
        self.after(200, lambda: _apply_rounded_corners_to(self))

        # Overlay sombre sur la fenêtre principale (noircissement, sans transparence)
        self._overlay = self._make_overlay(parent)

        # Rester toujours au-dessus de l'overlay et de la fenêtre principale
        self.wm_attributes("-topmost", True)
        self.after(1, self.lift)

        # Fond principal : 1px de gap sur tous les côtés → bordure visible partout
        main = ctk.CTkFrame(self, fg_color="#181818", corner_radius=0)
        main.pack(fill="both", expand=True, padx=1, pady=1)

        # Titlebar (même fond que main pour cohérence, légèrement plus sombre)
        tb = ctk.CTkFrame(main, fg_color="#0e0e0e", corner_radius=0, height=40)
        tb.pack(fill="x")
        tb.pack_propagate(False)
        for w in (tb,):
            w.bind("<ButtonPress-1>", self._drag_start)
            w.bind("<B1-Motion>", self._drag_do)

        ctk.CTkLabel(
            tb, text=title_text,
            font=("Segoe UI", 12, "bold"), text_color="#bbb"
        ).pack(side="left", padx=14)

        ctk.CTkButton(
            tb, text="✕", width=32, height=32,
            fg_color="transparent", hover_color="#4a1010",
            text_color=COLOR_CRIT, corner_radius=6,
            command=self.destroy, font=("Segoe UI", 13, "bold")
        ).pack(side="right", padx=4, pady=4)

        # Séparateur titlebar / contenu
        ctk.CTkFrame(main, height=1, fg_color="#2a2a2a",
                     corner_radius=0).pack(fill="x")

        # Zone contenu accessible aux sous-classes
        self.content = ctk.CTkFrame(main, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=22, pady=18)

    def _center_on(self, parent):
        self.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_x(), parent.winfo_y()
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{max(0, px + (pw - w) // 2)}+{max(0, py + (ph - h) // 2)}")

    def _drag_start(self, e):
        self._dx = e.x_root - self.winfo_x()
        self._dy = e.y_root - self.winfo_y()

    def _drag_do(self, e):
        self.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")

    def _make_overlay(self, parent):
        """Overlay sombre positionné exactement sur la fenêtre principale."""
        parent.update_idletasks()
        ov = tk.Toplevel(parent)
        ov.overrideredirect(True)
        ov.configure(bg="#000000")
        ov.wm_attributes("-alpha", 0.62)
        ov.geometry(
            f"{parent.winfo_width()}x{parent.winfo_height()}"
            f"+{parent.winfo_x()}+{parent.winfo_y()}"
        )
        return ov

    def destroy(self):
        try:
            self._overlay.destroy()
        except Exception:
            pass
        super().destroy()


class SettingsDialog(_BaseDialog):
    def __init__(self, parent, current_key):
        super().__init__(parent, "⚙   Paramètres", 460, 370)
        self._parent_app = parent

        ctk.CTkLabel(
            self.content, text="Clé de Session",
            font=("Segoe UI", 14, "bold"), anchor="w"
        ).pack(anchor="w", pady=(0, 10))

        # ── Méthode automatique ──────────────────────────────────
        m1 = ctk.CTkFrame(self.content, fg_color="#0d1f10", corner_radius=8)
        m1.pack(fill="x", pady=(0, 8))
        inner1 = ctk.CTkFrame(m1, fg_color="transparent")
        inner1.pack(fill="x", padx=12, pady=10)

        ctk.CTkLabel(
            inner1, text="①  Méthode automatique  (recommandée)",
            font=("Segoe UI", 11, "bold"), text_color=COLOR_SAFE, anchor="w"
        ).pack(anchor="w")
        ctk.CTkLabel(
            inner1,
            text="Activez l'extension  \"Claude Session Helper\"  dans votre navigateur.",
            font=("Segoe UI", 11), text_color="#7aad7a", anchor="w", wraplength=380
        ).pack(anchor="w", pady=(3, 4))
        ctk.CTkButton(
            inner1, text="↗  Ouvrir le guide d'installation",
            command=self._open_guide,
            fg_color="transparent", hover_color="#0b2115",
            text_color=COLOR_SAFE, font=("Segoe UI", 11),
            anchor="w", height=22, corner_radius=4
        ).pack(anchor="w")

        # ── Séparateur ───────────────────────────────────────────
        ctk.CTkFrame(self.content, height=1, fg_color="#2a2a2a",
                     corner_radius=0).pack(fill="x", pady=(0, 8))

        # ── Méthode manuelle ─────────────────────────────────────
        m2 = ctk.CTkFrame(self.content, fg_color="#0d1a2a", corner_radius=8)
        m2.pack(fill="x", pady=(0, 10))
        inner2 = ctk.CTkFrame(m2, fg_color="transparent")
        inner2.pack(fill="x", padx=12, pady=10)

        ctk.CTkLabel(
            inner2, text="②  Méthode manuelle",
            font=("Segoe UI", 11, "bold"), text_color=COLOR_BLUE, anchor="w"
        ).pack(anchor="w")
        ctk.CTkLabel(
            inner2,
            text="F12  ›  Application  ›  Cookies  ›  https://claude.ai  ›  sessionKey",
            font=("Segoe UI", 10), text_color="#5588aa", anchor="w"
        ).pack(anchor="w", pady=(3, 4))
        ctk.CTkButton(
            inner2, text="↗  Ouvrir claude.ai",
            command=lambda: webbrowser.open("https://claude.ai"),
            fg_color="transparent", hover_color="#0d1f3c",
            text_color=COLOR_BLUE, font=("Segoe UI", 11),
            anchor="w", height=22, corner_radius=4
        ).pack(anchor="w")

        self.key_entry = ctk.CTkEntry(
            self.content, height=36,
            placeholder_text="sk-ant-sid01-...",
            font=("Segoe UI", 11)
        )
        self.key_entry.insert(0, current_key)
        self.key_entry.pack(fill="x", pady=(0, 8))

        ctk.CTkButton(
            self.content, text="Sauvegarder & Relancer",
            command=self.save_and_close,
            fg_color=COLOR_BLUE, height=36,
            font=("Segoe UI", 12, "bold")
        ).pack(fill="x")

    def _open_guide(self):
        guide = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "guide_extension", "Guide d'installation.html")
        if os.path.exists(guide):
            webbrowser.open(f"file:///{guide.replace(os.sep, '/')}")
        else:
            webbrowser.open("https://claude.ai")

    def save_and_close(self):
        new_key = self.key_entry.get().strip()
        if new_key:
            ConfigManager.save(new_key)
            self._parent_app.reload_app()
            self.destroy()


class InfoDialog(_BaseDialog):
    _AUTHOR_URL = "https://www.skool.com/@laurent-gerard-1911?g=ia-mastery"

    def __init__(self, parent):
        super().__init__(parent, "🅻🅶   À propos", 340, 305)

        # Ligne logo + nom
        top = ctk.CTkFrame(self.content, fg_color="transparent")
        top.pack(fill="x", pady=(0, 14))

        logo = parent._load_logo(size=(40, 40))
        if logo:
            lbl = ctk.CTkLabel(top, image=logo, text="")
            lbl.image = logo
            lbl.pack(side="left", padx=(0, 12))

        titles = ctk.CTkFrame(top, fg_color="transparent")
        titles.pack(side="left")
        ctk.CTkLabel(
            titles, text=APP_NAME,
            font=("Segoe UI", 17, "bold"), anchor="w"
        ).pack(anchor="w")

        # Tableau version / date / auteur
        tbl = ctk.CTkFrame(self.content, fg_color="#212121", corner_radius=8)
        tbl.pack(fill="x", pady=(0, 14))

        for i, (label, value) in enumerate([("Version", APP_VERSION),
                                            ("Date", APP_DATE)]):
            row = ctk.CTkFrame(tbl, fg_color="transparent")
            row.pack(fill="x", padx=14,
                     pady=(8 if i == 0 else 4, 4))
            ctk.CTkLabel(
                row, text=label, width=70,
                font=("Segoe UI", 11), text_color="#666", anchor="w"
            ).pack(side="left")
            ctk.CTkLabel(
                row, text=value,
                font=("Segoe UI", 11, "bold"), text_color="#ddd", anchor="w"
            ).pack(side="left")

        # Ligne auteur avec lien
        author_row = ctk.CTkFrame(tbl, fg_color="transparent")
        author_row.pack(fill="x", padx=14, pady=(4, 8))
        ctk.CTkLabel(
            author_row, text="Auteur", width=70,
            font=("Segoe UI", 11), text_color="#666", anchor="w"
        ).pack(side="left")
        ctk.CTkButton(
            author_row, text=APP_AUTHOR,
            font=("Segoe UI", 11, "bold"), text_color=COLOR_BLUE,
            fg_color="transparent", hover_color="#1a2030",
            anchor="w", height=22, corner_radius=4,
            command=lambda: webbrowser.open(self._AUTHOR_URL)
        ).pack(side="left", padx=0)

        ctk.CTkButton(
            self.content, text="Fermer", command=self.destroy,
            fg_color=COLOR_BLUE, height=34,
            font=("Segoe UI", 12, "bold")
        ).pack(fill="x")

        # Fermeture au moindre clic (délai pour ne pas capturer le clic d'ouverture)
        self.after(150, self._bind_close_on_click)

    def _bind_close_on_click(self):
        def _rec(w):
            w.bind("<Button-1>", self._close_safely, add="+")
            for child in w.winfo_children():
                _rec(child)
        _rec(self)

    def _close_safely(self, _=None):
        try:
            self.destroy()
        except Exception:
            pass


# --- RECEIVER HTTP (extension navigateur → app) ---
RECEIVER_PORT = 27182


class _SessionKeyHandler(BaseHTTPRequestHandler):
    app_ref = None

    def do_GET(self):
        # L'app signale qu'elle est prête (pour que l'extension sache qu'elle peut envoyer)
        if self.path == '/ping':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'{"status":"ready"}')
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/session-key':
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length))
            new_key = body.get('session_key', '').strip()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            app = _SessionKeyHandler.app_ref
            if new_key and app and new_key != app.session_key:
                self.wfile.write(b'{"status":"updated"}')
                app.after(0, lambda k=new_key: app._on_new_session_key(k))
            else:
                self.wfile.write(b'{"status":"unchanged"}')
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def log_message(self, *args):
        pass  # silence des logs HTTP


def _start_receiver(app):
    _SessionKeyHandler.app_ref = app
    try:
        server = HTTPServer(('127.0.0.1', RECEIVER_PORT), _SessionKeyHandler)
        server.serve_forever()
    except OSError:
        pass  # port déjà occupé, on ignore


# --- APPLICATION PRINCIPALE ---
class ClaudeMonitorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Fenêtre sans barre native
        self.overrideredirect(True)
        self.resizable(False, False)
        self.configure(fg_color="#484848")  # couleur de bordure (1px visible)

        # Largeur fixe, hauteur auto calculée après rendu
        self.geometry("380x100")  # hauteur temporaire
        self.after(20, self._fit_and_center)

        # État interne
        self._topmost = False
        self._drag_x = self._drag_y = 0
        self._tray = None

        self.config = ConfigManager.load()
        self.session_key = self.config.get("session_key", "")
        self.org_id = self.config.get("org_id", "")
        self.session = requests.Session(impersonate="chrome120")
        self.is_running = True

        self._set_window_icon()
        self.create_ui()
        self._setup_tray()
        self.after(200, self._apply_rounded_corners)

        # Receiver HTTP pour l'extension navigateur
        threading.Thread(target=_start_receiver, args=(self,), daemon=True).start()

        if not self.session_key:
            self.after(500, self.open_settings)
        else:
            self.setup_session()
            threading.Thread(target=self.init_sequence, daemon=True).start()

    # ── HELPERS FENÊTRE ──────────────────────────────────────────────────────

    def _set_window_icon(self):
        for fname in ("work/Claude-Win-Monitor_ICO.ico", "work/icon3.ico"):
            if os.path.exists(fname):
                try:
                    self.wm_iconbitmap(fname)
                    return
                except Exception:
                    pass

    def _fit_and_center(self):
        """Ajuste la hauteur au contenu réel puis centre la fenêtre."""
        self.update_idletasks()
        h = self.winfo_reqheight()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = max(0, (sw - 380) // 2)
        y = max(0, (sh - h) // 2)
        self.geometry(f"380x{h}+{x}+{y}")

    def _apply_rounded_corners(self):
        _apply_rounded_corners_to(self)

    def _load_logo(self, size=(52, 52)):
        for fname in ("Claude-Win-Monitor_ICO.png", "icon3.png"):
            if os.path.exists(fname):
                try:
                    return ctk.CTkImage(Image.open(fname), size=size)
                except Exception:
                    pass
        return None

    def _on_new_session_key(self, session_key):
        """Appelé par le receiver HTTP quand l'extension envoie une nouvelle clé."""
        ConfigManager.save(session_key)
        try:
            self._settings_dialog.destroy()
        except Exception:
            pass
        self.reload_app()

    def reload_app(self):
        self.config = ConfigManager.load()
        self.session_key = self.config["session_key"]
        self.setup_session()
        self.update_status("● Redémarrage...", "gray")
        threading.Thread(target=self.init_sequence, daemon=True).start()

    def setup_session(self):
        self.session.headers.update({
            "Cookie": f"sessionKey={self.session_key}",
            "Origin": "https://claude.ai",
            "Referer": "https://claude.ai/chats",
            "Content-Type": "application/json"
        })

    # ── DRAG ─────────────────────────────────────────────────────────────────

    def _start_drag(self, event):
        self._drag_x = event.x_root - self.winfo_x()
        self._drag_y = event.y_root - self.winfo_y()

    def _do_drag(self, event):
        self.geometry(f"+{event.x_root - self._drag_x}+{event.y_root - self._drag_y}")

    # ── SYSTEM TRAY ───────────────────────────────────────────────────────────

    def _setup_tray(self):
        if not _HAVE_TRAY:
            return
        try:
            img = Image.open("Claude-Win-Monitor_ICO.png").resize((64, 64))
        except Exception:
            img = Image.new("RGB", (64, 64), "#3b82f6")

        menu = pystray.Menu(
            pystray.MenuItem("Afficher", self._show_window, default=True),
            pystray.MenuItem("Actualiser", self._tray_refresh),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quitter", self._quit_from_tray)
        )
        self._tray = pystray.Icon(
            "claude_monitor", img, "Claude Usage Monitor", menu
        )
        threading.Thread(target=self._tray.run, daemon=True).start()

    def _hide_to_tray(self):
        self.withdraw()

    def _show_window(self, *_):
        self.after(0, self.deiconify)
        self.after(0, lambda: self.wm_attributes("-topmost", self._topmost))

    def _tray_refresh(self, *_):
        threading.Thread(target=self.fetch_data, daemon=True).start()

    def _quit_from_tray(self, *_):
        self.is_running = False
        if self._tray:
            self._tray.stop()
        self.after(0, self.destroy)

    # ── TOUJOURS AU PREMIER PLAN ──────────────────────────────────────────────

    def _toggle_topmost(self):
        self._topmost = not self._topmost
        self.wm_attributes("-topmost", self._topmost)
        self._pin_btn.configure(text_color=COLOR_BLUE if self._topmost else "#505050")

    # ── TITLEBAR PERSONNALISÉE ────────────────────────────────────────────────

    def _build_titlebar(self, parent):
        tb = ctk.CTkFrame(parent, height=36, fg_color=COLOR_TITLEBAR, corner_radius=0)
        tb.pack(fill="x")
        tb.pack_propagate(False)

        for widget in (tb,):
            widget.bind("<ButtonPress-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._do_drag)

        # Gauche : icône + titre
        left = ctk.CTkFrame(tb, fg_color="transparent")
        left.pack(side="left", padx=10, fill="y")

        logo_small = self._load_logo(size=(20, 20))
        if logo_small:
            lbl = ctk.CTkLabel(left, image=logo_small, text="")
            lbl.image = logo_small
            lbl.pack(side="left", padx=(0, 7), pady=8)
            lbl.bind("<ButtonPress-1>", self._start_drag)
            lbl.bind("<B1-Motion>", self._do_drag)

        title = ctk.CTkLabel(
            left, text="🅻🅶 :  Claude Usage Monitor",
            font=("Segoe UI", 11), text_color="#666"
        )
        title.pack(side="left", pady=8)
        title.bind("<ButtonPress-1>", self._start_drag)
        title.bind("<B1-Motion>", self._do_drag)

        # Droite : boutons
        btns = ctk.CTkFrame(tb, fg_color="transparent")
        btns.pack(side="right", padx=6, fill="y")

        self._pin_btn = ctk.CTkButton(
            btns, text="📌", width=28, height=28,
            fg_color="transparent", hover_color="#252525",
            text_color="#505050", command=self._toggle_topmost,
            corner_radius=6, font=("Segoe UI", 12)
        )
        self._pin_btn.pack(side="left", padx=2, pady=4)

        ctk.CTkButton(
            btns, text="─", width=28, height=28,
            fg_color="transparent", hover_color="#252525",
            text_color="#888", command=self._hide_to_tray,
            corner_radius=6, font=("Segoe UI", 13, "bold")
        ).pack(side="left", padx=2, pady=4)

        ctk.CTkButton(
            btns, text="✕", width=28, height=28,
            fg_color="transparent", hover_color="#4a1010",
            text_color=COLOR_CRIT, command=self._hide_to_tray,
            corner_radius=6, font=("Segoe UI", 12, "bold")
        ).pack(side="left", padx=2, pady=4)

    # ── UI PRINCIPALE ─────────────────────────────────────────────────────────

    def create_ui(self):
        # 1px de gap → couleur de fond de la fenêtre visible comme bordure
        root = ctk.CTkFrame(self, fg_color=COLOR_BG, corner_radius=0)
        root.pack(fill="both", expand=True, padx=1, pady=1)

        self._build_titlebar(root)

        # Séparateur titlebar / contenu
        ctk.CTkFrame(root, height=1, fg_color="#1e1e1e", corner_radius=0).pack(fill="x")

        # Barre du bas (packée avant les cartes)
        bottom = ctk.CTkFrame(root, fg_color="#181818", corner_radius=0, height=56)
        bottom.pack(side="bottom", fill="x")
        bottom.pack_propagate(False)

        btn_settings = ctk.CTkButton(
            bottom, text="⚙   Paramètres",
            command=self.open_settings,
            fg_color="transparent", hover_color="#252525",
            text_color="#888", font=("Segoe UI", 14), corner_radius=0
        )
        btn_settings.pack(side="left", expand=True, fill="both")
        Tooltip(btn_settings, "Modifier la clé de session")

        ctk.CTkFrame(bottom, width=1, fg_color="#2a2a2a").pack(
            side="left", fill="y", pady=10
        )

        btn_quit = ctk.CTkButton(
            bottom, text="⏻   Quitter",
            command=self.quit_app,
            fg_color="transparent", hover_color="#2a0e0e",
            text_color=COLOR_CRIT, font=("Segoe UI", 14), corner_radius=0
        )
        btn_quit.pack(side="right", expand=True, fill="both")
        Tooltip(btn_quit, "Quitter l'application")

        # Header
        header = ctk.CTkFrame(root, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(16, 0))

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left")

        logo_img = self._load_logo()
        if logo_img:
            logo_lbl = ctk.CTkLabel(left, image=logo_img, text="")
            logo_lbl.image = logo_img
            logo_lbl.pack(side="left", padx=(0, 14))
        else:
            cv = tk.Canvas(left, width=52, height=52,
                           bg=COLOR_BG, highlightthickness=0)
            cv.create_oval(2, 2, 50, 50, fill=COLOR_BLUE, outline="")
            cv.create_text(26, 26, text="C", fill="white",
                           font=("Segoe UI", 22, "bold"))
            cv.pack(side="left", padx=(0, 14))

        info = ctk.CTkFrame(left, fg_color="transparent")
        info.pack(side="left")

        self.user_lbl = ctk.CTkLabel(
            info, text="Claude Usage",
            font=("Segoe UI", 16, "bold"), anchor="w"
        )
        self.user_lbl.pack(anchor="w")

        self.email_lbl = ctk.CTkLabel(
            info, text="",
            font=("Segoe UI", 10), text_color="#555", anchor="w"
        )
        self.email_lbl.pack(anchor="w")

        self.status_frame = ctk.CTkFrame(
            info, fg_color=COLOR_SAFE_BG, corner_radius=20
        )
        self.status_frame.pack(anchor="w", pady=(4, 0))
        self.status_lbl = ctk.CTkLabel(
            self.status_frame, text="● Connexion...",
            font=("Segoe UI", 10, "bold"), text_color=COLOR_SAFE
        )
        self.status_lbl.pack(padx=10, pady=3)

        right_col = ctk.CTkFrame(header, fg_color="transparent")
        right_col.pack(side="right", anchor="n")

        btn_refresh = ctk.CTkButton(
            right_col, text="↻", width=36, height=36,
            command=self.manual_refresh,
            fg_color="#242424", hover_color="#303030",
            corner_radius=10, font=("Segoe UI", 16, "bold")
        )
        btn_refresh.pack(pady=(0, 6))
        Tooltip(btn_refresh, "Actualiser les données")

        btn_info = ctk.CTkButton(
            right_col, text="i", width=36, height=36,
            command=self._show_info,
            fg_color="#242424", hover_color="#303030",
            text_color=COLOR_BLUE, corner_radius=10,
            font=("Segoe UI", 16, "bold")
        )
        btn_info.pack()
        Tooltip(btn_info, "À propos de l'application")

        # Séparateur header / cartes
        ctk.CTkFrame(root, height=1, fg_color="#242424").pack(
            fill="x", pady=(14, 0)
        )

        # Cartes (tk.Frame natif = gestion de hauteur 100% fiable)
        cards = tk.Frame(root, bg=COLOR_BG)
        cards.pack(fill="both", expand=True, padx=14, pady=(12, 6))

        self.card_session = self._make_card(
            cards, "Session en cours", "Limite glissante de 5h"
        )
        self.card_weekly = self._make_card(
            cards, "Hebdomadaire", "Limite de 7 jours"
        )
        self.card_billing = self._make_card(
            cards, "Budget mensuel", "Chargement..."
        )

    def _make_card(self, parent, title, subtitle):
        """Carte avec fond tintable et barre de progression."""
        wrapper = tk.Frame(parent, bg=COLOR_BG)
        wrapper.pack(fill="x", pady=(0, 10))

        card = ctk.CTkFrame(
            wrapper, fg_color=COLOR_CARD, corner_radius=14,
            border_width=1, border_color="#272727"
        )
        card.pack(fill="x")

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=(14, 0))

        row = ctk.CTkFrame(inner, fg_color="transparent")
        row.pack(fill="x")

        ctk.CTkLabel(
            row, text=title,
            font=("Segoe UI", 14, "bold"), anchor="w"
        ).pack(side="left")

        pct_zone = ctk.CTkFrame(row, fg_color="transparent")
        pct_zone.pack(side="right")

        pct_lbl = ctk.CTkLabel(
            pct_zone, text="--%",
            font=("Segoe UI", 24, "bold"), text_color=COLOR_SAFE
        )
        pct_lbl.pack(side="left")

        sub_lbl = ctk.CTkLabel(
            inner, text=subtitle,
            font=("Segoe UI", 12), text_color="#686868", anchor="w"
        )
        sub_lbl.pack(anchor="w", pady=(3, 0))

        bar = ctk.CTkProgressBar(
            card, height=10, corner_radius=5,
            progress_color=COLOR_SAFE, fg_color="#2e2e2e"
        )
        bar.set(0.004)
        bar.pack(fill="x", padx=16, pady=(10, 0))

        reset_lbl = ctk.CTkLabel(
            card, text="",
            font=("Segoe UI", 12), text_color="#686868"
        )
        reset_lbl.pack(anchor="e", padx=16, pady=(5, 13))

        return {"card": card, "p": pct_lbl, "bar": bar,
                "sub": sub_lbl, "reset": reset_lbl}

    # ── LOGIQUE ───────────────────────────────────────────────────────────────

    def open_settings(self):
        self._settings_dialog = SettingsDialog(self, self.session_key)

    def _show_info(self):
        InfoDialog(self)

    def init_sequence(self):
        try:
            res = self.session.get(f"{BASE_URL}/bootstrap", timeout=10)
            if res.status_code == 200:
                data = res.json()
                account = data.get("account", {})
                name = account.get("full_name", "Claude Usage")
                email = account.get("email_address", "")

                self.after(0, lambda: self.user_lbl.configure(text=name))
                self.after(0, lambda: self.email_lbl.configure(text=email))

                if not self.org_id:
                    memberships = account.get("memberships", [])
                    for m in memberships:
                        org = m.get("organization", {})
                        caps = org.get("capabilities", [])
                        if "claude_pro" in caps or "api" not in caps:
                            self.org_id = org.get("uuid")
                            ConfigManager.save(self.session_key, self.org_id)
                            break

            if self.org_id:
                self.background_loop()
            else:
                self.update_status("⚠️ Organisation introuvable", COLOR_CRIT)

        except Exception as e:
            print(e)
            self.update_status("❌ Erreur connexion", COLOR_CRIT)

    def background_loop(self):
        while self.is_running:
            self.fetch_data()
            for _ in range(REFRESH_RATE_SECONDS):
                if not self.is_running:
                    break
                time.sleep(1)

    def manual_refresh(self):
        threading.Thread(target=self.fetch_data, daemon=True).start()

    def fetch_data(self):
        self.update_status("● Actualisation...", COLOR_WARN)
        try:
            r_usage = self.session.get(
                f"{BASE_URL}/organizations/{self.org_id}/usage", timeout=10
            )
            r_limit = self.session.get(
                f"{BASE_URL}/organizations/{self.org_id}/overage_spend_limit", timeout=10
            )
            r_prepaid = self.session.get(
                f"{BASE_URL}/organizations/{self.org_id}/prepaid/credits", timeout=10
            )

            if r_usage.status_code == 200:
                self.after(0, lambda: self.update_ui(
                    r_usage.json(), r_limit.json(), r_prepaid.json()
                ))
            elif r_usage.status_code == 403:
                self.update_status("🔒 Session expirée", COLOR_CRIT)
            else:
                self.update_status(f"⚠️ Erreur API {r_usage.status_code}", COLOR_WARN)

        except Exception:
            self.update_status("📡 Erreur réseau", COLOR_CRIT)

    def update_ui(self, usage, limits, prepaid):
        five_hour = usage.get("five_hour", {})
        self._update_bar_card(self.card_session, five_hour)
        self._update_bar_card(self.card_weekly, usage.get("seven_day", {}))

        # Mise à jour du survol de l'icône dans la barre des tâches
        if self._tray:
            pct = int(five_hour.get("utilization", 0))
            self._tray.title = f"Claude Monitor  •  Session : {pct}%"

        limit_cap = limits.get("monthly_credit_limit", 500) / 100
        used_month = limits.get("used_credits", 0) / 100
        balance_real = prepaid.get("amount", 0) / 100

        ratio = used_month / limit_cap if limit_cap > 0 else 0.0
        color = self._ratio_color(ratio)
        card_bg = self._ratio_card_bg(ratio)

        card = self.card_billing
        card["card"].configure(fg_color=card_bg)
        card["bar"].set(max(min(ratio, 1.0), 0.004))
        card["bar"].configure(progress_color=color)
        card["p"].configure(text=f"{int(ratio * 100)}%", text_color=color)
        card["sub"].configure(text=f"{used_month:.2f} / {limit_cap:.2f} EUR")
        card["reset"].configure(text=f"Solde : {balance_real:.2f} €")

        self.update_status("● Système Opérationnel", COLOR_SAFE)

    def _update_bar_card(self, card, data):
        val = data.get("utilization", 0.0)
        reset = data.get("resets_at")

        ratio = val / 100.0
        color = self._ratio_color(ratio)
        card_bg = self._ratio_card_bg(ratio)

        card["card"].configure(fg_color=card_bg)
        card["bar"].set(max(min(ratio, 1.0), 0.004))
        card["bar"].configure(progress_color=color)
        card["p"].configure(text=f"{int(val)}%", text_color=color)

        if reset:
            card["reset"].configure(text=f"Reset : {format_date_french(reset)}")
        else:
            card["reset"].configure(text="Aucune limite active")

    @staticmethod
    def _ratio_color(ratio):
        if ratio > 0.8:
            return COLOR_CRIT
        if ratio > 0.5:
            return COLOR_WARN
        return COLOR_SAFE

    @staticmethod
    def _ratio_card_bg(ratio):
        if ratio > 0.8:
            return COLOR_CARD_CRIT
        if ratio > 0.5:
            return COLOR_CARD_WARN
        return COLOR_CARD

    def update_status(self, text, color):
        if color == COLOR_SAFE:
            badge_bg = COLOR_SAFE_BG
        elif color == COLOR_WARN:
            badge_bg = COLOR_WARN_BG
        elif color == COLOR_CRIT:
            badge_bg = COLOR_CRIT_BG
        else:
            badge_bg = "#1e1e1e"
        self.after(0, lambda: self.status_lbl.configure(text=text, text_color=color))
        self.after(0, lambda: self.status_frame.configure(fg_color=badge_bg))

    def quit_app(self):
        self.is_running = False
        if self._tray:
            self._tray.stop()
        self.destroy()
        sys.exit()


if __name__ == "__main__":
    app = ClaudeMonitorApp()
    app.mainloop()
