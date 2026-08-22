# -*- coding: utf-8 -*-
"""Iki asamali panel akisini arayuz uzerinden dogrular (pencere gostermeden)."""
import sys
import threading
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "src"))

import depo                                                   # noqa: E402
import arayuz as uygulama                                       # noqa: E402

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


gecen = kalan = 0


def kontrol(ad, sart):
    global gecen, kalan
    if sart:
        gecen += 1
        print(f"  [OK  ] {ad}")
    else:
        kalan += 1
        print(f"  [HATA] {ad}")


ayarlar = dict(depo.VARSAYILAN)
ayarlar["kullanicilar"] = {"yönetici": {"tuz": "00", "ozet": "00",
                                        "dongu": 1, "algo": "sha256",
                                        "rol": "yonetici"}}

app = uygulama.Uygulama(ayarlar, "yönetici")
app.withdraw()                      # ekranda gorunmesin

print("\n1) Dugmeler yerinde mi")
kontrol("1. asama dugmesi var", hasattr(app, "baslat_dugmesi"))
kontrol("2. asama dugmesi var", hasattr(app, "hazir_dugmesi"))
kontrol("1. asama metni dogru",
        "TARAYICIYI AÇ" in app.baslat_dugmesi.cget("text"))
kontrol("2. asama metni dogru",
        "BAŞLA" in app.hazir_dugmesi.cget("text"))

print("\n2) Baslangic durumlari")
kontrol("basla dugmesi basta PASIF",
        str(app.hazir_dugmesi.cget("state")) == "disabled")
kontrol("tarayici dugmesi basta AKTIF",
        str(app.baslat_dugmesi.cget("state")) == "normal")
kontrol("durdur basta PASIF",
        str(app.durdur_dugmesi.cget("state")) == "disabled")

print("\n3) Giris yolu secimi")
kontrol("giris yolu degiskeni var", hasattr(app, "giris_yolu"))
kontrol("varsayilan MEBBIS", app.giris_yolu.get() == "mebbis")
app.giris_yolu.set("tefbis")
app._giris_yolu_degisti()
kontrol("secim ayarlara yazildi", ayarlar.get("giris_yolu") == "tefbis")
app.giris_yolu.set("mebbis")
app._giris_yolu_degisti()

print("\n4) 'Hazirim' mekanizmasi")
app._hazir = threading.Event()
kontrol("baslangicta beklemede", not app._hazir.is_set())

# tarayici acildi mesaji gelince dugme aktiflesmeli
app.kuyruk.put(("hazir_aktif", None))
app._kuyrugu_isle()
kontrol("tarayici acilinca dugme AKTIF olur",
        str(app.hazir_dugmesi.cget("state")) == "normal")

app._kayitlara_basla()
kontrol("dugmeye basinca isaret verildi", app._hazir.is_set())
kontrol("basildiktan sonra dugme tekrar PASIF",
        str(app.hazir_dugmesi.cget("state")) == "disabled")

print("\n5) Bekleme sureleri")
kontrol("alan bekleme 45 sn", ayarlar.get("alan_bekleme") == 45.0)
kontrol("kayit arasi 2.0 sn", ayarlar.get("kayit_arasi_bekleme") == 2.0)

app.destroy()
print("\n" + "=" * 52)
print(f"GECEN: {gecen}   KALAN: {kalan}")
print("=" * 52)
sys.exit(1 if kalan else 0)
