import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(
    page_title="Pro Bot Trading XAUUSD - Live Exness Sync",
    page_icon="📈",
    layout="wide"
)

# Cek & Inisialisasi MetaTrader 5
try:
    import MetaTrader5 as mt5
    if mt5.initialize():
        MT5_CONNECTED = True
    else:
        MT5_CONNECTED = False
except ImportError:
    MT5_CONNECTED = False

st.sidebar.title("⚙️ Kontrol & Strategi")

if MT5_CONNECTED:
    st.sidebar.success("✅ Terhubung Langsung ke MT5 Exness (Real-Time)")
else:
    st.sidebar.warning("🌐 Mode Cloud Web (Sumber Data: Yahoo Finance Futures)")

symbol = st.sidebar.text_input("Simbol Aktif", value="XAUUSD")
tf_option = st.sidebar.selectbox("Timeframe Analisis", ["M5", "M15", "H1"], index=0)

# Fungsi Mengambil Harga Real-Time Presisi
def get_live_price():
    # 1. Coba ambil dari MT5 Exness lokal jika tersedia
    if MT5_CONNECTED:
        tick = mt5.symbol_info_tick(symbol)
        if tick:
            return tick.bid, tick.ask - tick.bid, "MT5 Exness Direct"
            
    # 2. Fallback ke Yahoo Finance (Tanpa Cache Panjang)
    try:
        gold = yf.Ticker("GC=F").history(period="1d", interval="1m")
        if not gold.empty:
            live_p = float(gold['Close'].iloc[-1])
            return live_p, 0.18, "Global Futures (yfinance)"
    except:
        pass
        
    return 4315.78, 0.18, "Harga Default/Fallback"

# Tab Utama
tab1, tab2 = st.tabs(["📡 Live Signals & MT5 Sync", "🧪 Optimization & Strategy"])

with tab1:
    price, spread, source = get_live_price()
    
    st.caption(f"Sumber Data Aktif: **{source}**")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("XAUUSD Running Price", f"${price:,.2f}")
    with col2:
        st.metric("Spread", f"{spread:.2f} Pips")
    with col3:
        st.metric("Status Sistem", "ONLINE" if MT5_CONNECTED else "CLOUD WEB")

    st.divider()
    st.subheader("🎯 ZONA ENTRY PRESISI (HIGH RRR)")
    
    # Hitung SL/TP presisi dari harga saat ini
    sl_val = price - 6.00
    tp_val = price + 12.00
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.info(f"**Tipe Aksi:**\n\n### BUY LIMIT / MARKET")
    with c2:
        st.success(f"**Take Profit (TP):**\n\n### ${tp_val:,.2f}")
    with c3:
        st.error(f"**Stop Loss (SL):**\n\n### ${sl_val:,.2f}")
