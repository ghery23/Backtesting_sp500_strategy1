# -*- coding: utf-8 -*-
"""
Created on Thu Sep 24 22:15:16 2026

This code reads a csv file  that contains  tickers from sp500 , and gets ohlcv data from 
them using  yfinance..., once the data is obtained,  indicators are calculated and those indicators 
create the buy_signal... which in turn, allows to vreate the true buy signal.

the true buy signal will be used  to get in the trade.. at the close price, that is the buy_price.

the exist signal is a little bit more complex:
1.- Put the stop loss at the absolute lowest price in the last 6 days taking into account the
 day the trade was opened , "buy_signal - 5 pior dates" 
2.- Wait 5 days from the "buy signal date", if the closing price is less than the buy_price,  cut the loss
otherwise wait 5 more days., in order  "to catch"  the uptrend.

a sell signal at the day of the sell is made using the logic above.

@author: Ghery Jorge Cardenas
"""

import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import time

# ==============================
# CONFIGURACIÓN
# ==============================
archivo_csv = "sp500_tickers.csv"
archivo_excel = "backtest_resultados.xlsx"
end_date = datetime.today().strftime("%Y-%m-%d")
start_date = (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=5*365)).strftime("%Y-%m-%d")

# Parámetros de la estrategia
STOP_LOOKBACK = 6      # Mínimo de los últimos 6 días (actual + 5 previos)
HOLD_PERIOD_1 = 5      # Primer check a los 5 días
HOLD_PERIOD_2 = 10     # Venta forzada a los 10 días

# ==============================
# FUNCIONES DE INDICADORES Y SEÑALES
# ==============================
def calculate_indicators(df):
    """Calcula TODOS los indicadores de la estrategia"""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # RSI 14
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD (12,26,9)
    ema12 = df['Close'].ewm(span=12).mean()
    ema26 = df['Close'].ewm(span=26).mean()
    df['MACD'] = ema12 - ema26
    df['MACD_signal'] = df['MACD'].ewm(span=9).mean()
    df['MACD_hist'] = df['MACD'] - df['MACD_signal']
    
    # EMAs
    df['EMA20'] = df['Close'].ewm(span=20).mean()
    df['EMA50'] = df['Close'].ewm(span=50).mean()
    
    # Volumen
    vol = df['Volume'].squeeze() if hasattr(df['Volume'], 'squeeze') else df['Volume']
    df['Vol_avg10'] = vol.rolling(10).mean()
    df['Vol_ratio'] = vol / df['Vol_avg10']
    
    return df


def add_entry_signals(df):
    """Añade señales de entrada"""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # Inicializar columnas
    df['RSI_ok'] = 0
    df['MACD_ok'] = 0
    df['EMA20_ok'] = 0
    df['EMA50_ok'] = 0
    df['Vol_ok'] = 0
    df['buy_signal'] = 0
    df['true_buy_signal'] = 0
    
    # Filtros individuales
    df['RSI_ok'] = ((df['RSI'] >= 50) & (df['RSI'] <= 70)).astype(int)
    df['MACD_ok'] = ((df['MACD'] > df['MACD_signal']) & (df['MACD_hist'] > 0)).astype(int)
    df['EMA20_ok'] = (df['Close'] > df['EMA20']).astype(int)
    df['EMA50_ok'] = (df['EMA20'] > df['EMA50']).astype(int)
    df['Vol_ok'] = (df['Vol_ratio'] > 1.2).astype(int)
    
    # Signal base
    df['buy_signal'] = ((df['RSI_ok'] + df['MACD_ok'] + df['EMA20_ok'] + 
                         df['EMA50_ok'] + df['Vol_ok']) >= 4).astype(int)
    
    # True buy signal (1 línea con shift)
    df['true_buy_signal'] = ((df['buy_signal'] == 1) & 
                             (df['buy_signal'].shift(1) == 0) & 
                             (df['buy_signal'].shift(2) == 0)).astype(int)
    
    return df


def run_backtest(df):
    """
    Ejecuta el backtest con la estrategia completa.
    
    Reglas:
    1. Entrada: true_buy_signal = 1, compra al Close
    2. Stop_loss: mínimo de los últimos 6 días (se recalcula cada día)
    3. Salida por stop loss: en CUALQUIER día (1-10), si Low <= stop_loss → vender
    4. Salida día 5: si Close < entry_price → vender (pérdida pequeña)
    5. Salida día 10: si el precio sobrevivió hasta aquí → vender al Close (momentum)
    """
    df = df.copy()
    
    if len(df) < 20:
        df['hold'] = 0.0
        df['sell_signal'] = 0.0
        df['stop_loss'] = 0.0
        df['entry_price'] = 0.0
        df['exit_price'] = 0.0
        df['pnl_pct'] = 0.0
        return df
    
    # Inicializar columnas EXPLÍCITAMENTE como float64
    df['hold'] = 0.0
    df['sell_signal'] = 0.0
    df['stop_loss'] = 0.0
    df['entry_price'] = 0.0
    df['exit_price'] = 0.0
    df['pnl_pct'] = 0.0
    
    in_position = False
    entry_idx = None
    entry_price = 0
    
    close = df['Close'].values
    low = df['Low'].values
    true_buy = df['true_buy_signal'].values
    
    for i in range(len(df)):
        # ==========================
        # CALCULAR STOP LOSS (mínimo últimos 6 días)
        # ==========================
        start_lookback = max(0, i - STOP_LOOKBACK + 1)
        stop_loss = min(low[start_lookback:i+1])
        df.at[df.index[i], 'stop_loss'] = float(stop_loss)
        
        # ==========================
        # ABRIR POSICIÓN
        # ==========================
        if not in_position and true_buy[i] == 1:
            in_position = True
            entry_idx = i
            entry_price = float(close[i])
            df.at[df.index[i], 'hold'] = 1.0
            df.at[df.index[i], 'entry_price'] = entry_price
        
        # ==========================
        # SI ESTÁ EN POSICIÓN
        # ==========================
        elif in_position:
            dias_en_trade = i - entry_idx
            
            # Marcar como hold
            df.at[df.index[i], 'hold'] = 1.0
            df.at[df.index[i], 'entry_price'] = entry_price
            
            # --- CRITERIO 1: STOP LOSS (cualquier día 1-10) ---
            if dias_en_trade >= 1 and low[i] <= stop_loss:
                df.at[df.index[i], 'sell_signal'] = 1.0
                df.at[df.index[i], 'exit_price'] = float(stop_loss)
                df.at[df.index[i], 'pnl_pct'] = float((stop_loss - entry_price) / entry_price)
                in_position = False
                continue
            
            # --- CRITERIO 2: Día 5 - Close < Compra → vender ---
            if dias_en_trade == HOLD_PERIOD_1:
                if close[i] < entry_price:
                    df.at[df.index[i], 'sell_signal'] = 1.0
                    df.at[df.index[i], 'exit_price'] = float(close[i])
                    df.at[df.index[i], 'pnl_pct'] = float((close[i] - entry_price) / entry_price)
                    in_position = False
                    continue
            
            # --- CRITERIO 3: Día 10 - Venta forzada ---
            if dias_en_trade == HOLD_PERIOD_2:
                df.at[df.index[i], 'sell_signal'] = 1.0
                df.at[df.index[i], 'exit_price'] = float(close[i])
                df.at[df.index[i], 'pnl_pct'] = float((close[i] - entry_price) / entry_price)
                in_position = False
                continue
    
    return df


def filter_hold_days(df):
    """
    Filtra el DataFrame: solo deja filas donde hold = 1.
    Elimina días sin posición abierta.
    """
    return df[df['hold'] == 1.0].copy()


# ==============================
# LEER TICKERS
# ==============================
print("Leyendo tickers...")
tickers_df = pd.read_csv(archivo_csv)

if tickers_df.shape[1] == 1:
    tickers_list = tickers_df.iloc[:, 0].dropna().astype(str).str.strip().tolist()
elif 'Ticker' in tickers_df.columns:
    tickers_list = tickers_df['Ticker'].dropna().astype(str).str.strip().tolist()
elif 'Symbol' in tickers_df.columns:
    tickers_list = tickers_df['Symbol'].dropna().astype(str).str.strip().tolist()
else:
    tickers_list = tickers_df.iloc[:, 0].dropna().astype(str).str.strip().tolist()

print(f"✓ Total tickers: {len(tickers_list)}")

# ==============================
# DESCARGAR + PROCESAR + BACKTEST
# ==============================
ohlcv_data = {}
resultados_stats = []

print(f"\nIniciando descarga + backtest ({start_date} a {end_date})...")
print("-" * 70)

for i, ticker in enumerate(tickers_list, 1):
    try:
        print(f"[{i}/{len(tickers_list)}] {ticker}...", end=" ")
        
        # Descargar
        data = yf.download(ticker, start=start_date, end=end_date, interval="1d", progress=False)
        
        if data.empty or len(data) < 60:
            print(f"⚠ Sin datos suficientes")
            continue
        
        # Formato estándar
        if isinstance(data.columns, pd.MultiIndex):
            data = data.droplevel(1, axis=1)
        
        # Añadir indicadores
        data = calculate_indicators(data)
        data = add_entry_signals(data)
        
        # Ejecutar backtest
        data = run_backtest(data)
        
        # Filtrar solo días con posición
        data_filtrado = filter_hold_days(data)
        
        if len(data_filtrado) > 0:
            ohlcv_data[ticker] = data_filtrado
            
            # Estadísticas del ticker
            trades = data_filtrado[data_filtrado['sell_signal'] == 1.0]
            total_trades = len(trades)
            win_rate = (trades['pnl_pct'] > 0).sum() / total_trades if total_trades > 0 else 0
            avg_pnl = trades['pnl_pct'].mean() if total_trades > 0 else 0
            
            resultados_stats.append({
                'ticker': ticker,
                'total_trades': total_trades,
                'win_rate': round(win_rate, 4),
                'avg_pnl_pct': round(avg_pnl, 4),
                'dias_hold': len(data_filtrado),
            })
            
            print(f"✓ {total_trades} trades, win_rate={win_rate:.2%}")
        else:
            print(f"⚠ Sin trades")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        continue
    
    time.sleep(0.3)

# ==============================
# GUARDAR EN EXCEL (MÚLTIPLES HOJAS)
# ==============================
print("-" * 70)
print(f"\nGuardando resultados en Excel...")

# Crear Excel writer
with pd.ExcelWriter(archivo_excel, engine='openpyxl') as writer:
    # Hoja 1: Resumen de estadísticas
    df_stats = pd.DataFrame(resultados_stats)
    df_stats['total_trades'] = df_stats['total_trades'].astype(int)
    df_stats['dias_hold'] = df_stats['dias_hold'].astype(int)
    df_stats.to_excel(writer, sheet_name='RESUMEN', index=False)
    
    # Hojas individuales por ticker
    for ticker, df in ohlcv_data.items():
        # Limitar nombre de hoja a 31 caracteres (límite de Excel)
        sheet_name = ticker[:31]
        df.to_excel(writer, sheet_name=sheet_name)

print(f"✓ Excel guardado: {archivo_excel}")
print(f"  - 1 hoja 'RESUMEN' con estadísticas")
print(f"  - {len(ohlcv_data)} hojas individuales (una por ticker)")

# ==============================
# EJEMPLO DE RESULTADOS
# ==============================
if ohlcv_data:
    primer_ticker = list(ohlcv_data.keys())[0]
    print(f"\n📊 Ejemplo: {primer_ticker}")
    print(ohlcv_data[primer_ticker].head(15))