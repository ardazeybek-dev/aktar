# -*- coding: utf-8 -*-
"""
panel_prova.py — Motoru gercek bir tarayiciyla, gercek panele girmeden dener.

`demo/sahte_tefbis/` icinde gercek kayit ekranina benzeyen bir sayfa var:
ayni etiketler (Odeyen Tipi, Evrak No, Evrak Tarihi, Tutar, Detay Kayit Ekle,
Kaydet), ayni akis (Kisi/Kurum Ekle -> AYRI PENCEREDE T.C. ara -> sec).

Bu prova sunlari kanitlar:
  - alanlar ekrandaki etiketten bulunuyor mu
  - "Toplam Tutar" yerine dogru "Tutar" kutusu dolduruluyor mu
  - kisi secimi ayri pencerede yapilip ANA SAYFAYA donuluyor mu
  - birden fazla kayit arka arkaya girilebiliyor mu
  - panelde olmayan T.C. atlanip dongu devam ediyor mu

Diger test dosyalari cekirdek mantigi olcer (okuma, eslestirme, Excel);
bu dosya MOTORU olcer: seciciler, pencere gecisleri, hata yalitimi.

Calistirma:  python testler/panel_prova.py
Chrome veya Edge kurulu olmalidir; pencere acilmaz (headless).
"""
from __future__ import annotations

import functools
import http.server
import socketserver
import sys
import threading
from datetime import date
from pathlib import Path

# exe olarak paketlendiginde dosyalar exe'nin yaninda olur
if getattr(sys, "frozen", False):
    KOK = Path(sys.executable).resolve().parent
else:
    KOK = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(KOK / "src"))

from panel import MotorAyarlari, PanelOtomasyonu       # noqa: E402
from tarifler.tefbis import TefbisTarifi               # noqa: E402

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


SAHTE_KLASOR = KOK / "demo" / "sahte_tefbis"


def sunucu_baslat() -> str:
    """Sahte panel sayfalarini HTTP uzerinden sunar.

    file:// ile acilinca tarayici, acilir pencerenin ana sayfaya deger
    yazmasini engelliyor (opaque origin). Gercek panel de http uzerinden
    calistigi icin prova da oyle yapilmali.
    """
    isleyici = functools.partial(http.server.SimpleHTTPRequestHandler,
                                 directory=str(SAHTE_KLASOR))
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", 0), isleyici)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{httpd.server_address[1]}/ana.html"


KAYITLAR = [
    {"tarih": date(2026, 5, 21), "evrak_no": "F13159", "tc": "99976892504",
     "tutar": 1250.0, "cocuk_ad": "Bade Naz ÖZTÜRKMEN"},
    {"tarih": date(2026, 5, 19), "evrak_no": "F00279", "tc": "99983501420",
     "tutar": 1375.5, "cocuk_ad": "Kuzey Asaf BOZDOĞAN"},
    # Panelde kayitli OLMAYAN T.C. — atlanmali, dongu durmamali
    {"tarih": date(2026, 5, 18), "evrak_no": "F31409", "tc": "99911111118",
     "tutar": 1250.0, "cocuk_ad": "Kayıtsız Öğrenci"},
    {"tarih": date(2026, 5, 15), "evrak_no": "F11475", "tc": "99938901558",
     "tutar": 900.0, "cocuk_ad": "Efe Han ÇAKIROĞLU"},
]


class ProvaTarifi(TefbisTarifi):
    """Sahte sayfada sol menu agaci yok; kayit ekranini tek tikla acar.

    Tarifin geri kalani — etiketler, haric_metinler, butonlar, kayit_gir —
    aynen gercek tarifin kendisi. Prova bu yuzden anlamli: degistirilen tek
    sey ekrana NASIL gelindigi, kaydin nasil girildigi degil.
    """

    def ekrani_hazirla(self, motor) -> None:
        motor.sayfa.click("#mnuOzBakim")


class ProvaMotoru(PanelOtomasyonu):
    """Gercek panel yerine sahte sayfayi acan surum."""

    adres = ""

    def tarayici_ac(self) -> None:
        """Asil programla AYNI yolu izler: sistemdeki Chrome, olmazsa Edge.

        Paketlenmis exe'de Playwright'in kendi chromium'u YOKTUR; program
        zaten kullanicinin tarayicisini kullanacak sekilde yazildi. Prova da
        ayni yoldan gitmezse gercegi olcmemis olur.
        """
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()

        son_hata = None
        for kanal in ("chrome", "msedge"):
            try:
                self.tarayici = self._pw.chromium.launch(channel=kanal,
                                                         headless=True)
                print(f"   (tarayici: {kanal})")
                break
            except Exception as e:
                son_hata = e
                self.tarayici = None
        if self.tarayici is None:
            raise SystemExit(f"Chrome/Edge acilamadi: {son_hata}")

        baglam = self.tarayici.new_context()
        self.sayfa = baglam.new_page()
        self.ana_sayfa = self.sayfa
        self.sayfa.goto(self.adres, wait_until="domcontentloaded")

    def giris_bekle(self, zaman_asimi_sn: int = 600) -> bool:
        # Sahte sayfada oturum yok; beklemeden devam.
        return True


def main() -> int:
    gunluk: list[str] = []
    ayar = MotorAyarlari(
        kayit_arasi_bekleme=0.2,
        alan_bekleme=6.0,
        secim={
            "modul": "Okul Öncesi Birimleri Modülü",
            "gelir_turu": "Öz Bakım Ücreti Gelirleri",
            "odeyen_tipi": "Öğrenciler",
            "islem_turu": "Öz Bakım Ücreti Gelirleri",
            "aciklama_sablonu": "{ay} ayı ödemesi",
        },
    )
    surucu = ProvaMotoru(ProvaTarifi(), ayar, gunlukcu=gunluk.append)
    surucu.adres = sunucu_baslat()

    print(f"Sahte panel ekranında prova yapılıyor  ({surucu.adres})\n")
    try:
        surucu.tarayici_ac()
        surucu.giris_bekle()
        surucu.ekrani_hazirla()
        sonuc = surucu.calistir(KAYITLAR)

        yazilan = surucu.ana_sayfa.locator(".kayit").all_inner_texts()
        son_durum = surucu.ana_sayfa.locator("#sonuc").inner_text()
        acik_pencere = len([x for x in surucu.ana_sayfa.context.pages
                            if not x.is_closed()])
    finally:
        surucu.kapat()

    for satir in gunluk:
        print("  ", satir)
    print()

    kontroller = []

    def kontrol(baslik, kosul, ek=""):
        kontroller.append((baslik, bool(kosul), ek))
        print(f"  [{'OK  ' if kosul else 'HATA'}] {baslik}"
              + (f"   {ek}" if not kosul else ""))

    print("SONUÇLAR")
    kontrol("3 geçerli kayıt girildi", len(sonuc.basarili) == 3,
            f"girilen: {len(sonuc.basarili)}")
    kontrol("kayıtsız T.C. atlandı, döngü durmadı", len(sonuc.atlanan) == 1,
            f"atlanan: {len(sonuc.atlanan)}")
    kontrol("ekrana gerçekten 3 satır yazıldı", len(yazilan) == 3,
            f"ekranda: {len(yazilan)}")

    if yazilan:
        ilk = yazilan[0].split("|")
        kontrol("evrak no doğru yazıldı", ilk[0] == "F13159", ilk[0])
        kontrol("T.C. doğru kişiye bağlandı", "99976892504" in ilk[1], ilk[1])
        kontrol("tutar Türkçe biçimde yazıldı", ilk[2] == "1.250,00", ilk[2])
        kontrol("evrak tarihi gg/aa/yyyy yazıldı", ilk[3] == "21/05/2026", ilk[3])

    if len(yazilan) > 1:
        ikinci = yazilan[1].split("|")
        kontrol("ikinci kayıt ana sayfada girildi (popup dönüşü çalıştı)",
                ikinci[0] == "F00279", ikinci[0])
        kontrol("kuruşlu tutar doğru", ikinci[2] == "1.375,50", ikinci[2])

    if len(yazilan) > 2:
        ucuncu = yazilan[2].split("|")
        kontrol("hatalı kayıttan sonra döngü devam etti", ucuncu[0] == "F11475",
                ucuncu[0])

    # MEB kilavuzundaki son iki adim: imzalayan secimi + kayit ciktisi
    kontrol("imzalayan seçimi ekranı geçildi (kayıt tamamlandı)",
            "Kayıt eklendi" in son_durum, son_durum[:60])
    kontrol("imzalayan adı kayda işlendi",
            "MÜDÜR" in son_durum
            or "MÜDÜR YARDIMCISI" in son_durum, son_durum[:60])
    kontrol("açılan pencereler kapatıldı (ekran birikmiyor)",
            acik_pencere == 1, f"açık pencere: {acik_pencere}")
    kontrol("günlükte imzalayan adımı görünüyor",
            any("imzalayan" in g for g in gunluk))

    kaldi = [b for b, ok, _ in kontroller if not ok]
    print("\n" + "=" * 58)
    print(f"GEÇEN: {len(kontroller) - len(kaldi)}   KALAN: {len(kaldi)}")
    print("=" * 58)
    return 1 if kaldi else 0


if __name__ == "__main__":
    raise SystemExit(main())
