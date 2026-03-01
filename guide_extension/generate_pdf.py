#!/usr/bin/env python3
# ================================================================
# CLAUDE-WIN-MONITOR — Générateur PDF du guide d'installation
# Convertit "Guide d'installation.html" → "Guide d'installation.pdf" (A4)
#
# Auteur  : 🅻🅶 @ IA Mastery
# Date    : 01/03/2026
# ================================================================
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE     = Path(__file__).parent.resolve()
HTML_IN  = HERE / "Guide d'installation.html"
PDF_OUT  = HERE / "Guide d'installation.pdf"

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
