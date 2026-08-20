# -*- coding: utf-8 -*-
"""
excel_ac.py — Bozuk bicimlendirmeli Excel dosyalarini da acabilen okuyucu.

NEDEN VAR:
Baska programlarla uretilmis ya da donusturulmus .xlsx dosyalarinda
(Google Sheets, LibreOffice, eski Excel'den kaydedilmis, banka ekranindan
disari aktarilmis dosyalar) openpyxl'in tanimadigi dolgu/yazitipi/kenarlik
tanimlari bulunabiliyor ve dosya hic acilmiyor:

    expected <class 'openpyxl.styles.fills.Fill'>

Veri bu tanimlarla ilgili degil - bunlar sadece hucrenin GORUNUSU. Bu yuzden
dosya acilamazsa, gecici bir kopyasinda yalnizca GORSEL stil bloklari
(fills / fonts / borders) varsayilanlariyla degistirilip yeniden denenir.

ONEMLI: sayi bicimleri (numFmts) ve hucre-stil eslemesi (cellXfs) ASLA
silinmez. Excel'de tarihler sayi olarak saklanir, tarih olduklari sayi
bicimlerinden anlasilir; o blok bozulursa tarihler 45900 gibi okunurdu.
Ayrica blok sayilari korunur, boylece cellXfs'teki fillId/fontId/borderId
referanslari gecerli kalir.
"""
from __future__ import annotations

import atexit
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

import openpyxl

# Acilan gecici kopyalar. read_only modda openpyxl dosyayi tembel okur,
# bu yuzden hemen silinemez; program kapanirken hepsi temizlenir.
_GECICILER = []

# Bozuk blogun yerine konacak, her zaman gecerli varsayilanlar
_VARSAYILAN = {
    b"fills": b'<fill><patternFill patternType="none"/></fill>',
    b"fonts": b'<font><sz val="11"/><name val="Calibri"/></font>',
    b"borders": b"<border><left/><right/><top/><bottom/><diagonal/></border>",
}


def _blogu_sifirla(styles_xml: bytes, blok: bytes) -> bytes:
    """Bir stil blogunu ayni sayida varsayilan ogeyle degistirir."""
    kalip = re.compile(rb"<" + blok + rb"[^>]*?(?:/>|>.*?</" + blok + rb">)",
                       re.DOTALL)
    eslesme = kalip.search(styles_xml)
    if not eslesme:
        return styles_xml

    sayi_eslesme = re.search(rb'count="(\d+)"', eslesme.group(0))
    adet = int(sayi_eslesme.group(1)) if sayi_eslesme else 1
    adet = max(1, min(adet, 10000))          # akil disi degerlere karsi

    yeni = (b"<" + blok + b' count="' + str(adet).encode() + b'">'
            + _VARSAYILAN[blok] * adet
            + b"</" + blok + b">")
    return kalip.sub(yeni, styles_xml, count=1)


def _stilleri_sadelestir(kaynak: Path) -> Path:
    """Gorsel stilleri varsayilana cekilmis gecici bir kopya uretir."""
    gecici = Path(tempfile.mkdtemp(prefix="tefbis_xlsx_")) / kaynak.name
    with zipfile.ZipFile(kaynak) as girdi, \
            zipfile.ZipFile(gecici, "w", zipfile.ZIP_DEFLATED) as cikti:
        for oge in girdi.infolist():
            veri = girdi.read(oge.filename)
            if oge.filename == "xl/styles.xml":
                for blok in (b"fills", b"fonts", b"borders"):
                    veri = _blogu_sifirla(veri, blok)
            cikti.writestr(oge.filename, veri)
    return gecici


def calisma_kitabi_ac(dosya, *, data_only=True, read_only=True):
    """Excel dosyasini acar; bicimlendirme bozuksa onarilmis kopyasini acar.

    Doner: (calisma_kitabi, temizlenecek_klasor)
    temizlenecek_klasor None degilse, is bitince silinmelidir.
    """
    yol = Path(dosya)
    try:
        return openpyxl.load_workbook(yol, data_only=data_only,
                                      read_only=read_only), None
    except Exception as ilk_hata:
        # Bozuk stil belirtisi mi, yoksa gercekten okunamaz bir dosya mi?
        try:
            onarilmis = _stilleri_sadelestir(yol)
        except Exception:
            raise ilk_hata
        try:
            wb = openpyxl.load_workbook(onarilmis, data_only=data_only,
                                        read_only=read_only)
        except Exception:
            shutil.rmtree(onarilmis.parent, ignore_errors=True)
            raise ilk_hata          # kullaniciya ilk, anlamli hatayi goster
        # Windows dosyayi acik oldugu surece kilitler; silmeden once
        # calisma kitabini kapatabilmek icin referansini da tutuyoruz.
        _GECICILER.append((onarilmis.parent, wb))
        return wb, onarilmis.parent


def temizle(klasor=None) -> None:
    """Gecici kopyalari siler. Klasor verilmezse hepsini temizler."""
    for kayit in list(_GECICILER):
        yol, wb = kayit
        if klasor is not None and Path(yol) != Path(klasor):
            continue
        try:
            wb.close()               # Windows'ta kilidi birakmasi icin sart
        except Exception:
            pass
        shutil.rmtree(yol, ignore_errors=True)
        _GECICILER.remove(kayit)


atexit.register(temizle)
