# ===============================================================
# CLAUDE-WIN-MONITOR v1.9.1
# 🅻🅶's Claude Usage Monitor pour suivre les quotas Anthropic
# Auteur  : 🅻🅶 @ IA Mastery
# Date    : 18/03/2026
# ===============================================================
#
# Architecture générale :
#   ClaudeMonitorApp     → fenêtre principale (customtkinter)
#   _BaseDialog          → base commune des fenêtres modales (drag, overlay, titlebar)
#   SettingsDialog       → configuration de la sessionKey (2 méthodes)
#   InfoDialog           → fenêtre "À propos"
#   _SessionKeyHandler   → serveur HTTP local port 27182
#                          reçoit la sessionKey depuis l'extension navigateur
#   ConfigManager        → lecture / écriture du fichier JSON de config
#   Tooltip              → infobulles au survol des boutons
#
# Flux de données :
#   Extension navigateur  →  POST localhost:27182/session-key
#   → _SessionKeyHandler  →  ClaudeMonitorApp._on_new_session_key()
#   → reload_app()        →  init_sequence()  →  fetch_data()  →  update_ui()
#
# Endpoints API claude.ai (non documentés officiellement) :
#   /api/bootstrap                                    → profil utilisateur + org_id
#   /api/organizations/{org_id}/usage                 → quotas fenêtre 5h et 7j
#   /api/organizations/{org_id}/overage_spend_limit   → budget mensuel consommé
#   /api/organizations/{org_id}/prepaid/credits       → solde prépayé restant
# ===============================================================


import customtkinter as ctk          # UI dark mode, widgets stylés
import tkinter as tk                 # widgets natifs (Canvas, Frame)
from PIL import Image                # chargement icône/logo
from curl_cffi import requests       # HTTP avec impersonation Chrome (évite les blocages)
import threading                     # appels réseau non bloquants
import time                          # sleep dans la boucle de refresh
import json                          # config JSON
import os                            # chemins fichiers
import sys                           # sys.exit() à la fermeture
from pathlib import Path             # chemins DATA_DIR (config persistante)
import webbrowser                    # ouvrir liens externes
import dateutil.parser               # parsing des dates ISO 8601
from http.server import HTTPServer, BaseHTTPRequestHandler  # receiver extension

# pystray est optionnel : si absent, l'icône système tray est désactivée silencieusement
try:
    import pystray
    _HAVE_TRAY = True
except ImportError:
    _HAVE_TRAY = False


# Répertoire du script (chemins absolus, compatibles Nuitka --standalone)
if getattr(sys, "frozen", False):
    _HERE = os.path.dirname(sys.executable)
else:
    _HERE = os.path.dirname(os.path.abspath(__file__))

# Données persistantes dans %LOCALAPPDATA% (C:\Program Files est protégé en écriture)
_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", _HERE)) / "Claude-Win-Monitor"
_DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── CONSTANTES GLOBALES ──────────────────────────────────────────────────────

BASE_URL             = "https://claude.ai/api"   # base des endpoints API
REFRESH_RATE_SECONDS = 300                        # intervalle auto-refresh (5 min)
CONFIG_FILE          = str(_DATA_DIR / "claude_monitor_config.json")
TRANSLATIONS_FILE    = os.path.join(_HERE, "translations.json")

APP_NAME    = "Claude Usage Monitor"
APP_AUTHOR  = "🅻🅶 @ IA Mastery"
APP_VERSION = "v1.9.1"
APP_DATE    = "28/03/2026"

# ── PALETTE DE COULEURS ──────────────────────────────────────────────────────
# Trois niveaux d'alerte : safe (vert) / warn (orange) / crit (rouge)
# Les couleurs *_BG sont les fonds de cartes et du badge de statut

COLOR_BG        = "#141414"   # fond général de l'app
COLOR_CARD      = "#1c1c1c"   # fond carte normal
COLOR_CARD_WARN = "#1e1a12"   # fond carte en avertissement
COLOR_CARD_CRIT = "#1e1212"   # fond carte en critique
COLOR_SAFE      = "#22c55e"   # vert  — usage < 50 %
COLOR_SAFE_BG   = "#0b2115"
COLOR_WARN      = "#f59e0b"   # orange — usage 50–80 %
COLOR_WARN_BG   = "#1f1508"
COLOR_CRIT      = "#ef4444"   # rouge  — usage > 80 %
COLOR_CRIT_BG   = "#1f0808"
COLOR_BLUE      = "#3b82f6"   # bleu   — liens, boutons actifs
COLOR_TITLEBAR  = "#0e0e0e"   # barre de titre

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")


# ── HELPERS FENÊTRE ──────────────────────────────────────────────────────────

def _apply_rounded_corners_to(window):
    """Active les coins arrondis Windows 11 via l'API DWM (Desktop Window Manager).
    Sans effet sur Windows 10 ou si DWM est indisponible (silencieux)."""
    try:
        import ctypes
        hwnd = window.winfo_id()
        DWMWCP_ROUND = 2   # valeur de l'enum DWM_WINDOW_CORNER_PREFERENCE
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 33,      # attribut DWMWA_WINDOW_CORNER_PREFERENCE
            ctypes.byref(ctypes.c_int(DWMWCP_ROUND)),
            ctypes.sizeof(ctypes.c_int(DWMWCP_ROUND))
        )
    except Exception:
        pass


# ── TOOLTIP ──────────────────────────────────────────────────────────────────

class Tooltip:
    """Infobulle légère apparaissant après un délai au survol d'un widget.
    S'annule si la souris quitte le widget ou si l'utilisateur clique."""
    DELAY = 420  # ms avant affichage

    def __init__(self, widget, text):
        self._w    = widget
        self._text = text
        self._tip  = None   # fenêtre Toplevel de l'infobulle
        self._aid  = None   # after-id pour annuler le timer
        widget.bind("<Enter>",       self._schedule)
        widget.bind("<Leave>",       self._cancel)
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
        """Crée la fenêtre flottante positionnée sous (ou au-dessus) du widget."""
        self._tip = tk.Toplevel()
        self._tip.overrideredirect(True)
        self._tip.wm_attributes("-topmost", True)
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
        x  = max(4, wx + (ww - tw) // 2)
        # Afficher au-dessus si pas de place en dessous
        y  = wy - th - 6 if wy + wh + th + 6 > sh - 50 else wy + wh + 6
        self._tip.geometry(f"+{x}+{y}")


# ── UTILITAIRES ──────────────────────────────────────────────────────────────

def _load_flag(code: str, size=(28, 20)):
    """Charge le drapeau PNG correspondant au code langue (flag-fr.png, flag-en.png, …).
    Retourne un CTkImage 28×20 prêt à l'emploi, ou None si le fichier est introuvable."""
    path = os.path.join(_HERE, f"flag-{code}.png")
    try:
        img = Image.open(path).convert("RGB")
        return ctk.CTkImage(img, size=size)
    except Exception:
        return None   # fallback silencieux → le bouton affiche uniquement le code texte


def _load_icon(path, color_hex, size=(22, 22)):
    """Charge un PNG blanc sur fond transparent et le teinte dans la couleur souhaitée.
    Retourne un CTkImage prêt à l'emploi, ou None si le fichier est introuvable."""
    try:
        img = Image.open(path).convert("RGBA")
        rv = int(color_hex[1:3], 16)
        gv = int(color_hex[3:5], 16)
        bv = int(color_hex[5:7], 16)
        r, g, b, a = img.split()
        r = r.point(lambda _: rv)
        g = g.point(lambda _: gv)
        b = b.point(lambda _: bv)
        return ctk.CTkImage(Image.merge("RGBA", (r, g, b, a)), size=size)
    except Exception:
        return None


def format_date_long(iso_date_str):
    """Retourne la date au format long localisé : 'mercredi 18 mars à 15h' (FR)."""
    if not iso_date_str:
        return ""
    try:
        import datetime as _dt
        dt     = dateutil.parser.isoparse(iso_date_str).astimezone()
        days   = I18n.days_long()   or ["lundi","mardi","mercredi","jeudi","vendredi","samedi","dimanche"]
        months = I18n.months_long() or ["","janvier","février","mars","avril","mai","juin",
                                         "juillet","août","septembre","octobre","novembre","décembre"]
        at = I18n.date_at() or "à"
        return f"{days[dt.weekday()]} {dt.day} {months[dt.month]} {at} {dt.hour}h"
    except Exception:
        return ""


def format_time_remaining(iso_date_str, include_days=False):
    """Retourne le temps restant avant la date donnée, dans la langue courante.
    include_days=False → '2h 30min'       (session 5h)
    include_days=True  → '1j 2h 30min'    (hebdomadaire)"""
    if not iso_date_str:
        return "—"
    try:
        import datetime as _dt
        dt        = dateutil.parser.isoparse(iso_date_str).astimezone()
        now       = _dt.datetime.now(tz=dt.tzinfo)
        total_sec = int((dt - now).total_seconds())
        h_u = I18n.t("unit_hour")
        m_u = I18n.t("unit_min")
        d_u = I18n.t("unit_day")
        if total_sec <= 0:
            return f"0{h_u} 00{m_u}"
        total_min = total_sec // 60
        if include_days:
            days  = total_min // (24 * 60)
            rem   = total_min % (24 * 60)
            hours = rem // 60
            mins  = rem % 60
            return f"{days}{d_u} {hours}{h_u} {mins:02d}{m_u}"
        else:
            hours = total_min // 60
            mins  = total_min % 60
            return f"{hours}{h_u} {mins:02d}{m_u}"
    except Exception:
        return "—"


def format_date_short(iso_date_str):
    """Convertit une date ISO 8601 en texte court localisé.
    Ex FR : 'sam 28 mars à 11h00' — Ex EN : 'Sat Mar 28 at 11:00'"""
    if not iso_date_str:
        return "—"
    try:
        dt     = dateutil.parser.isoparse(iso_date_str).astimezone()
        days   = I18n.days_short()   or ["lun","mar","mer","jeu","ven","sam","dim"]
        months = I18n.months_short() or ["","janv","fév","mars","avr","mai","juin",
                                          "juil","août","sept","oct","nov","déc"]
        at = I18n.date_at() or "à"
        return f"{days[dt.weekday()]} {dt.day} {months[dt.month]} {at} {dt.hour}h{dt.minute:02d}"
    except Exception:
        return "—"


class ConfigManager:
    """Gestion du fichier de configuration local (JSON).
    Contenu : session_key, org_id, language, currency."""

    @staticmethod
    def load():
        """Retourne le dict de config ou {} si le fichier est absent/corrompu."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    @staticmethod
    def save(session_key, org_id=None, language=None, currency=None):
        """Sauvegarde la sessionKey et les champs optionnels.
        Charge l'existant d'abord pour ne pas écraser language/currency/org_id."""
        data = ConfigManager.load()
        data["session_key"] = session_key
        if org_id is not None:
            data["org_id"] = org_id
        if language is not None:
            data["language"] = language
        if currency is not None:
            data["currency"] = currency
        with open(CONFIG_FILE, 'w') as f:
            json.dump(data, f)

    @staticmethod
    def save_locale(language=None, currency=None):
        """Sauvegarde uniquement la langue et/ou la devise (sans toucher à session_key)."""
        data = ConfigManager.load()
        if language is not None:
            data["language"] = language
        if currency is not None:
            data["currency"] = currency
        with open(CONFIG_FILE, 'w') as f:
            json.dump(data, f)


# ── INTERNATIONALISATION ──────────────────────────────────────────────────────

class I18n:
    """Gestionnaire de traductions multilingues.

    Charge translations.json au démarrage et expose :
      - I18n.t("clé")                → chaîne traduite (langue courante)
      - I18n.t("clé", x=1.2, cur="€") → chaîne traduite avec substitutions
      - I18n.lang()                  → code langue courant ("fr", "en", …)
      - I18n.currency()              → symbole devise courant ("€", "$", …)
      - I18n.available()             → liste des codes langues disponibles
      - I18n.name(code)              → nom humain d'une langue ("Français", …)
      - I18n.days_long()             → liste des noms de jours complets (lun=0)
      - I18n.days_short()            → liste des noms de jours abrégés
      - I18n.months_long()           → liste des noms de mois complets (idx 1..12)
      - I18n.months_short()          → liste des noms de mois abrégés
      - I18n.date_at()               → préposition "à" / "at" / "um" / …
    """
    _data:     dict = {}
    _lang:     str  = "fr"
    _currency: str  = "€"

    @classmethod
    def load(cls, path: str, lang: str = "fr", currency: str = "€") -> None:
        """Charge le fichier translations.json. Silencieux si le fichier est absent."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                cls._data = json.load(f)
        except Exception:
            cls._data = {}
        cls._lang     = lang if lang in cls._data else "fr"
        cls._currency = currency or "€"

    @classmethod
    def t(cls, key: str, **kwargs) -> str:
        """Retourne la chaîne traduite pour `key` dans la langue courante.
        Les kwargs sont injectés via str.format_map() — ex: I18n.t("reset_in", t="2h 30min")."""
        lang_data = cls._data.get(cls._lang) or cls._data.get("fr") or {}
        s = lang_data.get(key, key)   # fallback sur la clé si absente
        if kwargs:
            try:
                s = s.format_map(kwargs)
            except (KeyError, IndexError, ValueError):
                pass
        return s

    # ── Accesseurs ─────────────────────────────────────────────────────────

    @classmethod
    def lang(cls) -> str:
        return cls._lang

    @classmethod
    def set_lang(cls, code: str) -> None:
        if code in cls._data:
            cls._lang = code

    @classmethod
    def currency(cls) -> str:
        return cls._currency

    @classmethod
    def set_currency(cls, symbol: str) -> None:
        cls._currency = symbol or "€"

    @classmethod
    def available(cls) -> list:
        """Retourne la liste des codes de langues disponibles (exclut _meta)."""
        return [k for k in cls._data if not k.startswith("_")]

    @classmethod
    def name(cls, code: str) -> str:
        """Retourne le nom humain d'un code langue, ex. "fr" → "Français"."""
        return cls._data.get(code, {}).get("_name", code.upper())

    @classmethod
    def code_label(cls, code: str) -> str:
        """Retourne le label court d'un code langue, ex. "fr" → "FR"."""
        return cls._data.get(code, {}).get("_code", code.upper())

    # ── Helpers date/temps ─────────────────────────────────────────────────

    @classmethod
    def days_long(cls) -> list:
        return cls._data.get(cls._lang, {}).get("days_long", [])

    @classmethod
    def days_short(cls) -> list:
        return cls._data.get(cls._lang, {}).get("days_short", [])

    @classmethod
    def months_long(cls) -> list:
        return cls._data.get(cls._lang, {}).get("months_long", [""] * 13)

    @classmethod
    def months_short(cls) -> list:
        return cls._data.get(cls._lang, {}).get("months_short", [""] * 13)

    @classmethod
    def date_at(cls) -> str:
        return cls._data.get(cls._lang, {}).get("date_at", "at")


# ── FENÊTRES MODALES (base commune) ──────────────────────────────────────────

class _BaseDialog(ctk.CTkToplevel):
    """Base pour toutes les fenêtres modales de l'app.
    Fournit : overrideredirect, titlebar custom, drag, overlay sombre, coins arrondis."""

    def __init__(self, parent, title_text, width, height):
        super().__init__(parent)
        self.overrideredirect(True)       # supprime la barre Windows native
        self.configure(fg_color="#484848") # visible comme bordure (1px gap)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()                   # fenêtre modale (bloque l'app principale)
        self._dx = self._dy = 0
        self._parent = parent
        self.geometry(f"{width}x{height}")
        self.after(10,  lambda: self._center_on(parent))
        self.after(200, lambda: _apply_rounded_corners_to(self))

        # Overlay sombre couvrant la fenêtre principale pendant la modal
        self._overlay = self._make_overlay(parent)

        self.wm_attributes("-topmost", True)
        self.after(1, self.lift)

        # Contenu principal avec 1px de gap → bordure visible sur tout le pourtour
        main = ctk.CTkFrame(self, fg_color="#181818", corner_radius=0)
        main.pack(fill="both", expand=True, padx=1, pady=1)

        # Titlebar personnalisée (draggable)
        tb = ctk.CTkFrame(main, fg_color="#0e0e0e", corner_radius=0, height=40)
        tb.pack(fill="x")
        tb.pack_propagate(False)
        for w in (tb,):
            w.bind("<ButtonPress-1>", self._drag_start)
            w.bind("<B1-Motion>",     self._drag_do)

        ctk.CTkLabel(
            tb, text=title_text,
            font=("Segoe UI", 12), text_color="#bbb"
        ).pack(side="left", padx=14)

        ctk.CTkButton(
            tb, text="✕", width=32, height=32,
            fg_color="transparent", hover_color="#4a1010",
            text_color=COLOR_CRIT, corner_radius=6,
            command=self.destroy, font=("Segoe UI", 13, "bold")
        ).pack(side="right", padx=4, pady=4)

        # Séparateur visuel titlebar / zone de contenu
        ctk.CTkFrame(main, height=1, fg_color="#2a2a2a", corner_radius=0).pack(fill="x")

        # Zone contenu : les sous-classes placent leurs widgets ici
        self.content = ctk.CTkFrame(main, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=22, pady=18)

    def _center_on(self, parent):
        """Centre la fenêtre sur la fenêtre parente."""
        self.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_x(),     parent.winfo_y()
        w,  h  = self.winfo_width(),   self.winfo_height()
        self.geometry(f"+{max(0, px + (pw - w) // 2)}+{max(0, py + (ph - h) // 2)}")

    def _drag_start(self, e):
        self._dx = e.x_root - self.winfo_x()
        self._dy = e.y_root - self.winfo_y()

    def _drag_do(self, e):
        self.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")

    def _make_overlay(self, parent):
        """Crée un Toplevel semi-transparent couvrant exactement la fenêtre principale."""
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
        """Ferme l'overlay avant de détruire la fenêtre modale."""
        try:
            self._overlay.destroy()
        except Exception:
            pass
        super().destroy()


# ── FENÊTRE PARAMÈTRES ───────────────────────────────────────────────────────

class SettingsDialog(_BaseDialog):
    """Fenêtre de configuration : sessionKey, langue, devise.

    Présente deux méthodes d'authentification :
      ① Automatique — via l'extension navigateur "Claude Session Helper"
      ② Manuelle    — copier-coller depuis F12 > Application > Cookies > claude.ai
    Propose également le sélecteur de langue (FR/EN/DE/IT/ES) et de devise.
    """

    def __init__(self, parent, current_key):
        super().__init__(parent, I18n.t("settings_title"), 460, 420)
        self._parent_app = parent

        # ── Titre section Session Key ──────────────────────────────────────
        ctk.CTkLabel(
            self.content, text=I18n.t("settings_sk_title"),
            font=("Segoe UI", 15, "bold"), anchor="w"
        ).pack(anchor="w", pady=(0, 12))

        # ── ① Méthode automatique (fond vert sombre) ──────────────────────
        m1 = ctk.CTkFrame(self.content, fg_color="#0d1f10", corner_radius=8)
        m1.pack(fill="x", pady=(0, 10))
        inner1 = ctk.CTkFrame(m1, fg_color="transparent")
        inner1.pack(fill="x", padx=14, pady=12)

        ctk.CTkLabel(
            inner1, text=I18n.t("settings_method1"),
            font=("Segoe UI", 12, "bold"), text_color=COLOR_SAFE, anchor="w"
        ).pack(anchor="w")
        ctk.CTkLabel(
            inner1, text=I18n.t("settings_method1_desc"),
            font=("Segoe UI", 12), text_color="#7aad7a", anchor="w", wraplength=380
        ).pack(anchor="w", pady=(4, 5))
        ctk.CTkButton(
            inner1, text=I18n.t("settings_open_guide"),
            command=self._open_guide,
            fg_color="transparent", hover_color="#1e4d2e",
            text_color=COLOR_SAFE, font=("Segoe UI", 12),
            anchor="w", height=24, corner_radius=4
        ).pack(anchor="w")

        # Séparateur entre les deux méthodes
        ctk.CTkFrame(self.content, height=1, fg_color="#2a2a2a",
                     corner_radius=0).pack(fill="x", pady=(0, 10))

        # ── ② Méthode manuelle (fond bleu sombre) ─────────────────────────
        m2 = ctk.CTkFrame(self.content, fg_color="#0d1a2a", corner_radius=8)
        m2.pack(fill="x", pady=(0, 12))
        inner2 = ctk.CTkFrame(m2, fg_color="transparent")
        inner2.pack(fill="x", padx=14, pady=12)

        ctk.CTkLabel(
            inner2, text=I18n.t("settings_method2"),
            font=("Segoe UI", 12, "bold"), text_color=COLOR_BLUE, anchor="w"
        ).pack(anchor="w")
        ctk.CTkLabel(
            inner2, text=I18n.t("settings_method2_desc"),
            font=("Segoe UI", 11), text_color="#5588aa", anchor="w"
        ).pack(anchor="w", pady=(4, 5))
        ctk.CTkButton(
            inner2, text=I18n.t("settings_open_claudeai"),
            command=lambda: webbrowser.open("https://claude.ai"),
            fg_color="transparent", hover_color="#1a3a5c",
            text_color=COLOR_BLUE, font=("Segoe UI", 12),
            anchor="w", height=24, corner_radius=4
        ).pack(anchor="w")

        # Champ de saisie de la sessionKey
        self.key_entry = ctk.CTkEntry(
            self.content, height=38,
            placeholder_text="sk-ant-sid01-...",
            font=("Segoe UI", 12)
        )
        self.key_entry.insert(0, current_key)
        self.key_entry.pack(fill="x", pady=(0, 12))

        # ── Séparateur ────────────────────────────────────────────────────
        ctk.CTkFrame(self.content, height=1, fg_color="#2a2a2a",
                     corner_radius=0).pack(fill="x", pady=(0, 14))

        # ── Sélecteur de langue ───────────────────────────────────────────
        lang_row = ctk.CTkFrame(self.content, fg_color="transparent")
        lang_row.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            lang_row, text=I18n.t("settings_lang_label"),
            font=("Segoe UI", 12), text_color="#888", width=58, anchor="w"
        ).pack(side="left")

        # ── 5 boutons drapeau + code (remplace CTkSegmentedButton) ───────────
        # Chaque bouton : drapeau 28×20 au-dessus du code 2 lettres (compound="top")
        # Sélection : fond bleu sur le bouton actif, transparent sur les autres
        self._lang_codes    = I18n.available()
        self._selected_lang = I18n.lang()
        self._lang_buttons  = {}

        # Conteneur commun — fond légèrement visible, coins arrondis globaux
        lang_frame = ctk.CTkFrame(lang_row, fg_color="#252525", corner_radius=6)
        lang_frame.pack(side="left")

        for i, code in enumerate(self._lang_codes):
            flag_img = _load_flag(code)   # CTkImage 28×20 ou None si fichier absent
            is_first = (i == 0)
            is_last  = (i == len(self._lang_codes) - 1)
            # Coins arrondis sur les extrémités du groupe, plats au milieu
            cr = 6 if (is_first or is_last) else 0
            btn = ctk.CTkButton(
                lang_frame,
                image=flag_img,
                text=I18n.code_label(code),
                compound="top",             # drapeau au-dessus du code "FR"/"EN"/…
                width=54, height=46,
                fg_color=COLOR_BLUE if code == self._selected_lang else "transparent",
                hover_color="#2a6ad0",
                text_color="#ddd",
                corner_radius=cr,
                font=("Segoe UI", 10, "bold"),
                command=lambda c=code: self._select_lang(c),
            )
            btn.pack(side="left", padx=0)
            self._lang_buttons[code] = btn

        # ── Sélecteur de devise ───────────────────────────────────────────
        cur_row = ctk.CTkFrame(self.content, fg_color="transparent")
        cur_row.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(
            cur_row, text=I18n.t("settings_currency_label"),
            font=("Segoe UI", 12), text_color="#888", width=58, anchor="w"
        ).pack(side="left")

        cur_btns = ctk.CTkFrame(cur_row, fg_color="transparent")
        cur_btns.pack(side="left")

        cur = I18n.currency()
        self._cur_var = cur if cur in ("€", "$") else ""

        self._btn_eur = ctk.CTkButton(
            cur_btns, text="€", width=38, height=32,
            font=("Segoe UI", 14, "bold"),
            fg_color=COLOR_BLUE if cur == "€" else "#252525",
            hover_color="#2a6ad0", text_color="#fff", corner_radius=6,
            command=lambda: self._select_currency("€")
        )
        self._btn_eur.pack(side="left", padx=(0, 4))

        self._btn_usd = ctk.CTkButton(
            cur_btns, text="$", width=38, height=32,
            font=("Segoe UI", 14, "bold"),
            fg_color=COLOR_BLUE if cur == "$" else "#252525",
            hover_color="#2a6ad0", text_color="#fff", corner_radius=6,
            command=lambda: self._select_currency("$")
        )
        self._btn_usd.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(
            cur_btns, text=I18n.t("settings_currency_other"),
            font=("Segoe UI", 11), text_color="#666"
        ).pack(side="left", padx=(0, 5))

        # validate="key" + validatecommand bloque toute saisie au-delà de 3 caractères
        # %P = valeur APRÈS l'édition proposée (chaîne résultante, pas le caractère seul)
        vcmd = (self.register(lambda P: len(P) <= 3), "%P")
        self._cur_entry = ctk.CTkEntry(
            cur_btns, width=54, height=32,
            font=("Segoe UI", 13), placeholder_text="CHF",
            validate="key", validatecommand=vcmd
        )
        if cur not in ("€", "$"):
            self._cur_entry.insert(0, cur)
        self._cur_entry.pack(side="left")
        self._cur_entry.bind("<FocusIn>", self._on_custom_currency_focus)

        # ── Bouton Sauvegarder & Relancer ─────────────────────────────────
        ctk.CTkButton(
            self.content, text=I18n.t("settings_save"),
            command=self.save_and_restart,
            fg_color=COLOR_BLUE, height=38,
            font=("Segoe UI", 13, "bold")
        ).pack(fill="x")

        self.after(50, self._auto_fit)

    def _auto_fit(self):
        """Ajuste la hauteur de la fenêtre à son contenu réel et recentre."""
        self.update_idletasks()
        h  = self.winfo_reqheight() + 4
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = max(0, (sw - 460) // 2)
        y  = max(0, (sh - h)  // 2)
        self.geometry(f"460x{h}+{x}+{y}")

    def _select_currency(self, symbol):
        """Sélectionne € ou $ et vide le champ personnalisé."""
        self._cur_var = symbol
        self._btn_eur.configure(fg_color=COLOR_BLUE if symbol == "€" else "#252525")
        self._btn_usd.configure(fg_color=COLOR_BLUE if symbol == "$" else "#252525")
        self._cur_entry.delete(0, "end")

    def _on_custom_currency_focus(self, _=None):
        """Désélectionne € et $ quand l'utilisateur clique dans le champ personnalisé."""
        self._cur_var = ""
        self._btn_eur.configure(fg_color="#252525")
        self._btn_usd.configure(fg_color="#252525")

    def _get_currency(self):
        """Retourne la devise sélectionnée (entrée libre prioritaire sur boutons)."""
        custom = self._cur_entry.get().strip()[:3]
        return custom if custom else (self._cur_var or "€")

    def _select_lang(self, code: str):
        """Met à jour la sélection visuelle des boutons drapeaux."""
        self._selected_lang = code
        for c, btn in self._lang_buttons.items():
            btn.configure(fg_color=COLOR_BLUE if c == code else "transparent")

    def _get_language(self) -> str:
        """Retourne le code langue du bouton actuellement sélectionné."""
        return self._selected_lang

    def _open_guide(self):
        """Ouvre le guide d'installation au chapitre Extension navigateur."""
        lang = self._get_language()
        anchor = "#fr-7" if lang == "fr" else "#en-7"
        guide = os.path.join(_HERE, "guide_installation", "01-INSTALLATION.html")
        if os.path.exists(guide):
            webbrowser.open(f"file:///{guide.replace(os.sep, '/')}{anchor}")
        else:
            webbrowser.open("https://claude.ai")

    def save_and_restart(self):
        """Sauvegarde la config (clé, langue, devise) et relance l'application."""
        new_key  = self.key_entry.get().strip()
        new_lang = self._get_language()
        new_cur  = self._get_currency()
        if new_key:
            ConfigManager.save(new_key, language=new_lang, currency=new_cur)
        else:
            ConfigManager.save_locale(language=new_lang, currency=new_cur)
        self._parent_app._restart_app()


# ── FENÊTRE À PROPOS ─────────────────────────────────────────────────────────

class InfoDialog(_BaseDialog):
    """Fenêtre 'À propos' : version, date, auteur avec lien cliquable."""
    _AUTHOR_URL = "https://www.skool.com/@laurent-gerard-1911?g=ia-mastery"

    def __init__(self, parent):
        super().__init__(parent, I18n.t("info_title"), 340, 305)

        # Ligne logo + nom de l'app
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

        # Tableau : Version / Date / Auteur
        tbl = ctk.CTkFrame(self.content, fg_color="#212121", corner_radius=8)
        tbl.pack(fill="x", pady=(0, 14))

        for i, (label, value) in enumerate([(I18n.t("info_version"), APP_VERSION),
                                            (I18n.t("info_date"),    APP_DATE)]):
            row = ctk.CTkFrame(tbl, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=(8 if i == 0 else 4, 4))
            ctk.CTkLabel(row, text=label, width=70,
                         font=("Segoe UI", 11), text_color="#666", anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=value,
                         font=("Segoe UI", 11, "bold"), text_color="#ddd", anchor="w").pack(side="left")

        # Ligne auteur avec lien externe
        author_row = ctk.CTkFrame(tbl, fg_color="transparent")
        author_row.pack(fill="x", padx=14, pady=(4, 8))
        ctk.CTkLabel(author_row, text=I18n.t("info_author"), width=70,
                     font=("Segoe UI", 11), text_color="#666", anchor="w").pack(side="left")
        ctk.CTkButton(
            author_row, text=f"↗  {APP_AUTHOR}",
            font=("Segoe UI", 11), text_color=COLOR_BLUE,
            fg_color="transparent", hover_color="#1a2030",
            anchor="w", height=22, corner_radius=4,
            command=lambda: webbrowser.open(self._AUTHOR_URL)
        ).pack(side="left")

        ctk.CTkButton(
            self.content, text=I18n.t("info_close"), command=self.destroy,
            fg_color=COLOR_BLUE, height=34,
            font=("Segoe UI", 12, "bold")
        ).pack(fill="x")

        # Fermeture au clic n'importe où (délai pour ne pas capturer le clic d'ouverture)
        self.after(150, self._bind_close_on_click)

    def _bind_close_on_click(self):
        """Lie la fermeture à tout clic sur n'importe quel widget de la fenêtre."""
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


# ── RECEIVER HTTP (extension navigateur → app) ───────────────────────────────
# Serveur HTTP minimal écoutant sur localhost:27182.
# L'extension "Claude Session Helper" y envoie la sessionKey dès qu'elle la lit.
# Routes :
#   GET  /ping         → {"status":"ready"}   heartbeat pour détecter que l'app tourne
#   POST /session-key  → {"session_key":"..."} reçoit et applique la nouvelle clé
#   OPTIONS            → réponse CORS (requise par certains navigateurs)

RECEIVER_PORT = 27182


class _SessionKeyHandler(BaseHTTPRequestHandler):
    """Handler HTTP minimaliste pour recevoir la sessionKey de l'extension."""
    app_ref = None  # référence à l'instance ClaudeMonitorApp (injectée au démarrage)

    def do_GET(self):
        if self.path == '/ping':
            # L'extension poll ce endpoint toutes les 10s pour savoir si l'app est active
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
            try:
                length = int(self.headers.get('Content-Length', 0))
                body   = json.loads(self.rfile.read(length))
            except (ValueError, json.JSONDecodeError, OSError):
                self.send_response(400)
                self.end_headers()
                return
            new_key = body.get('session_key', '').strip()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            app = _SessionKeyHandler.app_ref
            if new_key and app and new_key != app.session_key:
                # Nouvelle clé reçue → notifier l'app dans le thread UI (after)
                self.wfile.write(b'{"status":"updated"}')
                app.after(0, lambda k=new_key: app._on_new_session_key(k))
            else:
                # Clé identique à celle déjà en mémoire → rien à faire
                self.wfile.write(b'{"status":"unchanged"}')
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        # Réponse pre-flight CORS pour les requêtes cross-origin du navigateur
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin',  '*')
        self.send_header('Access-Control-Allow-Methods', 'POST')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def log_message(self, *args):
        pass  # silence total des logs HTTP dans la console


def _start_receiver(app):
    """Démarre le serveur HTTP dans un thread daemon.
    Si le port est déjà occupé (instance précédente), on ignore silencieusement."""
    _SessionKeyHandler.app_ref = app
    try:
        server = HTTPServer(('127.0.0.1', RECEIVER_PORT), _SessionKeyHandler)
        server.serve_forever()
    except OSError:
        pass


# ── APPLICATION PRINCIPALE ───────────────────────────────────────────────────

class ClaudeMonitorApp(ctk.CTk):
    """Fenêtre principale de Claude-Win-Monitor.

    Responsabilités :
      - Afficher les 3 cartes de statistiques (session 5h, hebdo, budget)
      - Gérer le cycle de rafraîchissement automatique (toutes les 5 min)
      - Recevoir la sessionKey de l'extension via le serveur HTTP local
      - Gérer l'icône dans le system tray Windows
    """

    def __init__(self):
        super().__init__()

        # ── CONFIGURATION FENÊTRE ─────────────────────────────────────────────────
        # Fenêtre sans barre de titre Windows native — on gère tout custom
        # (permet le drag, les coins arrondis Windows 11, et un layout compact)
        self.overrideredirect(True)
        self.resizable(False, False)
        self.configure(fg_color="#484848")  # 1px visible comme bordure extérieure

        # ── DIMENSIONNEMENT FIXE 380×592 ──────────────────────────────────────────
        # Après tests exhaustifs, la hauteur fixe 592px est requise pour que le contenu
        # (titlebar 36 + header ~80 + cards ~320 + bottom 56 + paddings) tienne juste.
        # Dimensionnement DYNAMIQUE via winfo_reqheight() n'a pas fonctionné sur CTkTk
        # car le root frame avec expand=True retourne la taille allouée, pas le minimum
        # du contenu. Solution finale : taille fixe + pack() sans expand.
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        x, y = max(0, (sw - 380) // 2), max(0, (sh - 592) // 2)
        self.geometry(f"380x592+{x}+{y}")

        # État de la fenêtre
        self._topmost = False      # mode "toujours au premier plan"
        self._drag_x = self._drag_y = 0
        self._tray            = None   # instance pystray (system tray)
        self._settings_dialog = None   # référence pour fermeture automatique

        # Chargement de la configuration sauvegardée
        self.config      = ConfigManager.load()
        self.session_key = self.config.get("session_key", "")
        self.org_id      = self.config.get("org_id", "")

        # Chargement des traductions (langue + devise depuis la config)
        I18n.load(
            TRANSLATIONS_FILE,
            lang     = self.config.get("language", "fr"),
            currency = self.config.get("currency", "€")
        )

        # Session HTTP avec impersonation Chrome (contourne les vérifications User-Agent)
        self.session    = requests.Session(impersonate="chrome120")
        self.is_running      = True   # flag pour arrêter la boucle de refresh proprement
        self._session_expired = False  # True si 403 reçu → stoppe la boucle

        self._set_window_icon()
        self._preload_icons()
        self.create_ui()
        self._setup_tray()
        self.after(200, self._apply_rounded_corners)

        # Démarrage du receiver HTTP en arrière-plan (écoute l'extension navigateur)
        threading.Thread(target=_start_receiver, args=(self,), daemon=True).start()

        if not self.session_key:
            # Pas de clé en config → ouvrir les paramètres pour guider l'utilisateur
            self.after(500, self.open_settings)
        else:
            # Clé disponible → configurer la session et lancer la récupération des données
            self.setup_session()
            threading.Thread(target=self.init_sequence, daemon=True).start()

    # ── HELPERS FENÊTRE ──────────────────────────────────────────────────────

    def _set_window_icon(self):
        """Applique l'icône .ico à la fenêtre (visible dans Alt+Tab)."""
        for fname in (
            os.path.join(_HERE, "Claude-Win-Monitor.ico"),
            os.path.join(_HERE, "work", "Claude-Win-Monitor_ICO.ico"),
            os.path.join(_HERE, "work", "icon3.ico"),
        ):
            if os.path.exists(fname):
                try:
                    self.wm_iconbitmap(fname)
                    return
                except Exception:
                    pass

    def _center_window(self):
        """Centre la fenêtre à l'écran (taille fixe 380×592).

        OBSOLÈTE depuis v1.8.4 — la géométrie est maintenant définie dans __init__
        et ne change plus après. Cette méthode reste si recentrage futur est nécessaire.

        Résolution de bugs précédents :
        - Avant : tentatives de _fit_and_center() avec calculs dynamiques de hauteur.
        - Problem: winfo_reqheight() sur CTkTk retournait la taille allouée, pas le min.
        - Solution : taille fixe 380×592 (valeur confirmée par le user).
        """
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = max(0, (sw - 380) // 2)
        y  = max(0, (sh - 592) // 2)
        self.geometry(f"380x592+{x}+{y}")

    def _apply_rounded_corners(self):
        _apply_rounded_corners_to(self)

    def _load_logo(self, size=(52, 52)):
        """Charge le logo de l'app en CTkImage. Retourne None si aucun fichier trouvé."""
        for fname in (
            os.path.join(_HERE, "Claude-Win-Monitor_ICO.png"),
            os.path.join(_HERE, "work", "icon3.png"),
        ):
            try:
                return ctk.CTkImage(Image.open(fname), size=size)
            except Exception:
                pass
        return None

    def _preload_icons(self):
        """Charge et teinte les icônes PNG utilisées dans les boutons et titres de cartes."""
        b = _HERE
        self._icon_refresh      = _load_icon(os.path.join(b, "IMG-refresh.png"),      "#f59e0b", (22, 22))
        self._icon_engrenage    = _load_icon(os.path.join(b, "IMG-engrenage.png"),    "#888888", (22, 22))
        self._icon_poweroff     = _load_icon(os.path.join(b, "IMG-power-off.png"),    COLOR_CRIT, (22, 22))
        self._icon_info         = _load_icon(os.path.join(b, "IMG-information.png"),  COLOR_BLUE, (20, 20))
        self._icon_session      = _load_icon(os.path.join(b, "IMG-session.png"),      "#cccccc", (18, 18))
        self._icon_hebdo        = _load_icon(os.path.join(b, "IMG-hebdomadaire.png"), "#cccccc", (18, 18))
        self._icon_portefeuille = _load_icon(os.path.join(b, "IMG-portefeuille.png"), "#cccccc", (18, 18))

    # ── GESTION DE LA SESSION KEY ─────────────────────────────────────────────

    def _on_new_session_key(self, session_key):
        """Appelé par le receiver HTTP quand l'extension envoie une nouvelle clé.
        Ferme la fenêtre Paramètres si elle est ouverte, puis recharge l'app."""
        ConfigManager.save(session_key)
        if self._settings_dialog is not None:
            try:
                self._settings_dialog.destroy()
            except Exception:
                pass
            self._settings_dialog = None
        self._session_expired = False
        self.reload_app()

    def reload_app(self):
        """Recharge la config depuis le disque et relance la séquence d'initialisation."""
        self._session_expired = False
        self.config      = ConfigManager.load()
        self.session_key = self.config.get("session_key", "")
        self.setup_session()
        self.update_status(I18n.t("status_restarting"), "gray")
        threading.Thread(target=self.init_sequence, daemon=True).start()

    def setup_session(self):
        """Met à jour les headers HTTP de la session avec la sessionKey courante."""
        self.session.headers.update({
            "Cookie":       f"sessionKey={self.session_key}",
            "Origin":       "https://claude.ai",
            "Referer":      "https://claude.ai/chats",
            "Content-Type": "application/json"
        })

    # ── DRAG ─────────────────────────────────────────────────────────────────

    def _start_drag(self, event):
        """Mémorise la position de début de drag."""
        self._drag_x = event.x_root - self.winfo_x()
        self._drag_y = event.y_root - self.winfo_y()

    def _do_drag(self, event):
        """Déplace la fenêtre pendant le drag."""
        self.geometry(f"+{event.x_root - self._drag_x}+{event.y_root - self._drag_y}")

    # ── SYSTEM TRAY ───────────────────────────────────────────────────────────

    def _setup_tray(self):
        """Crée l'icône dans la zone de notification Windows (system tray).
        Menu : Afficher / Actualiser / Quitter."""
        if not _HAVE_TRAY:
            return
        try:
            img = Image.open(os.path.join(_HERE, "Claude-Win-Monitor_ICO.png")).resize((64, 64))
        except Exception:
            img = Image.new("RGB", (64, 64), "#3b82f6")  # fallback carré bleu

        menu = pystray.Menu(
            pystray.MenuItem(I18n.t("tray_show"),    self._show_window,   default=True),
            pystray.MenuItem(I18n.t("tray_refresh"), self._tray_refresh),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(I18n.t("tray_quit"),    self._quit_from_tray)
        )
        self._tray = pystray.Icon("claude_monitor", img, "Claude Usage Monitor", menu)
        threading.Thread(target=self._tray.run, daemon=True).start()

    def _hide_to_tray(self):
        """Masque la fenêtre (elle reste active en tray)."""
        self.withdraw()

    def _bring_to_front(self):
        """Force la fenêtre au premier plan, quelle que soit son état."""
        self.deiconify()
        self.wm_attributes("-topmost", True)   # élève momentanément
        self.lift()
        self.focus_force()
        if not self._topmost:
            self.after(100, lambda: self.wm_attributes("-topmost", False))

    def _show_window(self, *_):
        """Restaure la fenêtre depuis le tray et la place au premier plan."""
        self.after(0, self._bring_to_front)

    def _tray_refresh(self, *_):
        """Déclenche un rafraîchissement et ramène la fenêtre au premier plan."""
        self.after(0, self._bring_to_front)
        threading.Thread(target=self.fetch_data, daemon=True).start()

    def _quit_from_tray(self, *_):
        """Quitte l'app proprement depuis le menu tray."""
        self.is_running = False
        if self._tray:
            self._tray.stop()
        self.after(0, self.destroy)

    def _restart_app(self):
        """Ferme et relance l'application (changement de langue ou de devise)."""
        self.is_running = False
        if self._tray:
            try:
                self._tray.stop()
            except Exception:
                pass
        exe  = sys.executable
        args = [exe] if getattr(sys, "frozen", False) else [exe] + sys.argv
        import subprocess
        subprocess.Popen(args)
        self.after(100, lambda: sys.exit(0))

    # ── ÉPINGLE (TOUJOURS AU PREMIER PLAN) ────────────────────────────────────

    def _toggle_topmost(self):
        """Bascule le mode 'toujours au premier plan'. Icône bleue si actif."""
        self._topmost = not self._topmost
        self.wm_attributes("-topmost", self._topmost)
        self._pin_btn.configure(text_color=COLOR_BLUE if self._topmost else "#505050")

    # ── CONSTRUCTION DE L'INTERFACE ───────────────────────────────────────────

    def _build_titlebar(self, parent):
        """Construit la barre de titre custom : logo, titre, pin, minimiser, fermer."""
        tb = ctk.CTkFrame(parent, height=36, fg_color=COLOR_TITLEBAR, corner_radius=0)
        tb.pack(fill="x")
        tb.pack_propagate(False)
        for widget in (tb,):
            widget.bind("<ButtonPress-1>", self._start_drag)
            widget.bind("<B1-Motion>",     self._do_drag)

        # Gauche : logo miniature + titre
        left = ctk.CTkFrame(tb, fg_color="transparent")
        left.pack(side="left", padx=10, fill="y")

        logo_small = self._load_logo(size=(20, 20))
        if logo_small:
            lbl = ctk.CTkLabel(left, image=logo_small, text="")
            lbl.image = logo_small
            lbl.pack(side="left", padx=(0, 7), pady=8)
            lbl.bind("<ButtonPress-1>", self._start_drag)
            lbl.bind("<B1-Motion>",     self._do_drag)

        title = ctk.CTkLabel(
            left, text="🅻🅶 :  Claude Usage Monitor",
            font=("Segoe UI", 11), text_color="#666"
        )
        title.pack(side="left", pady=8)
        title.bind("<ButtonPress-1>", self._start_drag)
        title.bind("<B1-Motion>",     self._do_drag)

        # Droite : boutons pin / réduire / fermer
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

        # ✕ minimise vers le tray (ne quitte pas l'app)
        ctk.CTkButton(
            btns, text="✕", width=28, height=28,
            fg_color="transparent", hover_color="#4a1010",
            text_color=COLOR_CRIT, command=self._hide_to_tray,
            corner_radius=6, font=("Segoe UI", 12, "bold")
        ).pack(side="left", padx=2, pady=4)

    def create_ui(self):
        """Construit l'intégralité de l'UI : titlebar, header, cartes, barre du bas.

        ── LAYOUT ARCHITECTURE ──────────────────────────────────────────────────────
        Pack order (top → bottom, pas de side="bottom") :

        1. titlebar (height=36, pack_propagate=False)
        2. separator (height=1)
        3. header (logo + user info + status badge + refresh btn)
        4. separator
        5. cards (3 cartes : Session / Hebdomadaire / Budget)
        6. bottom bar (height=56, pack_propagate=False, grid layout pour boutons)

        IMPORTANT : root.pack(fill="x") SAN expand=True pour éviter les gaps.
        Avant cette correction, bottom.pack(side="bottom") créait un espace vide
        entre les cartes et les boutons car root avait expand=True et était plus grand
        que le contenu réel. La solution : ordre naturel pack (top→bottom) sans side="bottom".
        """
        # Fond principal avec 1px de gap → bordure visible partout (gris #484848)
        root = ctk.CTkFrame(self, fg_color=COLOR_BG, corner_radius=0)
        root.pack(fill="x", padx=1, pady=1)  # fill="x" SEULEMENT, pas expand=True
        self._root_frame = root

        self._build_titlebar(root)

        # Ligne de séparation titlebar / contenu
        ctk.CTkFrame(root, height=1, fg_color="#1e1e1e", corner_radius=0).pack(fill="x")

        # Header : logo 52px + nom utilisateur + email + badge de statut + boutons
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
            # Fallback : cercle bleu avec la lettre C
            cv = tk.Canvas(left, width=52, height=52, bg=COLOR_BG, highlightthickness=0)
            cv.create_oval(2, 2, 50, 50, fill=COLOR_BLUE, outline="")
            cv.create_text(26, 26, text="C", fill="white", font=("Segoe UI", 22, "bold"))
            cv.pack(side="left", padx=(0, 14))

        info = ctk.CTkFrame(left, fg_color="transparent")
        info.pack(side="left")

        # Nom de l'utilisateur (mis à jour après /bootstrap)
        self.user_lbl = ctk.CTkLabel(
            info, text="Claude Usage",
            font=("Segoe UI", 16, "bold"), anchor="w"
        )
        self.user_lbl.pack(anchor="w")

        # Email (mis à jour après /bootstrap)
        self.email_lbl = ctk.CTkLabel(
            info, text="", font=("Segoe UI", 10), text_color="#555", anchor="w"
        )
        self.email_lbl.pack(anchor="w")

        # Badge de statut (Connexion / Opérationnel / Erreur...)
        self.status_frame = ctk.CTkFrame(info, fg_color=COLOR_SAFE_BG, corner_radius=20)
        self.status_frame.pack(anchor="w", pady=(4, 0))
        self.status_lbl = ctk.CTkLabel(
            self.status_frame, text=I18n.t("status_connecting"),
            font=("Segoe UI", 10, "bold"), text_color=COLOR_SAFE
        )
        self.status_lbl.pack(padx=10, pady=3)

        # Colonne droite : bouton Refresh + bouton Info
        right_col = ctk.CTkFrame(header, fg_color="transparent")
        right_col.pack(side="right", anchor="n")

        btn_refresh = ctk.CTkButton(
            right_col,
            image=self._icon_refresh, text="" if self._icon_refresh else "↻",
            width=56, height=56,
            command=self.manual_refresh,
            fg_color="#242424", hover_color="#303020",
            text_color="#f59e0b",
            corner_radius=10, font=("Segoe UI", 20, "bold")
        )
        btn_refresh.pack()
        Tooltip(btn_refresh, I18n.t("tooltip_refresh_btn"))

        # Séparateur header / cartes
        ctk.CTkFrame(root, height=1, fg_color="#242424").pack(fill="x", pady=(14, 0))

        # Zone des 3 cartes (tk.Frame natif pour une gestion de hauteur fiable)
        cards = tk.Frame(root, bg=COLOR_BG)
        cards.pack(fill="x", padx=14, pady=(12, 6))
        self._cards_frame = cards

        self.card_session = self._make_card(cards, I18n.t("card_session_title"), I18n.t("tooltip_session"), icon=self._icon_session)
        self.card_weekly  = self._make_card(cards, I18n.t("card_weekly_title"),  I18n.t("tooltip_weekly"),  icon=self._icon_hebdo)
        self.card_billing = self._make_card(cards, I18n.t("card_budget_title"),  I18n.t("tooltip_budget"),  icon=self._icon_portefeuille)

        # ── BARRE DU BAS (3 boutons + séparateurs) ────────────────────────────────
        # Packée EN DERNIER pour éviter les gaps liés à side="bottom".
        # IMPORTANT : height=56 est FIXE via pack_propagate(False).
        # Le grid layout avec weight=1 sur les colonnes (0,2,4) rend les boutons
        # équilargeur (uniform="btn"), pas les hauteurs.
        bottom = ctk.CTkFrame(root, fg_color="#181818", corner_radius=0, height=56)
        bottom.pack(fill="x")  # pas side="bottom", ordre naturel top→bottom
        bottom.pack_propagate(False)  # VERROUILLE la hauteur à 56px exactement
        bottom.grid_columnconfigure((0, 2, 4), weight=1, uniform="btn")  # 3 boutons largeur égale
        bottom.grid_rowconfigure(0, weight=1)  # une seule ligne de boutons

        btn_settings = ctk.CTkButton(
            bottom,
            image=self._icon_engrenage, text="" if self._icon_engrenage else "⚙",
            command=self.open_settings,
            fg_color="transparent", hover_color="#252525",
            text_color="#888", font=("Segoe UI", 22), corner_radius=0
        )
        btn_settings.grid(row=0, column=0, sticky="nsew")
        Tooltip(btn_settings, I18n.t("tooltip_settings"))

        ctk.CTkFrame(bottom, width=1, fg_color="#2a2a2a").grid(
            row=0, column=1, sticky="ns", pady=10
        )

        btn_info_bar = ctk.CTkButton(
            bottom,
            image=self._icon_info, text="" if self._icon_info else "i",
            command=self._show_info,
            fg_color="transparent", hover_color="#1a2540",
            text_color=COLOR_BLUE, font=("Segoe UI", 18, "bold"), corner_radius=0
        )
        btn_info_bar.grid(row=0, column=2, sticky="nsew")
        Tooltip(btn_info_bar, I18n.t("tooltip_about"))

        ctk.CTkFrame(bottom, width=1, fg_color="#2a2a2a").grid(
            row=0, column=3, sticky="ns", pady=10
        )

        btn_quit = ctk.CTkButton(
            bottom,
            image=self._icon_poweroff, text="" if self._icon_poweroff else "⏻",
            command=self.quit_app,
            fg_color="transparent", hover_color="#2a0e0e",
            text_color=COLOR_CRIT, font=("Segoe UI", 22), corner_radius=0
        )
        btn_quit.grid(row=0, column=4, sticky="nsew")
        Tooltip(btn_quit, I18n.t("tooltip_quit"))

    def _make_card(self, parent, title, tooltip_text, icon=None):
        """Crée une carte statistique réutilisable pour afficher un quota (Session/Hebdo/Budget).

        Structure interne d'une carte :
        ┌─────────────────────────────────────────────────────────┐
        │ 🎨 ICON  Titre en gras                           NN%     │  ← row (flex)
        │━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
        │ [██████████░░░░░░░░] progression bar (10px)             │
        │━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
        │ Texte gauche (reset/conso)    Texte droite (date/solde) │  ← footer 2-col
        └─────────────────────────────────────────────────────────┘

        v1.8.4+ : suppressions des SOUS-TITRES (= -~50px de hauteur par carte).
        v1.8.4+ : FOOTER en 2 colonnes (left/right) au lieu de 1 ligne centrado.

        Args:
            parent: tk.Frame parent (cards zone)
            title: str — "Session en cours" / "Hebdomadaire" / "Budget mensuel"
            tooltip_text: str — infobulle au survol (icon + titre)
            icon: CTkImage | None — icône 18×18 PNG tintée

        Returns:
            dict {
                "card": CTkFrame — le container principal (mutable fg_color selon usage %)
                "p": CTkLabel — le % en gros (24px bold, text_color dynamique)
                "bar": CTkProgressBar — barre progress (height=10, corner=5)
                "reset_left": CTkLabel — texte bas-gauche (reset/conso)
                "reset_right": CTkLabel — texte bas-droite (date/solde)
            }
        """
        wrapper = tk.Frame(parent, bg=COLOR_BG)
        wrapper.pack(fill="x", pady=(0, 10))

        card = ctk.CTkFrame(
            wrapper, fg_color=COLOR_CARD, corner_radius=14,
            border_width=1, border_color="#272727"
        )
        card.pack(fill="x")

        # Zone titre : icon + titre (gauche) + % (droite)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=(14, 0))

        row = ctk.CTkFrame(inner, fg_color="transparent")
        row.pack(fill="x")

        # Icon optionnel (18×18, couleur grise #cccccc)
        if icon:
            icon_lbl = ctk.CTkLabel(row, image=icon, text="")
            icon_lbl.image = icon  # IMPORTANT : retenir ref pour éviter GC
            icon_lbl.pack(side="left", padx=(0, 8))
            Tooltip(icon_lbl, tooltip_text)

        # Titre bold 14px (anchored west pour alignement gauche)
        title_lbl = ctk.CTkLabel(
            row, text=title, font=("Segoe UI", 14, "bold"), anchor="w"
        )
        title_lbl.pack(side="left")
        Tooltip(title_lbl, tooltip_text)

        # Pourcentage en gros (24px bold, couleur dynamique : green/orange/red)
        pct_zone = ctk.CTkFrame(row, fg_color="transparent")
        pct_zone.pack(side="right")

        pct_lbl = ctk.CTkLabel(
            pct_zone, text="--%",
            font=("Segoe UI", 24, "bold"), text_color=COLOR_SAFE
        )
        pct_lbl.pack(side="left")

        # Barre de progression (height=10px, corner=5 pour arrondi)
        bar = ctk.CTkProgressBar(
            card, height=10, corner_radius=5,
            progress_color=COLOR_SAFE, fg_color="#2e2e2e"
        )
        bar.set(0.004)  # ~0.4% initialement (affiche quelque chose plutôt qu'une barre vide)
        bar.pack(fill="x", padx=16, pady=(8, 0))

        # ── FOOTER : 2 colonnes (LEFT + RIGHT) ────────────────────────────────────
        # Ligne 4: contient des textes contextuels petits (11px, gris #686868)
        # LEFT : "Réinitialisation dans Xh Ym" (Session/Hebdo) ou "Conso : X.XX / Y.YY €" (Budget)
        # RIGHT : "jeudi 20 mars à 15h" (Session/Hebdo) ou "Solde : XX.XX €" (Budget)
        footer = ctk.CTkFrame(card, fg_color="transparent")
        footer.pack(fill="x", padx=16, pady=(4, 12))

        reset_left = ctk.CTkLabel(
            footer, text="", font=("Segoe UI", 11), text_color="#686868", anchor="w"
        )
        reset_left.pack(side="left")

        reset_right = ctk.CTkLabel(
            footer, text="", font=("Segoe UI", 11), text_color="#686868", anchor="e"
        )
        reset_right.pack(side="right")

        return {"card": card, "p": pct_lbl, "bar": bar,
                "reset_left": reset_left, "reset_right": reset_right}

    # ── LOGIQUE MÉTIER ────────────────────────────────────────────────────────

    def open_settings(self):
        """Ouvre la fenêtre Paramètres et stocke la référence pour la fermer automatiquement."""
        self._settings_dialog = SettingsDialog(self, self.session_key)

    def _show_info(self):
        InfoDialog(self)

    def init_sequence(self):
        """Séquence d'initialisation (thread) :
        1. Appel /bootstrap pour récupérer le profil et l'org_id
        2. Lance la boucle de rafraîchissement des données."""
        try:
            res = self.session.get(f"{BASE_URL}/bootstrap", timeout=10)
            if res.status_code == 200:
                data    = res.json()
                account = data.get("account", {})
                name    = account.get("full_name",    "Claude Usage")
                email   = account.get("email_address", "")

                # Mise à jour de l'UI dans le thread principal via after()
                self.after(0, lambda: self.user_lbl.configure(text=name))
                self.after(0, lambda: self.email_lbl.configure(text=email))

                # Récupération de l'org_id si absent du cache
                if not self.org_id:
                    memberships = account.get("memberships", [])
                    for m in memberships:
                        org  = m.get("organization", {})
                        caps = org.get("capabilities", [])
                        # Sélectionner l'org Claude Pro (pas l'org API pure)
                        if "claude_pro" in caps or "api" not in caps:
                            self.org_id = org.get("uuid")
                            ConfigManager.save(self.session_key, self.org_id)
                            break

            if self.org_id:
                self.background_loop()
            else:
                self.update_status(I18n.t("status_no_org"), COLOR_CRIT)

        except Exception:
            self.update_status(I18n.t("status_conn_error"), COLOR_CRIT)

    def background_loop(self):
        """Boucle infinie (thread) : fetch_data() puis attente REFRESH_RATE_SECONDS.
        S'arrête proprement quand is_running passe à False ou _session_expired à True."""
        while self.is_running and not self._session_expired:
            self.fetch_data()
            for _ in range(REFRESH_RATE_SECONDS):
                if not self.is_running or self._session_expired:
                    break
                time.sleep(1)

    def manual_refresh(self):
        """Déclenche un rafraîchissement immédiat dans un thread dédié."""
        threading.Thread(target=self.fetch_data, daemon=True).start()

    def fetch_data(self):
        """Appelle les 3 endpoints API en parallèle et met à jour l'UI.
        Gère les erreurs HTTP (403 = session expirée, autres = avertissement)."""
        self.update_status(I18n.t("status_refreshing"), COLOR_WARN)
        try:
            r_usage   = self.session.get(
                f"{BASE_URL}/organizations/{self.org_id}/usage", timeout=10)
            r_limit   = self.session.get(
                f"{BASE_URL}/organizations/{self.org_id}/overage_spend_limit", timeout=10)
            r_prepaid = self.session.get(
                f"{BASE_URL}/organizations/{self.org_id}/prepaid/credits", timeout=10)

            if r_usage.status_code == 200 and r_limit.status_code == 200 and r_prepaid.status_code == 200:
                # Tout OK → mise à jour de l'UI dans le thread principal
                self.after(0, lambda: self.update_ui(
                    r_usage.json(), r_limit.json(), r_prepaid.json()
                ))
            elif r_usage.status_code == 403 or r_limit.status_code == 403 or r_prepaid.status_code == 403:
                # Session expirée → stopper la boucle et ouvrir les Paramètres
                self._session_expired = True
                self.update_status(I18n.t("status_expired"), COLOR_CRIT)
                self.after(0, self.open_settings)
            else:
                self.update_status(I18n.t("status_api_error", code=r_usage.status_code), COLOR_WARN)

        except Exception:
            self.update_status(I18n.t("status_network_error"), COLOR_CRIT)

    def update_ui(self, usage, limits, prepaid):
        """Met à jour les 3 cartes avec les données reçues de l'API.
        usage   : /usage           → five_hour, seven_day
        limits  : /overage_...     → monthly_credit_limit, used_credits
        prepaid : /prepaid/credits → amount (solde prépayé en centimes)"""
        five_hour = usage.get("five_hour", {})
        self._update_bar_card(self.card_session, five_hour,                  include_days=False)
        self._update_bar_card(self.card_weekly,  usage.get("seven_day", {}), include_days=True)

        # Mise à jour du tooltip de l'icône tray avec le % session courant
        if self._tray:
            pct = int(five_hour.get("utilization", 0))
            self._tray.title = f"Claude Monitor  •  Session : {pct}%"

        # Conversion centimes → euros (l'API renvoie des centimes × 10)
        limit_cap    = limits.get("monthly_credit_limit", 500) / 100
        used_month   = limits.get("used_credits",          0)  / 100
        balance_real = prepaid.get("amount",               0)  / 100

        ratio    = used_month / limit_cap if limit_cap > 0 else 0.0
        color    = self._ratio_color(ratio)
        card_bg  = self._ratio_card_bg(ratio)

        card = self.card_billing
        card["card"].configure(fg_color=card_bg)
        card["bar"].set(max(min(ratio, 1.0), 0.004))
        card["bar"].configure(progress_color=color)
        card["p"].configure(text=f"{int(ratio * 100)}%", text_color=color)
        cur = I18n.currency()
        card["reset_left"].configure(
            text=I18n.t("budget_spent",   x=f"{used_month:.2f}",  y=f"{limit_cap:.2f}", cur=cur))
        card["reset_right"].configure(
            text=I18n.t("budget_balance", x=f"{balance_real:.2f}", cur=cur))

        self.update_status(I18n.t("status_ok"), COLOR_SAFE)

    def _update_bar_card(self, card, data, include_days=False):
        """Met à jour une carte session ou hebdo avec les données de l'API.
        data = {"utilization": float, "resets_at": str|None}"""
        val   = data.get("utilization", 0.0)
        reset = data.get("resets_at")

        ratio   = val / 100.0
        color   = self._ratio_color(ratio)
        card_bg = self._ratio_card_bg(ratio)

        card["card"].configure(fg_color=card_bg)
        card["bar"].set(max(min(ratio, 1.0), 0.004))
        card["bar"].configure(progress_color=color)
        card["p"].configure(text=f"{int(val)}%", text_color=color)
        if reset:
            card["reset_left"].configure(
                text=I18n.t("reset_in", t=format_time_remaining(reset, include_days)))
            card["reset_right"].configure(text=format_date_long(reset))
        else:
            card["reset_left"].configure(text=I18n.t("no_limit"))
            card["reset_right"].configure(text="")

    @staticmethod
    def _ratio_color(ratio):
        """Retourne la couleur correspondant au niveau d'alerte du ratio."""
        if ratio > 0.8: return COLOR_CRIT
        if ratio > 0.5: return COLOR_WARN
        return COLOR_SAFE

    @staticmethod
    def _ratio_card_bg(ratio):
        """Retourne la couleur de fond de carte correspondant au niveau d'alerte."""
        if ratio > 0.8: return COLOR_CARD_CRIT
        if ratio > 0.5: return COLOR_CARD_WARN
        return COLOR_CARD

    def update_status(self, text, color):
        """Met à jour le badge de statut (texte + couleur + fond).
        Peut être appelé depuis n'importe quel thread (utilise after() pour le thread UI)."""
        badge_bg = {
            COLOR_SAFE: COLOR_SAFE_BG,
            COLOR_WARN: COLOR_WARN_BG,
            COLOR_CRIT: COLOR_CRIT_BG,
        }.get(color, "#1e1e1e")
        self.after(0, lambda: self.status_lbl.configure(text=text, text_color=color))
        self.after(0, lambda: self.status_frame.configure(fg_color=badge_bg))

    def quit_app(self):
        """Arrêt propre : stop la boucle de refresh, stop le tray, ferme la fenêtre."""
        self.is_running = False
        if self._tray:
            self._tray.stop()
        self.destroy()
        sys.exit()


# ── POINT D'ENTRÉE ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = ClaudeMonitorApp()
    app.mainloop()
