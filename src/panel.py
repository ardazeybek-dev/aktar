# -*- coding: utf-8 -*-
"""
panel.py — Bir web paneline toplu veri girisi yapan genel motor.

Bu dosya HANGI panele girdigini bilmez. Panele ozel olan her sey
(adresler, alan etiketleri, dugme metinleri, ekran akisi) bir **tarif**
dosyasindan gelir: bkz. `tarifler/temel.py` ve `tarifler/tefbis.py`.

Tasarim ilkeleri
----------------
1. **Sifre programda degil.** Tarayici acilir, kullanici girisini KENDI
   yapar. Motor sadece girisin tamamlanmasini bekler. Hicbir kimlik
   bilgisi diske yazilmaz, hicbir yere gonderilmez.
2. **Kullanicinin kendi oturumu.** Kullanicinin kendi tarayici profiliyle
   calisir; disaridan gelen bir istemci degil, kullanicinin actigi
   tarayicidir.
3. **Sabit CSS id'sine guvenme.** Eski ASP.NET WebForms panellerinde
   id'ler surum degisiminde kayar. Alanlar ekrandaki ETIKET metninden
   bulunur ("Evrak No :" etiketinin yanindaki input gibi). Bulunamazsa
   kullanici ayar dosyasindan kendi seciciyi verebilir.
4. **Bir kayit patlarsa dongu durmaz.** Hata yakalanir, satir atlanir,
   sonunda hangi satirin neden girilemedigi raporlanir.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date


class PanelHatasi(Exception):
    """Kullaniciya gosterilecek panel hatasi."""


@dataclass
class MotorAyarlari:
    """Panelden bagimsiz calisma ayarlari."""
    giris_yolu: str = ""            # tarifin giris_adresleri sozlugundeki anahtar
    kayit_arasi_bekleme: float = 2.0
    alan_bekleme: float = 45.0      # bir alan/dugme gorunene kadar beklenecek sure
    profil_klasoru: str = ""        # persistent context klasoru
    ozel_seciciler: dict = field(default_factory=dict)   # etiket -> css/xpath
    secim: dict = field(default_factory=dict)            # tarife ozel secimler


@dataclass
class Sonuc:
    basarili: list = field(default_factory=list)
    atlanan: list = field(default_factory=list)     # (kayit, sebep)

    @property
    def ozet_metni(self) -> str:
        s = f"{len(self.basarili)} kayıt girildi"
        if self.atlanan:
            s += f", {len(self.atlanan)} kayıt girilemedi"
        return s


def tr_tutar(t: float) -> str:
    """Turkce tutar formati: 1234.5 -> '1.234,50'."""
    return f"{t:,.2f}".replace(",", "#").replace(".", ",").replace("#", ".")


def tr_tarih(t: date) -> str:
    return t.strftime("%d/%m/%Y")


class PanelOtomasyonu:
    """Tarifte anlatilan paneli surer. Playwright sync API kullanir."""

    def __init__(self, tarif, ayarlar: MotorAyarlari | None = None, gunlukcu=None):
        self.tarif = tarif
        self.ayarlar = ayarlar or MotorAyarlari()
        self.gunlukcu = gunlukcu or (lambda m: None)
        self._pw = None
        self.tarayici = None
        self.sayfa = None
        self.ana_sayfa = None       # kayit formunun bulundugu asil sayfa
        self._durdur = False

    # ------------------------------------------------------------ altyapi
    def _log(self, mesaj: str) -> None:
        self.gunlukcu(mesaj)

    @property
    def durduruldu(self) -> bool:
        """Kullanici Durdur'a basti mi (arayuz bekleme donguleri icin)."""
        return self._durdur

    def durdur(self) -> None:
        """Arayuzdeki 'Durdur' dugmesi bunu cagirir; dongu temiz biter."""
        self._durdur = True

    def _chrome_kapat(self) -> None:
        """Kendi baslattigimiz Chrome surecini sonlandirir."""
        surec = getattr(self, "_chrome_sureci", None)
        if surec is None:
            return
        self._chrome_sureci = None
        try:
            surec.terminate()
            surec.wait(timeout=5)
        except Exception:
            try:
                surec.kill()
            except Exception:
                pass

    def _cerceveler(self):
        """Sayfa + icindeki tum frame'ler (eski paneller iframe kullanabilir)."""
        return [self.sayfa] + list(self.sayfa.frames)

    def _tum_sayfalar(self):
        """Tarayicidaki tum acik sekme/pencereler.

        launch() browser dondurur (pages yok), launch_persistent_context()
        context dondurur (pages var). Ikisinde de calisan tek dogru yol
        sayfanin kendi context'ini sormaktir.
        """
        for kaynak in (self.ana_sayfa, self.sayfa):
            try:
                if kaynak is not None:
                    return list(kaynak.context.pages)
            except Exception:
                continue
        return [x for x in (self.sayfa,) if x is not None]

    def acilan_pencereye_gec(self, bekle_sn: float = 4.0):
        """Ana sayfa disinda yeni bir pencere acildiysa ona gecer."""
        bitis = time.time() + bekle_sn
        while time.time() < bitis:
            for sayfa in self._tum_sayfalar():
                if sayfa is self.ana_sayfa:
                    continue
                try:
                    if sayfa.is_closed():
                        continue
                except Exception:
                    continue
                self.sayfa = sayfa
                return sayfa
            try:
                (self.ana_sayfa or self.sayfa).wait_for_timeout(250)
            except Exception:
                time.sleep(0.25)
        return None

    def yan_pencereleri_kapat(self) -> None:
        """Acik kalmis secim/cikti pencerelerini kapatir, ana sayfaya doner."""
        for sayfa in self._tum_sayfalar():
            if sayfa is self.ana_sayfa:
                continue
            try:
                if not sayfa.is_closed():
                    sayfa.close()
            except Exception:
                pass
        if self.ana_sayfa is not None:
            self.sayfa = self.ana_sayfa

    def etiketli_alan(self, anahtar: str, tur: str = "input", bekle: float | None = None):
        """Ekrandaki etiket metninden yola cikip ilgili alani bulur.

        Panel bazen agir aciliyor: alan hemen gorunmezse pes etmez,
        `alan_bekleme` suresi boyunca beklemeye devam eder. Boylece yavas
        acilan bir sekme yuzunden kayit atlanmaz.
        """
        sure = self.ayarlar.alan_bekleme if bekle is None else bekle
        bitis = time.time() + max(0.0, sure)
        while True:
            oge = self._alani_ara(anahtar, tur)
            if oge is not None:
                return oge
            if self._durdur or time.time() >= bitis:
                return None
            try:
                self.sayfa.wait_for_timeout(300)
            except Exception:
                time.sleep(0.3)

    def _alani_ara(self, anahtar: str, tur: str = "input"):
        """Tek seferlik arama (bekleme yok). etiketli_alan bunu tekrar tekrar cagirir."""
        ozel = self.ayarlar.ozel_seciciler.get(anahtar)
        if ozel:
            for cerceve in self._cerceveler():
                try:
                    oge = cerceve.locator(ozel).first
                    if oge.count():
                        return oge
                except Exception:
                    continue

        haric = self.tarif.haric_metinler.get(anahtar, ())
        haric_kosul = "".join(f" and not(contains(., '{h}'))" for h in haric)
        for metin in self.tarif.etiketler.get(anahtar, ()):
            # [not(*)] -> icinde baska element olmayan (yaprak) dugum.
            # Bu olmadan, sayfanin tamamini kapsayan bir div de "Evrak No"
            # metnini icerdigi icin eslesiyor ve yanlis input bulunuyordu.
            xpath = (f"xpath=//*[self::td or self::label or self::span or self::div]"
                     f"[not(*)][string-length(normalize-space(.)) < 40]"
                     f"[contains(normalize-space(.), '{metin}'){haric_kosul}]"
                     f"/following::{tur}[1]")
            for cerceve in self._cerceveler():
                try:
                    oge = cerceve.locator(xpath).first
                    if oge.count():
                        return oge
                except Exception:
                    continue
        return None

    def dugme(self, anahtar: str, bekle: float | None = None):
        """Metnine gore dugme/link bulur; gorunene kadar bekler."""
        sure = self.ayarlar.alan_bekleme if bekle is None else bekle
        bitis = time.time() + max(0.0, sure)
        while True:
            oge = self._dugmeyi_ara(anahtar)
            if oge is not None:
                return oge
            if self._durdur or time.time() >= bitis:
                return None
            try:
                self.sayfa.wait_for_timeout(300)
            except Exception:
                time.sleep(0.3)

    def _dugmeyi_ara(self, anahtar: str):
        """Tek seferlik dugme aramasi (bekleme yok)."""
        for metin in self.tarif.butonlar.get(anahtar, ()):
            for cerceve in self._cerceveler():
                for secici in (f"xpath=//input[@type='submit' or @type='button']"
                               f"[contains(@value, '{metin}')]",
                               f"xpath=//*[self::a or self::button or self::img]"
                               f"[contains(normalize-space(.), '{metin}')"
                               f" or contains(@title, '{metin}')"
                               f" or contains(@alt, '{metin}')]"):
                    try:
                        oge = cerceve.locator(secici).first
                        if oge.count():
                            return oge
                    except Exception:
                        continue
        return None

    def menu_tikla(self, metin: str, zorunlu: bool = True) -> None:
        """Sol menu / sekme gibi tam metinle eslesen bir ogeye tiklar."""
        xpath = (f"xpath=//*[self::a or self::span or self::td or self::li]"
                 f"[normalize-space(.)='{metin}']")
        for cerceve in self._cerceveler():
            try:
                oge = cerceve.locator(xpath).first
                if oge.count():
                    oge.click()
                    self.sayfa_dursun(400)
                    return
            except Exception:
                continue
        if zorunlu:
            raise PanelHatasi(f"Menüde '{metin}' bulunamadı.")

    def sayfa_dursun(self, ek_bekleme_ms: int = 0) -> None:
        """Sayfa yuklenmesi bitene kadar bekler (agir acilan ekranlar icin)."""
        try:
            self.sayfa.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception:
            pass
        try:
            self.sayfa.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        if ek_bekleme_ms:
            try:
                self.sayfa.wait_for_timeout(ek_bekleme_ms)
            except Exception:
                pass

    def zorunlu_alan(self, anahtar: str, tur: str = "input"):
        oge = self.etiketli_alan(anahtar, tur)
        if oge is None:
            raise PanelHatasi(
                f"'{anahtar}' alanı ekranda bulunamadı. Panelin doğru "
                "sayfada açık olduğundan emin olun.")
        return oge

    def ekran_hatasi(self) -> str:
        """Ekranda kirmizi uyari/hata metni varsa dondurur.

        Buyuk/kucuk harf duyarsiz aranir: ekranda "Zorunlu alanlar bos
        birakilamaz" yazarken kucuk harfli kalip aranirsa hata GORULMEZ ve
        program kaydi basarili sanar.
        """
        kaliplar = self.tarif.hata_kaliplari
        for cerceve in self._cerceveler():
            try:
                ogeler = cerceve.locator(
                    "xpath=//*[contains(@style,'red') or contains(@class,'error')"
                    " or contains(@class,'kirmizi') or contains(@class,'uyari')]")
                sayi = min(ogeler.count(), 12)
            except Exception:
                continue
            for i in range(sayi):
                try:
                    metin = ogeler.nth(i).inner_text().strip()
                except Exception:
                    continue
                if not metin:
                    continue
                kucuk = metin.lower()
                if any(k in kucuk for k in kaliplar):
                    return metin[:200]
        return ""

    # ------------------------------------------------------------- oturum
    def tarayici_ac(self) -> None:
        """Kullanicinin kendi profiliyle tarayiciyi acar ve panele gider.

        Once bilgisayardaki Chrome, olmazsa Edge kullanilir; ikisi de yoksa
        Playwright'in kendi chromium'una duser. Boylece programin yaninda
        150 MB'lik tarayici tasimaya gerek kalmaz (tasinabilirlik sarti).
        """
        from playwright.sync_api import sync_playwright

        import tarayici as tarayici_yardimcisi

        self._pw = sync_playwright().start()
        profil = self.ayarlar.profil_klasoru or None

        # 1. YOL (tercih): Chrome'u normal baslatip ona baglan.
        # Playwright tarayiciyi kendi baslatirsa Chrome "test yazilimi
        # tarafindan kontrol ediliyor" cubugunu gosterir; bazi kurum
        # panelleri bu durumda girisi reddediyor. Kullanicinin kendi
        # Chrome'una baglaninca tarayici normal calisir.
        self._chrome_sureci, cdp = tarayici_yardimcisi.normal_chrome_baslat(profil)
        if cdp:
            try:
                self.tarayici = self._pw.chromium.connect_over_cdp(cdp)
                baglam = (self.tarayici.contexts[0] if self.tarayici.contexts
                          else self.tarayici.new_context(no_viewport=True))
                self.sayfa = (baglam.pages[0] if baglam.pages
                              else baglam.new_page())
                self._log("Tarayıcı açıldı (normal Chrome).")
            except Exception as e:
                self._log(f"Chrome'a bağlanılamadı, yedek yol deneniyor: {e}")
                self.sayfa = None
                self._chrome_kapat()

        # --disable-popup-blocking : bazi panellerde giris/secim ekrani yeni
        #   pencerede acilir, Chrome varsayilan olarak engeller.
        ortak = {"headless": False, "args": [
            "--start-maximized",
            "--disable-popup-blocking",
        ]}
        son_hata = None

        # 2. YOL (yedek): Playwright tarayiciyi kendi baslatir.
        for kanal in ("chrome", "msedge", None) if self.sayfa is None else ():
            secenek = dict(ortak)
            if kanal:
                secenek["channel"] = kanal
            try:
                if profil:
                    self.tarayici = self._pw.chromium.launch_persistent_context(
                        profil, no_viewport=True, **secenek)
                    self.sayfa = (self.tarayici.pages[0] if self.tarayici.pages
                                  else self.tarayici.new_page())
                else:
                    self.tarayici = self._pw.chromium.launch(**secenek)
                    self.sayfa = self.tarayici.new_context(
                        no_viewport=True).new_page()
                break
            except Exception as e:
                son_hata = e
                continue

        if self.sayfa is None:
            raise PanelHatasi(
                "Tarayıcı açılamadı. Bilgisayarınızda Google Chrome veya "
                f"Microsoft Edge kurulu olmalı.\n({son_hata})")

        self.ana_sayfa = self.sayfa
        adres = self.tarif.giris_adresi(self.ayarlar.giris_yolu)
        if not adres:
            self._log("Tarayıcı açık. Panelin adresini kendiniz girin.")
            return
        try:
            self.sayfa.goto(adres, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            # Kurum aglarinda guvenlik duvari/proxy sayfayi kesebiliyor.
            # Program yine de acik kalsin: kullanici adresi elle yazabilir.
            self._log(f"'{adres}' açılamadı: {e}")
            self._log("Tarayıcı açık. Adres çubuğuna kendiniz girebilirsiniz.")
            return

        self._log(f"Tarayıcı açıldı ({self.tarif.ad}). Girişi kendiniz yapın; "
                  "şifreniz programa girilmez.")
        for satir in self.tarif.giris_notlari(self.ayarlar.giris_yolu):
            self._log(satir)

    def giris_yapildi_mi(self) -> bool:
        """Giris tamamlandi mi — karari tarif verir."""
        try:
            return bool(self.tarif.giris_yapildi_mi(self))
        except Exception:
            return False

    def giris_bekle(self, zaman_asimi_sn: int = 600) -> bool:
        """Kullanici girisi tamamlayana kadar bekler."""
        baslangic = time.time()
        while time.time() - baslangic < zaman_asimi_sn:
            if self._durdur:
                return False
            if self.giris_yapildi_mi():
                self._log("Giriş algılandı.")
                return True
            time.sleep(2)
        return False

    def kapat(self) -> None:
        try:
            if self.tarayici:
                self.tarayici.close()
        except Exception:
            pass
        finally:
            try:
                if self._pw:
                    self._pw.stop()
            finally:
                # kendi baslattigimiz Chrome varsa o da kapansin
                self._chrome_kapat()

    # -------------------------------------------------------------- akis
    def ekrani_hazirla(self) -> None:
        """Kayit ekranina gelir — adimlari tarif bilir."""
        self.tarif.ekrani_hazirla(self)

    def kayit_gir(self, kayit: dict) -> None:
        """Tek kayit girer — adimlari tarif bilir."""
        self.tarif.kayit_gir(self, kayit)

    # ------------------------------------------------------------- dongu
    def calistir(self, kayitlar: list[dict], ilerleme=None) -> Sonuc:
        """Tum kayitlari sirayla girer; hata olan satiri atlar, rapor doner."""
        sonuc = Sonuc()
        toplam = len(kayitlar)

        for i, kayit in enumerate(kayitlar, 1):
            if self._durdur:
                self._log("Kullanıcı durdurdu.")
                break
            ad = kayit.get("cocuk_ad") or kayit.get("ad") or kayit.get("tc", "")
            try:
                self.kayit_gir(kayit)
                sonuc.basarili.append(kayit)
                self._log(f"[{i}/{toplam}] {ad} — kaydedildi")
            except Exception as e:
                sebep = str(e).strip() or e.__class__.__name__
                sonuc.atlanan.append((kayit, sebep))
                self._log(f"[{i}/{toplam}] {ad} — ATLANDI ({sebep[:90]})")
                self._formu_temizle()
            if ilerleme:
                ilerleme(i, toplam)

        return sonuc

    def _formu_temizle(self) -> None:
        """Hatali kayittan sonra ekrani yeni kayda hazir hale getirmeye calisir."""
        # acik kalmis secim/cikti penceresi varsa kapat, ana sayfaya don
        try:
            self.yan_pencereleri_kapat()
        except Exception:
            pass
        try:
            self.tarif.formu_temizle(self)
        except Exception:
            pass


def rapor_metni(sonuc: Sonuc) -> str:
    """Kullaniciya gosterilecek kapanis raporu."""
    satirlar = [sonuc.ozet_metni, ""]
    if sonuc.atlanan:
        satirlar.append("Girilemeyen kayıtlar:")
        for kayit, sebep in sonuc.atlanan:
            ad = kayit.get("cocuk_ad") or kayit.get("ad") or kayit.get("tc", "")
            tarih = kayit.get("tarih")
            tarih_s = tarih.strftime("%d.%m.%Y") if hasattr(tarih, "strftime") else ""
            satirlar.append(f"  • {tarih_s} {ad} — {sebep[:120]}")
    return "\n".join(satirlar)
