# -*- coding: utf-8 -*-
"""
testler.py — Programin cekirdek mantigini dogrular.

Calistirma:  python testler.py
Bu testler musterinin gercek Mayis ekstresi uzerinde calisir; bir degisiklik
eslestirmeyi bozarsa buradan aninda gorulur.
"""
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "src"))

import depo                                                     # noqa: E402
import kilit                                                    # noqa: E402
from ekstre import baslik_satirini_bul, satirlari_oku, tarih_parse, tutar_parse, ust_bilgi_oku  # noqa: E402
from eslestir import (aciklamadan_tc_cek, aidat_disi_sinyal,      # noqa: E402
                      cocuk_bul, cocuk_listesi_yukle, normalize,
                      satirlari_eslestir, tc_gecerli_mi)
from rapor import ozet                                          # noqa: E402

EKSTRE = KOK / "demo" / "test_ekstre.xlsx"
LISTE = KOK / "demo" / "test_liste.xlsx"


class TutarVeTarih(unittest.TestCase):
    def test_turkce_tutar(self):
        self.assertEqual(tutar_parse("-22.936,29"), -22936.29)
        self.assertEqual(tutar_parse("1.250,00 TL"), 1250.0)
        self.assertEqual(tutar_parse("936,29"), 936.29)

    def test_hucre_zaten_sayiysa_bozulmaz(self):
        """En sinsi hata: float'i str'e cevirip noktayi silmek (111111.0 -> 1111110)."""
        self.assertEqual(tutar_parse(111111), 111111.0)
        self.assertEqual(tutar_parse(1234.56), 1234.56)

    def test_bos_deger(self):
        self.assertIsNone(tutar_parse(None))
        self.assertIsNone(tutar_parse(""))

    def test_tarih(self):
        self.assertEqual(tarih_parse("21.05.2026"), date(2026, 5, 21))
        self.assertIsNone(tarih_parse("filanca"))


class TcDogrulama(unittest.TestCase):
    def test_mernis(self):
        self.assertFalse(tc_gecerli_mi("12345678901"))   # checksum tutmaz
        self.assertFalse(tc_gecerli_mi("01234567890"))   # 0 ile baslayamaz
        self.assertFalse(tc_gecerli_mi("1234567890"))    # 10 hane
        self.assertTrue(tc_gecerli_mi("99976892504"))    # demo listesinden

    def test_ibandaki_sayi_tc_sanilmaz(self):
        aciklama = ("INTERNET SGK( EMS/BAĞ/SSK)/ 00000000000000000000000000 / "
                    "ÖRNEK ANAOKULU OKUL AİLE BİRLİĞİ")
        self.assertIsNone(aciklamadan_tc_cek(aciklama))

    def test_aciklamadaki_gercek_tc_bulunur(self):
        self.assertEqual(
            aciklamadan_tc_cek("Gönd: VELİ ADI 99976892504 mayıs ödemesi"),
            "99976892504")


class MetinNormalizasyonu(unittest.TestCase):
    def test_turkce_harfler(self):
        self.assertEqual(normalize("ERGÜVEN Iğdır Öz"), "erguven igdir oz")
        self.assertEqual(normalize("KARTAL"), normalize("kartal"))


class EkstreOkuma(unittest.TestCase):
    def test_baslik_kendi_bulunur(self):
        import openpyxl
        ws = openpyxl.load_workbook(EKSTRE, data_only=True).active
        satir, harita = baslik_satirini_bul(ws)
        self.assertEqual(satir, 12)                  # sabit yazilmadi, bulundu
        self.assertIn("tarih", harita)
        self.assertIn("aciklama", harita)

    def test_satirlar(self):
        satirlar = satirlari_oku(EKSTRE)
        self.assertEqual(len(satirlar), 41)          # dip notlar/bosluklar elendi
        self.assertTrue(all(s["tarih"] for s in satirlar))

    def test_ust_bilgi(self):
        bilgi = ust_bilgi_oku(EKSTRE)
        self.assertIn("ANAOKULU", bilgi["kurum"])
        self.assertEqual(bilgi["donem"], "01.05.2026 - 30.05.2026")


class Eslestirme(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cocuklar = cocuk_listesi_yukle(LISTE)
        cls.sonuc = satirlari_eslestir(satirlari_oku(EKSTRE), cls.cocuklar)

    def test_yazim_hatasi_tolere_edilir(self):
        """'beren artal' -> Beren KARTAL; 'TUNCAL' -> TUNÇEL."""
        b = cocuk_bul("Gönd: GAMZE KARTAL Mayıs ayı beren artal 0067-Yapı ve Kredi",
                      self.cocuklar)
        self.assertEqual(b["cocuk"]["ad_soyad"], "Beren KARTAL")
        b2 = cocuk_bul("Gönd: HANDE TUNCAL Ceylin TUNCAL mayis ayı aydatı",
                       self.cocuklar)
        self.assertEqual(b2["cocuk"]["ad_soyad"], "Ceylin TUNÇEL")

    def test_cocuk_adi_basta_da_olsa_bulunur(self):
        b = cocuk_bul("Tuna Efe TAŞDELEN, nisan ayı kulüb ücreti NERMİN TAŞDELEN",
                      self.cocuklar)
        self.assertEqual(b["cocuk"]["ad_soyad"], "Tuna Efe TAŞDELEN")

    def test_benzer_soyadli_ogrenci_karistirilmaz(self):
        """Listede Ozan AYDINLI ve Umut Efe AYDINLI var; ayni soyad karistirmamali."""
        b = cocuk_bul("Gönd: BİRSEN AYDINLI Ozan AYDINLI -Mayıs ödemesi", self.cocuklar)
        self.assertEqual(b["cocuk"]["ad_soyad"], "Ozan AYDINLI")
        self.assertEqual(b["durum"], "kesin")

    def test_aidat_disi_hareket_eslesmez(self):
        for aciklama in ("MESAJ ÜCRETİ TUTARI", "BSMV TUTARI",
                         "AYŞE PERSONEL MAAŞ ÖDEMESİ AYŞE PERSONEL İnternet Havale"):
            self.assertEqual(cocuk_bul(aciklama, self.cocuklar)["durum"], "yok",
                             f"yanlis eslesme: {aciklama}")

    def test_eksi_tutar_otomatik_girilmez(self):
        """Isim tutsa bile para hesaptan cikmissa program kendiliginden girmez."""
        eksi = [s for s in self.sonuc
                if s["tutar"] is not None and s["tutar"] < 0 and s["cocuk_ad"]]
        self.assertTrue(eksi)
        for s in eksi:
            self.assertEqual(s["durum"], "supheli")
            self.assertEqual(s["tc"], "")

    def test_genel_sonuc(self):
        o = ozet(self.sonuc)
        self.assertEqual(o["toplam"], 41)
        self.assertEqual(o["kesin"], 20)
        self.assertEqual(o["supheli"], 3)
        self.assertEqual(o["yok"], 18)

    def test_hafiza_calisiyor(self):
        """Kullanici bir kez onaylayinca ayni aciklama bir daha sorulmaz."""
        satir = {"satir_no": 1, "tarih": date(2026, 5, 1), "evrak_no": "F1",
                 "aciklama": "Gönd: BILINMEYEN VELI birseyler odedi", "tutar": 100.0}
        ogrenilen = {normalize(satir["aciklama"])[:80]: self.cocuklar[0]["tc"]}
        sonuc = satirlari_eslestir([satir], self.cocuklar, ogrenilen)
        self.assertEqual(sonuc[0]["durum"], "kesin")
        self.assertEqual(sonuc[0]["kaynak"], "hafiza")


class EkstredekiTcSutunu(unittest.TestCase):
    """Musteri ekstreye kendi elle T.C. yazarsa program onu kullanmali."""

    @classmethod
    def setUpClass(cls):
        cls.cocuklar = cocuk_listesi_yukle(LISTE)

    def _satir(self, tc):
        return {"satir_no": 1, "tarih": date(2026, 5, 21), "evrak_no": "F13159",
                "aciklama": "Gönd: BİLİNMEYEN VELİ mayıs ödemesi", "tutar": 1250.0,
                "tc_sutunu": tc}

    def test_elle_yazilan_tc_kullanilir(self):
        gecerli = self.cocuklar[0]["tc"]
        sonuc = satirlari_eslestir([self._satir(gecerli)], self.cocuklar)[0]
        self.assertEqual(sonuc["durum"], "kesin")
        self.assertEqual(sonuc["tc"], gecerli)
        self.assertEqual(sonuc["kaynak"], "ekstredeki TC sutunu")
        self.assertEqual(sonuc["cocuk_ad"], self.cocuklar[0]["ad_soyad"])

    def test_bozuk_tc_otomatik_girilmez(self):
        sonuc = satirlari_eslestir([self._satir("1234")], self.cocuklar)[0]
        self.assertEqual(sonuc["durum"], "supheli")
        self.assertEqual(sonuc["tc"], "")

    def test_sutun_bossa_isimden_devam_eder(self):
        satir = self._satir("")
        satir["aciklama"] = "Gönd: BİRSEN AYDINLI Ozan AYDINLI -Mayıs ödemesi"
        sonuc = satirlari_eslestir([satir], self.cocuklar)[0]
        self.assertEqual(sonuc["durum"], "kesin")
        self.assertEqual(sonuc["cocuk_ad"], "Ozan AYDINLI")


class EkstreSablonu(unittest.TestCase):
    """Musteri bankanin dosyasi yerine sablonu doldurursa da okunmali."""

    def test_sablon_okunur(self):
        sablon = KOK / "demo" / "ekstre_sablonu.xlsx"
        satirlar = satirlari_oku(sablon)
        self.assertGreaterEqual(len(satirlar), 8)
        self.assertEqual(satirlar[0]["evrak_no"], "F13159")
        self.assertEqual(satirlar[0]["tutar"], 1250.0)
        self.assertEqual(satirlar[0]["tarih"], date(2026, 5, 21))


class MusteriEkstresindenGercekVakalar(unittest.TestCase):
    """Musterinin gonderdigi ekstre fotografindan alinan gercek satirlar.

    Bu satirlar elimizdeki Mayis dosyasinda yok; fotograftan cikarilip
    buraya tasindi (fotograf silindi, bilgi burada duruyor).
    """

    @classmethod
    def setUpClass(cls):
        cls.cocuklar = cocuk_listesi_yukle(LISTE)

    def _isle(self, aciklama, tutar):
        satir = {"satir_no": 1, "tarih": date(2026, 8, 3), "evrak_no": "F30154",
                 "aciklama": aciklama, "tutar": tutar}
        return satirlari_eslestir([satir], self.cocuklar)[0]

    def test_bagis_otomatik_girilmez(self):
        """15.000 TL 'Fatime Simsek Bagis' — velinin soyadi listede olsa bile
        bagis aidat degildir, program kendiliginden girmemeli."""
        s = self._isle("Gönd: SUNA ERGÜVEN SUNA ERGÜVEN Bağış 0046-Akbank T.A.Ş",
                       15000.0)
        self.assertEqual(s["durum"], "supheli")
        self.assertEqual(s["tc"], "")
        self.assertIn("bağış", s["sebep"])

    def test_kantin_odemesi_girilmez(self):
        s = self._isle("Talimat No: 156393917-Kantin İl.Baş.Ödemesi Muhasebe Birimi",
                       -2500.0)
        self.assertEqual(s["durum"], "yok")

    def test_isimsiz_aidat_tahmin_edilmez(self):
        """Aciklamada isim yoksa program tahmin yurutmez, kullaniciya birakir."""
        s = self._isle("2025-2026 Eğitim Öğretim yılı Çocuk Kulübü Kalan Ücreti Okul",
                       500.0)
        self.assertEqual(s["durum"], "yok")
        self.assertEqual(s["cocuk_ad"], "")

    def test_listede_olmayan_cocuk_baskasina_yazilmaz(self):
        """'mehmet aydin' listede yok; listedeki 'Ezgi AYDIN' ile karistirilmamali."""
        s = self._isle("mehmet aydın MUSTAFA AYDIN Ziraat Mobil Havale", 600.0)
        self.assertNotEqual(s["cocuk_ad"], "Ezgi AYDIN")
        self.assertEqual(s["tc"], "")

    def test_sinyal_kelimeleri(self):
        self.assertEqual(aidat_disi_sinyal("SUNA ERGÜVEN Bağış"), "bağış")
        self.assertEqual(aidat_disi_sinyal("Kantin İl.Baş.Ödemesi"), "kantin geliri")
        self.assertEqual(aidat_disi_sinyal("mayıs ayı kulüp ücreti"), "")

    def test_cocuk_adi_yanlis_tetiklemez(self):
        """'Kiraz' gibi bir isim 'kira' sinyalini tetiklememeli (kelime siniri)."""
        self.assertEqual(aidat_disi_sinyal("Gönd: AYSU KIRAZ Kiraz Naz mayıs"), "")


class MukerrerKayitKorumasi(unittest.TestCase):
    """Ayni ekstre iki kez islenirse TEFBIS'e cift kayit gitmemeli."""

    @classmethod
    def setUpClass(cls):
        cls.cocuklar = cocuk_listesi_yukle(LISTE)
        cls.satirlar = satirlari_oku(EKSTRE)

    def test_ilk_isleyiste_hepsi_hazir(self):
        sonuc = satirlari_eslestir(self.satirlar, self.cocuklar, {}, {})
        self.assertEqual(sum(1 for s in sonuc if s["durum"] == "kesin"), 20)
        self.assertEqual(sum(1 for s in sonuc if s["durum"] == "girildi"), 0)

    def test_girilmis_kayit_tekrar_gonderilmez(self):
        import depo
        ilk = satirlari_eslestir(self.satirlar, self.cocuklar, {}, {})
        girilenler = {}
        for k in ilk:
            if k["durum"] == "kesin":
                iz = depo.parmak_izi(k["tarih"], k["evrak_no"], k["tc"], k["tutar"])
                girilenler[iz] = {"tarih": "19.08.2026", "ogrenci": k["cocuk_ad"]}

        ikinci = satirlari_eslestir(self.satirlar, self.cocuklar, {}, girilenler)
        self.assertEqual(sum(1 for s in ikinci if s["durum"] == "kesin"), 0,
                         "ikinci okuyusta girilecek kayit kalmamali")
        self.assertEqual(sum(1 for s in ikinci if s["durum"] == "girildi"), 20)
        for s in ikinci:
            if s["durum"] == "girildi":
                self.assertIn("daha önce", s["sebep"])

    def test_farkli_tutar_ayri_kayit_sayilir(self):
        """Ayni cocuk ayni gun iki farkli tutar yatirirsa ikisi de girilmeli."""
        import depo
        iz1 = depo.parmak_izi(date(2026, 5, 21), "F13159", "99976892504", 1250.0)
        iz2 = depo.parmak_izi(date(2026, 5, 21), "F13159", "99976892504", 1500.0)
        self.assertNotEqual(iz1, iz2)

    def test_eksi_artı_ayni_kayit(self):
        """Isaret farki parmak izini degistirmemeli (mutlak deger alinir)."""
        import depo
        self.assertEqual(
            depo.parmak_izi(date(2026, 5, 21), "F1", "99976892504", -1250.0),
            depo.parmak_izi(date(2026, 5, 21), "F1", "99976892504", 1250.0))


class SablonZenginligi(unittest.TestCase):
    def test_ekstre_sablonu_tum_tipleri_icerir(self):
        sablon_yolu = KOK / "demo" / "ekstre_sablonu.xlsx"
        satirlar = satirlari_oku(sablon_yolu)
        self.assertGreaterEqual(len(satirlar), 8)
        metinler = " ".join(s["aciklama"] for s in satirlar)
        for beklenen in ("Bağış", "MESAJ ÜCRETİ", "artal", "TAŞDELEN"):
            self.assertIn(beklenen, metinler)

    def test_ogrenci_sablonu_ek_sutunla_okunur(self):
        """Sinif/Sube sutunu eklendi; program yine de dogru okumali."""
        cocuklar = cocuk_listesi_yukle(KOK / "demo" / "ogrenci_listesi_sablonu.xlsx")
        self.assertGreaterEqual(len(cocuklar), 5)
        self.assertEqual(cocuklar[0]["ad_soyad"], "Ayşe YILMAZ")
        self.assertEqual(cocuklar[0]["tc"], "11111111111")

    def test_yardim_sayfasi_var(self):
        import openpyxl
        for ad in ("ekstre_sablonu.xlsx", "ogrenci_listesi_sablonu.xlsx"):
            wb = openpyxl.load_workbook(KOK / "demo" / ad)
            self.assertIn("Nasıl Doldurulur", wb.sheetnames, ad)


class VeliUzerindenBulma(unittest.TestCase):
    """Parayi hep anne ya da baba yatiriyorsa aciklamada cocuk adi olmaz."""

    @classmethod
    def setUpClass(cls):
        cls.cocuklar = cocuk_listesi_yukle(LISTE)

    def _isle(self, aciklama):
        satir = {"satir_no": 1, "tarih": date(2026, 5, 21), "evrak_no": "F1",
                 "aciklama": aciklama, "tutar": 1250.0, "tc_sutunu": ""}
        return satirlari_eslestir([satir], self.cocuklar)[0]

    def test_anne_yatirinca_cocuk_bulunur(self):
        s = self._isle("Gönd: SEHER ÖZTÜRKMEN mayıs ayı ödemesi")
        self.assertEqual(s["durum"], "kesin")
        self.assertEqual(s["cocuk_ad"], "Bade Naz ÖZTÜRKMEN")
        self.assertEqual(s["kaynak"], "veli ismi")

    def test_baba_yatirinca_cocuk_bulunur(self):
        s = self._isle("Gönd: TAYFUN ÇAKIROĞLU mayıs kulüp ücreti")
        self.assertEqual(s["durum"], "kesin")
        self.assertEqual(s["cocuk_ad"], "Efe Han ÇAKIROĞLU")

    def test_listede_olmayan_veli_eslesmez(self):
        s = self._isle("Gönd: HASAN TANIMAZ mayıs ödemesi")
        self.assertEqual(s["durum"], "yok")
        self.assertEqual(s["tc"], "")

    def test_cocuk_adi_varsa_o_oncelikli(self):
        """Hem veli hem cocuk yaziliysa cocuk adindan bulmali."""
        s = self._isle("Gönd: SEHER ÖZTÜRKMEN Bade Naz ÖZTÜRKMEN mayıs")
        self.assertEqual(s["cocuk_ad"], "Bade Naz ÖZTÜRKMEN")
        self.assertEqual(s["kaynak"], "isim eslesme")


class BosAciklama(unittest.TestCase):
    """Veli aciklamaya hicbir sey yazmamis olabilir; satir kaybolmamali."""

    @classmethod
    def setUpClass(cls):
        cls.cocuklar = cocuk_listesi_yukle(LISTE)

    def test_bos_aciklamali_satir_gosterilir(self):
        satir = {"satir_no": 1, "tarih": date(2026, 5, 21), "evrak_no": "F99",
                 "aciklama": "", "tutar": 1250.0, "tc_sutunu": ""}
        sonuc = satirlari_eslestir([satir], self.cocuklar)
        self.assertEqual(len(sonuc), 1, "bos aciklamali satir atlanmamali")
        self.assertEqual(sonuc[0]["durum"], "yok")
        self.assertIn("açıklama boş", sonuc[0]["sebep"])

    def test_bos_aciklamada_tc_sutunu_calisir(self):
        """Aciklama bos ama kullanici T.C. yazmissa yine de girilebilmeli."""
        satir = {"satir_no": 1, "tarih": date(2026, 5, 21), "evrak_no": "F99",
                 "aciklama": "", "tutar": 1250.0,
                 "tc_sutunu": self.cocuklar[0]["tc"]}
        sonuc = satirlari_eslestir([satir], self.cocuklar)[0]
        self.assertEqual(sonuc["durum"], "kesin")
        self.assertEqual(sonuc["cocuk_ad"], self.cocuklar[0]["ad_soyad"])


class AnneBabaSutunlari(unittest.TestCase):
    """Okul kaydindan gelen 6 sutunlu liste (ogrenci + anne + baba).

    En tehlikeli senaryo: anne sutunlari listenin BASINDA olursa program
    anneyi ogrenci sanabilir ve TEFBIS'e ANNENIN T.C.'sini yazabilir.
    """

    def _liste(self, basliklar, satirlar):
        import tempfile

        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(basliklar)
        for r in satirlar:
            ws.append(r)
        yol = Path(tempfile.mkdtemp()) / "liste.xlsx"
        wb.save(yol)
        return cocuk_listesi_yukle(yol)

    def test_cocuk_once_yazilirsa(self):
        c = self._liste(
            ["Çocuk Ad Soyad", "Çocuk TC", "Anne Ad Soyad", "Anne TC",
             "Baba Ad Soyad", "Baba TC"],
            [["Ayşe YILMAZ", "11111111111", "Fatma YILMAZ", "22222222222",
              "Ahmet YILMAZ", "33333333333"]])[0]
        self.assertEqual(c["ad_soyad"], "Ayşe YILMAZ")
        self.assertEqual(c["tc"], "11111111111")

    def test_anne_once_yazilirsa_ogrenci_karistirilmaz(self):
        """Sutun sirasi degisse bile ANNE ogrenci sanilmamali."""
        c = self._liste(
            ["Anne Ad Soyad", "Anne TC", "Baba Ad Soyad", "Baba TC",
             "Çocuk Ad Soyad", "Çocuk TC"],
            [["Fatma YILMAZ", "22222222222", "Ahmet YILMAZ", "33333333333",
              "Ayşe YILMAZ", "11111111111"]])[0]
        self.assertEqual(c["ad_soyad"], "Ayşe YILMAZ", "anne ogrenci sanildi")
        self.assertEqual(c["tc"], "11111111111", "annenin T.C.'si alindi")

    def test_anne_ve_baba_veli_olarak_alinir(self):
        c = self._liste(
            ["Öğrenci", "TC", "Anne", "Anne TC", "Baba", "Baba TC"],
            [["Ayşe YILMAZ", "11111111111", "Fatma YILMAZ", "22222222222",
              "Ahmet YILMAZ", "33333333333"]])[0]
        self.assertIn("Fatma YILMAZ", c["veli_adlari"])
        self.assertIn("Ahmet YILMAZ", c["veli_adlari"])

    def test_anneden_de_babadan_da_cocuga_ulasilir(self):
        cocuklar = self._liste(
            ["Öğrenci Ad Soyad", "Öğrenci TC", "Anne Ad Soyad", "Anne TC",
             "Baba Ad Soyad", "Baba TC"],
            [["Ayşe YILMAZ", "11111111111", "Fatma YILMAZ", "22222222222",
              "Ahmet YILMAZ", "33333333333"]])

        def isle(aciklama):
            satir = {"satir_no": 1, "tarih": date(2026, 5, 1), "evrak_no": "F1",
                     "aciklama": aciklama, "tutar": 1250.0, "tc_sutunu": ""}
            return satirlari_eslestir([satir], cocuklar)[0]

        anne = isle("Gönd: FATMA YILMAZ mayıs ayı ödemesi")
        self.assertEqual(anne["durum"], "kesin")
        self.assertEqual(anne["cocuk_ad"], "Ayşe YILMAZ")

        baba = isle("Gönd: AHMET YILMAZ mayıs kulüp ücreti")
        self.assertEqual(baba["durum"], "kesin")
        self.assertEqual(baba["cocuk_ad"], "Ayşe YILMAZ")

    def test_kardeslerde_veliden_gidilirse_sorulur(self):
        cocuklar = self._liste(
            ["Öğrenci Ad Soyad", "Öğrenci TC", "Anne Ad Soyad", "Anne TC"],
            [["Doruk AYDINLI", "44444444444", "SEVİM AYDINLI", "55555555555"],
             ["İpek AYDINLI", "77777777777", "SEVİM AYDINLI", "55555555555"]])
        satir = {"satir_no": 1, "tarih": date(2026, 5, 1), "evrak_no": "F1",
                 "aciklama": "Gönd: SEVİM AYDINLI mayıs ödemesi", "tutar": 1250.0,
                 "tc_sutunu": ""}
        s = satirlari_eslestir([satir], cocuklar)[0]
        self.assertEqual(s["durum"], "supheli")
        self.assertEqual(s["tc"], "")

    def test_8_sutunlu_liste(self):
        """Sira no ve sinif eklenmis 8 sutunlu liste de okunmali."""
        c = self._liste(
            ["Sıra No", "Öğrenci Ad Soyad", "Öğrenci TC", "Sınıf",
             "Anne Ad Soyad", "Anne TC", "Baba Ad Soyad", "Baba TC"],
            [[1, "Ayşe YILMAZ", "11111111111", "5-A", "Fatma YILMAZ",
              "22222222222", "Ahmet YILMAZ", "33333333333"]])[0]
        self.assertEqual(c["ad_soyad"], "Ayşe YILMAZ")
        self.assertEqual(c["tc"], "11111111111")
        self.assertEqual(len(c["veli_adlari"]), 2)

    def test_10_sutunlu_liste(self):
        """Dogum tarihi, telefon gibi fazladan sutunlar karistirmamali."""
        c = self._liste(
            ["Sıra", "Öğrenci Ad Soyad", "Öğrenci TC", "Doğum Tarihi", "Sınıf",
             "Anne Ad Soyad", "Anne TC", "Baba Ad Soyad", "Baba TC", "Telefon"],
            [[1, "Ayşe YILMAZ", "11111111111", "01.01.2020", "5-A",
              "Fatma YILMAZ", "22222222222", "Ahmet YILMAZ", "33333333333",
              "05551112233"]])[0]
        self.assertEqual(c["ad_soyad"], "Ayşe YILMAZ")
        self.assertEqual(c["tc"], "11111111111")

    def test_sutunlar_karisik_sirada(self):
        """Sutun sirasi tamamen degisse bile dogru okumali."""
        c = self._liste(
            ["Baba TC", "Sınıf", "Anne Ad Soyad", "Öğrenci TC", "Telefon",
             "Baba Ad Soyad", "Öğrenci Ad Soyad", "Anne TC"],
            [["33333333333", "5-A", "Fatma YILMAZ", "11111111111", "0555",
              "Ahmet YILMAZ", "Ayşe YILMAZ", "22222222222"]])[0]
        self.assertEqual(c["ad_soyad"], "Ayşe YILMAZ", "karisik sirada ogrenci sasti")
        self.assertEqual(c["tc"], "11111111111")
        self.assertIn("Fatma YILMAZ", c["veli_adlari"])

    def test_kardeslerde_cocuk_adi_yazilirsa_dogru_secilir(self):
        cocuklar = self._liste(
            ["Öğrenci Ad Soyad", "Öğrenci TC", "Anne Ad Soyad", "Anne TC"],
            [["Doruk AYDINLI", "44444444444", "SEVİM AYDINLI", "55555555555"],
             ["İpek AYDINLI", "77777777777", "SEVİM AYDINLI", "55555555555"]])
        satir = {"satir_no": 1, "tarih": date(2026, 5, 1), "evrak_no": "F1",
                 "aciklama": "Gönd: SEVİM AYDINLI İpek AYDINLI mayıs", "tutar": 1250.0,
                 "tc_sutunu": ""}
        s = satirlari_eslestir([satir], cocuklar)[0]
        self.assertEqual(s["durum"], "kesin")
        self.assertEqual(s["cocuk_ad"], "İpek AYDINLI")


class Sifre(unittest.TestCase):
    def test_dogrula(self):
        kayit = kilit.ozet_uret("gizli2026")
        self.assertTrue(kilit.dogrula("gizli2026", kayit))
        self.assertFalse(kilit.dogrula("gizli2027", kayit))
        self.assertFalse(kilit.dogrula("gizli2026", None))

    def test_sifre_diske_acik_yazilmaz(self):
        kayit = kilit.ozet_uret("gizli2026")
        self.assertNotIn("gizli2026", str(kayit))

    def test_kisa_sifre_reddedilir(self):
        self.assertTrue(kilit.sifre_kurallari("ab"))
        self.assertEqual(kilit.sifre_kurallari("abcd"), "")


class SaltOkunurKlasor(unittest.TestCase):
    """Okul bilgisayarinda program korumali bir klasorde calisabilir.

    Bu durumda program COKMEMELI ama ayarlarin kaydedilmedigi de
    sessizce gecistirilmemeli; yazilabilir_mi() bunu onceden haber verir.
    """

    def setUp(self):
        self.gercek = depo.program_klasoru

    def tearDown(self):
        depo.program_klasoru = self.gercek

    def test_yazilabilen_klasorde_dogru(self):
        with tempfile.TemporaryDirectory() as gecici:
            depo.program_klasoru = lambda: Path(gecici)
            self.assertTrue(depo.yazilabilir_mi())
            self.assertTrue(depo.kaydet({"modul": "deneme"}))

    def test_yazilamayan_klasorde_cokmez(self):
        depo.program_klasoru = lambda: Path("Z:/olmayan_surucu/klasor")
        self.assertFalse(depo.yazilabilir_mi())
        self.assertFalse(depo.kaydet({"modul": "deneme"}))   # istisna firlatmaz

    def test_deneme_dosyasi_geride_kalmaz(self):
        with tempfile.TemporaryDirectory() as gecici:
            depo.program_klasoru = lambda: Path(gecici)
            depo.yazilabilir_mi()
            self.assertEqual(list(Path(gecici).iterdir()), [])

    def test_bozuk_ayar_dosyasi_varsayilanla_acilir(self):
        with tempfile.TemporaryDirectory() as gecici:
            depo.program_klasoru = lambda: Path(gecici)
            (Path(gecici) / "ayarlar.json").write_text("{bozuk", encoding="utf-8")
            veri = depo.yukle()
            self.assertEqual(veri["aciklama_sablonu"], depo.VARSAYILAN["aciklama_sablonu"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
