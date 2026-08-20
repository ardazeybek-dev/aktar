# -*- coding: utf-8 -*-
"""
eslestir.py — Ekstre aciklamasindan cocugu ve TC'yi bulma katmani.

Iki yol vardir:
  1) Veli aciklamaya TC yazmissa: 11 haneli sayiyi cek, MERNIS ile dogrula.
  2) Yazmamissa: cocuk-TC listesindeki isimleri aciklama icinde bulanik ara.

Cikti her zaman bir durum tasir: kesin / supheli / yok.
Supheli olan ASLA otomatik TEFBIS'e girilmez, kullaniciya sorulur.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import openpyxl

from excel_ac import calisma_kitabi_ac, temizle
from rapidfuzz import fuzz

# --- esikler ------------------------------------------------------------
ESIK_KESIN = 88      # bu skorun ustu otomatik kabul
ESIK_SUPHE = 72      # bu skorun ustu kullaniciya sorulur, alti eslesmedi sayilir
FARK_ESIGI = 6       # en iyi ile ikinci aday arasindaki fark bundan azsa: supheli

# --- aciklamadaki banka/aidat gurultusu ---------------------------------
AYLAR = ("ocak", "subat", "mart", "nisan", "mayis", "haziran", "temmuz",
         "agustos", "eylul", "ekim", "kasim", "aralik")

GURULTU_KELIMELER = AYLAR + (
    "gond", "gonderen", "aciklama", "ayi", "ay", "aylik", "aylig",
    "kulup", "kulub", "klup", "klub", "kulubu", "kulubune", "cocuk", "cocugu",
    "aidat", "aidati", "aydat", "aydati", "ucret", "ucreti", "ucretleri",
    "odeme", "odemesi", "odemeleri", "tahsilat", "tahsilati", "havale", "eft",
    "fast", "islemi", "islem", "ziraat", "mobil", "internet", "bankasi",
    "banka", "bank", "katilim", "sube", "hesap", "iban", "tr", "as", "ao",
    "taahhut", "yatirilan", "yatan", "bakiye", "dekont", "referansli",
    "referans", "sn", "adina", "icin", "ve", "ile", "toki", "anaokulu",
    "okul", "aile", "birligi", "nolu", "tutari", "tutar",
)

# Aciklamanin banka kuyrugunu kesen isaretler (bunlardan sonrasi hep gurultudur)
KUYRUK_KALIPLARI = re.compile(
    r"(\d{4}\s*-\s*[A-Za-zÇĞİÖŞÜçğıöşü]"
    r"|FAST işlemi|Ziraat Mobil|İnternet Havale|internet havale|/TR\d{2}|TR\d{24})",
    re.IGNORECASE)


# Aciklamada bunlardan biri gecerse satir aidat OLMAYABILIR: isim tutsa bile
# otomatik girilmez, kullaniciya sorulur. (Musterinin ekstresinde 15.000 TL'lik
# "Fatime Simsek Bagis" satiri var; velinin soyadi listede oldugu icin bir
# ogrenciye benziyor ama aidat degil.)
AIDAT_DISI_SINYALLER = (
    (r"\bbagis\w*", "bağış"),
    (r"\bkantin\w*", "kantin geliri"),
    (r"\bkira(?:si|lari|lar|lama)?\b", "kira geliri"),
    (r"\bfaiz(?:i|leri)?\b", "faiz geliri"),
    (r"\baktarim\w*", "aktarım"),
    (r"\bdenetim pay\w*", "denetim payı"),
)


def aidat_disi_sinyal(aciklama: str) -> str:
    """Aciklamada aidat disi bir gelir isareti varsa okunabilir adini dondurur.

    Kalip sonlari kelime siniriyla korunur: 'KIRAZ' soyadi 'kira' sinyalini
    tetiklemez, ama 'kirasi' tetikler.
    """
    n = normalize(aciklama)
    for kalip, ad in AIDAT_DISI_SINYALLER:
        if re.search(kalip, n):
            return ad
    return ""


class EslestirmeHatasi(Exception):
    """Kullaniciya gosterilecek anlasilir eslestirme hatasi."""


# --- yardimcilar --------------------------------------------------------
def normalize(metin: str) -> str:
    """Turkce metni karsilastirilabilir hale getirir: kucuk harf, aksansiz."""
    if not metin:
        return ""
    m = metin.replace("İ", "i").replace("I", "ı").replace("ı", "i")
    m = m.lower()
    degisim = {"ş": "s", "ğ": "g", "ü": "u", "ö": "o",
               "ç": "c", "â": "a", "î": "i", "û": "u"}
    for k, v in degisim.items():
        m = m.replace(k, v)
    m = unicodedata.normalize("NFKD", m)
    m = "".join(c for c in m if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", m).strip()


def tc_gecerli_mi(tc: str) -> bool:
    """T.C. kimlik numarasi checksum dogrulamasi (MERNIS algoritmasi)."""
    if not (isinstance(tc, str) and len(tc) == 11 and tc.isdigit() and tc[0] != "0"):
        return False
    h = [int(c) for c in tc]
    tek = h[0] + h[2] + h[4] + h[6] + h[8]
    cift = h[1] + h[3] + h[5] + h[7]
    if (tek * 7 - cift) % 10 != h[9]:
        return False
    return sum(h[:10]) % 10 == h[10]


def aciklamadan_tc_cek(aciklama: str) -> str | None:
    """Aciklamada gecen gecerli bir TC varsa dondurur.

    Sadece MERNIS'e uyan aday kabul edilir; boylece IBAN/referans icindeki
    rastgele 11 hane yanlislikla TC sanilmaz.
    """
    for aday in re.findall(r"(?<!\d)(\d{11})(?!\d)", aciklama):
        if tc_gecerli_mi(aday):
            return aday
    return None


def _anlamli_tokenlar(metin: str) -> list[str]:
    """Aciklamayi isim adayi tokenlara indirger (banka/aidat gurultusu atilir)."""
    kesik = KUYRUK_KALIPLARI.split(metin)[0]
    n = normalize(kesik)
    n = re.sub(r"[^\w\s]", " ", n)
    return [t for t in n.split()
            if len(t) > 1 and not t.isdigit() and t not in GURULTU_KELIMELER]


# --- cocuk listesi ------------------------------------------------------
AD_BASLIKLARI = ("ad soyad", "adi soyadi", "ogrenci", "cocuk", "isim", "ad")
TC_BASLIKLARI = ("tc", "t.c", "kimlik", "tckn")

# Okul kayit formlarinda ogrencinin yaninda ANNE ve BABA bilgileri de bulunur
# (6 sutunlu liste). Bu sutunlar ogrenci sanilmamali; veli olarak kullanilmali.
VELI_BASLIKLARI = ("veli", "anne", "baba", "ana ", "vasi")
OGRENCI_ISARETLERI = ("ogrenci", "cocuk", "talebe")


def _veli_sutunu_mu(baslik: str) -> bool:
    return any(a in baslik for a in VELI_BASLIKLARI)


def cocuk_listesi_yukle(dosya: str | Path) -> list[dict]:
    """Cocuk-TC listesini okur.

    Beklenen sutunlar (basliktan bulunur, sirasi onemli degil):
      Ad Soyad (veya Ogrenci/Cocuk) + TC. Opsiyonel: Veli Ad Soyad, Veli TC.
    """
    yol = Path(dosya)
    if not yol.exists():
        raise EslestirmeHatasi("Cocuk listesi bulunamadi: %s" % yol)

    try:
        wb, gecici = calisma_kitabi_ac(yol)
    except Exception as e:
        raise EslestirmeHatasi("Ogrenci listesi acilamadi: %s" % e) from e
    ws = wb.active

    baslik_no, sut = None, {}
    for i, row in enumerate(ws.iter_rows(min_row=1, max_row=15, values_only=True), 1):
        hucreler = [normalize(str(c)) if c is not None else "" for c in row]

        def tc_sutunu(h):
            return bool(h) and any(a in h for a in TC_BASLIKLARI)

        def ad_sutunu(h):
            return bool(h) and any(a in h for a in AD_BASLIKLARI) and not tc_sutunu(h)

        # 1) Once acikca "Ogrenci"/"Cocuk" yazan sutunlar aranir; boylece
        #    "Anne Ad Soyad" listenin basinda olsa bile ogrenci sanilmaz.
        ad_idx = next((j for j, h in enumerate(hucreler)
                       if ad_sutunu(h) and not _veli_sutunu_mu(h)
                       and any(a in h for a in OGRENCI_ISARETLERI)), None)
        tc_idx = next((j for j, h in enumerate(hucreler)
                       if tc_sutunu(h) and not _veli_sutunu_mu(h)
                       and any(a in h for a in OGRENCI_ISARETLERI)), None)

        # 2) Bulunamazsa: veli/anne/baba OLMAYAN ilk ad ve TC sutunu
        if ad_idx is None:
            ad_idx = next((j for j, h in enumerate(hucreler)
                           if ad_sutunu(h) and not _veli_sutunu_mu(h)), None)
        if tc_idx is None:
            tc_idx = next((j for j, h in enumerate(hucreler)
                           if tc_sutunu(h) and not _veli_sutunu_mu(h)), None)

        if tc_idx is not None and ad_idx is not None:
            baslik_no = i
            sut = {"ad": ad_idx, "tc": tc_idx}
            # Veli sutunlarinin HEPSI toplanir (anne + baba + veli).
            # Parayi hangisi yatirirsa yatirsin cocuga ulasilabilsin diye.
            sut["veli_adlari"] = [j for j, h in enumerate(hucreler)
                                  if _veli_sutunu_mu(h) and not tc_sutunu(h)]
            sut["veli_tcleri"] = [j for j, h in enumerate(hucreler)
                                  if _veli_sutunu_mu(h) and tc_sutunu(h)]
            break

    if baslik_no is None:
        raise EslestirmeHatasi(
            "Cocuk listesinde 'Ad Soyad' ve 'TC' sutunlari bulunamadi. "
            "Ornek dosyadaki basliklari kullanin.")

    cocuklar: list[dict] = []
    for row in ws.iter_rows(min_row=baslik_no + 1, values_only=True):
        def hucre(anahtar):
            j = sut.get(anahtar)
            if j is None or j >= len(row) or row[j] is None:
                return ""
            return str(row[j]).strip()

        def sutun(j):
            if j is None or j >= len(row) or row[j] is None:
                return ""
            return str(row[j]).strip()

        ad = hucre("ad")
        tc = re.sub(r"\D", "", hucre("tc"))
        if not ad or not tc:
            continue

        veli_adlari = [sutun(j) for j in sut.get("veli_adlari", [])]
        veli_adlari = [v for v in veli_adlari if v]
        veli_tcleri = [re.sub(r"\D", "", sutun(j))
                       for j in sut.get("veli_tcleri", [])]
        veli_tcleri = [v for v in veli_tcleri if v]

        cocuklar.append({
            "ad_soyad": ad,
            "tc": tc,
            # geriye uyumluluk: tek veli alani ilk bulunani tutar
            "veli_ad": veli_adlari[0] if veli_adlari else "",
            "veli_tc": veli_tcleri[0] if veli_tcleri else "",
            "veli_adlari": veli_adlari,      # anne + baba + veli hepsi
            "veli_tcleri": veli_tcleri,
            "_tokenlar": [t for t in normalize(ad).split() if len(t) > 1],
            "_veli_tokenlar": [t for t in normalize(veli_adlari[0]).split()
                               if len(t) > 1] if veli_adlari else [],
            "_veli_token_listesi": [
                [t for t in normalize(v).split() if len(t) > 1]
                for v in veli_adlari],
        })
    wb.close()

    if not cocuklar:
        raise EslestirmeHatasi("Cocuk listesi bos gorunuyor (ad + TC dolu satir yok).")
    return cocuklar


# --- eslestirme cekirdegi ----------------------------------------------
def _cocuk_skoru(cocuk_tokenlari: list[str], aciklama_tokenlari: list[str]) -> float:
    """Cocugun her ad parcasini aciklamada arar, agirlikli skor uretir.

    Ilk ad ve soyad tam agirlikli, ortadaki ikinci ad yari agirlikli tartilir.
    Boylece sadece soyadi tutan veli ismi cocuk sanilmaz.
    """
    if not cocuk_tokenlari or not aciklama_tokenlari:
        return 0.0

    toplam, agirlik_toplam = 0.0, 0.0
    son_idx = len(cocuk_tokenlari) - 1
    for i, token in enumerate(cocuk_tokenlari):
        w = 1.0 if (i == 0 or i == son_idx) else 0.5
        en_iyi = max(fuzz.ratio(token, a) for a in aciklama_tokenlari)
        toplam += en_iyi * w
        agirlik_toplam += w
    return toplam / agirlik_toplam


def cocuk_bul(aciklama: str, cocuklar: list[dict]) -> dict:
    """Aciklamayi cocuk listesiyle karsilastirir.

    Doner: {cocuk, skor, durum, adaylar} — durum: kesin | supheli | yok
    """
    tokenlar = _anlamli_tokenlar(aciklama)
    bos = {"cocuk": None, "skor": 0.0, "durum": "yok", "adaylar": []}
    if not tokenlar:
        return bos

    puanlar = [(_cocuk_skoru(c["_tokenlar"], tokenlar), c) for c in cocuklar]
    puanlar = [p for p in puanlar if p[0] > 0]
    if not puanlar:
        return bos

    puanlar.sort(key=lambda p: p[0], reverse=True)
    en_iyi_skor, en_iyi = puanlar[0]
    ikinci_skor = puanlar[1][0] if len(puanlar) > 1 else 0.0
    adaylar = [(round(s, 1), c["ad_soyad"]) for s, c in puanlar[:3]]

    if en_iyi_skor >= ESIK_KESIN and (en_iyi_skor - ikinci_skor) >= FARK_ESIGI:
        return {"cocuk": en_iyi, "skor": round(en_iyi_skor, 1), "durum": "kesin",
                "adaylar": adaylar, "kaynak": "cocuk"}

    # Aciklamada gercekten bir ogrenci adi VAR (yuksek skor) ama hangisi oldugu
    # belirsizse VELI yoluna SAPMA — sapilirsa aciklamada adi gecen ogrenci
    # yerine bambaska bir kardes secilebilir. Kullaniciya sorulur.
    if en_iyi_skor >= ESIK_KESIN:
        return {"cocuk": en_iyi, "skor": round(en_iyi_skor, 1), "durum": "supheli",
                "adaylar": adaylar, "kaynak": "cocuk"}

    # Skor orta seviyedeyse (ornegin sadece SOYADI tutuyorsa) aciklamada
    # ogrenci adi yok demektir; parayi anne ya da baba yatirmis olabilir.
    # Once veli adlarindan bulmayi dene.
    veli_bulgu = _veliden_bul(tokenlar, cocuklar)
    if veli_bulgu:
        return veli_bulgu

    if en_iyi_skor >= ESIK_SUPHE:
        return {"cocuk": en_iyi, "skor": round(en_iyi_skor, 1), "durum": "supheli",
                "adaylar": adaylar, "kaynak": "cocuk"}

    return {"cocuk": None, "skor": round(en_iyi_skor, 1), "durum": "yok",
            "adaylar": adaylar, "kaynak": "cocuk"}


def _veliden_bul(tokenlar: list[str], cocuklar: list[dict]) -> dict | None:
    """Aciklamadaki isim listedeki bir VELI'ye uyuyorsa cocugunu dondurur.

    Ayni veliye bagli birden fazla cocuk varsa (kardesler) hangisi oldugu
    belli olmadigi icin kullaniciya sorulur.
    """
    # Bir cocugun birden fazla velisi olabilir (anne + baba). Hangisi
    # yatirmissa ondan bulunmali; bu yuzden tum veli adlari denenir.
    puanlar = []
    for c in cocuklar:
        token_listeleri = c.get("_veli_token_listesi") or (
            [c["_veli_tokenlar"]] if c.get("_veli_tokenlar") else [])
        en_iyi_veli, eslesen_ad = 0.0, ""
        for i, tokenlari in enumerate(token_listeleri):
            if not tokenlari:
                continue
            skor = _cocuk_skoru(tokenlari, tokenlar)
            if skor > en_iyi_veli:
                en_iyi_veli = skor
                adlar = c.get("veli_adlari") or [c.get("veli_ad", "")]
                eslesen_ad = adlar[i] if i < len(adlar) else ""
        if en_iyi_veli >= ESIK_KESIN:
            puanlar.append((en_iyi_veli, c, eslesen_ad))
    if not puanlar:
        return None

    puanlar.sort(key=lambda p: p[0], reverse=True)
    en_iyi_skor, en_iyi, eslesen_veli = puanlar[0]

    # ayni veliye (anne ya da baba) bagli tum cocuklar
    hedef = normalize(eslesen_veli)
    kardesler = [c for c in cocuklar
                 if hedef in [normalize(v) for v in
                              (c.get("veli_adlari") or [c.get("veli_ad", "")])]]
    adaylar = [(round(en_iyi_skor, 1), c["ad_soyad"]) for c in kardesler[:3]]

    if len(kardesler) > 1:
        return {"cocuk": kardesler[0], "skor": round(en_iyi_skor, 1),
                "durum": "supheli", "adaylar": adaylar, "kaynak": "veli",
                "veli_adi": eslesen_veli}
    return {"cocuk": en_iyi, "skor": round(en_iyi_skor, 1), "durum": "kesin",
            "adaylar": adaylar, "kaynak": "veli", "veli_adi": eslesen_veli}


ELEME_IZLERI = [
    (("mesaj ucreti", "bsmv", "komisyon"), "banka masrafı"),
    (("vergi", "stopaj", "sgk", "damga"), "vergi / resmi kesinti"),
    (("maas odemesi", "maas"), "personel maaşı"),
    (("denetim payi", "milli egitim"), "denetim payı"),
    (("ltd", "sti", "limited", "sirketi", "anonim"), "firma ödemesi"),
    (("baskan", "yonetim kurulu"), "yönetim ödemesi"),
]


def _eslesmeme_sebebi(satir: dict) -> str:
    """Kullaniciya 'neden girilmedi' diye anlasilir bir sebep uretir."""
    if not satir.get("aciklama", "").strip():
        return "açıklama boş - öğrenciyi kendiniz seçin"
    a = normalize(satir["aciklama"])
    for izler, sebep in ELEME_IZLERI:
        if any(iz in a for iz in izler):
            return sebep
    tutar = satir.get("tutar")
    if tutar is not None and tutar < 0:
        return "hesaptan çıkan para"
    return "öğrenci listesinde eşleşen isim yok"


def satirlari_eslestir(satirlar: list[dict], cocuklar: list[dict],
                       ogrenilen: dict | None = None,
                       girilenler: dict | None = None) -> list[dict]:
    """Ekstre satirlarina TC/cocuk bilgisini isler.

    Her satira eklenen alanlar:
      tc, cocuk_ad, veli_ad, kaynak, durum, skor, sebep, adaylar

    girilenler: daha once TEFBIS'e girilmis kayitlarin parmak izleri.
    Ayni kayit tekrar gelirse durum 'girildi' olur ve BIR DAHA GONDERILMEZ —
    ayni ekstre iki kez islenirse cift kayit olusmasin diye.
    """
    ogrenilen = ogrenilen or {}
    girilenler = girilenler or {}
    sonuc = []

    for s in satirlar:
        kayit = dict(s)
        aciklama = s["aciklama"]
        anahtar = normalize(aciklama)[:80]

        # 0) kullanicinin daha once onayladigi bir aciklama mi
        if anahtar in ogrenilen:
            tc = ogrenilen[anahtar]
            eslesen = next((c for c in cocuklar if c["tc"] == tc), None)
            kayit.update(tc=tc, cocuk_ad=eslesen["ad_soyad"] if eslesen else "",
                         veli_ad=eslesen["veli_ad"] if eslesen else "",
                         kaynak="hafiza", durum="kesin", skor=100.0,
                         sebep="daha önce onaylandı", adaylar=[])
            sonuc.append(kayit)
            continue

        # 1) kullanici ekstredeki TC sutununu elle doldurmus mu (en guvenilir)
        elle = s.get("tc_sutunu", "")
        if elle:
            eslesen = next((c for c in cocuklar if c["tc"] == elle), None)
            if len(elle) == 11 and tc_gecerli_mi(elle):
                kayit.update(tc=elle,
                             cocuk_ad=eslesen["ad_soyad"] if eslesen else "",
                             veli_ad=eslesen["veli_ad"] if eslesen else "",
                             kaynak="ekstredeki TC sutunu", durum="kesin", skor=100.0,
                             sebep="T.C. sutununa sizin yazdiginiz numara kullanildi",
                             adaylar=[])
            else:
                kayit.update(tc="", cocuk_ad=eslesen["ad_soyad"] if eslesen else "",
                             veli_ad="", kaynak="ekstredeki TC sutunu",
                             durum="supheli", skor=0.0,
                             sebep="T.C. sutunundaki numara gecersiz gorunuyor - kontrol edin",
                             adaylar=[])
            sonuc.append(kayit)
            continue

        # 2) veli aciklamaya TC yazmis mi
        tc = aciklamadan_tc_cek(aciklama)
        if tc:
            eslesen = next((c for c in cocuklar if c["tc"] == tc), None)
            kayit.update(tc=tc, cocuk_ad=eslesen["ad_soyad"] if eslesen else "",
                         veli_ad=eslesen["veli_ad"] if eslesen else "",
                         kaynak="aciklamadaki tc", durum="kesin", skor=100.0,
                         sebep="açıklamada geçerli T.C. bulundu", adaylar=[])
            sonuc.append(kayit)
            continue

        # 3) isimden bulanik eslestirme
        bulgu = cocuk_bul(aciklama, cocuklar)
        if bulgu["durum"] == "kesin":
            c = bulgu["cocuk"]
            tutar = s.get("tutar")
            disi = aidat_disi_sinyal(aciklama)
            if disi:
                # isim tutuyor ama aciklama bagis/kantin/kira diyor: karar sizin
                kayit.update(tc="", cocuk_ad=c["ad_soyad"], veli_ad=c["veli_ad"],
                             kaynak="isim eslesme", durum="supheli",
                             skor=bulgu["skor"],
                             sebep=f"açıklamada '{disi}' geçiyor - aidat olmayabilir",
                             adaylar=bulgu["adaylar"])
            elif tutar is not None and tutar < 0:
                # isim tutuyor ama para hesaptan cikmis: gider olabilir, otomatik girme
                kayit.update(tc="", cocuk_ad=c["ad_soyad"], veli_ad=c["veli_ad"],
                             kaynak="isim eslesme", durum="supheli", skor=bulgu["skor"],
                             sebep="isim tutuyor ama tutar eksi görünüyor - kontrol edin",
                             adaylar=bulgu["adaylar"])
            else:
                veliden = bulgu.get("kaynak") == "veli"
                kayit.update(tc=c["tc"], cocuk_ad=c["ad_soyad"], veli_ad=c["veli_ad"],
                             kaynak="veli ismi" if veliden else "isim eslesme",
                             durum="kesin", skor=bulgu["skor"],
                             sebep=("velisinin adından bulundu (%s)"
                                    % (bulgu.get("veli_adi") or c["veli_ad"])
                                    if veliden else
                                    "listedeki isimle %%%d örtüşüyor" % round(bulgu["skor"])),
                             adaylar=bulgu["adaylar"])
        elif bulgu["durum"] == "supheli":
            c = bulgu["cocuk"]
            disi = aidat_disi_sinyal(aciklama)
            if disi:
                sebep = f"açıklamada '{disi}' geçiyor - aidat olmayabilir"
            elif bulgu.get("kaynak") == "veli":
                sebep = ("aynı veliye bağlı birden fazla öğrenci var - hangisi olduğunu "
                         "seçin")
            else:
                sebep = "benzerlik %%%d - onayınız gerekiyor" % round(bulgu["skor"])
            kayit.update(tc="", cocuk_ad=c["ad_soyad"], veli_ad=c["veli_ad"],
                         kaynak="isim eslesme", durum="supheli", skor=bulgu["skor"],
                         sebep=sebep, adaylar=bulgu["adaylar"])
        else:
            kayit.update(tc="", cocuk_ad="", veli_ad="", kaynak="-", durum="yok",
                         skor=bulgu["skor"], sebep=_eslesmeme_sebebi(s),
                         adaylar=bulgu["adaylar"])
        sonuc.append(kayit)

    if girilenler:
        _girilmisleri_isaretle(sonuc, girilenler)
    return sonuc


def _girilmisleri_isaretle(sonuc: list[dict], girilenler: dict) -> None:
    """Daha once TEFBIS'e girilmis satirlari 'girildi' yapar."""
    from depo import parmak_izi
    for k in sonuc:
        if k["durum"] != "kesin" or not k.get("tc"):
            continue
        iz = parmak_izi(k["tarih"], k["evrak_no"], k["tc"], k["tutar"])
        kayit = girilenler.get(iz)
        if kayit:
            ne_zaman = kayit.get("tarih", "") if isinstance(kayit, dict) else ""
            k["durum"] = "girildi"
            k["sebep"] = ("bu kayıt daha önce TEFBİS'e girildi"
                          + (f" ({ne_zaman})" if ne_zaman else ""))
