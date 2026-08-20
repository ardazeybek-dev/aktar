# -*- coding: utf-8 -*-
"""
temel.py — Bir panel tarifinin yerine getirmesi gereken sozlesme.

Motor (`panel.py`) hicbir panelin ic yapisini bilmez. Bildigi tek sey
burada tarif edilen arayuzdur. Yeni bir panel eklemek = bu sinifi
miras alan bir dosya yazmak.

En kisa tarif soyle gorunur:

    from tarifler.temel import Tarif

    class BenimPanelim(Tarif):
        ad = "Ornek Panel"
        giris_adresleri = {"ana": "https://ornek.gov.tr/"}
        etiketler = {"evrak_no": ("Evrak No", "Evrak No :")}
        butonlar = {"kaydet": ("Kaydet",)}

        def kayit_gir(self, motor, kayit):
            motor.zorunlu_alan("evrak_no").fill(str(kayit["evrak_no"]))
            motor.dugme("kaydet").click()

Motorun tarife sundugu yardimcilar (hepsi `motor.` uzerinden):
    etiketli_alan(anahtar, tur)   etiket metninden alan bulur, bekler
    zorunlu_alan(anahtar, tur)    bulamazsa PanelHatasi firlatir
    dugme(anahtar)                metninden dugme/link bulur, bekler
    menu_tikla(metin)             sekme / sol menu ogesine tiklar
    sayfa_dursun(ms)              sayfa yuklenmesini bekler
    acilan_pencereye_gec(sn)      yeni acilan pencereye gecer
    yan_pencereleri_kapat()       ana sayfaya doner
    ekran_hatasi()                ekrandaki kirmizi uyari metnini dondurur
    sayfa                         o an aktif Playwright sayfasi
"""
from __future__ import annotations


class Tarif:
    """Panele ozel bilgi ve akisin tasiyicisi."""

    # --- kimlik
    ad = "Panel"

    # --- adresler: {anahtar: url}. Kullanici hangisinden girecegini secer.
    giris_adresleri: dict = {}
    varsayilan_giris = ""

    # --- alan etiketleri: {anahtar: (ekranda gecebilecek metinler...)}
    # Motor bu metinlerin YANINDAKI input/select/textarea'yi bulur.
    etiketler: dict = {}

    # --- etiket ararken yanlis alani yakalamamak icin dislanacak metinler
    # Ornek: ekranda hem "Toplam Tutar" hem "Tutar" varsa, "tutar" anahtari
    # icin ("Toplam",) yazmak "Toplam Tutar"i eleme disi birakir.
    haric_metinler: dict = {}

    # --- dugme metinleri: {anahtar: (dugmede yazabilecek metinler...)}
    butonlar: dict = {}

    # --- ekrandaki kirmizi metin bunlardan birini iceriyorsa kayit basarisiz
    hata_kaliplari = ("hata", "hatalı", "zorunlu", "bulunamadı", "geçersiz",
                      "yapılamadı", "boş bırakılamaz", "eksik")

    # ------------------------------------------------------------ adresler
    def giris_adresi(self, yol: str) -> str:
        """Kullanicinin sectigi giris yolunun adresi."""
        if not self.giris_adresleri:
            return ""
        return self.giris_adresleri.get(
            yol or self.varsayilan_giris,
            next(iter(self.giris_adresleri.values())))

    def giris_secenekleri(self) -> list:
        """Arayuzdeki "nereden girilsin" secenekleri.

        [(etiket, anahtar, aciklama)] — anahtar `giris_adresleri`ndeki ad.
        Bos donerse arayuz bu secimi hic gostermez.
        """
        return [(a, a, u) for a, u in self.giris_adresleri.items()]

    def giris_notlari(self, yol: str) -> list:
        """Tarayici acildiktan sonra kullaniciya gosterilecek yonlendirmeler."""
        return []

    # ------------------------------------------------------------ secimler
    def modlar(self) -> list:
        """Arayuzde radyo dugmesi olarak cikacak hazir secim setleri.

        [(etiket, {secim_anahtari: deger, ...})]
        Kullanicinin sectigi set `MotorAyarlari.secim` sozlugune yazilir.
        """
        return []

    def listeler(self, secim: dict) -> dict:
        """Secime bagli acilir kutular. Mod degisince yeniden sorulur.

        {anahtar: {"baslik": str, "degerler": [...]}}
        Ornek: modul degisince o modulun gelir turleri gelmeli.
        """
        return {}

    # ---------------------------------------------------------------- akis
    def giris_yapildi_mi(self, motor) -> bool:
        """Kullanici girisi tamamladi mi. Varsayilan: anlayamayiz, elle devam."""
        return True

    def ekrani_hazirla(self, motor) -> None:
        """Kayit ekranina gelinir (sekme sec, sol menuden kalem sec vb.)."""

    def kayit_gir(self, motor, kayit: dict) -> None:
        """Tek bir kaydi girer. Basarisiz olursa istisna firlatmali."""
        raise NotImplementedError

    def formu_temizle(self, motor) -> None:
        """Hatali kayittan sonra ekrani yeni kayda hazir hale getirir."""
        self.ekrani_hazirla(motor)
