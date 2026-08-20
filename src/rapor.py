# -*- coding: utf-8 -*-
"""
rapor.py — Eslestirme sonucunu insanin bakip anlayacagi ciktilara cevirir.

  html_rapor()  : tek dosyalik, disariya bagimsiz HTML rapor
  excel_cikti() : TC sutunu doldurulmus, TEFBIS'e girilecek liste
  ozet()        : sayisal ozet (arayuzde ve raporda kullanilir)
"""
from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

DURUM_ETIKET = {
    "kesin": ("TEFBİS'e girilecek", "ok"),
    "supheli": ("onayın gerekiyor", "uyari"),
    "girildi": ("daha önce girildi", "gecmis"),
    "yok": ("girilmeyecek", "pas"),
}


def _tutar_yaz(t) -> str:
    if t is None:
        return "-"
    return f"{t:,.2f}".replace(",", "#").replace(".", ",").replace("#", ".")


def ozet(sonuc: list[dict]) -> dict:
    kesin = [s for s in sonuc if s["durum"] == "kesin"]
    return {
        "toplam": len(sonuc),
        "kesin": len(kesin),
        "supheli": sum(1 for s in sonuc if s["durum"] == "supheli"),
        "girildi": sum(1 for s in sonuc if s["durum"] == "girildi"),
        "yok": sum(1 for s in sonuc if s["durum"] == "yok"),
        "toplam_tutar": sum(abs(s["tutar"]) for s in kesin if s["tutar"] is not None),
        "tc_aciklamadan": sum(1 for s in kesin if s.get("kaynak") == "aciklamadaki tc"),
        "tc_isimden": sum(1 for s in kesin if s.get("kaynak") == "isim eslesme"),
        "tc_sutundan": sum(1 for s in kesin if s.get("kaynak") == "ekstredeki TC sutunu"),
    }


# ---------------------------------------------------------------- HTML
_STIL = """
:root{--lacivert:#0f2d4a;--mavi:#1a6fb5;--yesil:#12805c;--sari:#b6791f;
--gri:#5b6b7b;--cizgi:#e2e8f0;--zemin:#f6f8fb;}
*{box-sizing:border-box;}
body{margin:0;padding:32px 24px;background:var(--zemin);color:#16232f;
font-family:'Segoe UI',system-ui,-apple-system,Arial,sans-serif;font-size:14px;}
.sayfa{max-width:1180px;margin:0 auto;}
header{border-bottom:3px solid var(--lacivert);padding-bottom:16px;margin-bottom:8px;}
h1{margin:0 0 6px;font-size:23px;color:var(--lacivert);letter-spacing:-.2px;}
.altbaslik{color:var(--gri);font-size:13px;}
.rozet{display:inline-block;background:var(--lacivert);color:#fff;font-size:11px;
font-weight:600;padding:3px 9px;border-radius:11px;letter-spacing:.4px;margin-left:8px;
vertical-align:middle;}
.kartlar{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
gap:14px;margin:22px 0 26px;}
.kart{background:#fff;border:1px solid var(--cizgi);border-radius:10px;padding:16px 18px;
border-top:3px solid var(--mavi);}
.kart.ok{border-top-color:var(--yesil);} .kart.uyari{border-top-color:var(--sari);}
.kart.pas{border-top-color:var(--gri);} .kart.gecmis{border-top-color:#3a5f9e;}
.kart .sayi{font-size:30px;font-weight:700;color:var(--lacivert);line-height:1.1;}
.kart .etiket{font-size:12px;color:var(--gri);margin-top:5px;}
h2{font-size:16px;color:var(--lacivert);margin:30px 0 10px;
border-left:4px solid var(--mavi);padding-left:10px;}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--cizgi);
border-radius:8px;overflow:hidden;}
th{background:var(--lacivert);color:#fff;text-align:left;font-size:12px;font-weight:600;
padding:10px 11px;white-space:nowrap;}
td{padding:9px 11px;border-top:1px solid var(--cizgi);vertical-align:top;}
tbody tr:nth-child(even){background:#fafcfe;}
.sag{text-align:right;white-space:nowrap;}
.tc{font-family:Consolas,monospace;letter-spacing:.4px;}
.ad{font-weight:600;}
.ham{color:var(--gri);font-size:12px;line-height:1.45;}
.etiketli{display:inline-block;font-size:11px;font-weight:600;padding:2px 8px;
border-radius:10px;white-space:nowrap;}
.e-ok{background:#e3f5ee;color:var(--yesil);}
.e-uyari{background:#fdf3e0;color:var(--sari);}
.e-pas{background:#eef1f5;color:var(--gri);}
.e-gecmis{background:#e8effa;color:#3a5f9e;}
.nasil{font-size:11px;color:var(--gri);margin-top:3px;}
footer{margin-top:34px;padding-top:16px;border-top:1px solid var(--cizgi);
color:var(--gri);font-size:12px;line-height:1.7;}
.not{background:#fff8e6;border:1px solid #f0dca8;border-left:4px solid var(--sari);
border-radius:6px;padding:12px 15px;margin:18px 0;font-size:13px;line-height:1.6;}
"""


def _kart(sayi, etiket, sinif=""):
    return (f'<div class="kart {sinif}"><div class="sayi">{sayi}</div>'
            f'<div class="etiket">{etiket}</div></div>')


def html_rapor(sonuc: list[dict], hedef: str | Path, *, baslik: str,
               kaynak_dosya: str = "", demo_notu: bool = False,
               ust_bilgi: dict | None = None) -> Path:
    """Eslestirme sonucunu tek dosyalik HTML rapora yazar."""
    o = ozet(sonuc)
    ust_bilgi = ust_bilgi or {}
    girilecek = [s for s in sonuc if s["durum"] == "kesin"]
    onay = [s for s in sonuc if s["durum"] == "supheli"]
    gecmis = [s for s in sonuc if s["durum"] == "girildi"]
    disarida = [s for s in sonuc if s["durum"] == "yok"]

    p = []
    p.append("<!doctype html><html lang='tr'><head><meta charset='utf-8'>")
    p.append(f"<title>{html.escape(baslik)}</title><style>{_STIL}</style></head><body>")
    p.append("<div class='sayfa'><header>")
    p.append(f"<h1>{html.escape(baslik)}"
             + ("<span class='rozet'>DEMO</span>" if demo_notu else "") + "</h1>")
    tarih = datetime.now().strftime("%d.%m.%Y %H:%M")
    kaynak = f" &middot; kaynak: {html.escape(Path(kaynak_dosya).name)}" if kaynak_dosya else ""
    p.append(f"<div class='altbaslik'>oluşturulma: {tarih}{kaynak}</div>")

    kurum_satiri = []
    if ust_bilgi.get("kurum"):
        kurum_satiri.append(f"<b>{html.escape(ust_bilgi['kurum'])}</b>")
    if ust_bilgi.get("donem"):
        kurum_satiri.append(f"dönem: {html.escape(ust_bilgi['donem'])}")
    if ust_bilgi.get("hesap_no"):
        kurum_satiri.append(f"hesap: {html.escape(ust_bilgi['hesap_no'])}")
    if kurum_satiri:
        p.append("<div class='altbaslik' style='margin-top:5px'>"
                 + " &middot; ".join(kurum_satiri) + "</div>")
    p.append("</header>")

    p.append("<div class='kartlar'>")
    p.append(_kart(o["toplam"], "ekstredeki hareket"))
    p.append(_kart(o["kesin"], "TEFBİS'e girilecek kayıt", "ok"))
    p.append(_kart(o["supheli"], "onayın beklenen kayıt", "uyari"))
    if o.get("girildi"):
        p.append(_kart(o["girildi"], "daha önce girilmiş kayıt", "gecmis"))
    p.append(_kart(o["yok"], "aidat olmadığı için elenen", "pas"))
    p.append("</div>")

    if demo_notu:
        p.append("<div class='not'><b>Bu bir demo çıktısıdır.</b> Gönderdiğiniz Mayıs "
                 "ekstresi hiç elle düzeltilmeden, olduğu gibi okundu. "
                 "T.C. numaraları <b>örnek listeden</b> gelmektedir — gerçek öğrenci "
                 "kimlik numarası kullanılmamıştır. Tutarlar dosyada sizin tarafınızdan "
                 "maskelendiği için aynı görünüyor; program gerçek tutarları da aynı "
                 "şekilde okur. Gerçek kullanımda kendi öğrenci listeniz okunur ve "
                 "veriler bilgisayarınızdan hiçbir yere gönderilmez.</div>")

    # --- girilecek kayitlar
    p.append(f"<h2>TEFBİS'e girilecek kayıtlar ({len(girilecek)})</h2>")
    p.append("<table><thead><tr><th>Tarih</th><th>Evrak No</th><th>Öğrenci</th>"
             "<th>T.C. No</th><th class='sag'>Tutar</th><th>Durum</th>"
             "<th>Ekstredeki açıklama</th></tr></thead><tbody>")
    for s in girilecek:
        nasil = {
            "aciklamadaki tc": "açıklamada T.C. yazılmış",
            "ekstredeki TC sutunu": "T.C. sütununa siz yazmışsınız",
            "hafiza": "daha önce onayladınız",
            "kullanıcı onayı": "sizin onayınızla",
        }.get(s["kaynak"], f"isimden eşleşti (%{s['skor']:.0f})")
        p.append(
            f"<tr><td>{s['tarih'].strftime('%d.%m.%Y')}</td>"
            f"<td>{html.escape(s['evrak_no'])}</td>"
            f"<td class='ad'>{html.escape(s['cocuk_ad'])}</td>"
            f"<td class='tc'>{html.escape(s['tc'])}</td>"
            f"<td class='sag'>{_tutar_yaz(s['tutar'])}</td>"
            f"<td><span class='etiketli e-ok'>hazır</span>"
            f"<div class='nasil'>{nasil}</div></td>"
            f"<td class='ham'>{html.escape(s['aciklama'][:110])}</td></tr>")
    p.append("</tbody></table>")

    # --- onay bekleyenler
    if onay:
        p.append(f"<h2>Emin olunamayan, onayınızı bekleyen kayıtlar ({len(onay)})</h2>")
        p.append("<table><thead><tr><th>Tarih</th><th>Evrak No</th>"
                 "<th>Program ne düşünüyor</th><th class='sag'>Tutar</th>"
                 "<th>Ekstredeki açıklama</th></tr></thead><tbody>")
        for s in onay:
            adaylar = ", ".join(f"{ad} (%{sk:.0f})" for sk, ad in s["adaylar"][:2])
            p.append(
                f"<tr><td>{s['tarih'].strftime('%d.%m.%Y')}</td>"
                f"<td>{html.escape(s['evrak_no'])}</td>"
                f"<td><span class='etiketli e-uyari'>onay bekliyor</span>"
                f"<div class='nasil'>{html.escape(adaylar)}</div></td>"
                f"<td class='sag'>{_tutar_yaz(s['tutar'])}</td>"
                f"<td class='ham'>{html.escape(s['aciklama'][:110])}</td></tr>")
        p.append("</tbody></table>")

    # --- daha once girilmis olanlar
    if gecmis:
        p.append(f"<h2>Daha önce TEFBİS'e girilmiş kayıtlar ({len(gecmis)})</h2>")
        p.append("<table><thead><tr><th>Tarih</th><th>Evrak No</th><th>Öğrenci</th>"
                 "<th>T.C. No</th><th class='sag'>Tutar</th><th>Durum</th>"
                 "</tr></thead><tbody>")
        for s2 in gecmis:
            p.append(
                f"<tr><td>{s2['tarih'].strftime('%d.%m.%Y')}</td>"
                f"<td>{html.escape(s2['evrak_no'])}</td>"
                f"<td class='ad'>{html.escape(s2['cocuk_ad'])}</td>"
                f"<td class='tc'>{html.escape(s2['tc'])}</td>"
                f"<td class='sag'>{_tutar_yaz(s2['tutar'])}</td>"
                f"<td><span class='etiketli e-gecmis'>tekrar girilmeyecek</span></td>"
                f"</tr>")
        p.append("</tbody></table>")

    # --- elenenler
    p.append(f"<h2>Aidat olmadığı için girilmeyen hareketler ({len(disarida)})</h2>")
    p.append("<table><thead><tr><th>Tarih</th><th>Evrak No</th><th>Neden girilmedi</th>"
             "<th class='sag'>Tutar</th><th>Ekstredeki açıklama</th></tr></thead><tbody>")
    for s in disarida:
        p.append(
            f"<tr><td>{s['tarih'].strftime('%d.%m.%Y')}</td>"
            f"<td>{html.escape(s['evrak_no'])}</td>"
            f"<td><span class='etiketli e-pas'>{html.escape(s['sebep'])}</span></td>"
            f"<td class='sag'>{_tutar_yaz(s['tutar'])}</td>"
            f"<td class='ham'>{html.escape(s['aciklama'][:110])}</td></tr>")
    p.append("</tbody></table>")

    if o["tc_aciklamadan"]:
        nasil_ozet = (f"Açıklamasına T.C. yazılmış {o['tc_aciklamadan']} kayıt doğrudan "
                      f"alındı ve kimlik algoritmasıyla doğrulandı, {o['tc_isimden']} "
                      "kayıt öğrenci listesindeki isimle eşleştirildi.")
    else:
        nasil_ozet = (f"Bu ekstrede hiçbir veli açıklamaya T.C. yazmamış; {o['tc_isimden']} "
                      "kaydın tamamı öğrenci listesindeki isimlerle bulundu. Bir veli "
                      "açıklamaya T.C. yazdığında program onu doğrudan alır ve kimlik "
                      "algoritmasıyla doğrular.")
    p.append("<footer>" + nasil_ozet +
             " Yazım hataları, ismin başta veya sonda yazılması ve banka açıklama "
             "farklılıkları programın kendisi tarafından tolere edilir.<br>"
             "Veriler bu bilgisayarın dışına çıkmaz, hiçbir sunucuya gönderilmez."
             "</footer></div></body></html>")

    yol = Path(hedef)
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text("\n".join(p), encoding="utf-8")
    return yol


# --------------------------------------------------------------- Excel
def excel_cikti(sonuc: list[dict], hedef: str | Path) -> Path:
    """TC sutunu doldurulmus, TEFBIS'e girilecek listeyi Excel'e yazar."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "TEFBIS Kayitlari"

    basliklar = ["Tarih", "Evrak No", "Öğrenci", "T.C. No", "Tutar",
                 "Durum", "Nasıl bulundu", "Ekstredeki açıklama"]
    ws.append(basliklar)
    for h in ws[1]:
        h.font = Font(bold=True, color="FFFFFF")
        h.fill = PatternFill("solid", fgColor="0F2D4A")
        h.alignment = Alignment(horizontal="center", vertical="center")

    renk = {"kesin": "E3F5EE", "supheli": "FDF3E0", "girildi": "E8EFFA",
            "yok": "F1F3F6"}
    for s in sonuc:
        etiket = DURUM_ETIKET[s["durum"]][0]
        ws.append([s["tarih"], s["evrak_no"], s["cocuk_ad"], s["tc"], s["tutar"],
                   etiket, s["sebep"], s["aciklama"]])
        for h in ws[ws.max_row]:
            h.fill = PatternFill("solid", fgColor=renk[s["durum"]])
        ws.cell(ws.max_row, 1).number_format = "DD.MM.YYYY"
        ws.cell(ws.max_row, 4).number_format = "@"
        ws.cell(ws.max_row, 5).number_format = "#,##0.00"

    for i, g in enumerate((12, 12, 24, 15, 13, 20, 30, 70), start=1):
        ws.column_dimensions[get_column_letter(i)].width = g
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:H{ws.max_row}"

    yol = Path(hedef)
    yol.parent.mkdir(parents=True, exist_ok=True)
    wb.save(yol)
    return yol
