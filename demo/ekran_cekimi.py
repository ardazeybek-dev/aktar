# -*- coding: utf-8 -*-
"""
ekran_cekimi.py — Programin her ekranini tek tek acar, test eder ve
musteriye gonderilecek gorselleri uretir.

Calistirma:  python demo/ekran_cekimi.py
Cikti:       docs/ klasorune numarali PNG dosyalari

Her cekimden once o ekranin gercekten calistigi dogrulanir; bir ekran
acilmazsa veya beklenen icerik yoksa hata verir.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "src"))

from PIL import ImageGrab                       # noqa: E402

import depo                                     # noqa: E402
import kilit                                    # noqa: E402
import arayuz as main                           # noqa: E402

# Musteri verisi kullanilmaz; ekran goruntuleri uydurma sablon
# dosyalariyla uretilir (gercek isim/T.C./banka kaydi icermez).
EKSTRE = KOK / "demo" / "ekstre_sablonu.xlsx"
LISTE = KOK / "demo" / "ogrenci_listesi_sablonu.xlsx"
CIKTI = KOK / "docs"

sonuclar: list[tuple[str, bool, str]] = []


def kaydet(pencere, dosya_adi: str, aciklama: str, kontrol=None) -> None:
    """Pencereyi ekrandan yakalar; kontrol verilmisse once dogrular."""
    # Pencereyi one getirip en uste sabitle. Bu yapilmazsa ImageGrab
    # ekranin o bolgesinde ne varsa onu yakalar: baska bir uygulama
    # ustteyse goruntu tamamen yanlis cikar ve fark edilmez.
    pencere.update_idletasks()
    pencere.deiconify()
    pencere.lift()
    pencere.attributes("-topmost", True)
    pencere.update()
    try:
        pencere.focus_force()
    except Exception:
        pass
    time.sleep(0.8)
    pencere.update()

    tamam, not_ = True, ""
    if kontrol is not None:
        try:
            tamam = bool(kontrol())
        except Exception as e:
            tamam, not_ = False, f"{type(e).__name__}: {e}"

    x, y = pencere.winfo_rootx(), pencere.winfo_rooty()
    g, y_ = pencere.winfo_width(), pencere.winfo_height()
    hedef = CIKTI / dosya_adi
    ImageGrab.grab(bbox=(x - 1, y - 1, x + g + 1, y + y_ + 1)).save(hedef)
    try:
        pencere.attributes("-topmost", False)
    except Exception:
        pass

    sonuclar.append((dosya_adi, tamam, not_ or aciklama))
    print(f"  [{'OK  ' if tamam else 'HATA'}] {dosya_adi}  —  {aciklama}"
          + (f"   ({not_})" if not_ else ""))


def temiz_ayar() -> dict:
    depo.ayar_dosyasi().unlink(missing_ok=True)
    return depo.yukle()


# ------------------------------------------------------------- ekranlar
def cek_sifre_ilk_kurulum() -> None:
    print("\n1) Sifre ekrani — ilk kurulum")
    ayarlar = temiz_ayar()
    p = main.KilitEkrani(ayarlar)
    p.after(250, lambda: (p.sifre.set("mudur2026"), p.sifre2.set("mudur2026"),
                          kaydet(p, "01-sifre-ilk-kurulum.png",
                                 "programı ilk açışta kendi şifrenizi belirliyorsunuz",
                                 lambda: p.ilk_kurulum),
                          p._onayla()))
    p.mainloop()
    if not p.basarili:
        raise SystemExit("ilk kurulum basarisiz")


def cek_sifre_giris() -> None:
    print("\n2) Sifre ekrani — sonraki girisler")
    ayarlar = depo.yukle()
    p = main.KilitEkrani(ayarlar)
    p.after(250, lambda: (p.sifre.set("mudur2026"),
                          kaydet(p, "02-sifre-giris.png",
                                 "her açılışta şifre sorulur, yanlış şifre kabul edilmez",
                                 lambda: not p.ilk_kurulum),
                          p._onayla()))
    p.mainloop()


def cek_ana_ekranlar() -> None:
    print("\n3-6) Ana ekran adimlari")
    ayarlar = depo.yukle()
    u = main.Uygulama(ayarlar, "yönetici")

    def akis():
        # --- bos ekran
        kaydet(u, "03-ana-ekran.png",
               "açılış ekranı: numaralı adımlar, dosya seçilmemiş",
               lambda: "henüz" in u.ekstre_etiketi.cget("text"))

        # --- dosyalar secili
        u.ekstre_yolu.set(str(EKSTRE))
        u.liste_yolu.set(str(LISTE))
        u._dosya_etiketlerini_tazele()
        kaydet(u, "04-dosyalar-secildi.png",
               "ekstre ve öğrenci listesi seçildi, yeşil tikle görünüyor",
               lambda: "✔" in u.ekstre_etiketi.cget("text"))

        # --- mod degistirme
        u.mod_dugmeleri[2].invoke()
        u.update()
        kaydet(u, "05-mod-secimi.png",
               "mod değişince gelir türü listesi de değişiyor",
               lambda: "Okula Yapılan" in u.ek_secim.get())
        u.mod_dugmeleri[0].invoke()
        u.update()

        # --- eslestirme
        u._onizle()
        u.update()
        kaydet(u, "06-eslestirme-sonucu.png",
               "şablondaki 9 hareket okundu ve eşleştirildi",
               lambda: len(u.tablo.get_children()) == 9
               and sum(1 for s in u.sonuc if s["durum"] == "kesin") == 4)

        # --- onay penceresi (supheli satir)
        supheli = [i for i, s in enumerate(u.sonuc) if s["durum"] == "supheli"]
        if supheli:
            satir = u.sonuc[supheli[0]]
            onay = main.OnayPenceresi(u, satir, u.cocuklar)
            kaydet(onay, "07-onay-penceresi.png",
                   "emin olunamayan satırda program tahminini gösterip soruyor",
                   lambda: onay.liste.get() != "")
            onay.destroy()

        # --- kullanicilar
        ek = main.KullanicilarEkrani(u, u.ayarlar, "yönetici")
        ek.yeni_ad.set("idareci")
        ek.yeni_sifre.set("idareci2026")
        ek._ekle()
        kaydet(ek, "08-kullanicilar.png",
               "yönetici ikinci kişiye kullanıcı açıp şifre veriyor",
               lambda: "idareci" in u.ayarlar.get("kullanicilar", {}))
        ek.destroy()

        # --- kilit
        kilitli = main.SifreSor(u, u.ayarlar)
        kilitli.sifre.set("yanlissifre")
        kilitli._onayla()
        kaydet(kilitli, "09-ekran-kilidi.png",
               "kilitle düğmesi: ekran temizlenir, yanlış şifre kabul edilmez",
               lambda: not kilitli.basarili
               and "yanlış" in kilitli.uyari.cget("text").lower())
        kilitli.destroy()

        u.after(200, u.destroy)

    u.after(600, akis)
    u.mainloop()


def main_cekim() -> int:
    CIKTI.mkdir(exist_ok=True)
    # eski gorselleri temizle (rapor gorseli demo_calistir tarafindan uretiliyor)
    for eski in CIKTI.glob("*.png"):
        if eski.name != "demo_rapor.png":
            eski.unlink()

    ayar_yedek = depo.ayar_dosyasi()
    yedek = ayar_yedek.read_bytes() if ayar_yedek.exists() else None
    try:
        cek_sifre_ilk_kurulum()
        cek_sifre_giris()
        cek_ana_ekranlar()
    finally:
        ayar_yedek.unlink(missing_ok=True)
        if yedek is not None:
            ayar_yedek.write_bytes(yedek)

    print("\n" + "=" * 60)
    basarili = sum(1 for _, ok, _ in sonuclar if ok)
    print(f"{basarili}/{len(sonuclar)} ekran doğrulandı ve çekildi")
    for ad, ok, notu in sonuclar:
        print(f"  {'OK  ' if ok else 'HATA'}  {ad}")
    print("=" * 60)
    return 0 if basarili == len(sonuclar) else 1


if __name__ == "__main__":
    raise SystemExit(main_cekim())
