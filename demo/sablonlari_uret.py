# -*- coding: utf-8 -*-
"""Ornek sablon dosyalarini uretir (arayuzdeki 1. dugmeyle ayni islevi yapar)."""
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "src"))

import sablon  # noqa: E402

if __name__ == "__main__":
    hedef = Path(__file__).parent
    e = sablon.ekstre_sablonu(hedef / "ekstre_sablonu.xlsx")
    o = sablon.ogrenci_sablonu(hedef / "ogrenci_listesi_sablonu.xlsx")
    print("Uretildi:", e.name, "|", o.name)
