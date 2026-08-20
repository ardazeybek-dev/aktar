# -*- coding: utf-8 -*-
"""
bozuk_excel_testi.py — Bozuk bicimlendirmeli Excel dosyalarinin okunmasi.

Musteride cikan gercek hata: baska programla uretilmis .xlsx dosyasi
openpyxl ile acilmiyordu:
    Excel dosyasi acilamadi: expected <class 'openpyxl.styles.fills.Fill'>

Bu testler, bozuk stil bloklarinin onarildigini VE onarim sirasinda
tarihlerin/sayilarin bozulmadigini dogrular.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import zipfile
from datetime import date
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "src"))

import openpyxl                                              # noqa: E402
from excel_ac import calisma_kitabi_ac, temizle              # noqa: E402
from ekstre import satirlari_oku                             # noqa: E402
from eslestir import cocuk_listesi_yukle                     # noqa: E402

gecen = kalan = 0


def kontrol(ad, sart):
    global gecen, kalan
    if sart:
        gecen += 1
        print(f"  [OK  ] {ad}")
    else:
        kalan += 1
        print(f"  [HATA] {ad}")


def _stil_bozan(kaynak: Path, hedef: Path, blok: bytes = b"fills") -> Path:
    """Gercek musteri hatasini taklit eder: stil blogunu gecersiz yapar."""
    with zipfile.ZipFile(kaynak) as girdi, \
            zipfile.ZipFile(hedef, "w", zipfile.ZIP_DEFLATED) as cikti:
        for oge in girdi.infolist():
            veri = girdi.read(oge.filename)
            if oge.filename == "xl/styles.xml":
                # openpyxl'in tanimadigi bir oge: Fill bekledigi yerde baska sey
                veri = veri.replace(
                    b"<fills", b'<fills><fill><anlamsizDolgu tip="x"/></fill>', 1)
            cikti.writestr(oge.filename, veri)
    return hedef


def main() -> int:
    calisma = Path(tempfile.mkdtemp(prefix="bozuk_test_"))
    try:
        print("\n1) Saglam dosya normal aciliyor")
        saglam = KOK / "demo" / "ekstre_sablonu.xlsx"
        wb, g = calisma_kitabi_ac(saglam)
        kontrol("saglam dosya acildi", wb.active is not None)
        kontrol("gereksiz gecici kopya uretilmedi", g is None)
        temizle(g)

        print("\n2) Bozuk bicimlendirmeli dosya (musteri hatasi)")
        bozuk = _stil_bozan(saglam, calisma / "bozuk.xlsx")
        patladi = False
        try:
            openpyxl.load_workbook(bozuk, data_only=True, read_only=True)
        except Exception as e:
            patladi = True
            print(f"       (duz openpyxl bekledigimiz gibi patladi: "
                  f"{type(e).__name__})")
        kontrol("hazirlanan dosya gercekten bozuk", patladi)

        wb, g = calisma_kitabi_ac(bozuk)
        kontrol("bozuk dosya yine de acildi", wb.active is not None)
        kontrol("onarim icin gecici kopya uretildi", g is not None)
        temizle(g)

        print("\n3) Onarim sirasinda VERI bozulmuyor")
        beklenen = satirlari_oku(saglam)
        gelen = satirlari_oku(bozuk)
        kontrol("satir sayisi ayni",
                len(beklenen) == len(gelen) and len(gelen) > 0)

        tarihler_ayni = all(
            b["tarih"] == g2["tarih"] for b, g2 in zip(beklenen, gelen))
        kontrol("TARIHLER bozulmadi (sayiya donmedi)", tarihler_ayni)
        kontrol("tarihler gercekten tarih nesnesi",
                all(isinstance(s["tarih"], date) for s in gelen if s["tarih"]))

        tutarlar_ayni = all(
            b["tutar"] == g2["tutar"] for b, g2 in zip(beklenen, gelen))
        kontrol("tutarlar bozulmadi", tutarlar_ayni)

        aciklama_ayni = all(
            b["aciklama"] == g2["aciklama"] for b, g2 in zip(beklenen, gelen))
        kontrol("aciklamalar bozulmadi", aciklama_ayni)

        print("\n4) Ogrenci listesi de onariliyor")
        liste = KOK / "demo" / "ogrenci_listesi_sablonu.xlsx"
        bozuk_liste = _stil_bozan(liste, calisma / "bozuk_liste.xlsx")
        cocuklar_b = cocuk_listesi_yukle(liste)
        cocuklar_g = cocuk_listesi_yukle(bozuk_liste)
        kontrol("bozuk ogrenci listesi okundu", len(cocuklar_g) > 0)
        kontrol("ogrenci sayisi ayni", len(cocuklar_b) == len(cocuklar_g))
        kontrol("T.C. numaralari ayni",
                [c["tc"] for c in cocuklar_b] == [c["tc"] for c in cocuklar_g])

        print("\n5) Gercekten okunamaz dosyada anlamli hata")
        cop = calisma / "cop.xlsx"
        cop.write_bytes(b"bu bir excel dosyasi degil")
        hata_verdi = False
        try:
            satirlari_oku(cop)
        except Exception as e:
            hata_verdi = "acilamadi" in str(e).lower()
        kontrol("bozuk olmayan cop dosyada anlasilir hata", hata_verdi)

        print("\n6) Gecici kopyalar birikmiyor")
        import excel_ac
        wb, g = calisma_kitabi_ac(bozuk)
        kontrol("kopya kayda alindi", any(Path(y)==Path(g) for y,_ in excel_ac._GECICILER))
        temizle()
        kontrol("hepsi temizlendi", not excel_ac._GECICILER)
        kontrol("klasor diskten silindi", not Path(g).exists())

    finally:
        shutil.rmtree(calisma, ignore_errors=True)

    print("\n" + "=" * 58)
    print(f"GECEN: {gecen}   KALAN: {kalan}")
    print("=" * 58)
    return 1 if kalan else 0


if __name__ == "__main__":
    sys.exit(main())
