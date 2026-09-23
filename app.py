import streamlit as st
import pandas as pd
import numpy as np

# Konfigurasi Halaman
st.set_page_config(
    page_title="Pro Bot Trading XAUUSD",
    page_icon="📈",
    layout="wide"
)

# Cek MetaTrader 5
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
timeframe = st.sidebar.selectbox("Timeframe / Mode", ["M5", "M15", "H1", "SWING (D1)"], index=1)
execution_mode = st.sidebar.radio(
    "Mode Tipe Eksekusi Order:",
    ["PENDING ORDER (LIMIT) - Presisi High RRR", "INSTANT ORDER (MARKET) - Eksekusi Langsung"]
)

max_spread = st.sidebar.number_input("Max Spread (Pips):", value=0.40, step=0.05)
base_lot = st.sidebar.number_input("Ukuran Lot Auto Trade:", value=0.01, step=0.01)

# Fitur Pembobotan Indikator
st.sidebar.divider()
st.sidebar.subheader("⚖️ Pembobotan Indikator (%)")
w_ema = st.sidebar.slider("Bobot Trend (EMA/MA)", 0, 100, 40)
w_rsi = st.sidebar.slider("Bobot Momentum (RSI)", 0, 100, 30)
w_macd = st.sidebar.slider("Bobot Oscillator (MACD)", 0, 100, 30)

total_weight = w_ema + w_rsi + w_macd
if total_weight != 100:
    st.sidebar.warning(f"Total bobot: {total_weight}%. Disarankan total 100%.")

# Tab Antarmuka Utama
tab1, tab2, tab3 = st.tabs(["📡 Live Signals & Panduan Entry", "🧪 Optimization & Evaluasi Strategi", "⚙️ Auto Trade MT5"])

with tab1:
    # Header Saldo & Akun
    acc_number, balance, server_name = "414361306 (Simulasi)", 1007.90, "Exness-MT5Trial6"
    st.markdown(f"**Akun Exness:** {acc_number} | **Saldo:** ${balance:,.2f} | **Server:** {server_name}")
    st.divider()

    # Indikator Pasar Utama
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="US Dollar Index (DXY)", value="100.00", delta="0.00% (Inverse vs Emas)")
    with col2:
        st.metric(label="Crude Oil (WTI)", value="$70.00", delta="0.00%")

    st.write("")
    btn_analyze = st.button("🚀 Analisis & Dapatkan Sinyal Entry", type="primary", use_container_width=True)

    # State Analisis
    if "analyzed" not in st.session_state:
        st.session_state.analyzed = False

    if btn_analyze:
        st.session_state.analyzed = True

    # Nilai Simulasi/Kalkulasi Hasil
    if st.session_state.analyzed:
        price_val = 2650.45
        spread_val = 0.18
        
        # Contoh kalkulasi skor berdasarkan pembobotan
        score_ema = 0.8 * (w_ema / 100)
        score_rsi = -0.5 * (w_rsi / 100)
        score_macd = 0.6 * (w_macd / 100)
        total_score = (score_ema + score_rsi + score_macd) * 100

        st.subheader("📌 RINGKASAN SINYAL PASAR")
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            st.metric("Harga XAUUSD Saat Ini", f"${price_val:,.2f}")
        with sc2:
            st.metric("Spread Saat Ini", f"{spread_val} Pips", delta="Aman", delta_color="normal")
        with sc3:
            signal_text = "BUY (Beli)" if total_score > 0 else "SELL (Jual)"
            delta_col = "normal" if total_score > 0 else "inverse"
            st.metric("Arah Tren & Skor Kekuatan", f"{total_score:.1f}%", delta=signal_text, delta_color=delta_col)

        st.divider()
        st.subheader("💡 REKOMENDASI POSISI OPTIMAL")
        r1, r2, r3 = st.columns(3)
        with r1:
            st.info(f"**Aksi:** {signal_text}")
        with r2:
            st.success(f"**Take Profit (TP):** ${price_val + 12.50:.2f}")
        with r3:
            st.error(f"**Stop Loss (SL):** ${price_val - 6.00:.2f}")

        st.markdown("### 📊 Detail Kontribusi Pembobotan Indikator")
        detail_df = pd.DataFrame({
            "Indikator": ["Trend (EMA)", "Momentum (RSI)", "Oscillator (MACD)"],
            "Bobot Diterapkan (%)": [w_ema, w_rsi, w_macd],
            "Kontribusi Skor": [f"{score_ema*100:.1f}%", f"{score_rsi*100:.1f}%", f"{score_macd*100:.1f}%"]
        })
        st.table(detail_df)
    else:
        st.info("Klik tombol **🚀 Analisis & Dapatkan Sinyal Entry** di atas untuk menjalankan perhitungan sinyal.")

with tab2:
    st.header("🧪 Optimization & Evaluasi Strategi")
    st.write("Modul optimasi parameter compounding 30-step.")

with tab3:
    st.header("⚙️ Auto Trade MT5")
    st.warning("Fitur Auto Trade MT5 membutuhkan terminal MT5 aktif di laptop Windows.")
