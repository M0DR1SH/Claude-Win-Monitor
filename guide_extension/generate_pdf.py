#!/usr/bin/env python3
# ================================================================
# CLAUDE-WIN-MONITOR — Générateur PDF du guide d'installation
# Convertit GUIDE-SESSION-KEY.html → GUIDE-SESSION-KEY.pdf (A4)
#
# Auteur  : 🅻🅶 @ IA Mastery
# Date    : 28/02/2026
# ================================================================
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE     = Path(__file__).parent.resolve()
HTML_IN  = HERE / "GUIDE-SESSION-KEY.html"
PDF_OUT  = HERE / "GUIDE-SESSION-KEY.pdf"

print(f"Source  : {HTML_IN}")
print(f"Sortie  : {PDF_OUT}")

with sync_playwright() as p:
    browser = p.chromium.launch()
    page    = browser.new_page()

    # Rendu "screen" pour conserver le thème dark (sinon @media print blanchit)
    page.emulate_media(media="screen")
    page.goto(HTML_IN.as_uri(), wait_until="networkidle")

    page.pdf(
        path=str(PDF_OUT),
        format="A4",
        print_background=True,   # indispensable pour les fonds colorés
        margin={"top": "0mm", "bottom": "0mm", "left": "0mm", "right": "0mm"}
    )

    browser.close()

print("PDF généré avec succès !")
