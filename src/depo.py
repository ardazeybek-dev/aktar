# -*- coding: utf-8 -*-
"""
depo.py — Ayarlarin ve ogrenilen eslesmelerin saklandigi yer.

Her sey programin yaninda duran tek bir ayarlar.json dosyasinda tutulur.
Tasinabilirlik icin mutlak yol yazilmaz; dosya programla birlikte tasinir.
Icinde T.C. numarasi TUTULMAZ - sadece kullanicinin onayladigi
"bu aciklama su cocuga aittir" eslesmesi (aciklama ozeti -> TC) tutulur ki
ayni veli her ay tekrar sorulmasin. Bu dosya kullanicinin bilgisayarinda kalir.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

VARSAYILAN = {
    "sifre": None,                  # ESKI surum: tek sifre (goc icin tutuluyor)
    "kullanicilar": {},             # ad -> {tuz, ozet, dongu, algo, rol}
    "cocuk_listesi": "",            # son kullanilan cocuk-TC listesi yolu
    "son_ekstre_klasoru": "",
    "tarif": "",                    # secili panel tarifi (bos = ilk tarif)
    "mod": 0,                       # tarifin sundugu hazir modlardan secim
    "ek_secim": "",                 # tarifin ikinci listesi (or. gelir turu)
    "aciklama_sablonu": "{ay} ayı ödemesi",
    "kayit_arasi_bekleme": 2.0,
    "alan_bekleme": 45.0,          # bir alani ekranda bekleme suresi (sn)
    "giris_yolu": "",               # tarifin giris_adresleri anahtari
    "ogrenilen": {},                # aciklama ozeti -> TC (kullanici onayi)
    "girilenler": {},               # panele girilmis kayitlarin parmak izi
    "son_ekstre": "",               # en son islenen ekstre dosyasi
    "ozel_seciciler": {},           # panel ekrani degisirse elle duzeltme
}


def parmak_izi(tarih, evrak_no, tc, tutar) -> str:
    """Bir kaydi tekil tanimlayan anahtar (mukerrer girisi engellemek icin)."""
    gun = tarih.strftime("%Y%m%d") if hasattr(tarih, "strftime") else str(tarih)
    kurus = "" if tutar is None else str(int(round(abs(float(tutar)) * 100)))
    return f"{gun}|{str(evrak_no).strip()}|{str(tc).strip()}|{kurus}"


def program_klasoru() -> Path:
    """exe olarak paketlendiginde exe'nin yani, kaynak halde proje koku."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def ayar_dosyasi() -> Path:
    return program_klasoru() / "ayarlar.json"


def yukle() -> dict:
    yol = ayar_dosyasi()
    veri = dict(VARSAYILAN)
    if yol.exists():
        try:
            veri.update(json.loads(yol.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass                     # bozuk dosya varsayilanla acilsin
    _tek_sifreden_goc(veri)
    return veri


def _tek_sifreden_goc(veri: dict) -> None:
    """Eski surumde tek sifre vardi; onu 'yonetici' kullanicisina cevirir.

    Boylece programi guncelleyen kullanici sifresini yeniden kurmak zorunda
    kalmaz, ayni sifreyle girmeye devam eder.
    """
    if veri.get("kullanicilar"):
        return
    eski = veri.get("sifre")
    if eski:
        kayit = dict(eski)
        kayit["rol"] = "yonetici"
        veri["kullanicilar"] = {"yönetici": kayit}


def kaydet(veri: dict) -> bool:
    """Ayarlari diske yazar. Yazamazsa program yine calisir, False doner."""
    yol = ayar_dosyasi()
    try:
        yol.write_text(json.dumps(veri, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        return True
    except OSError:
        return False                 # salt okunur ortamda program yine calissin


def yazilabilir_mi() -> bool:
    """Program klasorune yazilabiliyor mu?

    Okul/kurum bilgisayarlarinda program "Program Files" gibi korumali bir
    klasore konursa sifre ve ogrenilen eslesmeler diske yazilamaz; kullanici
    bunu bilmezse her acilista sifresinin kayboldugunu sanir. Bu yuzden
    acilista sessizce denenip uyarilir.
    """
    deneme = program_klasoru() / ".yazma_denemesi"
    try:
        deneme.write_text("x", encoding="utf-8")
        deneme.unlink()
        return True
    except OSError:
        return False
