# -*- coding: utf-8 -*-
"""
tarifler — Aktar'in tanidigi panel tarifleri.

Yeni bir panel eklemek icin: bu klasore `temel.Tarif`i miras alan bir
dosya koy ve asagidaki listeye ekle. Arayuz listeyi kendisi okur.
"""
from tarifler.temel import Tarif                  # noqa: F401
from tarifler.tefbis import TefbisTarifi

# Arayuzde gorunecek tarifler (sirasiyla)
TARIFLER = [TefbisTarifi]


def tarif_bul(ad: str):
    """Adina gore tarif sinifi dondurur; bulunamazsa ilkini verir."""
    for t in TARIFLER:
        if t.ad == ad:
            return t
    return TARIFLER[0]


def adlar() -> list:
    return [t.ad for t in TARIFLER]
