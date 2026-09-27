# -*- coding: utf-8 -*-
"""
Created on Thu Sep 24 21:37:16 2026

This code downloads the tickers of stocks in the sp500 index
after that it  saves them in an excel file "sp500_tickers.xlsx"


@author: Ghery Jorge Cardenas L.
"""


import pandas as pd
import requests

def obtener_sp500_tickers() -> list[str]:
    """
    Obtiene la lista actual de tickers del S&P 500 desde Wikipedia,
    usando un User-Agent para evitar error 403.
    """
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()  # lanza error si falla la petición

    tablas = pd.read_html(response.text)
    tabla = tablas[0]  # primera tabla = constituyentes del S&P 500
    tickers = tabla["Symbol"].tolist()
    return tickers

if __name__ == "__main__":
    sp500_tickers = obtener_sp500_tickers()
    print(f"Cantidad de tickers: {len(sp500_tickers)}")
    print( sp500_tickers)
    
    pd.DataFrame({"ticker": sp500_tickers}).to_csv(
        "sp500_tickers.csv",
        index=False,
        encoding="utf-8"
    )