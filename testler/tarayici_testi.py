# -*- coding: utf-8 -*-
"""
tarayici_testi.py — Chrome'a normal baglanma yolunu dogrular.

Sahada cikan sorun: Playwright tarayiciyi kendi baslattiginda Chrome
"test yazilimi tarafindan kontrol ediliyor" cubugunu gosteriyor ve hedef
kurum paneli girisi reddediyor, sayfa hic acilmiyordu.

Bu testler, tarayicinin normal bir surec olarak baslatilip ona
baglanildigini ve otomasyon izinin gorunmedigini dogrular. Son bolum
panel.py kaynagini okur: her iki yolun da (CDP ve yedek) otomasyon izini
gizledigini dogrular, cunku yedek yol bunu kaybederse sessizce ise yaramaz
hale gelir ve bu ancak gercek panelde fark edilir.

Calistirma:  python testler/tarayici_testi.py
Gorunur bir Chrome penceresi acar (headless degil).
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "src"))

import tarayici                                              # noqa: E402


gecen = kalan = 0


def kontrol(ad, sart, ek=""):
    global gecen, kalan
    if sart:
        gecen += 1
        print(f"  [OK  ] {ad}" + (f"  ({ek})" if ek else ""))
    else:
        kalan += 1
        print(f"  [HATA] {ad}" + (f"  ({ek})" if ek else ""))


def main() -> int:
    print("\n1) Bilgisayardaki tarayici bulunuyor mu")
    yol = tarayici.tarayici_yolu()
    kontrol("Chrome ya da Edge bulundu", yol is not None and yol.is_file(),
            str(yol))
    if yol is None:
        print("\nTarayici bulunamadi, kalan testler atlaniyor.")
        return 1

    profil = Path(tempfile.mkdtemp(prefix="tarayici_test_"))
    surec = None
    pw = None
    try:
        print("\n2) Chrome normal baslatilip baglaniliyor")
        surec, cdp = tarayici.normal_chrome_baslat(str(profil))
        kontrol("chrome baslatildi", surec is not None)
        kontrol("hata ayiklama adresi verildi", bool(cdp), cdp or "")
        if not cdp:
            return 1

        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start()
        tar = pw.chromium.connect_over_cdp(cdp)
        kontrol("playwright baglandi", tar is not None)

        baglam = tar.contexts[0] if tar.contexts else tar.new_context()
        sayfa = baglam.pages[0] if baglam.pages else baglam.new_page()
        kontrol("sayfa alindi", sayfa is not None)

        print("\n3) Otomasyon izi gorunuyor mu (asil mesele)")
        sahte = KOK / "demo" / "sahte_tefbis" / "ana.html"
        sayfa.goto(sahte.as_uri(), wait_until="domcontentloaded")
        kontrol("sayfa acilabildi", "TEFB" in sayfa.title(), sayfa.title())

        webdriver = sayfa.evaluate("() => navigator.webdriver")
        kontrol("navigator.webdriver ISARETLI DEGIL",
                not webdriver, f"deger: {webdriver}")

        print("\n4) Sayfayla etkilesim calisiyor")
        sayfa.fill("#txtEvrakNo", "TEST-1")
        kontrol("alana yazilabildi",
                sayfa.input_value("#txtEvrakNo") == "TEST-1")

        print("\n5) Surucu bu yolu kullaniyor mu")
        kaynak = (KOK / "src" / "panel.py").read_text(encoding="utf-8")
        kontrol("panel.py once CDP deniyor", "connect_over_cdp" in kaynak)
        kontrol("basarisizsa eski yola dusuyor",
                "if self.sayfa is None else ()" in kaynak)
        kontrol("chrome sureci kapatiliyor", "_chrome_kapat" in kaynak)
        kontrol("otomasyon cubugu yedek yolda da kapali",
                "ignore_default_args" in kaynak)

        try:
            tar.close()
        except Exception:
            pass
    finally:
        if pw is not None:
            try:
                pw.stop()
            except Exception:
                pass
        if surec is not None:
            try:
                surec.terminate()
                surec.wait(timeout=5)
            except Exception:
                try:
                    surec.kill()
                except Exception:
                    pass
        shutil.rmtree(profil, ignore_errors=True)

    print("\n" + "=" * 56)
    print(f"GECEN: {gecen}   KALAN: {kalan}")
    print("=" * 56)
    return 1 if kalan else 0


if __name__ == "__main__":
    sys.exit(main())
