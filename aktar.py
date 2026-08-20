# -*- coding: utf-8 -*-
"""
aktar.py — Programin giris noktasi.

    python aktar.py
"""
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK / "src"))

from arayuz import main   # noqa: E402

if __name__ == "__main__":
    main()
