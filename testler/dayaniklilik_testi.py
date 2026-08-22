# -*- coding: utf-8 -*-
"""
dayaniklilik_testi.py — Program zorlandiginda ne yapiyor?

testler.py dogru calismayi olcer; bu dosya YANLIS kullanimi olcer:
bozuk dosya secilirse, dosya bos ise, 130 kayitlik ekstre gelirse,
ayarlar dosyasi bozulursa program COKUYOR MU, yoksa anlasilir bir sey
mi soyluyor?

Calistirma:  python dayaniklilik_testi.py
"""
from __future__ import annotations

import json
import random
import shutil
import sys
import tempfile
import time
from datetime import date, timedelta
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "src"))

import openpyxl                                  # noqa: E402

import depo                                      # noqa: E402
from ekstre import EkstreHatasi, satirlari_oku, tutar_parse   # noqa: E402
from eslestir import (EslestirmeHatasi, cocuk_listesi_yukle,  # noqa: E402
                      satirlari_eslestir)
from rapor import excel_cikti, html_rapor, ozet   # noqa: E402
from sablon import ekstre_sablonu, ogrenci_sablonu  # noqa: E402

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


gecti: list[str] = []
kaldi: list[tuple[str, str]] = []


def kontrol(baslik: str, kosul: bool, ek: str = "") -> None:
    if kosul:
        gecti.append(baslik)
        print(f"  [OK  ] {baslik}")
    else:
        kaldi.append((baslik, ek))
        print(f"  [HATA] {baslik}   {ek}")


def bolum(ad: str) -> None:
    print(f"\n{ad}")
    print("-" * len(ad))


def anlasilir_hata(fn, *a, **k) -> tuple[bool, str]:
    """Fonksiyon anlasilir bir hata mi veriyor, yoksa cirkin bir cokme mi?"""
    try:
        fn(*a, **k)
        return False, "hic hata vermedi"
    except (EkstreHatasi, EslestirmeHatasi) as e:
        return True, str(e)
    except Exception as e:
        return False, f"beklenmeyen cokme: {type(e).__name__}: {e}"


# ------------------------------------------------------------ 1 buyuk veri
def buyuk_veri(gecici: Path) -> None:
    bolum("1) BUYUK VERI — gercek kullanimda ayda 80-130 kayit giriliyor")

    adlar = ["Ada", "Ege", "Mira", "Kuzey", "Defne", "Poyraz", "Zeynep", "Ali",
             "Elif", "Mert", "Nisa", "Kaan", "Duru", "Efe", "Asya", "Bora"]
    soyadlar = ["YILMAZ", "DEMİR", "ŞAHİN", "ÇELİK", "KAYA", "YILDIZ", "ARSLAN",
                "DOĞAN", "KILIÇ", "AYDIN", "ÖZTÜRK", "KURT"]

    ikinci_adlar = ["", "Naz ", "Can ", "Ada ", "Kaan ", "Su ", "Deniz ", "Alp "]

    cocuklar_wb = openpyxl.Workbook()
    cw = cocuklar_wb.active
    cw.append(["Ad Soyad", "TC", "Veli Ad Soyad", "Veli TC"])
    liste = []
    kullanilan = set()
    rng = random.Random(42)
    while len(liste) < 150:
        # gercek bir okul listesinde her ogrenci ayirt edilebilir olur;
        # rastgele ayni isimden iki tane uretirsek programi degil testi olcmus
        # oluruz (mukerrer isim durumu uc_veriler bolumunde ayrica deneniyor)
        ad = (f"{rng.choice(adlar)} {rng.choice(ikinci_adlar)}"
              f"{rng.choice(soyadlar)}").replace("  ", " ")
        if ad in kullanilan:
            continue
        kullanilan.add(ad)
        tc = f"999{rng.randint(10**7, 10**8 - 1)}"
        veli = f"{rng.choice(adlar)} {ad.split()[-1]}"
        liste.append((ad, tc, veli))
        cw.append([ad, tc, veli, f"999{rng.randint(10**7, 10**8 - 1)}"])
    coc_yolu = gecici / "buyuk_ogrenci.xlsx"
    cocuklar_wb.save(coc_yolu)

    ek_wb = openpyxl.Workbook()
    ew = ek_wb.active
    for _ in range(11):
        ew.append([])
    ew.append(["Tarih", "Fiş No", "Açıklama", "İşlem Tutarı", "Bakiye"])
    gun = date(2026, 5, 1)
    for i in range(130):
        ad, _tc, veli = liste[i % len(liste)]
        ew.append([(gun + timedelta(days=i % 30)).strftime("%d.%m.%Y"),
                   f"F{10000 + i}",
                   f"Gönd: {veli} {ad} mayıs ayı kulüp ücreti "
                   f"00{i:02d}-Banka A.Ş. FAST işlemi",
                   "1.250,00", "50.000,00"])
    for i in range(20):
        ew.append([(gun + timedelta(days=i)).strftime("%d.%m.%Y"),
                   f"F{90000 + i}", "MESAJ ÜCRETİ TUTARI", "-0,60", "50.000,00"])
    ek_yolu = gecici / "buyuk_ekstre.xlsx"
    ek_wb.save(ek_yolu)

    basla = time.time()
    satirlar = satirlari_oku(ek_yolu)
    cocuklar = cocuk_listesi_yukle(coc_yolu)
    sonuc = satirlari_eslestir(satirlar, cocuklar)
    sure = time.time() - basla

    o = ozet(sonuc)
    kontrol("150 satirlik ekstre okundu", len(satirlar) == 150, str(len(satirlar)))
    kontrol("150 ogrencilik liste okundu", len(cocuklar) == 150, str(len(cocuklar)))
    # Bu test verisinde bilerek cok benzer isimler var (Duru Kaan DEMIR /
    # Duru Su DEMIR gibi). Onemli olan kac tanesinin otomatik gectigi degil,
    # HICBIRININ yanlis ogrenciye yazilmamasi ve belirsiz olanlarin
    # kullaniciya sorulmasi.
    oran = o["kesin"] / max(1, o["kesin"] + o["supheli"])
    kontrol("aidatlarin cogu otomatik eslesti (>=%65)", oran >= 0.65,
            f"oran: %{oran*100:.0f} — {o['kesin']} otomatik, {o['supheli']} soruldu")
    kontrol("otomatik gecmeyenler gercekten belirsiz",
            all(len(k.get("adaylar", [])) >= 2 or k.get("kaynak") == "veli ismi"
                for k in sonuc if k["durum"] == "supheli"),
            "sebepsiz onaya dusen kayit var")

    # EN ONEMLI KONTROL: otomatik girilen bir kayit YANLIS ogrenciye
    # baglanmis olabilir mi? Aciklamada adi gecmeyen bir ogrenciye
    # baglandiysa ve veli yoluyla da aciklanamiyorsa bu ciddi hatadir.
    yanlis = []
    for k in sonuc:
        if k["durum"] != "kesin":
            continue
        adi_geciyor = k["cocuk_ad"] in k["aciklama"]
        veliden = k.get("kaynak") == "veli ismi" and k.get("veli_ad")             and k["veli_ad"] in k["aciklama"]
        if not adi_geciyor and not veliden:
            yanlis.append(k)
    kontrol("hicbir kayit yanlis ogrenciye yazilmadi", not yanlis,
            f"{len(yanlis)} kayit: " + "; ".join(
                f"{k['aciklama'][:34]}... -> {k['cocuk_ad']}" for k in yanlis[:2]))
    kontrol("banka masraflari elendi", o["yok"] >= 20, f"elenen: {o['yok']}")
    kontrol("makul surede bitti (<15 sn)", sure < 15, f"{sure:.1f} sn")
    print(f"         süre: {sure:.1f} sn  |  {o['kesin']} hazır, {o['yok']} elendi")

    basla = time.time()
    html_rapor(sonuc, gecici / "buyuk.html", baslik="Büyük Test")
    excel_cikti(sonuc, gecici / "buyuk.xlsx")
    kontrol("150 satirlik rapor uretildi", (gecici / "buyuk.html").exists()
            and (gecici / "buyuk.xlsx").exists())
    kontrol("rapor uretimi hizli (<10 sn)", time.time() - basla < 10)


# --------------------------------------------------------- 2 bozuk dosyalar
def bozuk_dosyalar(gecici: Path) -> None:
    bolum("2) BOZUK / YANLIS DOSYALAR — kullanici yanlis dosya secerse")

    yok = gecici / "olmayan_dosya.xlsx"
    ok, mesaj = anlasilir_hata(satirlari_oku, yok)
    kontrol("olmayan dosya: anlasilir hata", ok, mesaj)

    metin = gecici / "aslinda_metin.xlsx"
    metin.write_text("bu bir excel degil, duz metin", encoding="utf-8")
    ok, mesaj = anlasilir_hata(satirlari_oku, metin)
    kontrol("excel olmayan dosya: anlasilir hata", ok, mesaj)

    bos_wb = openpyxl.Workbook()
    bos_yolu = gecici / "bos.xlsx"
    bos_wb.save(bos_yolu)
    ok, mesaj = anlasilir_hata(satirlari_oku, bos_yolu)
    kontrol("bos excel: anlasilir hata", ok, mesaj)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["filan", "falan", "filanca"])
    ws.append(["1", "2", "3"])
    bassiz = gecici / "baslıksız.xlsx"
    wb.save(bassiz)
    ok, mesaj = anlasilir_hata(satirlari_oku, bassiz)
    kontrol("baslik satiri olmayan dosya: anlasilir hata", ok, mesaj)

    wb2 = openpyxl.Workbook()
    ws2 = wb2.active
    ws2.append(["Ad", "Numara"])
    ws2.append(["Ali Veli", "123"])
    yanlis_liste = gecici / "yanlis_liste.xlsx"
    wb2.save(yanlis_liste)
    ok, mesaj = anlasilir_hata(cocuk_listesi_yukle, yanlis_liste)
    kontrol("yanlis ogrenci listesi: anlasilir hata", ok, mesaj)

    wb3 = openpyxl.Workbook()
    ws3 = wb3.active
    ws3.append(["Ad Soyad", "TC"])
    bos_liste = gecici / "bos_liste.xlsx"
    wb3.save(bos_liste)
    ok, mesaj = anlasilir_hata(cocuk_listesi_yukle, bos_liste)
    kontrol("bos ogrenci listesi: anlasilir hata", ok, mesaj)


# ------------------------------------------------------- 3 farkli duzenler
def farkli_duzenler(gecici: Path) -> None:
    bolum("3) FARKLI BANKA DUZENLERI — sutun sirasi degisirse")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Açıklama", "İşlem Tutarı", "Tarih", "Fiş No"])
    ws.append(["Gönd: EZGİ AYDINLI Ozan AYDINLI mayıs", "1.250,00", "21.05.2026", "F111"])
    ws.append(["MESAJ ÜCRETİ TUTARI", "-0,60", "21.05.2026", "F112"])
    ters = gecici / "ters_sutun.xlsx"
    wb.save(ters)
    try:
        satirlar = satirlari_oku(ters)
        kontrol("sutun sirasi degisse de okuyor", len(satirlar) == 2, str(len(satirlar)))
        kontrol("ters duzende tutar dogru", satirlar[0]["tutar"] == 1250.0,
                str(satirlar[0]["tutar"]))
        kontrol("ters duzende evrak no dogru", satirlar[0]["evrak_no"] == "F111",
                satirlar[0]["evrak_no"])
    except Exception as e:
        kontrol("sutun sirasi degisse de okuyor", False, str(e))

    wb2 = openpyxl.Workbook()
    ws2 = wb2.active
    for _ in range(30):
        ws2.append(["banka reklam metni"])
    ws2.append(["Tarih", "Fiş No", "Açıklama", "İşlem Tutarı"])
    ws2.append(["21.05.2026", "F1", "Gönd: X Y mayıs", "100,00"])
    derin = gecici / "derin_baslik.xlsx"
    wb2.save(derin)
    ok, mesaj = anlasilir_hata(satirlari_oku, derin)
    kontrol("cok asagidaki baslik: anlasilir hata veriyor (sessiz kalmiyor)",
            ok, mesaj)


# ------------------------------------------------------------ 4 uc veriler
def uc_veriler(gecici: Path) -> None:
    bolum("4) UC DURUMLAR — garip veriler program cokertiyor mu")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Ad Soyad", "TC", "Veli Ad Soyad", "Veli TC"])
    ws.append(["A B", "99912345678", "C D", ""])                       # tek harf
    ws.append(["Ayşe Nur Beyza Zeynep YILMAZKARADEMİROĞULLARI",
               "99987654321", "", ""])                                  # cok uzun
    ws.append(["Ali KAYA", "99911223344", "", ""])
    ws.append(["Ali KAYA", "99955667788", "", ""])                      # ayni isim!
    ws.append(["Çğıöşü ÇĞIÖŞÜ", "99933445566", "", ""])                 # tr karakter
    liste_yolu = gecici / "uc_liste.xlsx"
    wb.save(liste_yolu)
    cocuklar = cocuk_listesi_yukle(liste_yolu)
    kontrol("uc durumlu liste okundu", len(cocuklar) == 5, str(len(cocuklar)))

    satirlar = [
        {"satir_no": 1, "tarih": date(2026, 5, 1), "evrak_no": "F1",
         "aciklama": "Gönd: C D A B mayıs", "tutar": 0.0, "tc_sutunu": ""},
        {"satir_no": 2, "tarih": date(2026, 5, 2), "evrak_no": "F2",
         "aciklama": "Gönd: X Ali Kaya mayıs", "tutar": 1250.0, "tc_sutunu": ""},
        {"satir_no": 3, "tarih": date(2026, 5, 3), "evrak_no": "F3",
         "aciklama": "Gönd: Çğıöşü ÇĞIÖŞÜ mayıs", "tutar": 999999.99,
         "tc_sutunu": ""},
        {"satir_no": 4, "tarih": date(2026, 5, 4), "evrak_no": "F4",
         "aciklama": "!@#$%^&*()_+ ????", "tutar": None, "tc_sutunu": ""},
        {"satir_no": 5, "tarih": date(2026, 5, 5), "evrak_no": "",
         "aciklama": "Gönd: Ayşe Nur Beyza Zeynep YILMAZKARADEMİROĞULLARI",
         "tutar": 1250.0, "tc_sutunu": ""},
    ]
    try:
        sonuc = satirlari_eslestir(satirlar, cocuklar)
        kontrol("garip veriler cokertmedi", len(sonuc) == 5)
        ayni_isim = sonuc[1]
        kontrol("ayni isimli iki ogrenci: otomatik girilmiyor",
                ayni_isim["durum"] != "kesin", ayni_isim["durum"])
        kontrol("sifir tutar cokertmedi", sonuc[0]["durum"] in ("kesin", "supheli", "yok"))
        kontrol("tutari bos satir cokertmedi", sonuc[3]["durum"] == "yok")
        kontrol("cok uzun isim eslesti", sonuc[4]["cocuk_ad"].startswith("Ayşe Nur"),
                sonuc[4]["cocuk_ad"])
        kontrol("turkce karakterli isim eslesti",
                sonuc[2]["cocuk_ad"] == "Çğıöşü ÇĞIÖŞÜ", sonuc[2]["cocuk_ad"])
        html_rapor(sonuc, gecici / "uc.html", baslik="Uç Test")
        excel_cikti(sonuc, gecici / "uc.xlsx")
        kontrol("garip verilerle rapor uretildi", (gecici / "uc.html").exists())
    except Exception as e:
        kontrol("garip veriler cokertmedi", False, f"{type(e).__name__}: {e}")

    kontrol("tutar: harf iceren deger", tutar_parse("abc") is None)
    kontrol("tutar: bos metin", tutar_parse("") is None)
    kontrol("tutar: sadece eksi", tutar_parse("-") is None)
    kontrol("tutar: cok buyuk sayi", tutar_parse("9.999.999,99") == 9999999.99)


# ------------------------------------------------------- 5 bozuk ayarlar
def bozuk_ayarlar(gecici: Path) -> None:
    bolum("5) BOZUK AYAR DOSYASI — program yine aciliyor mu")

    ayar_yolu = depo.ayar_dosyasi()
    yedek = ayar_yolu.read_bytes() if ayar_yolu.exists() else None
    try:
        ayar_yolu.write_text("{bu bozuk json!!", encoding="utf-8")
        veri = depo.yukle()
        kontrol("bozuk json: program varsayilanla aciliyor",
                isinstance(veri, dict) and "kullanicilar" in veri)

        ayar_yolu.write_text("", encoding="utf-8")
        veri = depo.yukle()
        kontrol("bos ayar dosyasi: program aciliyor", isinstance(veri, dict))

        ayar_yolu.write_text(json.dumps({"kullanicilar": "bu bir sozluk degil"}),
                             encoding="utf-8")
        veri = depo.yukle()
        kontrol("yanlis tipte ayar: cokertmiyor", isinstance(veri, dict))

        ayar_yolu.unlink(missing_ok=True)
        veri = depo.yukle()
        kontrol("ayar dosyasi silinmis: ilk kurulum gibi aciliyor",
                not veri.get("kullanicilar"))
    finally:
        ayar_yolu.unlink(missing_ok=True)
        if yedek is not None:
            ayar_yolu.write_bytes(yedek)


# --------------------------------------------------------- 6 sablon dongusu
def sablon_dongusu(gecici: Path) -> None:
    bolum("6) SABLON DONGUSU — program urettigini geri okuyabiliyor mu")

    e = ekstre_sablonu(gecici / "s_ekstre.xlsx")
    o = ogrenci_sablonu(gecici / "s_ogrenci.xlsx")
    try:
        satirlar = satirlari_oku(e)
        cocuklar = cocuk_listesi_yukle(o)
        sonuc = satirlari_eslestir(satirlar, cocuklar)
        kontrol("uretilen ekstre sablonu geri okundu", len(satirlar) >= 8,
                str(len(satirlar)))
        kontrol("uretilen ogrenci sablonu geri okundu", len(cocuklar) >= 5,
                str(len(cocuklar)))
        kontrol("sablon verisi islenebildi", len(sonuc) == len(satirlar))
        bagis = [s for s in sonuc if "Bağış" in s["aciklama"]]
        kontrol("sablondaki bagis satiri otomatik girilmiyor",
                bagis and bagis[0]["durum"] != "kesin",
                bagis[0]["durum"] if bagis else "yok")
    except Exception as ex:
        kontrol("sablon dongusu calisti", False, f"{type(ex).__name__}: {ex}")


def main() -> int:
    gecici = Path(tempfile.mkdtemp(prefix="tefbis_dayaniklilik_"))
    print("=" * 64)
    print("DAYANIKLILIK TESTI — program zorlandiginda ne yapiyor")
    print("=" * 64)
    try:
        buyuk_veri(gecici)
        bozuk_dosyalar(gecici)
        farkli_duzenler(gecici)
        uc_veriler(gecici)
        bozuk_ayarlar(gecici)
        sablon_dongusu(gecici)
    finally:
        shutil.rmtree(gecici, ignore_errors=True)

    print("\n" + "=" * 64)
    print(f"GECEN: {len(gecti)}   KALAN: {len(kaldi)}")
    for baslik, ek in kaldi:
        print(f"   ! {baslik}  —  {ek}")
    print("=" * 64)
    return 1 if kaldi else 0


if __name__ == "__main__":
    raise SystemExit(main())
