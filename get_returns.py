# -*- coding: utf-8 -*-
"""
Created on Fri Sep 25 00:09:46 2026

@author: HP
"""
import pandas as pd

# ==============================
# CONFIGURACIÓN
# ==============================
archivo_excel = "backtest_resultados.xlsx"
archivo_salida = "retornos_por_ticker.xlsx"

# ==============================
# LEER TODAS LAS HOJAS DEL EXCEL
# ==============================
print("Leyendo archivo Excel...")
xl = pd.ExcelFile(archivo_excel, engine='openpyxl')
hojas = xl.sheet_names

print(f"✓ Total de hojas encontradas: {len(hojas)}")

# ==============================
# PROCESAR CADA TICKER
# ==============================
resultados = []

for hoja in hojas:
    # Saltar hoja de resumen
    if hoja == 'RESUMEN':
        continue
    
    print(f"Procesando {hoja}...", end=" ")
    
    # Leer DataFrame
    df = pd.read_excel(xl, sheet_name=hoja)
    
    # Añadir columna return_pct = pnl_pct + 1
    df['return_pct'] = df['pnl_pct'] + 1.0
    
    # Calcular retorno total (producto de todos los return_pct)
    retorno_total = df['return_pct'].prod()
    retorno_total_pct = (retorno_total - 1) * 100
    
    resultados.append({
        'ticker': hoja,
        'return_total': retorno_total,
        'return_total_pct': retorno_total_pct,
        'num_operaciones': len(df),
    })
    
    print(f"✓ Return: {retorno_total_pct:.2f}%")

# ==============================
# CREAR DATAFRAME RESUMEN
# ==============================
df_resumen = pd.DataFrame(resultados)

# Ordenar de mayor a menor retorno
df_resumen_ordenado = df_resumen.sort_values(
    by='return_total', 
    ascending=False
).reset_index(drop=True)

# ==============================
# MOSTRAR RESULTADOS
# ==============================
print("\n" + "=" * 70)
print("RETORNO TOTAL POR TICKER (ORDENADO)")
print("=" * 70)

for i, row in df_resumen_ordenado.iterrows():
    print(f"{i+1:3}. {row['ticker']:5} | Ops: {row['num_operaciones']:3} | "
          f"Return: {row['return_total']:.4f} ({row['return_total_pct']:7.2f}%)")

# ==============================
# GUARDAR EN EXCEL CON FORMATO
# ==============================
print(f"\nGuardando resultados en Excel...")

with pd.ExcelWriter(archivo_salida, engine='openpyxl') as writer:
    # Hoja 1: Resumen ordenado
    df_resumen_ordenado.to_excel(writer, sheet_name='RESUMEN', index=False)
    
    # Hoja 2: Top 20
    df_resumen_ordenado.head(20).to_excel(writer, sheet_name='TOP_20', index=False)
    
    # Hoja 3: Bottom 20
    df_resumen_ordenado.tail(20).to_excel(writer, sheet_name='BOTTOM_20', index=False)

print(f"✓ Guardado en '{archivo_salida}'")

# ==============================
# AÑADIR HOJA AL EXCEL ORIGINAL (opcional)
# ==============================
with pd.ExcelWriter(archivo_excel, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
    df_resumen_ordenado.to_excel(writer, sheet_name='RETORNOS', index=False)

print(f"✓ Añadida hoja 'RETORNOS' en el Excel original")

# ==============================
# TOP 10 Y BOTTOM 10
# ==============================
print("\n" + "=" * 70)
print("🏆 TOP 10 TICKERS POR RETORNO")
print("=" * 70)
print(df_resumen_ordenado.head(10).to_string(index=False))

print("\n" + "=" * 70)
print("📉 BOTTOM 10 TICKERS POR RETORNO")
print("=" * 70)
print(df_resumen_ordenado.tail(10).to_string(index=False))

# ==============================
# ESTADÍSTICAS GENERALES
# ==============================
print("\n" + "=" * 70)
print("📊 ESTADÍSTICAS GENERALES")
print("=" * 70)
print(f"Total tickers analizados: {len(df_resumen_ordenado)}")
print(f"Retorno promedio: {df_resumen_ordenado['return_total_pct'].mean():.2f}%")
print(f"Retorno mediano: {df_resumen_ordenado['return_total_pct'].median():.2f}%")
print(f"Mejor ticker: {df_resumen_ordenado.iloc[0]['ticker']} ({df_resumen_ordenado.iloc[0]['return_total_pct']:.2f}%)")
print(f"Peor ticker: {df_resumen_ordenado.iloc[-1]['ticker']} ({df_resumen_ordenado.iloc[-1]['return_total_pct']:.2f}%)")