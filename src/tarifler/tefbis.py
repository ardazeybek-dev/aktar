# -*- coding: utf-8 -*-
"""
tefbis.py — MEB TEFBIS gelir kayit ekrani icin ornek tarif.

Bu dosya, `panel.py` motorunun gercek bir panelde nasil kullanildigini
gosteren calisan ornektir. Aktar'in kendisi TEFBIS'e bagli degildir;
baska bir panel icin bunun gibi ikinci bir tarif yazmak yeterlidir.

Onemli: Program hicbir kimlik bilgisi saklamaz veya gondermez. Kullanici
MEBBIS/TEFBIS girisini kendi tarayicisinda kendisi yapar; motor yalnizca
girisin tamamlanmasini bekler ve kullanicinin kendi yetkisiyle, kendi
verisini, kendi yerine girer.

Ekran akisi (musterinin ekran kaydindan cikarildi)
--------------------------------------------------
  modul sekmesi (Okul Oncesi Birimleri / Okul Aile Birlikleri)
    -> sol menu: Gelir Islemleri > ilgili gelir turu
    -> Odeyen Tipi (Ogrenciler / Veliler)
    -> "Kisi/Kurum Ekle" (+)  -> windows/secici.aspx: T.C. Kimlik No + [Ara]
    -> Evrak No, Evrak Tarihi
    -> "Detay Kayit Ekle" -> Turu + Tutar -> satir kaydet
    -> ust araç çubugu "Kaydet"
    -> "Imzalayan Secimi" (Tamam) -> "Gelir Kayit Ciktisi" (kapat)
"""
from __future__ import annotations

from panel import PanelHatasi, tr_tarih, tr_tutar
from tarifler.temel import Tarif

# TEFBIS'e iki yoldan girilir:
#   MEBBIS  : mebbis.meb.gov.tr -> sifre + telefona gelen kod -> icinden TEFBIS
#             (idarecilerin gunluk kullandigi yol, tum paneller burada)
#   TEFBIS  : tefbis.meb.gov.tr -> "MEBBIS ile giris" -> sadece TEFBIS
# Bazi okul aglarinda ikinci yoldaki yonlendirme ERR_CONNECTION_RESET veriyor;
# bu yuzden varsayilan, kullanicinin zaten girdigi MEBBIS adresidir.
MEBBIS_ADRES = "https://mebbis.meb.gov.tr/"
TEFBIS_ADRES = "https://tefbis.meb.gov.tr/"

MODULLER = ("Okul Öncesi Birimleri Modülü", "Okul Aile Birlikleri Modülü")

# Sol menudeki gelir kalemleri (ekran kaydindan). Kullanici arayuzde secer.
GELIR_TURLERI = {
    "Okul Öncesi Birimleri Modülü": [
        "Öz Bakım Ücreti Gelirleri",
        "Diğer Gelirler",
        "Aktarım Gelirleri",
    ],
    "Okul Aile Birlikleri Modülü": [
        "Okula Yapılan Yardımlar (Nakdi)",
        "Öğrenciye Yapılan Yardımlar (Nakdi)",
        "Okula Yapılan Bağışlar (Ayni)",
        "Öğrenciye Yapılan Bağışlar (Ayni)",
        "Hızlı Bağış İşlemleri",
        "İşletilebilir Alan Gelirleri",
        "Kira Geliri",
        "Etkinlik Organizasyon Gelirleri",
        "Faiz Gelirleri",
        "Aktarım Gelirleri",
        "Diğer Gelirler",
    ],
}

ODEYEN_TIPLERI = ("Öğrenciler", "Veliler", "Personel/Öğretmen",
                  "Özel Kurum ve Kuruluşlar", "Muhtarlıklar", "Vakıflar")


class TefbisTarifi(Tarif):
    ad = "MEB TEFBİS"

    giris_adresleri = {"mebbis": MEBBIS_ADRES, "tefbis": TEFBIS_ADRES}
    varsayilan_giris = "mebbis"

    # Etiket -> o etiketin yanindaki alani bulmak icin kullanilacak metinler
    etiketler = {
        "odeyen_tipi": ("Ödeyen Tipi", "Ödeyen Tipi :"),
        "odeyen": ("Ödeyen", "Ödeyen :"),
        "aciklama": ("Açıklama", "Açıklama :"),
        "evrak_no": ("Evrak No", "Evrak No :"),
        "evrak_tarihi": ("Evrak Tarihi", "Evrak Tarihi :"),
        "tc_kimlik": ("T.C. Kimlik No", "TC Kimlik No", "T.C. Kimlik No :"),
        "tutar": ("Tutar", "Tutar :"),
        "islem_turu": ("Türü", "İşlem Türü", "Türü :"),
        "detay_aciklama": ("Detay Açıklaması", "Detay Açıklaması :"),
        # MEB kullanici kilavuzundan (Bolum 2) dogrulanan ek alanlar
        "faaliyet_kodu": ("Faaliyet Kodu",),
        "imzalayan": ("İmzalayan Adı", "İmzalayan"),
    }

    # Etiket ararken yanlis alani yakalamamak icin disarida birakilacak metinler.
    # Ekranda hem "Toplam Tutar" hem detay satirinda "Tutar" var; sadece "Tutar"
    # arayinca "Toplam Tutar" da esleşiyordu.
    haric_metinler = {
        "tutar": ("Toplam", "Satır Toplamı"),
        "aciklama": ("Detay Açıklaması",),
        "odeyen": ("Ödeyen Tipi",),
    }

    butonlar = {
        "kisi_kurum_ekle": ("Kişi/Kurum Ekle", "Kişi Kurum Ekle", "Kişi/Kurum",
                            "Yeni Ekle"),
        "ara": ("Ara",),
        "sec": ("Seç",),                    # arama sonucundaki secim baglantisi
        "detay_kayit_ekle": ("Detay Kayıt Ekle",),
        "guncelle": ("Güncelle",),          # detay satirini isleme ekler
        "kaydet": ("Kaydet",),
        "tamam": ("Tamam",),                # imzalayan secimi onayi
        "formu_yazdir": ("Formu Yazdır", "Formu yazdır"),
        "iptal": ("İptal",),
    }

    # ------------------------------------------------------------ adresler
    def giris_secenekleri(self) -> list:
        # MEBBIS gunluk kullanilan yol oldugu icin once o gelir.
        return [("MEBBİS", "mebbis", "mebbis.meb.gov.tr"),
                ("TEFBİS", "tefbis", "tefbis.meb.gov.tr")]

    def giris_notlari(self, yol: str) -> list:
        if self.giris_adresi(yol) == MEBBIS_ADRES:
            return ["MEBBİS'e girdikten sonra TEFBİS panelini açın, "
                    "gelir kayıt ekranına gelin."]
        return []

    # ------------------------------------------------------------ secimler
    def modlar(self) -> list:
        """Modul + kaydin kimin adina acilacagi: dort hazir kombinasyon."""
        return [
            ("1- Okul Öncesi (Öğrenci Adına)",
             {"modul": MODULLER[0], "odeyen_tipi": "Öğrenciler"}),
            ("2- Okul Öncesi (Veli Adına)",
             {"modul": MODULLER[0], "odeyen_tipi": "Veliler"}),
            ("3- Okul Aile Birliği (Öğrenci Adına)",
             {"modul": MODULLER[1], "odeyen_tipi": "Öğrenciler"}),
            ("4- Okul Aile Birliği (Veli Adına)",
             {"modul": MODULLER[1], "odeyen_tipi": "Veliler"}),
        ]

    def listeler(self, secim: dict) -> dict:
        # Modul degisince o modulun gelir turleri gelmeli.
        modul = secim.get("modul", MODULLER[0])
        return {"gelir_turu": {"baslik": "Gelir türü",
                               "degerler": list(GELIR_TURLERI.get(modul, []))}}

    # ---------------------------------------------------------------- akis
    def giris_yapildi_mi(self, motor) -> bool:
        """Kayit ekranina ulasilabiliyorsa giris yapilmis sayilir."""
        for cerceve in motor._cerceveler():
            try:
                if cerceve.locator(
                        "xpath=//*[contains(., 'Gelir İşlemleri')]").count():
                    return True
            except Exception:
                continue
        return False

    def ekrani_hazirla(self, motor) -> None:
        """Modul sekmesini ve sol menudeki gelir turunu secer."""
        secim = motor.ayarlar.secim
        modul = secim.get("modul", MODULLER[0])
        gelir_turu = secim.get("gelir_turu", GELIR_TURLERI[MODULLER[0]][0])

        motor.menu_tikla(modul)
        motor.menu_tikla("Gelir İşlemleri", zorunlu=False)
        motor.menu_tikla(gelir_turu)
        motor.sayfa_dursun(500)
        motor._log(f"Ekran hazır: {modul} > {gelir_turu}")

    def kayit_gir(self, motor, kayit: dict) -> None:
        """Tek bir gelir kaydini girer.

        kayit: {tarih, evrak_no, tc, tutar, cocuk_ad}
        """
        secim = motor.ayarlar.secim

        # Onceki kayittan kalma acilir pencere varsa ana sayfaya don
        if motor.ana_sayfa is not None:
            motor.sayfa = motor.ana_sayfa

        # 1) Odeyen tipi
        tip_alani = motor.etiketli_alan("odeyen_tipi", "select")
        if tip_alani is not None:
            try:
                tip_alani.select_option(
                    label=secim.get("odeyen_tipi", ODEYEN_TIPLERI[0]))
                motor.sayfa.wait_for_timeout(500)
            except Exception:
                pass

        # 2) Kisi secimi: TC ile ara
        self._kisi_sec(motor, kayit["tc"])

        # 3) Evrak bilgileri
        motor.zorunlu_alan("evrak_no").fill(str(kayit["evrak_no"]))
        tarih_alani = motor.etiketli_alan("evrak_tarihi")
        if tarih_alani is not None:
            tarih_alani.fill(tr_tarih(kayit["tarih"]))

        sablon = secim.get("aciklama_sablonu", "{ay} ayı ödemesi")
        aciklama_alani = motor.etiketli_alan("aciklama", "textarea")
        if aciklama_alani is not None and sablon:
            ay = kayit["tarih"].strftime("%m/%Y")
            aciklama_alani.fill(sablon.format(ay=ay,
                                              cocuk=kayit.get("cocuk_ad", "")))

        # 4) Detay satiri: tur + tutar
        detay = motor.dugme("detay_kayit_ekle")
        if detay is not None:
            detay.click()
            motor.sayfa_dursun(400)

        islem_turu = secim.get("islem_turu", "")
        if islem_turu:
            tur_alani = motor.etiketli_alan("islem_turu", "select", bekle=3)
            if tur_alani is not None:
                try:
                    tur_alani.select_option(label=islem_turu)
                except Exception:
                    pass

        tutar_alani = motor.zorunlu_alan("tutar")
        tutar_alani.fill(tr_tutar(abs(float(kayit["tutar"] or 0))))

        # 5) Kaydet
        kaydet = motor.dugme("kaydet")
        if kaydet is None:
            raise PanelHatasi("Kaydet düğmesi bulunamadı.")
        kaydet.click()
        motor.sayfa_dursun(int(motor.ayarlar.kayit_arasi_bekleme * 1000))

        hata = motor.ekran_hatasi()
        if hata:
            raise PanelHatasi(hata)

        # Kilavuz (Bolum 2): Kaydet'ten sonra "Imzalayan Secimi" ekrani gelir,
        # "Tamam"a basilir, ardindan "Gelir Kayit Ciktisi" ekrani acilir.
        # Bu iki adim yapilmazsa kayit TAMAMLANMAZ.
        self._kaydi_tamamla(motor)

    def _kaydi_tamamla(self, motor) -> None:
        """Kaydet sonrasi acilan imzalayan ve cikti ekranlarini gecer.

        Imzalayan zaten secili gelir; sadece Tamam'a basmak yeterlidir.
        Ekranlar cikmazsa (surum farki) sessizce gecilir.
        """
        # Imzalayan ekrani AYRI PENCEREDE acilir; once oraya gecmek gerekir,
        # yoksa alanlar ana sayfada aranir ve bulunamaz.
        motor.acilan_pencereye_gec(4.0)

        # 1) imzalayan secimi
        imzalayan_adi = motor.ayarlar.secim.get("imzalayan", "")
        imzalayan = motor.etiketli_alan("imzalayan", "select", bekle=4)
        if imzalayan is not None and imzalayan_adi:
            try:
                imzalayan.select_option(label=imzalayan_adi)
            except Exception:
                pass

        tamam = motor.dugme("tamam", bekle=5)
        if tamam is not None:
            try:
                tamam.click()
                motor.sayfa_dursun(600)
                motor._log("imzalayan onaylandı")
            except Exception:
                pass

        # 2) kayit ciktisi ekrani acilir; yazdirmiyoruz, kapatip donuyoruz
        motor.acilan_pencereye_gec(3.0)
        motor.yan_pencereleri_kapat()

        hata = motor.ekran_hatasi()
        if hata:
            raise PanelHatasi(hata)

    def _kisi_sec(self, motor, tc: str) -> None:
        """Kisi/Kurum Ekle -> TC yaz -> Ara -> ilk sonucu sec.

        Secim ekrani (windows/secici.aspx) YENI PENCEREDE acilabiliyor.
        Is bitince ANA SAYFAYA geri donulur; yoksa evrak no, tutar ve Kaydet
        kapanmis pencerede aranir ve her kayit patlar.
        """
        if not tc:
            raise PanelHatasi("Bu satırda T.C. numarası yok.")

        ana = motor.ana_sayfa or motor.sayfa
        popup = None

        ekle = motor.dugme("kisi_kurum_ekle")
        if ekle is not None:
            try:
                with motor.sayfa.context.expect_page(timeout=4000) as yeni:
                    ekle.click()
                popup = yeni.value
                popup.wait_for_load_state("domcontentloaded")
                motor.sayfa = popup
            except Exception:
                # yeni pencere acilmadi: secim ayni sayfada veya iframe icinde
                try:
                    ekle.click()
                except Exception:
                    pass
                motor.sayfa_dursun(500)

        try:
            tc_alani = motor.zorunlu_alan("tc_kimlik")
            tc_alani.fill(str(tc))

            ara = motor.dugme("ara")
            if ara is not None:
                ara.click()
                motor.sayfa_dursun(600)

            # Kilavuz: "Listeden 'Sec' dugmesine bastiginizda kisi secimi
            # islemi gerceklesir." Once o baglantiyi arariz, bulamazsak
            # satirin kendisine tiklariz.
            secildi = False
            for xpath in (f"xpath=//tr[contains(., '{tc}')]"
                          f"//*[self::a or self::input or self::button]"
                          f"[contains(., 'Seç') or contains(@value, 'Seç')]",
                          f"xpath=//tr[contains(., '{tc}')]//a",
                          f"xpath=//tr[contains(., '{tc}')]"):
                for cerceve in motor._cerceveler():
                    try:
                        oge = cerceve.locator(xpath).first
                        if oge.count():
                            oge.click()
                            motor.sayfa_dursun(400)
                            secildi = True
                            break
                    except Exception:
                        continue
                if secildi:
                    break
            if not secildi:
                raise PanelHatasi(
                    f"T.C. {tc} icin kisi bulunamadi "
                    "(TEFBIS'te kayitli olmayabilir).")
        finally:
            # NE OLURSA OLSUN ana sayfaya don
            if popup is not None:
                try:
                    if not popup.is_closed():
                        popup.close()
                except Exception:
                    pass
            motor.sayfa = ana

    def formu_temizle(self, motor) -> None:
        """Hatali kayittan sonra ekrani yeni kayda hazir hale getirir."""
        iptal = motor.dugme("iptal", bekle=3)
        if iptal is not None:
            iptal.click()
            motor.sayfa.wait_for_timeout(600)
            return
        self.ekrani_hazirla(motor)
