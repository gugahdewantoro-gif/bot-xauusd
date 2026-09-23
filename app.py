import streamlit as st
import pandas as pd
import numpy as np

# Set Konfigurasi Halaman
st.set_page_config(
    page_title="Pro Bot Trading XAUUSD",
    page_icon="📈",
    layout="wide"
)

# Cek Ketersediaan MetaTrader 5 (Karna MT5 hanya bisa di Windows)
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

# Sidebar Kontrol & Parameter
st.sidebar.title("⚙️ Kontrol & Strategi")

if MT5_AVAILABLE:
    st.sidebar.success("✅ MT5 Terhubung (Mode Live Terminal)")
else:
    st.sidebar.info("🌐 Mode Cloud Web (MT5 Tidak Terdeteksi di Server)")

symbol = st.sidebar.text_input("Simbol Aktif", value="XAUUSD")
timeframe = st.sidebar.selectbox("Timeframe / Mode", ["M5", "M15", "H1", "SWING (D1)"], index=3)
execution_mode = st.sidebar.radio(
    "Mode Tipe Eksekusi Order:",
    ["PENDING ORDER (LIMIT) - Presisi High RRR", "INSTANT ORDER (MARKET) - Eksekusi Langsung"]
)

max_spread = st.sidebar.number_input("Max Spread (Pips):", value=0.40, step=0.05)
base_lot = st.sidebar.number_input("Ukuran Lot Auto Trade:", value=0.01, step=0.01)

# Tab Antarmuka Utama
tab1, tab2, tab3 = st.tabs(["📡 Live Signals & Panduan Entry", "🧪 Optimization & Evaluasi Strategi", "⚙️ Auto Trade MT5"])

with tab1:
    # Header Saldo & Akun
    if MT5_AVAILABLE and mt5.initialize():
        account_info = mt5.account_info()
        if account_info is not None:
            acc_number = account_info.login
            balance = account_info.balance
            server_name = account_info.server
        else:
            acc_number, balance, server_name = "Demo Cloud", 1007.90, "Exness-MT5Trial6"
        mt5.shutdown()
    else:
        acc_number, balance, server_name = "414361306 (Simulasi)", 1007.90, "Exness-MT5Trial6"

    st.markdown(f"**Akun Exness:** {acc_number} | **Saldo:** ${balance:,.2f} | **Server:** {server_name}")
    st.divider()

    # Indikator Pasar Utama
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="US Dollar Index (DXY)", value="100.00", delta="0.00% (Inverse vs Emas)")
    with col2:
        st.metric(label="Crude Oil (WTI)", value="$70.00", delta="0.00%")

    st.button("🚀 Analisis & Dapatkan Sinyal Entry", type="primary", use_container_width=True)

    st.subheader("📌 RINGKASAN SINYAL PASAR")
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        st.metric("Harga XAUUSD Saat Ini", "$4316.63")
    with sc2:
        st.metric("Spread Saat Ini", "0.18 Pips", delta="Aman", delta_color="normal")
    with sc3:
        st.metric("Arah Tren & Kekuatan", "-50.0%", delta="SELL (Jual)", delta_color="inverse")

with tab2:
    st.header("🧪 Optimization & Evaluasi Strategi")
    st.write("Fitur backtest dan optimasi parameter strategi lot compounding 30-step.")

with tab3:
    st.header("⚙️ Auto Trade MT5")
    if MT5_AVAILABLE:
        st.success("Sistem siap mengumpankan sinyal langsung ke MetaTrader 5 di laptop.")
    else:
        st.warning("Fitur eksekusi langsung ke MT5 nonaktif di server cloud. Jalankan aplikasi di laptop kamu jika ingin melakukan eksekusi order otomatis secara langsung.")
