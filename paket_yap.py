# -*- coding: utf-8 -*-
"""
paket_yap.py — Aktar'i calistirilabilir hale getirir (PyInstaller).

Kullanim:
    python paket_yap.py         -> build/dist/Aktar/Aktar.exe  (klasor, hizli acilir)
    python paket_yap.py tek     -> build/tek/Aktar.exe         (tek dosya, yavas acilir)

Tek dosya surumu teknik olmayan kullanici icin daha kolaydir: klasor/_internal
derdi olmaz, sadece exe'ye cift tiklanir.
"""
import shutil
import subprocess
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent
AD = "Aktar"

# Programin kullanmadigi ama bagimliliklarla gelen agir paketler.
# Disarida birakilinca paket ~40 MB kuculuyor.
HARIC = ["numpy", "PIL", "cv2", "matplotlib", "pandas", "scipy",
         "IPython", "pytest", "setuptools"]


def main() -> int:
    tek_dosya = "tek" in sys.argv[1:]

    komut = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--onefile" if tek_dosya else "--onedir", "--windowed",
        "--name", AD,
        "--collect-all", "playwright",
        "--hidden-import", "rapidfuzz",
        "--hidden-import", "openpyxl",
        "--hidden-import", "tarayici",
        "--hidden-import", "excel_ac",
        # Tarifler arayuzden degil, tarifler/__init__.py uzerinden yukleniyor;
        # PyInstaller bunlari statik analizle goremedigi icin elle bildiriliyor.
        "--hidden-import", "tarifler",
        "--hidden-import", "tarifler.temel",
        "--hidden-import", "tarifler.tefbis",
        "--paths", str(KOK / "src"),
        "--distpath", str(KOK / "build" / ("tek" if tek_dosya else "dist")),
        "--workpath", str(KOK / "build" / ("tekwork" if tek_dosya else "work")),
        "--specpath", str(KOK / "build"),
    ]
    for m in HARIC:
        komut += ["--exclude-module", m]
    komut.append(str(KOK / "aktar.py"))

    print("Paketleniyor...")
    sonuc = subprocess.run(komut)
    if sonuc.returncode != 0:
        print("Paketleme basarisiz.")
        return sonuc.returncode

    hedef = (KOK / "build" / "tek") if tek_dosya else (KOK / "build" / "dist" / AD)

    # Ornek dosyalari programin yanina koy: kullanici hemen deneyebilsin
    if not tek_dosya:
        ornekler = hedef / "ornekler"
        ornekler.mkdir(exist_ok=True)
        for dosya in ("demo/ogrenci_listesi_sablonu.xlsx",
                      "demo/ekstre_sablonu.xlsx"):
            kaynak = KOK / dosya
            if kaynak.exists():
                shutil.copy2(kaynak, ornekler / kaynak.name)

    boyut = sum(f.stat().st_size for f in hedef.rglob("*") if f.is_file())
    print(f"\nTamam: {hedef}")
    print(f"Boyut: {boyut / 1024 / 1024:.0f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
