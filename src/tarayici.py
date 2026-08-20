# -*- coding: utf-8 -*-
"""
tarayici.py — Chrome'u NORMAL baslatip ona baglanir.

NEDEN VAR:
Playwright tarayiciyi kendisi baslattiginda Chrome "test yazilimi tarafindan
kontrol ediliyor" bilgi cubugunu gosterir ve otomasyon bayraklariyla acilir.
MEB/MEBBIS gibi kamu siteleri bu bayraklari taniyip girisi reddedebiliyor;
musteride tam bu yasandi - sayfa hic acilmadi.

COZUM: Chrome'u kendimiz normal bir surec olarak baslatiyoruz (sadece uzaktan
hata ayiklama portu acik), sonra Playwright'i o surece BAGLIYORUZ. Tarayici
kullanicinin elle actigindan farksiz gorunur; bilgi cubugu cikmaz, site
otomasyon tespit etmez.

Baglanti kurulamazsa cagiran taraf eski yonteme (launch) duser.
"""
from __future__ import annotations

import os
import socket
import subprocess
import time
from pathlib import Path

# Chrome ve Edge'in Windows'ta bulundugu olagan yerler
_ADAYLAR = (
    r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
    r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
    r"%LocalAppData%\Google\Chrome\Application\chrome.exe",
    r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
    r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
)


def tarayici_yolu() -> Path | None:
    """Bilgisayardaki Chrome (yoksa Edge) calistirilabilir dosyasi."""
    for kalip in _ADAYLAR:
        yol = Path(os.path.expandvars(kalip))
        try:
            if yol.is_file():
                return yol
        except OSError:
            continue

    # Kayit defterinden dene (farkli bir dizine kurulmus olabilir)
    try:
        import winreg
        for kok in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for alt in (r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
                        r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe"):
                try:
                    with winreg.OpenKey(kok, alt) as anahtar:
                        yol = Path(winreg.QueryValue(anahtar, None))
                        if yol.is_file():
                            return yol
                except OSError:
                    continue
    except Exception:
        pass
    return None


def _bos_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _port_acildi_mi(port: int, saniye: float = 25.0) -> bool:
    bitis = time.time() + saniye
    while time.time() < bitis:
        with socket.socket() as s:
            s.settimeout(0.4)
            try:
                s.connect(("127.0.0.1", port))
                return True
            except OSError:
                time.sleep(0.25)
    return False


def normal_chrome_baslat(profil_klasoru: str | None = None):
    """Chrome'u normal baslatir. (surec, cdp_adresi) doner; olmazsa (None, None)."""
    calistirilabilir = tarayici_yolu()
    if calistirilabilir is None:
        return None, None

    port = _bos_port()
    komut = [
        str(calistirilabilir),
        f"--remote-debugging-port={port}",
        "--start-maximized",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-popup-blocking",
    ]
    if profil_klasoru:
        # Kendi profil klasoru: cerezler saklanir, kullanicinin kisisel
        # Chrome profili kilitlenmez (o profil acikken baslatilamazdi).
        komut.append(f"--user-data-dir={profil_klasoru}")

    try:
        surec = subprocess.Popen(
            komut, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception:
        return None, None

    if not _port_acildi_mi(port):
        try:
            surec.terminate()
        except Exception:
            pass
        return None, None

    return surec, f"http://127.0.0.1:{port}"
