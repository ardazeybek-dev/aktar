# -*- coding: utf-8 -*-
"""
sablon.py — Kullanicinin dolduracagi ornek Excel dosyalarini uretir.

Arayuzdeki "Ornek Excel Sablonu Olustur" dugmesi burayi cagirir.
  ekstre_sablonu()   : tarih / fis no / aciklama / tutar / T.C. sutunlari
  ogrenci_sablonu()  : ad soyad / TC / veli ad soyad / veli TC
"""
from __future__ import annotations

from pathlib import Path

import openpyxl
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

BASLIK_ZEMIN = "0F2D4A"
ORNEK_ZEMIN = "FFF6E0"


def _baslik_bicimle(ws, satir: int) -> None:
    for hucre in ws[satir]:
        if hucre.value is None:
            continue
        hucre.font = Font(bold=True, color="FFFFFF")
        hucre.fill = PatternFill("solid", fgColor=BASLIK_ZEMIN)
        hucre.alignment = Alignment(horizontal="center", vertical="center")


def _genislikler(ws, olculer) -> None:
    for i, g in enumerate(olculer, start=1):
        ws.column_dimensions[get_column_letter(i)].width = g


EKSTRE_YARDIM = [
    ("Bu dosya ne işe yarar?", ""),
    ("", "Bankadan indirdiğiniz Excel'i programa DOĞRUDAN verebilirsiniz; "
         "bu dosya sadece elle doldurmak isterseniz diye hazırlanmıştır."),
    ("", ""),
    ("Sütunlar", ""),
    ("Tarih", "Ödemenin tarihi. 21.05.2026 biçiminde."),
    ("Fiş No", "Bankadaki fiş/evrak numarası. TEFBİS'e evrak no olarak girilir."),
    ("Açıklama", "Bankadaki açıklama. OLDUĞU GİBİ bırakın, düzeltmeyin. "
                 "Program öğrenciyi buradan bulur."),
    ("İşlem Tutarı", "Yatan tutar. 1.250,00 gibi Türkçe biçim olabilir."),
    ("T.C. Kimlik No", "İSTEĞE BAĞLI. Boş bırakırsanız program kendisi bulur."),
    ("", ""),
    ("Program neyi nasıl anlıyor?", ""),
    ("Veli + çocuk yazılmışsa", "İkisini de görür, listedeki öğrenciyi bulur."),
    ("Çocuk adı başta yazılmışsa", "Sorun değil, sırası önemli değil."),
    ("Yazım hatası varsa", "'artal' → KARTAL, 'aydatı' → aidatı tolere edilir."),
    ("Açıklamada T.C. varsa", "Doğrudan alır, kimlik algoritmasıyla doğrular."),
    ("Bağış / kantin / kira yazıyorsa", "Aidat saymaz, size sorar."),
    ("Banka masrafı / vergi / maaş", "Otomatik elenir, TEFBİS'e girilmez."),
    ("Emin olamazsa", "ASLA tahmin yürütmez, onayınızı ister."),
]

OGRENCI_YARDIM = [
    ("Bu dosya ne işe yarar?", ""),
    ("", "Programın öğrenci–T.C. eşleştirmesi için kullandığı listedir. "
         "Bir kez hazırlarsınız, program hatırlar."),
    ("", ""),
    ("Sütunlar", ""),
    ("Öğrenci Ad Soyad", "ZORUNLU. Öğrencinin adı soyadı."),
    ("Öğrenci TC", "ZORUNLU. 11 haneli kimlik numarası. TEFBİS'e bu girilir."),
    ("Anne Ad Soyad", "Önerilir. Parayı anne yatırdığında çocuğu bulmak için."),
    ("Anne TC", "İsteğe bağlı. Veli adına kayıt yapacaksanız."),
    ("Baba Ad Soyad", "Önerilir. Parayı baba yatırdığında çocuğu bulmak için."),
    ("Baba TC", "İsteğe bağlı. Veli adına kayıt yapacaksanız."),
    ("Sınıf/Şube", "İsteğe bağlı. Program kullanmaz."),
    ("", ""),
    ("Dikkat", ""),
    ("Sütun sırası önemli değil", "Anne bilgisi başta olsa bile program "
                                  "öğrenciyi karıştırmaz."),
    ("Kendi listeniz de olur", "Okul kaydındaki 6 sütunlu listeyi olduğu gibi "
                               "kullanabilirsiniz."),
    ("Sütun ekleyebilirsiniz", "Program tanımadığı sütunlara karışmaz."),
    ("Yeni öğrenci gelince", "Alta bir satır eklemeniz yeterli."),
    ("Kardeşler varsa", "İkisini de yazın; program adlarından ayırt eder."),
]


def _yardim_sayfasi(wb, satirlar) -> None:
    """Dosyaya 'Nasıl Doldurulur' sayfasi ekler."""
    ws = wb.create_sheet("Nasıl Doldurulur")
    for baslik, aciklama in satirlar:
        ws.append([baslik, aciklama])
        hucre = ws.cell(ws.max_row, 1)
        if baslik and not aciklama:
            hucre.font = Font(bold=True, size=12, color="0F2D4A")
        elif baslik:
            hucre.font = Font(bold=True)
    _genislikler(ws, (30, 92))


# ------------------------------------------------------------- ekstre
EKSTRE_BASLIKLARI = ["Tarih", "Fiş No", "Açıklama", "İşlem Tutarı", "T.C. Kimlik No"]

# Gercek ekstrede karsilasilan butun aciklama tipleri ornek olarak konuldu:
# veli+cocuk, cocuk basta, yazim hatali, T.C. yazili, bagis, banka masrafi.
EKSTRE_ORNEK = [
    ["21.05.2026", "F13159",
     "Gönd: SEHER ÖZTÜRKMEN Bade Naz ÖZTÜRKMEN (Mayıs Klüp Ödemesi)", "1.250,00", ""],
    ["19.05.2026", "F00279",
     "Gönd: FİGEN BOZDOĞAN Kuzey Asaf BOZDOĞAN mayıs ayı kulüp ücreti", "1.250,00", ""],
    ["18.05.2026", "F31409",
     "Gönd: ALTAN YILDIRIMLI Peri YILDIRIMLI Mayıs", "1.250,00", ""],
    ["15.05.2026", "F11475",
     "Tuna Efe TAŞDELEN, mayıs ayı kulüb ücreti NERMİN TAŞDELEN", "1.250,00", ""],
    ["13.05.2026", "F03814",
     "Gönd: GAMZE KARTAL Mayıs ayı beren artal", "1.375,50", ""],
    ["11.05.2026", "F35180",
     "Gönd: HANDE TUNCAL Ceylin TUNCAL mayis ayı aydatı", "1.250,00", ""],
    ["08.05.2026", "F09534",
     "Gönd: VELİ ADI SOYADI mayıs ödemesi", "1.250,00", "10000000146"],
    ["07.05.2026", "F04017", "MESAJ ÜCRETİ TUTARI", "-0,60", ""],
    ["05.05.2026", "F07733",
     "Gönd: SUNA ERGÜVEN SUNA ERGÜVEN Bağış", "15.000,00", ""],
]

EKSTRE_NOTLARI = {
    "A": "Ödemenin tarihi (gg.aa.yyyy). TEFBİS'e evrak tarihi olarak girilir.",
    "B": "Bankadaki fiş / evrak numarası. TEFBİS'e evrak no olarak girilir.",
    "C": "Bankadaki açıklama. Program öğrenciyi buradan bulur — "
         "olduğu gibi bırakın, düzeltmeye çalışmayın.",
    "D": "Yatan tutar. 1.250,00 gibi Türkçe biçim olabilir.",
    "E": "İSTEĞE BAĞLI. Doldurursanız program bu numarayı kullanır. "
         "Boş bırakırsanız açıklamadan ya da öğrenci listenizden kendisi bulur.",
}


def ekstre_sablonu(hedef: str | Path) -> Path:
    """Banka hareketleri sablonu. Bankanin kendi dosyasi da dogrudan okunur."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Hesap Hareketleri"

    ws["A1"] = ("Bankadan indirdiğiniz dosyayı doğrudan programa verebilirsiniz. "
                "Bu sayfa, elle doldurmak isterseniz diye hazırlanmıştır.")
    ws["A1"].font = Font(italic=True, color="5B6B7B", size=9)
    ws.append([])

    ws.append(EKSTRE_BASLIKLARI)
    baslik_satiri = ws.max_row
    _baslik_bicimle(ws, baslik_satiri)
    for sutun, metin in EKSTRE_NOTLARI.items():
        ws[f"{sutun}{baslik_satiri}"].comment = Comment(metin, "TEFBİS Otomasyon")

    for satir in EKSTRE_ORNEK:
        ws.append(satir)
        for hucre in ws[ws.max_row]:
            hucre.fill = PatternFill("solid", fgColor=ORNEK_ZEMIN)
        ws.cell(ws.max_row, 5).number_format = "@"

    ws.append([])
    ws.append(["↑ Yukarıdaki satırlar örnektir — silip kendi hareketlerinizi yazın ya da bankanın dosyasını doğrudan programa verin."])
    ws.cell(ws.max_row, 1).font = Font(italic=True, color="8A6D3B")

    _genislikler(ws, (13, 12, 78, 15, 18))
    ws.freeze_panes = f"A{baslik_satiri + 1}"
    _yardim_sayfasi(wb, EKSTRE_YARDIM)

    yol = Path(hedef)
    yol.parent.mkdir(parents=True, exist_ok=True)
    wb.save(yol)
    return yol


# ------------------------------------------------------ ogrenci listesi
# Okul kayit formunda ogrenci + anne + baba bilgisi alindigi icin sablon da
# ayni duzende: 6 sutun + istege bagli sinif. Anne ya da baba hangisi para
# yatirirsa yatirsin program cocuga ulasabilsin diye ikisi de tutuluyor.
OGRENCI_BASLIKLARI = ["Öğrenci Ad Soyad", "Öğrenci TC",
                      "Anne Ad Soyad", "Anne TC",
                      "Baba Ad Soyad", "Baba TC", "Sınıf/Şube"]

OGRENCI_ORNEK = [
    ["Ayşe YILMAZ", "11111111111", "Fatma YILMAZ", "22222222222",
     "Ahmet YILMAZ", "12345678901", "A Şubesi"],
    ["Mehmet Can DEMİR", "33333333333", "Hatice DEMİR", "44444444444",
     "Ali DEMİR", "23456789012", "A Şubesi"],
    ["Peri YILDIRIMLI", "55555555555", "BENGİ YILDIRIMLI", "66666666666",
     "ALTAN YILDIRIMLI", "34567890123", "B Şubesi"],
    ["Tuna Efe TAŞDELEN", "77777777777", "NERMİN TAŞDELEN", "88888888888",
     "SAVAŞ TAŞDELEN", "45678901234", "B Şubesi"],
    ["Beren KARTAL", "99999999999", "GAMZE KARTAL", "10000000146",
     "SERHAT KARTAL", "56789012345", "C Şubesi"],
]

OGRENCI_NOTLARI = {
    "A": "ZORUNLU. Öğrencinin adı ve soyadı. Bankada veliler ismi farklı yazsa "
         "da program bulur (yazım hatası, ismin başta/sonda olması sorun değil).",
    "B": "ZORUNLU. Öğrencinin 11 haneli T.C. kimlik numarası. "
         "TEFBİS'e bu numara girilir.",
    "C": "İsteğe bağlı ama önerilir. Parayı anne yatırdığında ve açıklamada "
         "çocuğun adı olmadığında program bu isimden çocuğa ulaşır.",
    "D": "İsteğe bağlı. Veli adına kayıt yapacaksanız gerekir.",
    "E": "İsteğe bağlı ama önerilir. Parayı baba yatırdığında kullanılır.",
    "F": "İsteğe bağlı. Veli adına kayıt yapacaksanız gerekir.",
    "G": "İsteğe bağlı. Program kullanmaz, sizin takibiniz için. "
         "İstediğiniz sütunu ekleyebilirsiniz, program karışmaz.",
}


def ogrenci_sablonu(hedef: str | Path) -> Path:
    """Ogrenci-TC listesi sablonu."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Öğrenci Listesi"

    ws.append(OGRENCI_BASLIKLARI)
    _baslik_bicimle(ws, 1)
    for sutun, metin in OGRENCI_NOTLARI.items():
        ws[f"{sutun}1"].comment = Comment(metin, "TEFBİS Otomasyon")

    for satir in OGRENCI_ORNEK:
        ws.append(satir)
        for hucre in ws[ws.max_row]:
            hucre.fill = PatternFill("solid", fgColor=ORNEK_ZEMIN)
        ws.cell(ws.max_row, 2).number_format = "@"
        ws.cell(ws.max_row, 4).number_format = "@"

    ws.append([])
    ws.append(["↑ Yukarıdaki satırlar örnektir — silip kendi öğrencilerinizi yazın."])
    ws.cell(ws.max_row, 1).font = Font(italic=True, color="8A6D3B")

    _genislikler(ws, (26, 15, 24, 15, 24, 15, 13))
    ws.freeze_panes = "A2"
    _yardim_sayfasi(wb, OGRENCI_YARDIM)

    yol = Path(hedef)
    yol.parent.mkdir(parents=True, exist_ok=True)
    wb.save(yol)
    return yol


def ikisini_de_uret(klasor: str | Path) -> tuple[Path, Path]:
    """Iki sablonu birden secilen klasore yazar."""
    k = Path(klasor)
    return (ekstre_sablonu(k / "ornek_ekstre_sablonu.xlsx"),
            ogrenci_sablonu(k / "ornek_ogrenci_listesi.xlsx"))
