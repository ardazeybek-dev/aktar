# -*- coding: utf-8 -*-
"""
arayuz.py — Aktar arayuzu.

Akis: sifre -> (istege bagli sablon uret) -> ekstre sec -> kisi listesi sec
      -> mod sec -> Oku ve Eslestir -> supheli satirlari onayla
      -> KAYITLARI BASLAT -> rapor.

Arayuz hangi panele girildigini bilmez; secim kutularini, giris
adreslerini ve ekran akisini secili TARIF bildirir (bkz. src/tarifler/).
"""
from __future__ import annotations

import queue
import os
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

KOK = Path(__file__).resolve().parent
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

import depo                                                     # noqa: E402
import kilit                                                    # noqa: E402
import sablon                                                   # noqa: E402
import panel                                                    # noqa: E402
import tarifler                                                 # noqa: E402
from ekstre import EkstreHatasi, satirlari_oku, ust_bilgi_oku   # noqa: E402
from eslestir import (EslestirmeHatasi, cocuk_listesi_yukle,    # noqa: E402
                      normalize, satirlari_eslestir)
from rapor import excel_cikti, html_rapor, ozet                 # noqa: E402

BASLIK = "AKTAR"
SURUM = "1.0"

R = {
    "zemin": "#2f3e50",
    "panel": "#3a4b5e",
    "panel2": "#243342",
    "cizgi": "#4a5d72",
    "sari": "#f5c542",
    "turuncu": "#e8730c",
    "turuncu_ust": "#f7862a",
    "mavi": "#3aa3e3",
    "mavi_ust": "#55b4ef",
    "mor": "#8e6fd8",
    "mor_ust": "#a184e8",
    "yesil": "#27ae60",
    "yesil_ust": "#2ecc71",
    "yesil_yazi": "#4ade80",
    "kirmizi": "#c0392b",
    "kirmizi_ust": "#e74c3c",
    "metin": "#e8edf2",
    "soluk": "#9db0c2",
}

def renkli_dugme(ana, metin, komut, zemin, ust_zemin, **ek):
    """Duz renkli, buyuk dugme (ttk yerine tk: arka plan rengi verilebiliyor)."""
    d = tk.Button(ana, text=metin, command=komut, bg=zemin, fg="white",
                  activebackground=ust_zemin, activeforeground="white",
                  font=ek.pop("font", ("Segoe UI", 10, "bold")),
                  relief="flat", bd=0, cursor="hand2",
                  padx=ek.pop("padx", 16), pady=ek.pop("pady", 11),
                  anchor=ek.pop("anchor", "w"), **ek)

    def uzerine(_):
        if str(d["state"]) != "disabled":
            d.config(bg=ust_zemin)

    def ayril(_):
        if str(d["state"]) != "disabled":
            d.config(bg=zemin)

    d.bind("<Enter>", uzerine)
    d.bind("<Leave>", ayril)
    return d


# --------------------------------------------------------------- sifre
class KilitEkrani(tk.Tk):
    """Acilis sifresi. Ilk calistirmada sifreyi kullanici belirler.

    Ana pencereden bagimsiz kendi penceresidir: gizlenmis bir koke bagli
    Toplevel Windows'ta hic gorunmedigi icin boyle kuruldu.
    """

    def __init__(self, ayarlar: dict):
        super().__init__()
        self.ayarlar = ayarlar
        self.basarili = False
        self.kullanici = ""
        self.ilk_kurulum = not ayarlar.get("kullanicilar")

        self.title("Aktar")
        self.resizable(False, False)
        self.configure(bg=R["zemin"])

        c = tk.Frame(self, bg=R["zemin"], padx=38, pady=30)
        c.pack()

        tk.Label(c, text="🤖  " + BASLIK, font=("Segoe UI", 16, "bold"),
                 fg=R["sari"], bg=R["zemin"]).pack()

        aciklama = ("Programı ilk kez açıyorsunuz.\nKendi şifrenizi belirleyin — "
                    "bu şifreyi sadece siz bilirsiniz."
                    if self.ilk_kurulum else "Devam etmek için şifrenizi girin.")
        tk.Label(c, text=aciklama, font=("Segoe UI", 9), fg=R["soluk"],
                 bg=R["zemin"], justify="center").pack(pady=(8, 18))

        self.sifre = tk.StringVar()
        giris = tk.Entry(c, textvariable=self.sifre, show="●", width=24,
                         font=("Segoe UI", 12), justify="center",
                         bg=R["panel2"], fg=R["metin"], insertbackground=R["metin"],
                         relief="flat", bd=8)
        giris.pack()
        giris.focus_set()

        self.sifre2 = tk.StringVar()
        if self.ilk_kurulum:
            tk.Label(c, text="şifreyi tekrar yazın", font=("Segoe UI", 8),
                     fg=R["soluk"], bg=R["zemin"]).pack(pady=(12, 4))
            tk.Entry(c, textvariable=self.sifre2, show="●", width=24,
                     font=("Segoe UI", 12), justify="center",
                     bg=R["panel2"], fg=R["metin"], insertbackground=R["metin"],
                     relief="flat", bd=8).pack()

        self.uyari = tk.Label(c, text="", font=("Segoe UI", 9),
                              fg="#ff8080", bg=R["zemin"])
        self.uyari.pack(pady=(12, 6))

        renkli_dugme(c, "Devam", self._onayla, R["yesil"], R["yesil_ust"],
                     anchor="center", padx=52).pack()
        self.bind("<Return>", lambda e: self._onayla())
        self.protocol("WM_DELETE_WINDOW", self._vazgec)

        self._ortala()
        self.lift()
        self.attributes("-topmost", True)
        self.after(300, lambda: self.attributes("-topmost", False))

    def _ortala(self):
        self.update_idletasks()
        x = self.winfo_screenwidth() // 2 - self.winfo_width() // 2
        y = self.winfo_screenheight() // 2 - self.winfo_height() // 2
        self.geometry(f"+{x}+{y}")

    def _onayla(self):
        s = self.sifre.get()
        if self.ilk_kurulum:
            hata = kilit.sifre_kurallari(s)
            if hata:
                self.uyari.config(text=hata)
                return
            if s != self.sifre2.get():
                self.uyari.config(text="İki şifre birbirini tutmuyor.")
                return
            self.ayarlar["kullanicilar"] = {
                "yönetici": kilit.kullanici_olustur(s, "yonetici")}
            self.ayarlar.pop("sifre", None)
            depo.kaydet(self.ayarlar)
            self.kullanici = "yönetici"
            self.basarili = True
            self.destroy()
            return

        ad = kilit.kullanici_bul(s, self.ayarlar.get("kullanicilar", {}))
        if ad:
            self.kullanici = ad
            self.basarili = True
            self.destroy()
        else:
            self.uyari.config(text="Şifre yanlış.")
            self.sifre.set("")

    def _vazgec(self):
        self.basarili = False
        self.destroy()


# ------------------------------------------------------- supheli duzeltme
class OnayPenceresi(tk.Toplevel):
    """Emin olunamayan bir satir icin ogrenciyi kullaniciya sectirir."""

    def __init__(self, ana, satir: dict, cocuklar: list[dict]):
        super().__init__(ana)
        self.satir = satir
        self.cocuklar = cocuklar
        self.secilen = None

        self.title("Bu ödeme kime ait?")
        self.configure(bg=R["zemin"])
        self.resizable(False, False)

        c = tk.Frame(self, bg=R["zemin"], padx=26, pady=22)
        c.pack(fill="both", expand=True)

        tk.Label(c, text="EKSTREDEKİ AÇIKLAMA", font=("Segoe UI", 8, "bold"),
                 fg=R["sari"], bg=R["zemin"]).pack(anchor="w")
        tk.Message(c, text=satir["aciklama"], width=560, font=("Segoe UI", 9),
                   bg=R["panel2"], fg=R["metin"], padx=12, pady=10,
                   relief="flat").pack(fill="x", pady=(4, 16))

        tk.Label(c, text="ÖĞRENCİYİ SEÇİN", font=("Segoe UI", 8, "bold"),
                 fg=R["sari"], bg=R["zemin"]).pack(anchor="w")

        adaylar = [ad for _, ad in satir.get("adaylar", [])]
        digerleri = [k["ad_soyad"] for k in cocuklar if k["ad_soyad"] not in adaylar]
        self.liste = ttk.Combobox(c, values=adaylar + digerleri, width=46,
                                  font=("Segoe UI", 10), state="readonly")
        if adaylar:
            self.liste.current(0)
        self.liste.pack(pady=(5, 8), ipady=3)

        if satir.get("adaylar"):
            en_iyi = satir["adaylar"][0]
            tk.Label(c, text=f"program bunu tahmin etti: {en_iyi[1]} (%{en_iyi[0]:.0f})",
                     font=("Segoe UI", 8), fg=R["soluk"], bg=R["zemin"]).pack(anchor="w")

        self.hatirla = tk.BooleanVar(value=True)
        tk.Checkbutton(c, text="bu veliyi bir daha sorma, aklında tut",
                       variable=self.hatirla, bg=R["zemin"], fg=R["metin"],
                       selectcolor=R["panel2"], activebackground=R["zemin"],
                       activeforeground=R["metin"], font=("Segoe UI", 9),
                       bd=0, highlightthickness=0).pack(anchor="w", pady=(12, 16))

        dugmeler = tk.Frame(c, bg=R["zemin"])
        dugmeler.pack(fill="x")
        renkli_dugme(dugmeler, "Bu satırı atla", self._atla, R["panel"], R["cizgi"],
                     anchor="center", font=("Segoe UI", 9)).pack(side="left")
        renkli_dugme(dugmeler, "Onayla", self._onayla, R["yesil"], R["yesil_ust"],
                     anchor="center", padx=26).pack(side="right")

        self.transient(ana)
        self.grab_set()

    def _onayla(self):
        ad = self.liste.get()
        cocuk = next((c for c in self.cocuklar if c["ad_soyad"] == ad), None)
        if not cocuk:
            messagebox.showwarning(BASLIK, "Öğrenci seçilmedi.", parent=self)
            return
        self.secilen = cocuk
        self.destroy()

    def _atla(self):
        self.secilen = None
        self.destroy()


# ------------------------------------------------------- kilit acma
class SifreSor(tk.Toplevel):
    """Program acikken ekrani kilitleyip sifre soran pencere.

    Acilistaki KilitEkrani ayri bir Tk penceresi; bu ise ana pencerenin
    uzerine gelen kilittir (Kilitle dugmesi bunu acar).
    """

    def __init__(self, ana, ayarlar: dict):
        super().__init__(ana)
        self.ayarlar = ayarlar
        self.basarili = False

        self.title("Kilitli")
        self.configure(bg=R["zemin"])
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._vazgec)

        c = tk.Frame(self, bg=R["zemin"], padx=34, pady=26)
        c.pack()
        tk.Label(c, text="🔒  Ekran kilitli", font=("Segoe UI", 14, "bold"),
                 fg=R["sari"], bg=R["zemin"]).pack()
        tk.Label(c, text="Devam etmek için şifrenizi girin.", font=("Segoe UI", 9),
                 fg=R["soluk"], bg=R["zemin"]).pack(pady=(8, 16))

        self.sifre = tk.StringVar()
        giris = tk.Entry(c, textvariable=self.sifre, show="●", width=22,
                         font=("Segoe UI", 12), justify="center",
                         bg=R["panel2"], fg=R["metin"], insertbackground=R["metin"],
                         relief="flat", bd=8)
        giris.pack()
        giris.focus_set()

        self.uyari = tk.Label(c, text="", font=("Segoe UI", 9), fg="#ff8080",
                              bg=R["zemin"])
        self.uyari.pack(pady=(10, 6))

        dugmeler = tk.Frame(c, bg=R["zemin"])
        dugmeler.pack(fill="x")
        renkli_dugme(dugmeler, "Programı Kapat", self._vazgec, R["kirmizi"],
                     R["kirmizi_ust"], anchor="center",
                     font=("Segoe UI", 9)).pack(side="left")
        renkli_dugme(dugmeler, "Aç", self._onayla, R["yesil"], R["yesil_ust"],
                     anchor="center", padx=28).pack(side="right")
        self.bind("<Return>", lambda e: self._onayla())

        self.transient(ana)
        self.grab_set()
        self.update_idletasks()
        x = ana.winfo_rootx() + ana.winfo_width() // 2 - self.winfo_width() // 2
        y = ana.winfo_rooty() + ana.winfo_height() // 3
        self.geometry(f"+{x}+{y}")

    def _onayla(self):
        if kilit.kullanici_bul(self.sifre.get(),
                               self.ayarlar.get("kullanicilar", {})):
            self.basarili = True
            self.destroy()
        else:
            self.uyari.config(text="Şifre yanlış.")
            self.sifre.set("")

    def _vazgec(self):
        self.basarili = False
        self.destroy()


# --------------------------------------------------- kullanici yonetimi
class KullanicilarEkrani(tk.Toplevel):
    """Yoneticinin programa girebilecek kisileri yonettigi ekran.

    Yonetici kendi sifresini kurar; ikinci bir kisiye kullanici acip sifre
    verebilir. O kisi kendi sifresiyle girer, silinebilir, sifresi degistirilebilir.
    Sifreler burada da duz yazilmaz, sadece geri cevrilemez ozeti saklanir.
    """

    def __init__(self, ana, ayarlar: dict, giren: str):
        super().__init__(ana)
        self.ayarlar = ayarlar
        self.giren = giren

        self.title("Kullanıcılar")
        self.configure(bg=R["zemin"])
        self.resizable(False, False)

        c = tk.Frame(self, bg=R["zemin"], padx=24, pady=20)
        c.pack(fill="both", expand=True)

        tk.Label(c, text="👥  PROGRAMA GİREBİLECEK KİŞİLER",
                 font=("Segoe UI", 10, "bold"), fg=R["sari"],
                 bg=R["zemin"]).pack(anchor="w")
        tk.Label(c, text="Şifreyi siz belirlersiniz; kimse sizin şifrenizi göremez.",
                 font=("Segoe UI", 8), fg=R["soluk"],
                 bg=R["zemin"]).pack(anchor="w", pady=(2, 12))

        self.liste = ttk.Treeview(c, columns=("ad", "rol"), show="headings", height=6)
        self.liste.heading("ad", text="Kullanıcı")
        self.liste.heading("rol", text="Yetki")
        self.liste.column("ad", width=220)
        self.liste.column("rol", width=110)
        self.liste.pack(fill="x")

        ekle = tk.Frame(c, bg=R["zemin"])
        ekle.pack(fill="x", pady=(14, 0))
        tk.Label(ekle, text="Ad", font=("Segoe UI", 9), fg=R["soluk"],
                 bg=R["zemin"]).grid(row=0, column=0, sticky="w")
        tk.Label(ekle, text="Şifre", font=("Segoe UI", 9), fg=R["soluk"],
                 bg=R["zemin"]).grid(row=0, column=1, sticky="w", padx=(10, 0))

        self.yeni_ad = tk.StringVar()
        self.yeni_sifre = tk.StringVar()
        tk.Entry(ekle, textvariable=self.yeni_ad, width=22, font=("Segoe UI", 10),
                 bg=R["panel2"], fg=R["metin"], insertbackground=R["metin"],
                 relief="flat", bd=6).grid(row=1, column=0, sticky="w")
        tk.Entry(ekle, textvariable=self.yeni_sifre, show="●", width=18,
                 font=("Segoe UI", 10), bg=R["panel2"], fg=R["metin"],
                 insertbackground=R["metin"], relief="flat",
                 bd=6).grid(row=1, column=1, sticky="w", padx=(10, 10))
        renkli_dugme(ekle, "Ekle", self._ekle, R["yesil"], R["yesil_ust"],
                     anchor="center", font=("Segoe UI", 9),
                     padx=18, pady=8).grid(row=1, column=2)

        self.uyari = tk.Label(c, text="", font=("Segoe UI", 9), fg="#ff8080",
                              bg=R["zemin"])
        self.uyari.pack(anchor="w", pady=(10, 4))

        alt = tk.Frame(c, bg=R["zemin"])
        alt.pack(fill="x", pady=(6, 0))
        renkli_dugme(alt, "Şifresini Değiştir", self._sifre_degistir,
                     R["panel"], R["cizgi"], anchor="center",
                     font=("Segoe UI", 9)).pack(side="left")
        renkli_dugme(alt, "Sil", self._sil, R["kirmizi"], R["kirmizi_ust"],
                     anchor="center", font=("Segoe UI", 9)).pack(side="left", padx=8)
        renkli_dugme(alt, "Kapat", self.destroy, R["panel"], R["cizgi"],
                     anchor="center", font=("Segoe UI", 9)).pack(side="right")

        self._tazele()
        self.transient(ana)
        self.grab_set()

    # ---------------------------------------------------------- islemler
    def _tazele(self):
        self.liste.delete(*self.liste.get_children())
        for ad, kayit in self.ayarlar.get("kullanicilar", {}).items():
            rol = "Yönetici" if kayit.get("rol") == "yonetici" else "Kullanıcı"
            etiket = ad + ("  (siz)" if ad == self.giren else "")
            self.liste.insert("", "end", iid=ad, values=(etiket, rol))

    def _secili(self) -> str:
        secim = self.liste.selection()
        return secim[0] if secim else ""

    def _ekle(self):
        ad = self.yeni_ad.get().strip()
        sifre = self.yeni_sifre.get()
        if not ad:
            self.uyari.config(text="Kullanıcı adı yazın.")
            return
        if ad in self.ayarlar.get("kullanicilar", {}):
            self.uyari.config(text="Bu isimde bir kullanıcı zaten var.")
            return
        hata = kilit.sifre_kurallari(sifre)
        if hata:
            self.uyari.config(text=hata)
            return

        self.ayarlar.setdefault("kullanicilar", {})[ad] = kilit.kullanici_olustur(
            sifre, "kullanici")
        depo.kaydet(self.ayarlar)
        self.yeni_ad.set("")
        self.yeni_sifre.set("")
        self.uyari.config(text=f"{ad} eklendi, kendi şifresiyle girebilir.",
                          fg=R["yesil_yazi"])
        self._tazele()

    def _sil(self):
        ad = self._secili()
        if not ad:
            self.uyari.config(text="Silinecek kullanıcıyı seçin.", fg="#ff8080")
            return
        if ad == self.giren:
            self.uyari.config(text="Kendinizi silemezsiniz.", fg="#ff8080")
            return
        if kilit.yonetici_mi(self.ayarlar.get("kullanicilar", {}), ad):
            self.uyari.config(text="Yönetici silinemez.", fg="#ff8080")
            return
        if not messagebox.askokcancel(BASLIK, f"{ad} silinsin mi?", parent=self):
            return
        self.ayarlar["kullanicilar"].pop(ad, None)
        depo.kaydet(self.ayarlar)
        self.uyari.config(text=f"{ad} silindi.", fg=R["yesil_yazi"])
        self._tazele()

    def _sifre_degistir(self):
        ad = self._secili()
        if not ad:
            self.uyari.config(text="Önce listeden bir kullanıcı seçin.", fg="#ff8080")
            return
        sifre = self.yeni_sifre.get()
        hata = kilit.sifre_kurallari(sifre)
        if hata:
            self.uyari.config(text="Yeni şifreyi Şifre kutusuna yazın. " + hata,
                              fg="#ff8080")
            return
        eski_rol = self.ayarlar["kullanicilar"][ad].get("rol", "kullanici")
        self.ayarlar["kullanicilar"][ad] = kilit.kullanici_olustur(sifre, eski_rol)
        depo.kaydet(self.ayarlar)
        self.yeni_sifre.set("")
        self.uyari.config(text=f"{ad} kullanıcısının şifresi değişti.",
                          fg=R["yesil_yazi"])


# ------------------------------------------------------------ ana pencere
class Uygulama(tk.Tk):
    def __init__(self, ayarlar: dict | None = None, kullanici: str = ""):
        super().__init__()
        self.ayarlar = ayarlar if ayarlar is not None else depo.yukle()
        self.kullanici = kullanici or "yönetici"
        self.tarif = tarifler.tarif_bul(self.ayarlar.get("tarif", ""))()
        self.modlar = self.tarif.modlar()
        self.title(f"Aktar v{SURUM}  ·  {self.tarif.ad}")
        # ekran kucukse pencereyi kirp: alt satirlar gorev cubugunun altinda kalmasin
        genislik = min(1180, self.winfo_screenwidth() - 80)
        yukseklik = min(870, self.winfo_screenheight() - 120)
        self.geometry(f"{genislik}x{yukseklik}+40+20")
        self.minsize(1000, 660)
        self.configure(bg=R["zemin"])

        son = self.ayarlar.get("son_ekstre", "")
        self.ekstre_yolu = tk.StringVar(value=son if son and Path(son).exists() else "")
        liste = self.ayarlar.get("cocuk_listesi", "")
        self.liste_yolu = tk.StringVar(value=liste if liste and Path(liste).exists() else "")
        self.sonuc: list[dict] = []
        self.cocuklar: list[dict] = []
        self.ust_bilgi: dict = {}
        self.surucu: panel.PanelOtomasyonu | None = None
        self.kuyruk: queue.Queue = queue.Queue()

        self._stil()
        self._arayuz()
        self._dosya_etiketlerini_tazele()
        self.protocol("WM_DELETE_WINDOW", self._kapanirken)
        self.after(120, self._kuyrugu_isle)

    # --------------------------------------------------------------- stil
    def _stil(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        s.configure("Treeview", rowheight=25, font=("Segoe UI", 9),
                    background=R["panel2"], fieldbackground=R["panel2"],
                    foreground=R["metin"], borderwidth=0)
        s.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"),
                    background="#1b2836", foreground=R["sari"], borderwidth=0)
        s.map("Treeview.Heading", background=[("active", "#22334a")])
        s.map("Treeview", background=[("selected", R["mavi"])],
              foreground=[("selected", "white")])
        s.configure("TCombobox", fieldbackground=R["panel2"], background=R["panel"],
                    foreground=R["metin"], arrowcolor=R["sari"],
                    bordercolor=R["cizgi"], lightcolor=R["panel"],
                    darkcolor=R["panel"], padding=5)
        s.map("TCombobox",
              fieldbackground=[("readonly", R["panel2"]), ("disabled", R["panel2"])],
              foreground=[("readonly", R["metin"]), ("disabled", R["soluk"])],
              selectbackground=[("readonly", R["panel2"])],
              selectforeground=[("readonly", R["metin"])],
              background=[("readonly", R["panel"]), ("active", R["panel"])],
              arrowcolor=[("readonly", R["sari"])])
        # acilir listenin kendisi ttk degil, klasik Listbox: option ile boyanir
        self.option_add("*TCombobox*Listbox.background", R["panel2"])
        self.option_add("*TCombobox*Listbox.foreground", R["metin"])
        self.option_add("*TCombobox*Listbox.selectBackground", R["mavi"])
        self.option_add("*TCombobox*Listbox.selectForeground", "white")
        self.option_add("*TCombobox*Listbox.font", "{Segoe UI} 9")
        s.configure("Dikey.Vertical.TScrollbar", background=R["panel"], troughcolor=R["panel2"],
                    bordercolor=R["panel2"], arrowcolor=R["metin"])
        s.configure("Yesil.Horizontal.TProgressbar", background=R["yesil_ust"],
                    troughcolor=R["panel2"], bordercolor=R["panel2"],
                    lightcolor=R["yesil_ust"], darkcolor=R["yesil"])

    def _baslikli_panel(self, ana, metin):
        """Koyu zeminde baslikli bir bolum kutusu doner: (dis cerceve, ic cerceve)."""
        dis = tk.Frame(ana, bg=R["panel"], highlightbackground=R["cizgi"],
                       highlightthickness=1)
        tk.Label(dis, text=metin, font=("Segoe UI", 9, "bold"), fg=R["sari"],
                 bg=R["panel"], anchor="w").pack(fill="x", padx=14, pady=(10, 0))
        ic = tk.Frame(dis, bg=R["panel"], padx=14, pady=10)
        ic.pack(fill="both", expand=True)
        return dis, ic

    # ------------------------------------------------------------ arayuz
    def _arayuz(self):
        ust = tk.Frame(self, bg=R["panel2"], height=62)
        ust.pack(fill="x")
        ust.pack_propagate(False)
        tk.Label(ust, text="🤖  " + BASLIK, font=("Segoe UI", 16, "bold"),
                 fg=R["sari"], bg=R["panel2"]).pack(side="left", padx=22)
        tk.Label(ust, text=f"v{SURUM}  ·  ekstreyi oku · kişiyi bul · panele kaydet",
                 font=("Segoe UI", 9), fg=R["soluk"], bg=R["panel2"]).pack(side="left")

        renkli_dugme(ust, "Çıkış", self._cikis, R["kirmizi"], R["kirmizi_ust"],
                     anchor="center", font=("Segoe UI", 9, "bold"),
                     padx=18, pady=7).pack(side="right", padx=(0, 20), pady=13)
        renkli_dugme(ust, "🔒  Kilitle", self._kilitle, R["panel"], R["cizgi"],
                     anchor="center", font=("Segoe UI", 9),
                     padx=14, pady=7).pack(side="right", padx=(0, 10), pady=13)

        if kilit.yonetici_mi(self.ayarlar.get("kullanicilar", {}), self.kullanici):
            renkli_dugme(ust, "👥  Kullanıcılar", self._kullanicilar,
                         R["panel"], R["cizgi"], anchor="center",
                         font=("Segoe UI", 9), padx=14,
                         pady=7).pack(side="right", padx=(0, 10), pady=13)

        govde = tk.Frame(self, bg=R["zemin"], padx=16, pady=14)
        govde.pack(fill="both", expand=True)

        # --- EN ALT: calistirma seridi (once yerlesir, hicbir zaman kesilmez)
        alt_dis, alt = self._baslikli_panel(
            govde, f"5 · PANELE KAYDET  ·  {self.tarif.ad}")
        alt_dis.pack(fill="x", side="bottom", pady=(12, 0))
        alt.columnconfigure(1, weight=1)

        sol = tk.Frame(alt, bg=R["panel"])
        sol.grid(row=0, column=0, rowspan=4, padx=(0, 14), sticky="ns")

        self.baslat_dugmesi = renkli_dugme(
            sol, "1 ·  TARAYICIYI AÇ", self._panel_baslat,
            R["mavi"], R["mavi_ust"], font=("Segoe UI", 10, "bold"),
            anchor="center", padx=18, pady=10)
        self.baslat_dugmesi.pack(fill="x")

        # Kullanici panelde kayit ekranina geldiginde kendisi basar.
        self.hazir_dugmesi = renkli_dugme(
            sol, "2 ·  HAZIRIM, BAŞLA", self._kayitlara_basla,
            R["yesil"], R["yesil_ust"], font=("Segoe UI", 10, "bold"),
            anchor="center", padx=18, pady=10)
        self.hazir_dugmesi.pack(fill="x", pady=(8, 0))
        self.hazir_dugmesi.config(state="disabled", bg=R["panel2"],
                                  fg=R["soluk"])

        self.durdur_dugmesi = renkli_dugme(
            alt, "Durdur", self._durdur, R["kirmizi"], R["kirmizi_ust"],
            anchor="center", font=("Segoe UI", 9, "bold"))
        self.durdur_dugmesi.grid(row=0, column=2, rowspan=4, padx=(14, 0),
                                 sticky="ns")
        self.durdur_dugmesi.config(state="disabled", bg=R["panel2"], fg=R["soluk"])

        # Giris yolu secenekleri tariften gelir; tarif tek adres veriyorsa
        # bu satir hic gosterilmez.
        yol = tk.Frame(alt, bg=R["panel"])
        yol.grid(row=0, column=1, sticky="ew")
        giris_secenekleri = self.tarif.giris_secenekleri()
        self.giris_yolu = tk.StringVar(
            value=self.ayarlar.get("giris_yolu", "")
            or self.tarif.varsayilan_giris)
        if len(giris_secenekleri) > 1:
            tk.Label(yol, text="Tarayıcı nereden açılsın:", font=("Segoe UI", 9),
                     fg=R["soluk"], bg=R["panel"]).pack(side="left")
        for etiket, deger, ipucu in (giris_secenekleri
                                     if len(giris_secenekleri) > 1 else ()):
            tk.Radiobutton(
                yol, text=etiket, value=deger, variable=self.giris_yolu,
                command=self._giris_yolu_degisti, font=("Segoe UI", 9),
                fg=R["metin"], bg=R["panel"], selectcolor=R["panel2"],
                activebackground=R["panel"], activeforeground=R["metin"],
                highlightthickness=0, bd=0).pack(side="left", padx=(10, 0))

        self.ilerleme = ttk.Progressbar(alt, mode="determinate",
                                        style="Yesil.Horizontal.TProgressbar")
        self.ilerleme.grid(row=2, column=1, sticky="ew", pady=(8, 0))

        self.gunluk = tk.Text(alt, height=4, font=("Consolas", 9), relief="flat",
                              bg=R["panel2"], fg=R["metin"], state="disabled",
                              wrap="none", bd=0, padx=10, pady=6)
        self.gunluk.grid(row=3, column=1, sticky="ew", pady=(8, 0))

        for satir in ("program hazır",
                      "ekstreyi okutup KAYITLARI BAŞLAT deyin",
                      f"{self.tarif.ad} girişini siz yapacaksınız, "
                      "şifreniz istenmez"):
            self._gunluge_yaz(satir)

        self.durum_metni = tk.StringVar(value="Sistem hazır.")
        tk.Label(alt, textvariable=self.durum_metni, font=("Segoe UI", 9, "bold"),
                 fg=R["yesil_yazi"], bg=R["panel"], anchor="w").grid(
            row=2, column=0, columnspan=3, sticky="w", pady=(9, 0))

        # --- 1-2-3: dosyalar
        dosya_dis, dosya = self._baslikli_panel(govde, "DOSYALAR")
        dosya_dis.pack(fill="x")
        for sutun in (0, 1, 2):
            dosya.columnconfigure(sutun, weight=1)

        renkli_dugme(dosya, "⭐   1. Örnek Excel Şablonu Oluştur", self._sablon_uret,
                     R["turuncu"], R["turuncu_ust"]).grid(
            row=0, column=0, sticky="ew", padx=(0, 8))
        renkli_dugme(dosya, "📗   2. Banka Ekstresini Seçin", self._ekstre_sec,
                     R["mavi"], R["mavi_ust"]).grid(
            row=0, column=1, sticky="ew", padx=8)
        renkli_dugme(dosya, "👥   3. Kişi Listesini Seçin", self._liste_sec,
                     R["mavi"], R["mavi_ust"]).grid(
            row=0, column=2, sticky="ew", padx=(8, 0))

        self.ekstre_etiketi = tk.Label(dosya, text="", font=("Segoe UI", 8),
                                       fg=R["soluk"], bg=R["panel"], anchor="w")
        self.ekstre_etiketi.grid(row=1, column=1, sticky="ew", padx=8, pady=(6, 0))
        self.liste_etiketi = tk.Label(dosya, text="", font=("Segoe UI", 8),
                                      fg=R["soluk"], bg=R["panel"], anchor="w")
        self.liste_etiketi.grid(row=1, column=2, sticky="ew", padx=(8, 0), pady=(6, 0))

        # --- 4: mod secimi
        mod_dis, mod = self._baslikli_panel(govde, "4 · MODU SEÇİN")
        mod_dis.pack(fill="x", pady=(12, 0))

        self.mod = tk.IntVar(value=int(self.ayarlar.get("mod", 0)))
        self.mod_dugmeleri: list[tk.Radiobutton] = []
        secimler = tk.Frame(mod, bg=R["panel"])
        secimler.pack(fill="x")
        for i, (etiket, _secim) in enumerate(self.modlar):
            d = tk.Radiobutton(secimler, text=etiket, variable=self.mod, value=i,
                               command=self._mod_degisti, indicatoron=False,
                               bg=R["panel2"],            # secili DEGILken zemin
                               selectcolor=R["mavi"],     # secili iken zemin
                               fg="white", activeforeground="white",
                               activebackground=R["cizgi"],
                               font=("Segoe UI", 10), bd=0, highlightthickness=0,
                               relief="flat", anchor="w", cursor="hand2",
                               padx=14, pady=8)
            d.grid(row=i // 2, column=i % 2, sticky="ew", padx=(0, 10), pady=4)
            self.mod_dugmeleri.append(d)
        secimler.columnconfigure(0, weight=1)
        secimler.columnconfigure(1, weight=1)

        ek = tk.Frame(mod, bg=R["panel"])
        ek.pack(fill="x", pady=(10, 0))
        # Tarifin sundugu ikinci liste (TEFBIS'te "gelir turu"). Tarif
        # liste vermiyorsa bu kutu hic gosterilmez.
        ilk_liste = next(iter(self.tarif.listeler({}).items()), None)
        self.ek_anahtar = ilk_liste[0] if ilk_liste else ""
        self.ek_baslik = tk.Label(
            ek, text=(ilk_liste[1].get("baslik", "") if ilk_liste else ""),
            font=("Segoe UI", 9), fg=R["soluk"], bg=R["panel"])
        self.ek_secim = tk.StringVar(value=self.ayarlar.get("ek_secim", ""))
        self.ek_kutu = ttk.Combobox(ek, textvariable=self.ek_secim,
                                    state="readonly", width=34,
                                    font=("Segoe UI", 9))
        if self.ek_anahtar:
            self.ek_baslik.pack(side="left")
            self.ek_kutu.pack(side="left", padx=(10, 26))

        tk.Label(ek, text="Açıklama", font=("Segoe UI", 9), fg=R["soluk"],
                 bg=R["panel"]).pack(side="left")
        self.aciklama_sablonu = tk.StringVar(value=self.ayarlar.get("aciklama_sablonu"))
        tk.Entry(ek, textvariable=self.aciklama_sablonu, font=("Segoe UI", 9),
                 bg=R["panel2"], fg=R["metin"], insertbackground=R["metin"],
                 relief="flat", bd=6).pack(side="left", fill="x", expand=True,
                                           padx=(10, 0))
        self._mod_degisti()

        # --- ONIZLEME (kalan alani doldurur)
        on_dis, on = self._baslikli_panel(govde, "ÖNİZLEME")
        on_dis.pack(fill="both", expand=True, pady=(12, 0))

        serit = tk.Frame(on, bg=R["panel"])
        serit.pack(fill="x", pady=(0, 8))
        renkli_dugme(serit, "🔍   Ekstreyi Oku ve Eşleştir", self._onizle,
                     R["mor"], R["mor_ust"], anchor="center").pack(side="left")
        renkli_dugme(serit, "Emin Olunamayanları Onayla", self._supheli_onayla,
                     R["panel2"], R["cizgi"], anchor="center",
                     font=("Segoe UI", 9)).pack(side="left", padx=8)
        renkli_dugme(serit, "Raporu Kaydet", self._rapor_kaydet,
                     R["panel2"], R["cizgi"], anchor="center",
                     font=("Segoe UI", 9)).pack(side="left")
        self.ozet_etiketi = tk.Label(serit, text="ekstre ve öğrenci listesini seçin",
                                     font=("Segoe UI", 9), fg=R["soluk"], bg=R["panel"])
        self.ozet_etiketi.pack(side="right")

        sutunlar = ("tarih", "evrak", "ogrenci", "tc", "tutar", "durum", "aciklama")
        basliklar = ("Tarih", "Evrak No", "Kişi", "T.C. No", "Tutar",
                     "Durum", "Ekstredeki açıklama")
        genislikler = (78, 78, 168, 102, 94, 152, 430)

        tablo_cerceve = tk.Frame(on, bg=R["panel"])
        tablo_cerceve.pack(fill="both", expand=True)
        self.tablo = ttk.Treeview(tablo_cerceve, columns=sutunlar, show="headings")
        for s, b, g in zip(sutunlar, basliklar, genislikler):
            self.tablo.heading(s, text=b)
            self.tablo.column(s, width=g, anchor="w")
        self.tablo.column("tutar", anchor="e")

        kaydirma = ttk.Scrollbar(tablo_cerceve, orient="vertical",
                                 style="Dikey.Vertical.TScrollbar", command=self.tablo.yview)
        self.tablo.configure(yscrollcommand=kaydirma.set)
        self.tablo.pack(side="left", fill="both", expand=True)
        kaydirma.pack(side="right", fill="y")

        self.tablo.tag_configure("kesin", background="#1e4638", foreground="#c8f3df")
        self.tablo.tag_configure("supheli", background="#4a3a1c", foreground="#ffe1a3")
        self.tablo.tag_configure("girildi", background="#22344f", foreground="#9db9e6")
        self.tablo.tag_configure("yok", background=R["panel2"], foreground="#7b8b9c")
        self.tablo.bind("<Double-1>", lambda e: self._satir_duzelt())

    # --------------------------------------------------------- yardimcilar
    def _mod_degisti(self, _olay=None):
        secili = self.mod.get()

        # Zemin rengini tk kendisi yonetiyor (selectcolor); biz sadece
        # secili olanin yazisini kalinlastiriyoruz.
        for i, d in enumerate(getattr(self, "mod_dugmeleri", [])):
            d.config(font=("Segoe UI", 10, "bold" if i == secili else "normal"))

        if self.ek_anahtar:
            liste = self.tarif.listeler(dict(self.modlar[secili][1]))
            degerler = liste.get(self.ek_anahtar, {}).get("degerler", [])
            self.ek_kutu.configure(values=degerler)
            if self.ek_secim.get() not in degerler and degerler:
                self.ek_secim.set(degerler[0])

        if hasattr(self, "durum_metni"):
            metin = f"Seçilen mod: {self.modlar[secili][0]}"
            if self.ek_anahtar:
                metin += f"  ·  {self.ek_secim.get()}"
            self._durum(metin)

    def _dosya_etiketlerini_tazele(self):
        for degisken, etiket in ((self.ekstre_yolu, self.ekstre_etiketi),
                                 (self.liste_yolu, self.liste_etiketi)):
            yol = degisken.get()
            if yol:
                etiket.config(text="✔ " + Path(yol).name, fg=R["yesil_yazi"])
            else:
                etiket.config(text="henüz dosya seçilmedi", fg=R["soluk"])

    def _durum(self, metin: str):
        self.durum_metni.set(metin)

    # ------------------------------------------------------------ dosyalar
    def _sablon_uret(self):
        klasor = filedialog.askdirectory(title="Örnek dosyalar nereye kaydedilsin?")
        if not klasor:
            return
        try:
            ekstre, ogrenci = sablon.ikisini_de_uret(klasor)
        except OSError as e:
            messagebox.showerror(BASLIK, f"Örnek dosyalar oluşturulamadı:\n{e}")
            return
        self._durum("Örnek Excel dosyaları oluşturuldu.")
        messagebox.showinfo(
            BASLIK,
            "İki örnek dosya oluşturuldu:\n\n"
            f"• {ekstre.name}\n     banka hareketleri için (bankanın kendi "
            "dosyasını da doğrudan verebilirsiniz)\n\n"
            f"• {ogrenci.name}\n     öğrenci ve T.C. listesi için\n\n"
            f"Klasör: {klasor}")

    def _ekstre_sec(self):
        yol = filedialog.askopenfilename(
            title="Banka ekstresini seçin",
            initialdir=self.ayarlar.get("son_ekstre_klasoru") or str(Path.home()),
            filetypes=[("Excel dosyası", "*.xlsx *.xlsm"), ("Tüm dosyalar", "*.*")])
        if yol:
            self.ekstre_yolu.set(yol)
            self.ayarlar["son_ekstre_klasoru"] = str(Path(yol).parent)
            depo.kaydet(self.ayarlar)
            self._dosya_etiketlerini_tazele()
            self._durum("Ekstre seçildi.")

    def _liste_sec(self):
        yol = filedialog.askopenfilename(
            title="Öğrenci listesini seçin",
            filetypes=[("Excel dosyası", "*.xlsx *.xlsm"), ("Tüm dosyalar", "*.*")])
        if yol:
            self.liste_yolu.set(yol)
            self.ayarlar["cocuk_listesi"] = yol
            depo.kaydet(self.ayarlar)
            self._dosya_etiketlerini_tazele()
            self._durum("Öğrenci listesi seçildi.")

    # ----------------------------------------------------------- onizleme
    def _onizle(self):
        if not self.ekstre_yolu.get():
            messagebox.showwarning(BASLIK, "Önce banka ekstresini seçin (2. adım).")
            return
        if not self.liste_yolu.get():
            messagebox.showwarning(BASLIK, "Önce öğrenci listesini seçin (3. adım).")
            return
        try:
            satirlar = satirlari_oku(self.ekstre_yolu.get())
            self.ust_bilgi = ust_bilgi_oku(self.ekstre_yolu.get())
            self.cocuklar = cocuk_listesi_yukle(self.liste_yolu.get())
        except (EkstreHatasi, EslestirmeHatasi) as e:
            messagebox.showerror(BASLIK, str(e))
            self._durum("Dosya okunamadı.")
            return
        except Exception as e:
            messagebox.showerror(BASLIK, f"Dosya okunamadı:\n{e}")
            self._durum("Dosya okunamadı.")
            return

        self.sonuc = satirlari_eslestir(satirlar, self.cocuklar,
                                        self.ayarlar.get("ogrenilen", {}),
                                        self.ayarlar.get("girilenler", {}))
        self.ayarlar["son_ekstre"] = self.ekstre_yolu.get()
        self._tabloyu_doldur()
        self._ayarlari_sakla()

    def _tabloyu_doldur(self):
        self.tablo.delete(*self.tablo.get_children())
        for i, s in enumerate(self.sonuc):
            durum = {"kesin": "panele girilecek",
                     "supheli": "onayınızı bekliyor",
                     "girildi": "daha önce girildi",
                     "yok": s["sebep"]}[s["durum"]]
            tutar = "-" if s["tutar"] is None else f"{s['tutar']:,.2f}".replace(
                ",", "#").replace(".", ",").replace("#", ".")
            self.tablo.insert(
                "", "end", iid=str(i),
                values=(s["tarih"].strftime("%d.%m.%Y"), s["evrak_no"],
                        s["cocuk_ad"], s["tc"], tutar, durum, s["aciklama"][:120]),
                tags=(s["durum"],))

        o = ozet(self.sonuc)
        ozet_metni = (f"{o['toplam']} hareket · {o['kesin']} kayıt hazır · "
                      f"{o['supheli']} onay bekliyor · {o['yok']} elendi")
        if o.get("girildi"):
            ozet_metni += f" · {o['girildi']} daha önce girilmiş"
        self.ozet_etiketi.config(text=ozet_metni)
        durum = f"{o['kesin']} kayıt panele girilmeye hazır."
        if o["supheli"]:
            durum += f"  {o['supheli']} satır onayınızı bekliyor."
        if o.get("girildi"):
            durum += f"  {o['girildi']} kayıt daha önce girildiği için atlanacak."
        self._durum(durum)

    def _satir_duzelt(self):
        secili = self.tablo.selection()
        if not secili or not self.cocuklar:
            return
        self._satiri_onaya_ac(int(secili[0]))

    def _satiri_onaya_ac(self, i: int):
        satir = self.sonuc[i]
        pencere = OnayPenceresi(self, satir, self.cocuklar)
        self.wait_window(pencere)
        if pencere.secilen:
            cocuk = pencere.secilen
            satir.update(tc=cocuk["tc"], cocuk_ad=cocuk["ad_soyad"],
                         veli_ad=cocuk.get("veli_ad", ""), durum="kesin",
                         kaynak="kullanıcı onayı", sebep="sizin onayınızla eşleşti")
            if pencere.hatirla.get():
                anahtar = normalize(satir["aciklama"])[:80]
                self.ayarlar.setdefault("ogrenilen", {})[anahtar] = cocuk["tc"]
                depo.kaydet(self.ayarlar)
        self._tabloyu_doldur()

    def _supheli_onayla(self):
        if not self.sonuc:
            messagebox.showinfo(BASLIK, "Önce ekstreyi okutun.")
            return
        supheliler = [i for i, s in enumerate(self.sonuc) if s["durum"] == "supheli"]
        if not supheliler:
            messagebox.showinfo(BASLIK, "Onay bekleyen satır yok.")
            return
        for i in supheliler:
            self._satiri_onaya_ac(i)

    @staticmethod
    def _masaustu() -> Path:
        """Masaustu klasoru. OneDrive'a tasinmis ya da Turkce adlandirilmis
        olabilir; bulunamazsa programin yanina kaydedilir."""
        adaylar = []
        for anahtar in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
            kok = os.environ.get(anahtar)
            if kok:
                adaylar += [Path(kok) / "Desktop", Path(kok) / "Masaüstü"]
        ev = Path.home()
        adaylar += [ev / "Desktop", ev / "Masaüstü", ev / "OneDrive" / "Desktop"]
        for aday in adaylar:
            try:
                if aday.is_dir():
                    return aday
            except OSError:
                continue
        return depo.program_klasoru()

    def _rapor_kaydet(self):
        """Kontrol listesini Excel + HTML olarak masaustune indirir.

        Klasor sorulmuyor: kullanici her ay ayni yeri secmek zorunda
        kalmasin diye dogrudan masaustune kaydedilip klasor aciliyor.
        """
        if not self.sonuc:
            messagebox.showinfo(BASLIK, "Önce ekstreyi okutun.")
            return

        klasor = self._masaustu()
        damga = datetime.now().strftime("%Y%m%d_%H%M")
        try:
            html_yolu = html_rapor(
                self.sonuc, klasor / f"aktar_rapor_{damga}.html",
                baslik="Ekstre Okuma ve Öğrenci Eşleştirme Raporu",
                kaynak_dosya=self.ekstre_yolu.get(), ust_bilgi=self.ust_bilgi)
            excel_yolu = excel_cikti(self.sonuc,
                                     klasor / f"aktar_liste_{damga}.xlsx")
        except OSError as e:
            messagebox.showerror(BASLIK, f"Rapor kaydedilemedi:\n{e}")
            return

        self._durum(f"Rapor masaüstüne kaydedildi: {excel_yolu.name}")
        messagebox.showinfo(
            BASLIK,
            "Masaüstüne iki dosya kaydedildi:\n\n"
            f"Excel  :  {excel_yolu.name}\n"
            f"Rapor  :  {Path(html_yolu).name}\n\n"
            "Excel'de her satırın hangi öğrenciye bağlandığı, T.C. numarası "
            "ve bağlanamadıysa sebebi yazılıdır.")
        try:                       # klasoru acip dosyayi isaretle
            os.startfile(klasor)   # noqa: S606 - sadece Windows
        except Exception:
            pass

    def _ayarlari_sakla(self):
        self.ayarlar.update(tarif=self.tarif.ad, mod=self.mod.get(),
                            ek_secim=self.ek_secim.get(),
                            aciklama_sablonu=self.aciklama_sablonu.get())
        depo.kaydet(self.ayarlar)

    # -------------------------------------------------------------- panel
    def _panel_baslat(self):
        girilecek = [s for s in self.sonuc if s["durum"] == "kesin"]
        if not girilecek:
            messagebox.showinfo(
                BASLIK, "Girilecek kayıt yok. Önce 'Ekstreyi Oku ve Eşleştir' deyin.")
            return

        supheli = sum(1 for s in self.sonuc if s["durum"] == "supheli")
        etiket = self.modlar[self.mod.get()][0] if self.modlar else ""
        mesaj = (f"{len(girilecek)} kayıt {self.tarif.ad} paneline girilecek.\n\n"
                 f"Mod: {etiket}\n"
                 + (f"{self.ek_baslik.cget('text')}: {self.ek_secim.get()}\n"
                    if self.ek_anahtar else "")
                 + "\nTarayıcı açılacak ve girişi kendiniz yapacaksınız.\n"
                 "Kayıt ekranına geldiğinizde programa dönüp "
                 "'2 · HAZIRIM, BAŞLA' düğmesine basın.")
        if supheli:
            mesaj += f"\n\nOnay bekleyen {supheli} satır girilmeyecek."
        if not messagebox.askokcancel(BASLIK, mesaj):
            return

        self._ayarlari_sakla()
        self._hazir = threading.Event()
        self.baslat_dugmesi.config(state="disabled", bg=R["panel2"], fg=R["soluk"])
        self.durdur_dugmesi.config(state="normal", bg=R["kirmizi"], fg="white")
        self.ilerleme.configure(maximum=len(girilecek), value=0)
        self._durum("Tarayıcı açılıyor...")

        threading.Thread(target=self._panel_isi, args=(girilecek,),
                         daemon=True).start()

    def _kayitlara_basla(self):
        """Kullanici panelde kayit ekranina geldigini bildirir."""
        if getattr(self, "_hazir", None) is None:
            return
        self.hazir_dugmesi.config(state="disabled", bg=R["panel2"],
                                  fg=R["soluk"])
        self._durum("Kayıtlar giriliyor...")
        self._hazir.set()

    def _giris_yolu_degisti(self):
        self.ayarlar["giris_yolu"] = self.giris_yolu.get()
        depo.kaydet(self.ayarlar)

    def _tefbis_isi(self, kayitlar: list[dict]):
        """Ayri is parcaciginda calisir; arayuze kuyrukla haber verir."""
        def yaz(mesaj):
            self.kuyruk.put(("gunluk", mesaj))

        # Secimler tarife ait; motor bunlari yorumlamaz, oldugu gibi tarife
        # aktarir. Boylece yeni bir panel eklemek arayuzu degistirmez.
        secim = dict(self.modlar[self.mod.get()][1]) if self.modlar else {}
        if self.ek_anahtar:
            secim[self.ek_anahtar] = self.ek_secim.get()
        secim["aciklama_sablonu"] = self.aciklama_sablonu.get()

        ayar = panel.MotorAyarlari(
            secim=secim,
            kayit_arasi_bekleme=float(self.ayarlar.get("kayit_arasi_bekleme", 2.0)),
            profil_klasoru=str(depo.program_klasoru() / "tarayici_profili"),
            giris_yolu=self.giris_yolu.get(),
            alan_bekleme=float(self.ayarlar.get("alan_bekleme", 45.0)),
            ozel_seciciler=self.ayarlar.get("ozel_seciciler", {}))

        surucu = panel.PanelOtomasyonu(self.tarif, ayar, gunlukcu=yaz)
        self.surucu = surucu
        try:
            surucu.tarayici_ac()
            yaz("Girişinizi yapın. Kayıt ekranına gelince "
                "'2 · HAZIRIM, BAŞLA' düğmesine basın.")
            self.kuyruk.put(("hazir_aktif", None))

            # Kullanici hazir oldugunu bildirene kadar beklenir.
            # Otomatik algilama yerine kullanici karari: ayni panele farkli
            # yollardan gelindiginde ekran degisebiliyor, algilama tutmuyor.
            while not self._hazir.wait(timeout=0.5):
                if surucu.durduruldu:
                    self.kuyruk.put(("bitti", "İşlem iptal edildi."))
                    return

            yaz("Başlıyorum...")
            surucu.ekrani_hazirla()
            sonuc = surucu.calistir(
                kayitlar,
                ilerleme=lambda i, n: self.kuyruk.put(("ilerleme", (i, n))))
            self.kuyruk.put(("girilenleri_kaydet", sonuc.basarili))
            self.kuyruk.put(("bitti", panel.rapor_metni(sonuc)))
        except Exception as e:
            self.kuyruk.put(("bitti", f"İşlem durdu:\n{e}"))
        finally:
            try:
                surucu.kapat()
            except Exception:
                pass
            self.surucu = None

    def _durdur(self):
        if self.surucu:
            self.surucu.durdur()
            self._gunluge_yaz("durdurma isteği gönderildi, sıradaki kayıtta duracak")
            self._durum("Durduruluyor...")

    def _kuyrugu_isle(self):
        try:
            while True:
                tur, veri = self.kuyruk.get_nowait()
                if tur == "gunluk":
                    self._gunluge_yaz(veri)
                elif tur == "hazir_aktif":
                    # Tarayici acildi; kullanici girisini yapip bu dugmeye basacak
                    self.hazir_dugmesi.config(state="normal", bg=R["yesil"],
                                              fg="white")
                elif tur == "girilenleri_kaydet":
                    self._girilenleri_kaydet(veri)
                elif tur == "ilerleme":
                    i, n = veri
                    self.ilerleme.configure(value=i)
                    self._durum(f"Kaydediliyor: {i} / {n}")
                elif tur == "bitti":
                    self.baslat_dugmesi.config(state="normal", bg=R["mavi"],
                                               fg="white")
                    self.hazir_dugmesi.config(state="disabled",
                                              bg=R["panel2"], fg=R["soluk"])
                    self.durdur_dugmesi.config(state="disabled", bg=R["panel2"],
                                               fg=R["soluk"])
                    self._gunluge_yaz("--- bitti ---")
                    self._durum("İşlem tamamlandı.")
                    messagebox.showinfo(BASLIK, veri)
        except queue.Empty:
            pass
        self.after(150, self._kuyrugu_isle)

    def _girilenleri_kaydet(self, basarili: list[dict]) -> None:
        """Panele girilen kayitlarin parmak izini saklar.

        Ayni ekstre bir daha islenirse bu kayitlar 'daha once girildi' diye
        isaretlenir ve TEKRAR GONDERILMEZ.
        """
        if not basarili:
            return
        girilenler = self.ayarlar.setdefault("girilenler", {})
        damga = datetime.now().strftime("%d.%m.%Y")
        for k in basarili:
            iz = depo.parmak_izi(k["tarih"], k["evrak_no"], k.get("tc", ""),
                                 k.get("tutar"))
            girilenler[iz] = {"tarih": damga, "ogrenci": k.get("cocuk_ad", "")}
        depo.kaydet(self.ayarlar)
        self._gunluge_yaz(f"{len(basarili)} kayıt hafızaya alındı, "
                          "aynı ekstre tekrar okutulursa bir daha girilmeyecek")

    def _kullanicilar(self):
        """Yonetici: programa girebilecek kisileri yonetir."""
        pencere = KullanicilarEkrani(self, self.ayarlar, self.kullanici)
        self.wait_window(pencere)

    def _kilitle(self):
        """Oturumu kapatir: ekrandaki veriyi temizler, sifre sorar."""
        self.sonuc = []
        self.cocuklar = []
        self.tablo.delete(*self.tablo.get_children())
        self.ozet_etiketi.config(text="ekran kilitlendi")
        self._durum("Kilitli — devam etmek için şifrenizi girin.")
        self.update_idletasks()

        pencere = SifreSor(self, self.ayarlar)
        self.wait_window(pencere)
        if not pencere.basarili:
            self.destroy()
            return
        self._durum("Sistem hazır.")
        self.ozet_etiketi.config(text="ekstre ve öğrenci listesini seçin")

    def _cikis(self):
        if messagebox.askokcancel(BASLIK, "Programdan çıkılsın mı?"):
            self._kapanirken()

    def _kapanirken(self):
        """Carpi ile kapatilsa bile ayarlar ve hafiza diske yazilir."""
        try:
            if self.ekstre_yolu.get():
                self.ayarlar["son_ekstre"] = self.ekstre_yolu.get()
            if self.liste_yolu.get():
                self.ayarlar["cocuk_listesi"] = self.liste_yolu.get()
            self._ayarlari_sakla()
        except Exception:
            pass
        self.destroy()

    def _gunluge_yaz(self, mesaj: str):
        self.gunluk.configure(state="normal")
        self.gunluk.insert("end", mesaj + "\n")
        self.gunluk.see("end")
        self.gunluk.configure(state="disabled")


def main():
    ayarlar = depo.yukle()

    kilit_ekrani = KilitEkrani(ayarlar)
    # Korumali klasorde (orn. Program Files) sifre ve hafiza diske yazilamaz.
    # Sessizce kaybolmasin diye kullanici daha sifresini kurmadan uyarilir.
    if not depo.yazilabilir_mi():
        kilit_ekrani.after(300, lambda: messagebox.showwarning(
            "Program klasörüne yazılamıyor",
            "Program şu an yazma izni olmayan bir klasörde çalışıyor:\n\n"
            f"{depo.program_klasoru()}\n\n"
            "Bu haliyle şifreniz ve öğrenilen eşleşmeler kaydedilmez; "
            "program her açılışta sizi yeniden tanımaz.\n\n"
            "Çözüm: klasörün tamamını Masaüstü'ne veya Belgeler'e kopyalayıp "
            "oradan çalıştırın.",
            parent=kilit_ekrani))
    kilit_ekrani.mainloop()
    if not kilit_ekrani.basarili:
        return

    Uygulama(ayarlar, kilit_ekrani.kullanici).mainloop()


if __name__ == "__main__":
    main()
