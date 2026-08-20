# -*- coding: utf-8 -*-
"""
DEMO calistirici — musteriye gonderilecek ciktilari uretir.

Akis: gercek Mayis ekstresini oku -> sahte cocuk listesiyle eslestir ->
HTML rapor + PNG gorsel + Excel cikti uret.
"""
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "src"))

from ekstre import satirlari_oku, ust_bilgi_oku   # noqa: E402
from eslestir import cocuk_listesi_yukle, satirlari_eslestir   # noqa: E402
from rapor import excel_cikti, html_rapor, ozet  # noqa: E402

EKSTRE = KOK / "demo" / "test_ekstre.xlsx"
LISTE = KOK / "demo" / "test_liste.xlsx"
CIKTI = KOK / "cikti"


def png_uret(html_yolu: Path, png_yolu: Path) -> Path | None:
    """HTML raporu tek parca PNG'ye cevirir (Bionluk'tan gonderilebilsin diye)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None

    with sync_playwright() as p:
        tarayici = p.chromium.launch()
        sayfa = tarayici.new_page(viewport={"width": 1280, "height": 1000},
                                  device_scale_factor=2)
        sayfa.goto(html_yolu.as_uri())
        sayfa.wait_for_load_state("networkidle")
        sayfa.screenshot(path=str(png_yolu), full_page=True)
        tarayici.close()
    return png_yolu


def main() -> None:
    satirlar = satirlari_oku(EKSTRE)
    ust = ust_bilgi_oku(EKSTRE)
    cocuklar = cocuk_listesi_yukle(LISTE)
    sonuc = satirlari_eslestir(satirlar, cocuklar)
    o = ozet(sonuc)

    CIKTI.mkdir(exist_ok=True)
    html_yolu = html_rapor(
        sonuc, CIKTI / "demo_rapor.html",
        baslik="Ekstre Okuma ve Öğrenci Eşleştirme Raporu",
        kaynak_dosya=str(EKSTRE), demo_notu=True, ust_bilgi=ust)
    xlsx_yolu = excel_cikti(sonuc, CIKTI / "demo_tefbis_listesi.xlsx")
    png_yolu = png_uret(html_yolu, CIKTI / "demo_rapor.png")

    print(f"Okunan hareket      : {o['toplam']}")
    print(f"Panele girilecek    : {o['kesin']}")
    print(f"Onay bekleyen       : {o['supheli']}")
    print(f"Elenen              : {o['yok']}")
    print(f"  - aciklamadan TC  : {o['tc_aciklamadan']}")
    print(f"  - isimden eslesme : {o['tc_isimden']}")
    print()
    print("HTML :", html_yolu)
    print("Excel:", xlsx_yolu)
    print("PNG  :", png_yolu or "uretilemedi (playwright yok)")


if __name__ == "__main__":
    main()
