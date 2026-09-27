# -*- coding: utf-8 -*-
"""
Created on Fri Sep 25 08:58:24 2026

@author: HP
"""

import pandas as pd
import numpy as np

# ==========================================
# CONFIGURACIÓN
# ==========================================
archivo_top20 = "retornos_por_ticker.xlsx"
archivo_backtest = "backtest_resultados.xlsx"
archivo_salida = "metricas_top20_corregidas.xlsx"

# Tasa libre de riesgo anual.
# Puedes modificarla según el Treasury de 5 años que quieras usar.
RISK_FREE_RATE_ANNUAL = 0.035

# Como los resultados son por operación, no por día,
# no conviene restar directamente 3.5% / 252.
# Usaremos una tasa equivalente por operación.
# Aproximación: una operación dura, en promedio, 7.5 días bursátiles.
AVG_TRADE_DAYS = 7.5
TRADING_DAYS_YEAR = 252

RISK_FREE_RATE_PER_TRADE = (
    (1 + RISK_FREE_RATE_ANNUAL)
    ** (AVG_TRADE_DAYS / TRADING_DAYS_YEAR)
    - 1
)

print(
    f"Tasa libre de riesgo anual: {RISK_FREE_RATE_ANNUAL:.2%}"
)
print(
    f"Tasa libre de riesgo por operación: "
    f"{RISK_FREE_RATE_PER_TRADE:.6%}"
)


# ==========================================
# FUNCIONES AUXILIARES
# ==========================================
def clean_pnl_series(df):
    """
    Devuelve únicamente el PnL de operaciones cerradas.

    Se conservan solo las filas donde sell_signal == 1.
    Cada una de esas filas representa una operación finalizada.
    """
    required_columns = ["pnl_pct", "sell_signal"]

    for column in required_columns:
        if column not in df.columns:
            raise ValueError(
                f"No existe la columna requerida: {column}"
            )

    # Convertir a numérico por seguridad
    pnl = pd.to_numeric(df["pnl_pct"], errors="coerce")
    sell_signal = pd.to_numeric(
        df["sell_signal"],
        errors="coerce"
    )

    # Solo las filas donde se cerró una operación
    pnl_trades = pnl[sell_signal == 1]

    # Eliminar valores faltantes
    pnl_trades = pnl_trades.dropna()

    return pnl_trades.reset_index(drop=True)


def calculate_win_rate(pnl):
    """Porcentaje de operaciones ganadoras."""
    if len(pnl) == 0:
        return 0.0

    return float((pnl > 0).sum() / len(pnl))


def calculate_avg_win(pnl):
    """Ganancia media de las operaciones ganadoras."""
    wins = pnl[pnl > 0]

    if len(wins) == 0:
        return 0.0

    return float(wins.mean())


def calculate_avg_loss(pnl):
    """Pérdida media de las operaciones perdedoras."""
    losses = pnl[pnl < 0]

    if len(losses) == 0:
        return 0.0

    return float(losses.mean())


def calculate_profit_factor(pnl):
    """
    Profit Factor =
    suma de ganancias / valor absoluto de pérdidas.
    """
    gains = pnl[pnl > 0].sum()
    losses = abs(pnl[pnl < 0].sum())

    if losses == 0:
        return np.inf if gains > 0 else 0.0

    return float(gains / losses)


def calculate_total_return(pnl):
    """
    Retorno compuesto:
    (1 + pnl_1) * (1 + pnl_2) * ... - 1
    """
    if len(pnl) == 0:
        return 0.0

    return float((1 + pnl).prod() - 1)


def calculate_equity_curve(pnl):
    """Calcula la curva de capital compuesta."""
    return (1 + pnl).cumprod()


def calculate_max_drawdown(pnl):
    """Calcula el máximo drawdown de la curva de capital."""
    if len(pnl) == 0:
        return 0.0

    equity = calculate_equity_curve(pnl)
    running_max = equity.cummax()
    drawdown = equity / running_max - 1

    return float(drawdown.min())


def calculate_max_consecutive_losses(pnl):
    """Máximo número de pérdidas consecutivas."""
    max_losses = 0
    current_losses = 0

    for value in pnl:
        if value < 0:
            current_losses += 1
            max_losses = max(max_losses, current_losses)
        else:
            current_losses = 0

    return int(max_losses)


def calculate_max_consecutive_wins(pnl):
    """Máximo número de ganancias consecutivas."""
    max_wins = 0
    current_wins = 0

    for value in pnl:
        if value > 0:
            current_wins += 1
            max_wins = max(max_wins, current_wins)
        else:
            current_wins = 0

    return int(max_wins)


def calculate_sharpe_ratio(
    pnl,
    risk_free_rate=RISK_FREE_RATE_PER_TRADE
):
    """
    Sharpe calculado sobre retornos por operación.

    Importante:
    Como pnl contiene retornos por operación, la anualización
    usa aproximadamente 252 / AVG_TRADE_DAYS operaciones por año.
    """
    if len(pnl) < 2:
        return 0.0

    excess_returns = pnl - risk_free_rate
    std = excess_returns.std(ddof=1)

    if std == 0 or pd.isna(std):
        return 0.0

    periods_per_year = TRADING_DAYS_YEAR / AVG_TRADE_DAYS

    sharpe = (
        excess_returns.mean()
        / std
        * np.sqrt(periods_per_year)
    )

    return float(sharpe)


def calculate_sortino_ratio(
    pnl,
    risk_free_rate=RISK_FREE_RATE_PER_TRADE
):
    """
    Sortino calculado sobre retornos por operación.
    Solo considera desviaciones negativas.
    """
    if len(pnl) < 2:
        return 0.0

    excess_returns = pnl - risk_free_rate

    # Downside deviation semideviation:
    # se consideran también los retornos positivos como 0
    downside = np.minimum(excess_returns, 0)
    downside_deviation = np.sqrt(np.mean(downside ** 2))

    if downside_deviation == 0:
        return np.inf if excess_returns.mean() > 0 else 0.0

    periods_per_year = TRADING_DAYS_YEAR / AVG_TRADE_DAYS

    sortino = (
        excess_returns.mean()
        / downside_deviation
        * np.sqrt(periods_per_year)
    )

    return float(sortino)


def calculate_recovery_factor(pnl):
    """
    Recovery Factor =
    retorno neto acumulado / máximo drawdown absoluto.
    """
    total_return = calculate_total_return(pnl)
    max_drawdown = abs(calculate_max_drawdown(pnl))

    if max_drawdown == 0:
        return np.inf if total_return > 0 else 0.0

    return float(total_return / max_drawdown)


def calculate_max_trade_gain(pnl):
    """Mayor ganancia individual."""
    return float(pnl.max()) if len(pnl) else 0.0


def calculate_max_trade_loss(pnl):
    """Mayor pérdida individual."""
    return float(pnl.min()) if len(pnl) else 0.0


def calculate_expectancy(pnl):
    """Retorno medio esperado por operación."""
    return float(pnl.mean()) if len(pnl) else 0.0


def calculate_calmar_ratio(pnl):
    """
    Calmar aproximado:
    retorno anualizado / máximo drawdown absoluto.
    """
    if len(pnl) == 0:
        return 0.0

    total_return = calculate_total_return(pnl)
    years = (len(pnl) * AVG_TRADE_DAYS) / TRADING_DAYS_YEAR

    if years <= 0:
        return 0.0

    annualized_return = (1 + total_return) ** (1 / years) - 1
    max_drawdown = abs(calculate_max_drawdown(pnl))

    if max_drawdown == 0:
        return np.inf if annualized_return > 0 else 0.0

    return float(annualized_return / max_drawdown)


# ==========================================
# LEER TOP 20
# ==========================================
print("\nLeyendo archivo del Top 20...")

xl_top20 = pd.ExcelFile(
    archivo_top20,
    engine="openpyxl"
)

df_top20 = pd.read_excel(
    xl_top20,
    sheet_name="TOP_20"
)

# Normalizar nombres de columnas
df_top20.columns = (
    df_top20.columns
    .astype(str)
    .str.strip()
    .str.lower()
)

if "ticker" not in df_top20.columns:
    raise ValueError(
        "No se encontró la columna 'ticker' en la hoja TOP_20."
    )

top_20_tickers = (
    df_top20["ticker"]
    .dropna()
    .astype(str)
    .str.strip()
    .tolist()
)

print(f"Tickers encontrados: {len(top_20_tickers)}")
print(top_20_tickers)


# ==========================================
# LEER ARCHIVO BACKTEST
# ==========================================
print("\nLeyendo archivo de backtest...")

xl_backtest = pd.ExcelFile(
    archivo_backtest,
    engine="openpyxl"
)

hojas_backtest = xl_backtest.sheet_names

resultados_metricas = []
dataframes_por_ticker = {}


# ==========================================
# CALCULAR MÉTRICAS
# ==========================================
for ticker in top_20_tickers:
    print(f"\nProcesando {ticker}...", end=" ")

    if ticker not in hojas_backtest:
        print("⚠ No existe la hoja.")
        continue

    df_ticker = pd.read_excel(
        xl_backtest,
        sheet_name=ticker
    )

    try:
        pnl = clean_pnl_series(df_ticker)
    except ValueError as error:
        print(f"⚠ {error}")
        continue

    if len(pnl) == 0:
        print("⚠ No hay operaciones cerradas.")
        continue

    # Añadir al DataFrame solo las filas de operaciones cerradas
    df_ticker = df_ticker.copy()
    sell_signal = pd.to_numeric(
        df_ticker["sell_signal"],
        errors="coerce"
    )

    df_trades = df_ticker[sell_signal == 1].copy()
    df_trades["return_pct"] = (
        1 + pd.to_numeric(
            df_trades["pnl_pct"],
            errors="coerce"
        )
    )

    # Curva de capital por operación
    df_trades["equity_curve"] = (
        df_trades["return_pct"].cumprod()
    )

    dataframes_por_ticker[ticker] = df_trades

    metrics = {
        "ticker": ticker,
        "num_trades": len(pnl),
        "winning_trades": int((pnl > 0).sum()),
        "losing_trades": int((pnl < 0).sum()),
        "zero_pnl_trades": int((pnl == 0).sum()),
        "win_rate": calculate_win_rate(pnl),
        "avg_pnl": calculate_expectancy(pnl),
        "avg_win": calculate_avg_win(pnl),
        "avg_loss": calculate_avg_loss(pnl),
        "profit_factor": calculate_profit_factor(pnl),
        "total_return": calculate_total_return(pnl),
        "max_drawdown": calculate_max_drawdown(pnl),
        "sharpe_ratio": calculate_sharpe_ratio(pnl),
        "sortino_ratio": calculate_sortino_ratio(pnl),
        "calmar_ratio": calculate_calmar_ratio(pnl),
        "recovery_factor": calculate_recovery_factor(pnl),
        "max_consecutive_losses": calculate_max_consecutive_losses(pnl),
        "max_consecutive_wins": calculate_max_consecutive_wins(pnl),
        "max_trade_gain": calculate_max_trade_gain(pnl),
        "max_trade_loss": calculate_max_trade_loss(pnl),
        "avg_trade_days": AVG_TRADE_DAYS,
    }

    resultados_metricas.append(metrics)

    print(
        f"✓ Trades: {len(pnl)} | "
        f"Win rate: {metrics['win_rate']:.2%} | "
        f"PF: {metrics['profit_factor']:.2f}"
    )


# ==========================================
# DATAFRAME DE MÉTRICAS
# ==========================================
df_metricas = pd.DataFrame(resultados_metricas)

if df_metricas.empty:
    raise ValueError(
        "No se pudieron calcular métricas para ningún ticker."
    )

df_metricas = df_metricas.sort_values(
    by="sharpe_ratio",
    ascending=False
).reset_index(drop=True)


# ==========================================
# GUARDAR RESULTADOS
# ==========================================
print("\nGuardando archivo Excel...")

with pd.ExcelWriter(
    archivo_salida,
    engine="openpyxl"
) as writer:

    # Resumen general
    df_metricas.to_excel(
        writer,
        sheet_name="RESUMEN_METRICAS",
        index=False
    )

    # Top 10 por Sharpe
    df_metricas.head(10).to_excel(
        writer,
        sheet_name="TOP_10_SHARPE",
        index=False
    )

    # Una hoja por ticker, únicamente con operaciones cerradas
    for ticker, df_trades in dataframes_por_ticker.items():
        df_trades.to_excel(
            writer,
            sheet_name=ticker[:31],
            index=False
        )

print(f"\n✓ Archivo generado: {archivo_salida}")


# ==========================================
# MOSTRAR RESULTADOS
# ==========================================
columnas_mostrar = [
    "ticker",
    "num_trades",
    "winning_trades",
    "losing_trades",
    "win_rate",
    "total_return",
    "max_drawdown",
    "sharpe_ratio",
    "sortino_ratio",
    "profit_factor",
    "max_consecutive_losses",
]

print("\n" + "=" * 100)
print("MÉTRICAS CORREGIDAS: SOLO OPERACIONES CERRADAS")
print("=" * 100)

print(
    df_metricas[columnas_mostrar]
    .to_string(index=False)
)