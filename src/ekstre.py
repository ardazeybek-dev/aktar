# -*- coding: utf-8 -*-
"""
ekstre.py — Banka ekstresi (xlsx) okuma katmani.

Sorumluluk: dosyayi acmak, basligi bulmak, gecerli hareket satirlarini
normalize edilmis sozluk listesi olarak dondurmek.
Eslestirme/TC isi bu modulun disinda (bkz. eslestir.py).
"""
from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

import openpyxl

from excel_ac import calisma_kitabi_ac, temizle

# Ekstre basligindaki sutunlarin hangi anahtar kelimeyle bulunacagi
SUTUN_ANAHTARLARI = {
    "tarih": ("tarih",),
    "evrak_no": ("fiş no", "fis no", "evrak", "dekont", "işlem no", "islem no"),
    "aciklama": ("açıklama", "aciklama"),
    "tutar": ("işlem tutarı", "islem tutari", "tutar"),
    "bakiye": ("bakiye",),
    # Kullanicinin ekstreye kendi ekledigi T.C. sutunu (varsa oncelikle kullanilir)
    "tc_sutunu": ("t.c", "tc kimlik", "tckn", "kimlik no", "tc no"),
}

# Alt bilgi / uyari metinlerini yakalamak icin (bu satirlar hareket degildir)
DIP_NOT_IZLERI = (
    "taraflar arasında", "merkez:", "ticaret sicil", "www.", "borç:", "alacak:",
)


class EkstreHatasi(Exception):
    """Ekstre okunamadiginda kullaniciya gosterilecek anlasilir hata."""


def _metin(hucre) -> str:
    return "" if hucre is None else str(hucre).strip()


def baslik_satirini_bul(ws, tarama_derinligi: int = 30) -> tuple[int, dict[str, int]]:
    """Basligi tarayarak bulur; sabit satir numarasi varsaymaz.

    Doner: (baslik_satir_no, {alan_adi: sutun_indeksi})
    """
    for i, row in enumerate(ws.iter_rows(min_row=1, max_row=tarama_derinligi,
                                         values_only=True), start=1):
        hucreler = [_metin(c).lower() for c in row]
        if not any("tarih" == h or h.startswith("tarih") for h in hucreler):
            continue
        if not any("çıklama" in h or "ciklama" in h for h in hucreler):
            continue

        harita: dict[str, int] = {}
        for alan, anahtarlar in SUTUN_ANAHTARLARI.items():
            for idx, h in enumerate(hucreler):
                if not h:
                    continue
                if any(a in h for a in anahtarlar):
                    harita.setdefault(alan, idx)
                    break
        if "tarih" in harita and "aciklama" in harita:
            return i, harita

    raise EkstreHatasi(
        "Ekstrede baslik satiri bulunamadi. Dosyanin bankadan indirilen "
        "hesap hareketleri dosyasi oldugundan emin olun."
    )


def tarih_parse(v):
    """Hucreyi date'e cevirir. Hem datetime hem 'dd.mm.yyyy' metnini kabul eder."""
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = _metin(v)
    for kalip in ("%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%y"):
        try:
            return datetime.strptime(s, kalip).date()
        except ValueError:
            continue
    return None


def tutar_parse(v):
    """Turkce sayi formatini float'a cevirir.

    '-22.936,29' -> -22936.29   |   '1.250,00 TL' -> 1250.0
    Hucre zaten sayiysa oldugu gibi doner (str'e cevirip nokta silme tuzagi yok).
    """
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)

    s = _metin(v)
    if not s:
        return None
    s = re.sub(r"[^\d,.\-+]", "", s)          # TL, bosluk, para simgesi vs. at
    if not s:
        return None

    if "," in s and "." in s:                  # 22.936,29 -> binlik nokta + ondalik virgul
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:                             # 936,29
        s = s.replace(",", ".")
    # sadece nokta varsa: 22.936 mi 22.936 TL mi? son parca 3 hane ise binliktir
    elif s.count(".") >= 1:
        parcalar = s.split(".")
        if len(parcalar[-1]) == 3:
            s = "".join(parcalar)
    try:
        return float(s)
    except ValueError:
        return None


def _dip_not_mu(aciklama: str) -> bool:
    d = aciklama.lower()
    return any(iz in d for iz in DIP_NOT_IZLERI)


def ust_bilgi_oku(dosya: str | Path) -> dict:
    """Ekstrenin baslik ustundeki kurum/hesap/donem bilgisini toplar.

    Hicbiri bulunamazsa bos alanlar doner; rapor bunlarsiz da calisir.
    """
    try:
        wb, gecici = calisma_kitabi_ac(Path(dosya))
    except Exception:
        return {"kurum": "", "donem": "", "hesap_no": "", "iban": ""}
    ws = wb.active
    bilgi = {"kurum": "", "donem": "", "hesap_no": "", "iban": ""}

    for row in ws.iter_rows(min_row=1, max_row=20, values_only=True):
        hucreler = [_metin(c) for c in row if _metin(c)]
        if not hucreler:
            continue
        satir = " ".join(hucreler)
        d = satir.lower()

        if not bilgi["kurum"] and d.startswith("sayın"):
            bilgi["kurum"] = satir.split(" ", 1)[1].strip()
        elif not bilgi["donem"] and "tarihleri aras" in d:
            m = re.search(r"(\d{2}\.\d{2}\.\d{4})\s*-\s*(\d{2}\.\d{2}\.\d{4})", satir)
            if m:
                bilgi["donem"] = f"{m.group(1)} - {m.group(2)}"
        elif not bilgi["hesap_no"] and "hesap numaras" in d:
            bilgi["hesap_no"] = hucreler[-1].strip()
        elif not bilgi["iban"] and "iban" in d:
            m = re.search(r"TR\d{24}", satir)
            if m:
                bilgi["iban"] = m.group(0)

        if "açıklama" in d and "tarih" in d:
            break

    wb.close()
    return bilgi


def satirlari_oku(dosya: str | Path) -> list[dict]:
    """Ekstredeki gecerli hareket satirlarini dondurur.

    Her satir: {satir_no, tarih, evrak_no, aciklama, tutar}
    Tarihi cozulemeyen / aciklamasi bos / dip not olan satirlar atlanir.
    """
    yol = Path(dosya)
    if not yol.exists():
        raise EkstreHatasi(f"Dosya bulunamadi: {yol}")

    try:
        wb, gecici = calisma_kitabi_ac(yol)
    except Exception as e:                      # bozuk/xls dosyasi
        raise EkstreHatasi(f"Excel dosyasi acilamadi: {e}") from e

    ws = wb.active
    baslik, harita = baslik_satirini_bul(ws)

    def al(row, alan):
        idx = harita.get(alan)
        if idx is None or idx >= len(row):
            return None
        return row[idx]

    kayitlar: list[dict] = []
    for satir_no, row in enumerate(
        ws.iter_rows(min_row=baslik + 1, values_only=True), start=baslik + 1
    ):
        aciklama = _metin(al(row, "aciklama"))
        if _dip_not_mu(aciklama):
            continue
        tarih = tarih_parse(al(row, "tarih"))
        if tarih is None:
            continue                            # tarihi olmayan satir hareket degildir
        # Aciklama BOS olabilir (veli hicbir sey yazmamis olabilir). Boyle bir
        # satir atlanmaz; kullaniciya gosterilir ki gozden kacmasin.

        kayitlar.append({
            "satir_no": satir_no,
            "tarih": tarih,
            "evrak_no": _metin(al(row, "evrak_no")),
            "aciklama": aciklama,
            "tutar": tutar_parse(al(row, "tutar")),
            # kullanici ekstreye elle T.C. yazdiysa buradan gelir
            "tc_sutunu": re.sub(r"\D", "", _metin(al(row, "tc_sutunu"))),
        })

    wb.close()
    if not kayitlar:
        raise EkstreHatasi("Ekstrede islenebilir hareket satiri bulunamadi.")
    return kayitlar


if __name__ == "__main__":
    import sys
    for k in satirlari_oku(sys.argv[1]):
        print(k["tarih"], k["evrak_no"], (k["tutar"] or 0), k["aciklama"][:60])
