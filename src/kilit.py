# -*- coding: utf-8 -*-
"""
kilit.py — Programin acilis sifresi.

Sifreyi KULLANICI belirler. Diskte sadece PBKDF2 ozeti (hash) tutulur;
sifrenin kendisi hicbir yere yazilmaz, gelistirici de bilemez.
Disariya bagimli bir lisans sunucusu YOKTUR — program internetsiz calisir.
"""
from __future__ import annotations

import hashlib
import hmac
import os

DONGU = 200_000          # PBKDF2 tur sayisi
ALGO = "sha256"


def ozet_uret(sifre: str) -> dict:
    """Sifreden saklanabilir ozet uretir."""
    tuz = os.urandom(16)
    ozet = hashlib.pbkdf2_hmac(ALGO, sifre.encode("utf-8"), tuz, DONGU)
    return {"tuz": tuz.hex(), "ozet": ozet.hex(), "dongu": DONGU, "algo": ALGO}


def dogrula(sifre: str, kayit: dict | None) -> bool:
    """Girilen sifre kayitli ozetle uyuyor mu."""
    if not kayit or "tuz" not in kayit or "ozet" not in kayit:
        return False
    try:
        tuz = bytes.fromhex(kayit["tuz"])
        beklenen = bytes.fromhex(kayit["ozet"])
    except ValueError:
        return False
    hesap = hashlib.pbkdf2_hmac(kayit.get("algo", ALGO), sifre.encode("utf-8"),
                                tuz, int(kayit.get("dongu", DONGU)))
    return hmac.compare_digest(hesap, beklenen)


def kullanici_bul(sifre: str, kullanicilar: dict) -> str | None:
    """Girilen sifre hangi kullaniciya aitse onun adini dondurur.

    Kullanici adi sormaya gerek yok: sifre kimin ise program onu tanir.
    Hicbiri tutmazsa None doner.
    """
    for ad, kayit in (kullanicilar or {}).items():
        if dogrula(sifre, kayit):
            return ad
    return None


def kullanici_olustur(sifre: str, rol: str = "kullanici") -> dict:
    """Yeni kullanici kaydi (sifre ozeti + rol)."""
    kayit = ozet_uret(sifre)
    kayit["rol"] = rol
    return kayit


def yonetici_mi(kullanicilar: dict, ad: str) -> bool:
    return (kullanicilar or {}).get(ad, {}).get("rol") == "yonetici"


def sifre_kurallari(sifre: str) -> str:
    """Kabul edilebilir mi? Uygunsa bos metin, degilse sebep doner."""
    if len(sifre) < 4:
        return "Şifre en az 4 karakter olmalı."
    return ""
