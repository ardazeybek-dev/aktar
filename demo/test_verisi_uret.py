# -*- coding: utf-8 -*-
"""
test_verisi_uret.py — Testler icin UYDURMA ekstre ve ogrenci listesi uretir.

Testler eskiden musterinin gercek banka ekstresini kullaniyordu. Gercek veri
(kisi adlari, T.C. numaralari, banka hareketleri) projede tutulmamali; bu
yuzden ayni zorluktaki senaryolar tamamen uydurma verilerle uretiliyor.

Uretilenler:
    demo/test_ekstre.xlsx   - 41 hareket, baslik satiri 12. satirda
    demo/test_liste.xlsx    - 20 ogrenci, anne/baba sutunlariyla

Korunan zorluklar (testlerin dogruladigi senaryolar):
  - ayni soyadli birden fazla ogrenci (KAYA ailesi) karistirilmamali
  - yazim hatasi: "beren artal" -> Beren KARTAL, "tuncal" -> TUNCEL
  - veli adindan bulma (anne ya da baba yatirinca)
  - kardesler: ayni veliye bagli iki cocuk -> onay bekler
  - aidat disi satirlar: bagis, kantin, kira, faiz, aktarim, denetim payi
  - eksi tutarlar, bos aciklama, aciklamada elle yazilmis T.C.
  - listede hic olmayan kisiler
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill

KOK = Path(__file__).resolve().parent


def _tc(cekirdek: int) -> str:
    """MERNIS kurallarina uyan UYDURMA T.C. numarasi."""
    r = [int(c) for c in str(cekirdek).zfill(9)]
    if r[0] == 0:
        r[0] = 1
    d10 = (sum(r[0:9:2]) * 7 - sum(r[1:8:2])) % 10
    d11 = (sum(r) + d10) % 10
    return "".join(map(str, r + [d10, d11]))


# (ogrenci, anne, baba)  - hepsi uydurma
AILELER = [
    ("Bade Naz ÖZTÜRKMEN", "SEHER ÖZTÜRKMEN", "LEVENT ÖZTÜRKMEN"),
    ("Tuna Efe TAŞDELEN", "NERMİN TAŞDELEN", "SAVAŞ TAŞDELEN"),
    ("Beren KARTAL", "GAMZE KARTAL", "SERHAT KARTAL"),
    ("Bulut KARTAL", "GAMZE KARTAL", "SERHAT KARTAL"),      # kardes
    ("Ceylin TUNÇEL", "HANDE TUNÇEL", "ÜMİT TUNÇEL"),
    ("Ozan AYDINLI", "BİRSEN AYDINLI", "KADİR AYDINLI"),
    ("İpek AYDINLI", "SEVİM AYDINLI", "HALİL AYDINLI"),
    ("Umut Efe AYDINLI", "NAZLI AYDINLI", "BURAK AYDINLI"),
    ("Doruk AYDINLI", "PERİHAN AYDINLI", "YAVUZ AYDINLI"),
    ("Efe Han ÇAKIROĞLU", "PELİN ÇAKIROĞLU", "TAYFUN ÇAKIROĞLU"),
    ("Aras Kaan SEVİNDİK", "JALE SEVİNDİK", "ERSİN SEVİNDİK"),
    ("Zümra Su ERGÜVEN", "SUNA ERGÜVEN", "CENGİZ ERGÜVEN"),
    ("Ediz Ali GÖKMENLER", "ŞENAY GÖKMENLER", "OKTAY GÖKMENLER"),
    ("Peri YILDIRIMLI", "BENGİ YILDIRIMLI", "ALTAN YILDIRIMLI"),
    ("Kuzey Asaf BOZDOĞAN", "FİGEN BOZDOĞAN", "SİNAN BOZDOĞAN"),
    ("Lina Nur KESKİNER", "REYHAN KESKİNER", "ERTAN KESKİNER"),
    ("Irmak ULUTÜRK", "SEVİL ULUTÜRK", "BARAN ULUTÜRK"),
    ("Poyraz Eren ŞENGÜLER", "NALAN ŞENGÜLER", "ÖMÜR ŞENGÜLER"),
    ("Zeytin ARIKBOĞA", "SELDA ARIKBOĞA", "HAKAN ARIKBOĞA"),
    ("Alperen MERTOĞLU", "İLKNUR MERTOĞLU", "MELİH MERTOĞLU"),
]


def liste_uret(hedef: Path) -> Path:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Öğrenci Listesi"
    ws.append(["Öğrenci Ad Soyad", "Öğrenci TC", "Anne Ad Soyad", "Anne TC",
               "Baba Ad Soyad", "Baba TC", "Sınıf/Şube"])
    for h in ws[1]:
        h.font = Font(bold=True, color="FFFFFF")
        h.fill = PatternFill("solid", fgColor="1F4E79")
        h.alignment = Alignment(horizontal="center")

    for i, (cocuk, anne, baba) in enumerate(AILELER):
        ws.append([cocuk, _tc(100000000 + i * 1237),
                   anne, _tc(200000000 + i * 1237),
                   baba, _tc(300000000 + i * 1237), f"{(i % 3) + 1}-A"])

    for sutun, gen in zip("ABCDEFG", (24, 14, 22, 14, 22, 14, 11)):
        ws.column_dimensions[sutun].width = gen
    ws.freeze_panes = "A2"
    wb.save(hedef)
    return hedef


def _hareketler() -> list[tuple]:
    """(tarih, evrak, aciklama, tutar) — 41 satir."""
    h = []
    ay = 5

    def ek(gun, no, aciklama, tutar):
        # sira numarasi 31'i asabilir; gunu ay icinde dondur
        h.append((date(2026, ay, ((gun - 1) % 28) + 1), no, aciklama, tutar))

    # --- ogrenci adindan bulunacaklar (kesin)
    ek(2, "F10001", "Gönd: SEHER ÖZTÜRKMEN Bade Naz ÖZTÜRKMEN mayıs", 1500.0)
    ek(3, "F10002", "Gönd: NERMİN TAŞDELEN Tuna Efe TAŞDELEN mayıs ayı", 1500.0)
    ek(4, "F10003", "Gönd: BİRSEN AYDINLI Ozan AYDINLI -Mayıs ödemesi", 1500.0)
    ek(5, "F10004", "Gönd: SEVİM AYDINLI İpek AYDINLI mayıs", 1500.0)
    ek(6, "F10005", "Gönd: NAZLI AYDINLI Umut Efe AYDINLI mayıs ödemesi", 1500.0)
    ek(7, "F10006", "Gönd: PERİHAN AYDINLI Doruk AYDINLI aidat", 1500.0)
    ek(8, "F10007", "Gönd: JALE SEVİNDİK Aras Kaan SEVİNDİK mayıs", 1500.0)
    ek(9, "F10008", "Gönd: ŞENAY GÖKMENLER Ediz Ali GÖKMENLER aidat", 1500.0)
    ek(10, "F10009", "Gönd: BENGİ YILDIRIMLI Peri YILDIRIMLI mayıs ayı", 1500.0)
    ek(11, "F10010", "Gönd: REYHAN KESKİNER Lina Nur KESKİNER ödeme", 1500.0)

    # --- yazim hatalari (kesin)
    ek(12, "F10011", "Gönd: GAMZE KARTAL Mayıs ayı beren artal 0067-Yapı ve Kredi", 1500.0)
    ek(13, "F10012", "Gönd: HANDE TUNCAL Ceylin TUNCAL mayis ayı aydatı", 1500.0)

    # --- veli adindan bulunacaklar (cocuk adi hic gecmiyor)
    ek(14, "F10013", "Gönd: FİGEN BOZDOĞAN mayıs ayı ödemesi", 1500.0)
    ek(15, "F10014", "Gönd: TAYFUN ÇAKIROĞLU mayıs kulüp ücreti", 1500.0)

    # --- kardes: iki cocuk ayni veliye bagli -> onay bekler (supheli)
    ek(16, "F10015", "Gönd: SERHAT KARTAL mayıs ayı aidat", 1500.0)

    # --- aciklamada elle yazilmis T.C.
    ek(17, "F10016", f"{_tc(100000000 + 16 * 1237)} nolu öğrenci aidatı", 1500.0)
    ek(18, "F10017", f"AİDAT {_tc(100000000 + 17 * 1237)}", 1500.0)

    # --- aidat disi gelirler (elenir)
    ek(19, "F20001", "Gönd: SUNA ERGÜVEN SUNA ERGÜVEN Bağış 0046-Akbank T.A.Ş", 5000.0)
    ek(20, "F20002", "KANTİN GELİRİ MAYIS", 4200.0)
    ek(21, "F20003", "KİRA GELİRİ - SPOR SALONU", 8000.0)
    ek(22, "F20004", "FAİZ GELİRİ", 312.45)
    ek(23, "F20005", "AKTARIM - OKUL AİLE BİRLİĞİ", 5000.0)
    ek(24, "F20006", "DENETİM PAYI", 450.0)
    ek(25, "F20007", "MESAJ ÜCRETİ TUTARI", 45.0)
    ek(26, "F20008", "BSMV TUTARI", 12.75)

    # --- giden para (elenir)
    ek(27, "F30001", "AYŞE PERSONEL MAAŞ ÖDEMESİ AYŞE PERSONEL İnternet Havale", -22936.29)
    ek(28, "F30002", "ELEKTRİK FATURASI", -3120.55)
    # isim tutuyor ama para hesaptan CIKMIS: program kendiliginden girmemeli
    ek(29, "F30003", "Gönd: BENGİ YILDIRIMLI Peri YILDIRIMLI fazla ödeme iadesi", -1500.0)
    ek(30, "F30004", "INTERNET SGK( EMS/BAĞ/SSK)/ 00000000000000000000000000 / ", -4210.10)

    # --- listede olmayan kisiler (elenir)
    ek(31, "F40001", "Gönd: AHMET YOLCU havale", 1500.0)
    ek(32, "F40002", "Gönd: NURAY BEKTAŞLI ödeme", 1500.0)
    ek(33, "F40003", "Gönd: HÜSEYİN ARABACI aidat", 1500.0)
    ek(34, "F40004", "Gönd: SEMRA KOÇYİĞİT mayıs", 1500.0)
    ek(35, "F40005", "Gönd: RECEP TANRIVERDİ ödeme", 1500.0)
    ek(36, "F40006", "Gönd: HAVVA SARIOĞLU aidat", 1500.0)
    ek(37, "F40007", "Gönd: İSMAİL KURTULUŞ mayıs", 1500.0)

    # --- bos aciklama (elenir)
    ek(38, "F50001", "", 1500.0)

    # --- kurus hassasiyeti (kesin)
    ek(39, "F50002", "Gönd: SEVİL ULUTÜRK Irmak ULUTÜRK aidat", 1499.99)
    ek(40, "F50003", "Gönd: NALAN ŞENGÜLER Poyraz Eren ŞENGÜLER mayıs", 1500.0)
    ek(41, "F50004", "Gönd: SELDA ARIKBOĞA Zeytin ARIKBOĞA mayıs ayı", 1500.0)
    ek(42, "F50005", "Gönd: İLKNUR MERTOĞLU Alperen MERTOĞLU mayıs aidatı", 1500.0)
    return h


def ekstre_uret(hedef: Path) -> Path:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Hesap Hareketleri"

    # Gercek ekstrelerdeki gibi baslik ustunde bilgi bloklari; boylece
    # baslik satirinin sabit yazilmadigi, aranarak bulundugu dogrulanir.
    ws.append(["Sayın ÖRNEK ANAOKULU OKUL AİLE BİRLİĞİ"])
    ws.append(["01.05.2026 - 30.05.2026 tarihleri arasındaki hesap hareketleri"])
    ws.append([])
    ws.append(["Hesap No: 1234-5678"])
    ws.append(["IBAN: TR00 0000 0000 0000 0000 0000 00"])
    ws.append([])
    ws.append(["Bu dosya TEST amaçlıdır."])
    ws.append(["İçindeki tüm isimler, T.C. numaraları ve hareketler uydurmadır."])
    ws.append([])
    ws.append(["Şube: 0000 - ÖRNEK ŞUBE"])
    ws.append([])
    # 12. satir: baslik
    ws.append(["Tarih", "Fiş No", "Açıklama", "İşlem Tutarı", "Bakiye"])
    for h in ws[12]:
        h.font = Font(bold=True, color="FFFFFF")
        h.fill = PatternFill("solid", fgColor="1F4E79")

    bakiye = 50000.0
    for gun, evrak, aciklama, tutar in _hareketler():
        bakiye += tutar
        ws.append([gun.strftime("%d/%m/%Y"), evrak, aciklama,
                   round(tutar, 2), round(bakiye, 2)])

    for sutun, gen in zip("ABCDE", (13, 12, 52, 15, 15)):
        ws.column_dimensions[sutun].width = gen
    ws.freeze_panes = "A13"
    wb.save(hedef)
    return hedef


def main() -> None:
    liste = liste_uret(KOK / "test_liste.xlsx")
    ekstre = ekstre_uret(KOK / "test_ekstre.xlsx")
    print("uretildi:")
    print("  ", liste.name, f"({len(AILELER)} öğrenci)")
    print("  ", ekstre.name, f"({len(_hareketler())} hareket, başlık 12. satırda)")
    print("\nTum veriler uydurmadir; gercek kisi/kurum bilgisi icermez.")


if __name__ == "__main__":
    main()
