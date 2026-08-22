# -*- coding: utf-8 -*-
"""
uctan_uca_test.py — Programi kullanicinin yaptigi sirayla bastan sona dener.

testler.py cekirdek mantigi olcer; bu dosya ARAYUZU de acarak gercek akisi
izler: sifre belirle -> sablon uret -> dosyalari sec -> mod sec -> esleştir
-> supheli onayla -> rapor kaydet.

Calistirma:  python uctan_uca_test.py
Ekran gerektirir (tkinter penceresi acilir ve kendiliginden kapanir).
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "src"))

import depo                                     # noqa: E402
import kilit                                    # noqa: E402
import arayuz                                   # noqa: E402
import sablon                                   # noqa: E402
from ekstre import satirlari_oku                # noqa: E402

# Konsol Turkce harfleri kodlayamiyorsa cokme, yerine '?' yaz. Windows'ta
# varsayilan konsol kod sayfasi (cp1252/cp857) 'ı' veya 'ş' harfini kodlayamaz
# ve programin TAMAMI tek bir print yuzunden UnicodeEncodeError ile duser.
# Kodlamayi degistirmiyoruz - sadece kodlanamayani hataya donusturmuyoruz;
# UTF-8 konsolda cikti yine kusursuz.
for _akis in (sys.stdout, sys.stderr):
    if hasattr(_akis, "reconfigure"):
        try:
            _akis.reconfigure(errors="replace")
        except Exception:
            pass


EKSTRE = KOK / "demo" / "test_ekstre.xlsx"
LISTE = KOK / "demo" / "test_liste.xlsx"

gecti, kaldi = [], []


def kontrol(baslik: str, kosul: bool, ayrinti: str = "") -> None:
    if kosul:
        gecti.append(baslik)
        print(f"  [OK]   {baslik}")
    else:
        kaldi.append(f"{baslik} — {ayrinti}")
        print(f"  [HATA] {baslik}  {ayrinti}")


def bolum(baslik: str) -> None:
    print(f"\n{baslik}")


# ---------------------------------------------------------------- 1 sifre
def sifre_akisi(ayar_dosyasi: Path) -> dict:
    bolum("1) Acilis sifresi")
    if ayar_dosyasi.exists():
        ayar_dosyasi.unlink()

    ayarlar = depo.yukle()
    kontrol("ilk acilista sifre sorulur", not ayarlar.get("kullanicilar"))

    pencere = arayuz.KilitEkrani(ayarlar)
    pencere.after(200, lambda: (pencere.sifre.set("gizli2026"),
                                pencere.sifre2.set("gizli2026"),
                                pencere._onayla()))
    pencere.mainloop()
    kontrol("sifre belirlenip giris yapilir", pencere.basarili)

    kayitli = depo.yukle()
    kullanicilar = kayitli.get("kullanicilar", {})
    kontrol("kullanici diske yazilir", bool(kullanicilar))
    kontrol("ilk kuran yonetici olur", kilit.yonetici_mi(kullanicilar, "yönetici"))
    kontrol("sifrenin kendisi diske yazilmaz",
            "gizli2026" not in str(kullanicilar))
    kontrol("dogru sifre kabul edilir",
            kilit.kullanici_bul("gizli2026", kullanicilar) == "yönetici")
    kontrol("yanlis sifre reddedilir",
            kilit.kullanici_bul("baskasifre", kullanicilar) is None)
    return kayitli


# --------------------------------------------------------------- 2 sablon
def sablon_akisi(gecici: Path) -> None:
    bolum("2) Ornek Excel sablonu olusturma")
    ekstre_yolu, ogrenci_yolu = sablon.ikisini_de_uret(gecici)
    kontrol("ekstre sablonu olusur", ekstre_yolu.exists())
    kontrol("ogrenci sablonu olusur", ogrenci_yolu.exists())

    satirlar = satirlari_oku(ekstre_yolu)
    kontrol("uretilen sablon program tarafindan geri okunur",
            len(satirlar) >= 8, f"okunan satir: {len(satirlar)}")
    kontrol("sablondaki tutar dogru cozulur",
            satirlar[0]["tutar"] == 1250.0, str(satirlar[0]["tutar"]))


MAVI = (58, 163, 227)      # secili mod dugmesi
KOYU = (36, 51, 66)        # secili olmayan


def _dugme_rengi(pencere, dugme):
    """Dugmenin ekranda GERCEKTEN gorunen rengini okur.

    cget('bg') yaniltici: indicatoron=False olan Radiobutton'da secili zemin
    'selectcolor'dan gelir, bg'den degil. Bu yuzden ekrandan okuyoruz —
    bir keresinde secili dugme bembeyaz cikmisti ve cget bunu gostermemisti.

    Okumadan once pencere one getirilir; baska bir pencere ustunu ortmussa
    okunan renk yaniltici olur.
    """
    import time

    from PIL import ImageGrab
    try:
        pencere.attributes("-topmost", True)
        pencere.lift()
    except Exception:
        pass
    pencere.update_idletasks()
    pencere.update()
    time.sleep(0.25)

    x = dugme.winfo_rootx() + 6
    y = dugme.winfo_rooty() + dugme.winfo_height() // 2
    renk = ImageGrab.grab(bbox=(x, y, x + 3, y + 3)).getpixel((1, 1))[:3]
    try:
        pencere.attributes("-topmost", False)
    except Exception:
        pass
    return renk


def _renk_yakin(renk, hedef, tolerans=26):
    return all(abs(a - b) <= tolerans for a, b in zip(renk, hedef))


# --------------------------------------------------------------- 3 arayuz
def arayuz_akisi(ayarlar: dict, gecici: Path) -> None:
    bolum("3) Ana ekran: dosya sec -> mod sec -> eslestir -> onayla -> rapor")
    uygulama = arayuz.Uygulama(ayarlar)
    sonuclar = {}

    def adimlar():
        try:
            # dosyalar
            uygulama.ekstre_yolu.set(str(EKSTRE))
            uygulama.liste_yolu.set(str(LISTE))
            uygulama._dosya_etiketlerini_tazele()
            sonuclar["etiket"] = uygulama.ekstre_etiketi.cget("text")

            # mod dugmelerine GERCEK tiklama (invoke = kullanicinin tiklamasi)
            uygulama.mod_dugmeleri[2].invoke()
            uygulama.update()
            sonuclar["oab_turleri"] = list(uygulama.ek_kutu.cget("values"))
            sonuclar["oab_renkleri"] = [_dugme_rengi(uygulama, d)
                                        for d in uygulama.mod_dugmeleri]
            sonuclar["oab_durum"] = uygulama.durum_metni.get()

            uygulama.mod_dugmeleri[0].invoke()
            uygulama.update()
            sonuclar["okul_oncesi_turleri"] = list(uygulama.ek_kutu.cget("values"))
            sonuclar["ilk_mod_renkleri"] = [_dugme_rengi(uygulama, d)
                                            for d in uygulama.mod_dugmeleri]

            # eslestirme
            uygulama._onizle()
            uygulama.update()
            sonuclar["satir_sayisi"] = len(uygulama.sonuc)
            sonuclar["tablo_satiri"] = len(uygulama.tablo.get_children())
            sonuclar["kesin"] = sum(1 for s in uygulama.sonuc if s["durum"] == "kesin")
            sonuclar["supheli"] = [i for i, s in enumerate(uygulama.sonuc)
                                   if s["durum"] == "supheli"]

            # supheli satiri kullanici onayliyor (OnayPenceresi'ni acmadan, ayni yol)
            if sonuclar["supheli"]:
                i = sonuclar["supheli"][0]
                satir = uygulama.sonuc[i]
                cocuk = next(c for c in uygulama.cocuklar
                             if c["ad_soyad"] == satir["cocuk_ad"])
                satir.update(tc=cocuk["tc"], durum="kesin", kaynak="kullanıcı onayı",
                             sebep="sizin onayınızla eşleşti")
                uygulama._tabloyu_doldur()
                sonuclar["onay_sonrasi_kesin"] = sum(
                    1 for s in uygulama.sonuc if s["durum"] == "kesin")

            # rapor
            from rapor import excel_cikti, html_rapor
            h = html_rapor(uygulama.sonuc, gecici / "rapor.html",
                           baslik="Test Raporu", kaynak_dosya=str(EKSTRE),
                           ust_bilgi=uygulama.ust_bilgi)
            x = excel_cikti(uygulama.sonuc, gecici / "liste.xlsx")
            sonuclar["html"] = h.exists() and h.stat().st_size > 3000
            sonuclar["xlsx"] = x.exists() and x.stat().st_size > 3000
            sonuclar["html_metni"] = h.read_text(encoding="utf-8")

            # --- KILIT: ekrani kilitleyip sifre soran pencere
            kilit_p = arayuz.SifreSor(uygulama, ayarlar)
            kilit_p.sifre.set("kesinlikle-yanlis")
            kilit_p._onayla()
            sonuclar["kilit_yanlis"] = kilit_p.basarili
            sonuclar["kilit_uyari"] = kilit_p.uyari.cget("text")
            kilit_p.sifre.set("gizli2026")
            kilit_p._onayla()
            sonuclar["kilit_dogru"] = kilit_p.basarili

            # --- hafiza: girilen kayitlar saklanip tekrar gonderilmiyor mu
            hazir = [k for k in uygulama.sonuc if k["durum"] == "kesin"]
            uygulama._girilenleri_kaydet(hazir[:3])
            sonuclar["hafiza_sayisi"] = len(uygulama.ayarlar.get("girilenler", {}))
            uygulama._onizle()
            uygulama.update()
            sonuclar["ikinci_okuma_kesin"] = sum(
                1 for k in uygulama.sonuc if k["durum"] == "kesin")
            sonuclar["ikinci_okuma_girildi"] = sum(
                1 for k in uygulama.sonuc if k["durum"] == "girildi")

            # bos sonucla TEFBIS baslatilmamali
            eski = uygulama.sonuc
            uygulama.sonuc = []
            sonuclar["bos_baslat"] = uygulama.baslat_dugmesi.cget("state")
            uygulama.sonuc = eski
        except Exception as e:                      # testin kendisi patlamasin
            sonuclar["hata"] = f"{type(e).__name__}: {e}"
        finally:
            uygulama.after(100, uygulama.destroy)

    uygulama.after(400, adimlar)
    uygulama.mainloop()

    kontrol("arayuz hatasiz calisti", "hata" not in sonuclar,
            sonuclar.get("hata", ""))
    kontrol("secilen dosya ekranda gorunur",
            "test_ekstre" in sonuclar.get("etiket", ""))
    kontrol("Okul Aile Birligi secilince gelir turleri degisir",
            "Okula Yapılan Yardımlar (Nakdi)" in sonuclar.get("oab_turleri", []))
    kontrol("Okul Oncesi secilince oz bakim gelir turu gelir",
            "Öz Bakım Ücreti Gelirleri" in sonuclar.get("okul_oncesi_turleri", []))

    # mod dugmesine basinca SECILI OLDUGU GORULMELI (renk degismeli)
    oab = sonuclar.get("oab_renkleri", [])
    ilk = sonuclar.get("ilk_mod_renkleri", [])
    kontrol("3. moda basinca o dugme EKRANDA mavi gorunur",
            len(oab) == 4 and _renk_yakin(oab[2], MAVI), str(oab))
    kontrol("secili olmayan mod dugmeleri koyu kalir (beyaz olmaz)",
            len(oab) == 4 and all(_renk_yakin(oab[i], KOYU)
                                  for i in (0, 1, 3)), str(oab))
    kontrol("1. moda donunce secim ekranda geri gelir",
            len(ilk) == 4 and _renk_yakin(ilk[0], MAVI)
            and _renk_yakin(ilk[2], KOYU), str(ilk))
    kontrol("secilen mod alt satirda yaziyor",
            "Okul Aile Birliği" in sonuclar.get("oab_durum", ""),
            sonuclar.get("oab_durum", ""))
    kontrol("41 hareket okundu", sonuclar.get("satir_sayisi") == 41,
            str(sonuclar.get("satir_sayisi")))
    kontrol("tabloya tum satirlar basildi",
            sonuclar.get("tablo_satiri") == 41, str(sonuclar.get("tablo_satiri")))
    kontrol("20 kayit TEFBIS'e hazir", sonuclar.get("kesin") == 20,
            str(sonuclar.get("kesin")))
    kontrol("3 satir onaya dustu", len(sonuclar.get("supheli", [])) == 3,
            str(len(sonuclar.get("supheli", []))))
    kontrol("kullanici onayindan sonra 21 kayit hazir",
            sonuclar.get("onay_sonrasi_kesin") == 21,
            str(sonuclar.get("onay_sonrasi_kesin")))
    kontrol("HTML rapor uretildi", sonuclar.get("html"))
    kontrol("Excel listesi uretildi", sonuclar.get("xlsx"))
    metin = sonuclar.get("html_metni", "")
    kontrol("raporda okul adi yazili", "ANAOKULU" in metin)
    kontrol("raporda ogrenci adi yazili", "Bade Naz ÖZTÜRKMEN" in metin)
    kontrol("raporda elenme sebebi Turkce", "banka masrafı" in metin)

    # --- kilit
    kontrol("kilit ekraninda yanlis sifre reddedilir",
            sonuclar.get("kilit_yanlis") is False)
    kontrol("yanlis sifrede uyari gosterilir",
            "yanlış" in sonuclar.get("kilit_uyari", "").lower(),
            sonuclar.get("kilit_uyari", ""))
    kontrol("kilit ekraninda dogru sifre kabul edilir",
            sonuclar.get("kilit_dogru") is True)

    # --- hafiza / mukerrer koruma
    kontrol("girilen kayitlar hafizaya yazilir",
            sonuclar.get("hafiza_sayisi") == 3,
            str(sonuclar.get("hafiza_sayisi")))
    kontrol("ayni ekstre tekrar okununca girilmisler ayiklanir",
            sonuclar.get("ikinci_okuma_girildi") == 3,
            str(sonuclar.get("ikinci_okuma_girildi")))
    kontrol("tekrar okumada girilecek kayit sayisi azalir",
            sonuclar.get("ikinci_okuma_kesin") == 17,
            str(sonuclar.get("ikinci_okuma_kesin")))


# ----------------------------------------------------------------- 4 ayar
def ayar_akisi(gecici: Path) -> None:
    bolum("4) Ayarlarin hatirlanmasi")
    ayarlar = depo.yukle()
    ayarlar.update(mod=2, gelir_turu="Okula Yapılan Yardımlar (Nakdi)",
                   ogrenilen={"ornek aciklama": "99976892504"})
    depo.kaydet(ayarlar)

    tekrar = depo.yukle()
    kontrol("secilen mod hatirlanir", tekrar.get("mod") == 2)
    kontrol("gelir turu hatirlanir",
            tekrar.get("gelir_turu") == "Okula Yapılan Yardımlar (Nakdi)")
    kontrol("ogrenilen eslesme hatirlanir",
            tekrar.get("ogrenilen", {}).get("ornek aciklama") == "99976892504")


# ------------------------------------------------------- 5 kullanicilar
def kullanici_akisi(ayarlar: dict) -> None:
    bolum("5) Kullanici yonetimi (yonetici + ikinci kullanici)")
    pencere = arayuz.Uygulama(ayarlar, "yönetici")
    ekran = arayuz.KullanicilarEkrani(pencere, ayarlar, "yönetici")
    try:
        ekran.yeni_ad.set("idareci")
        ekran.yeni_sifre.set("idareci2026")
        ekran._ekle()
        kontrol("yonetici ikinci kullanici ekleyebiliyor",
                "idareci" in ayarlar.get("kullanicilar", {}))
        kontrol("ikinci kullanici kendi sifresiyle giriyor",
                kilit.kullanici_bul("idareci2026", ayarlar["kullanicilar"]) == "idareci")
        kontrol("ikinci kullanici yonetici degil",
                not kilit.yonetici_mi(ayarlar["kullanicilar"], "idareci"))

        ekran.liste.selection_set("yönetici")
        ekran._sil()
        kontrol("yonetici silinemiyor", "yönetici" in ayarlar["kullanicilar"])

        ekran.yeni_sifre.set("degisti99")
        ekran.liste.selection_set("idareci")
        ekran._sifre_degistir()
        kontrol("sifre degistirilebiliyor",
                kilit.kullanici_bul("degisti99", ayarlar["kullanicilar"]) == "idareci")
        kontrol("eski sifre artik gecmiyor",
                kilit.kullanici_bul("idareci2026", ayarlar["kullanicilar"]) is None)

        eski = {"sifre": kilit.ozet_uret("eskisurum")}
        depo._tek_sifreden_goc(eski)
        kontrol("eski tek sifreli surumden gecis calisiyor",
                kilit.kullanici_bul("eskisurum", eski.get("kullanicilar", {})) == "yönetici")
    finally:
        ekran.destroy()
        pencere.destroy()


def main_test() -> int:
    gecici = Path(tempfile.mkdtemp(prefix="tefbis_test_"))
    ayar_dosyasi = depo.ayar_dosyasi()
    yedek = ayar_dosyasi.read_bytes() if ayar_dosyasi.exists() else None

    print("=" * 62)
    print("AKTAR — UCTAN UCA TEST")
    print("=" * 62)
    try:
        ayarlar = sifre_akisi(ayar_dosyasi)
        sablon_akisi(gecici)
        arayuz_akisi(ayarlar, gecici)
        kullanici_akisi(depo.yukle())
        ayar_akisi(gecici)
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
        if yedek is None:
            ayar_dosyasi.unlink(missing_ok=True)
        else:
            ayar_dosyasi.write_bytes(yedek)

    print("\n" + "=" * 62)
    print(f"GECEN: {len(gecti)}   KALAN: {len(kaldi)}")
    for k in kaldi:
        print("  ! " + k)
    print("=" * 62)
    return 1 if kaldi else 0


if __name__ == "__main__":
    raise SystemExit(main_test())
