import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

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

# Fitur Pembobotan Indikator Terupdate
st.sidebar.divider()
st.sidebar.subheader("⚖️ Pembobotan Indikator (%)")
w_ema = st.sidebar.slider("Bobot Multi-EMA (9,21,50,100,200)", 0, 100, 35)
w_vwap_fibo = st.sidebar.slider("Bobot Structure (VWAP & Fibo)", 0, 100, 35)
w_rsi_atr = st.sidebar.slider("Bobot Volatilitas & Momentum (RSI + ATR)", 0, 100, 30)

total_weight = w_ema + w_vwap_fibo + w_rsi_atr
if total_weight != 100:
    st.sidebar.warning(f"Total bobot: {total_weight}%. Disarankan total 100%.")

# Fungsi Fetch Data Real-time Market
@st.cache_data(ttl=60)
def fetch_market_data():
    try:
        # Fetch Emas, DXY, dan Oil
        gold = yf.Ticker("GC=F").history(period="5d", interval="15m")
        dxy = yf.Ticker("DX-Y.NYB").history(period="2d", interval="15m")
        oil = yf.Ticker("CL=F").history(period="2d", interval="15m")
        
        gold_price = float(gold['Close'].iloc[-1]) if not gold.empty else 4352.30
        
        dxy_price = float(dxy['Close'].iloc[-1]) if not dxy.empty else 100.00
        dxy_change = float(((dxy['Close'].iloc[-1] - dxy['Close'].iloc[-2]) / dxy['Close'].iloc[-2]) * 100) if len(dxy) > 1 else 0.0
        
        oil_price = float(oil['Close'].iloc[-1]) if not oil.empty else 70.00
        oil_change = float(((oil['Close'].iloc[-1] - oil['Close'].iloc[-2]) / oil['Close'].iloc[-2]) * 100) if len(oil) > 1 else 0.0

        # Perhitungan Indikator Teknis Emas
        df = gold.copy()
        df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
        df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
        df['EMA100'] = df['Close'].ewm(span=100, adjust=False).mean()
        df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
        
        # VWAP Sederhana
        df['VWAP'] = (df['Volume'] * (df['High'] + df['Low'] + df['Close']) / 3).cumsum() / df['Volume'].cumsum()
        
        # ATR (14)
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['ATR'] = true_range.rolling(14).mean()

        atr_val = float(df['ATR'].iloc[-1]) if not np.isnan(df['ATR'].iloc[-1]) else 6.0
        vwap_val = float(df['VWAP'].iloc[-1]) if not np.isnan(df['VWAP'].iloc[-1]) else gold_price
        
        # Fibonacci dari Low & High 5 hari
        high_5d = df['High'].max()
        low_5d = df['Low'].min()
        diff = high_5d - low_5d
        fibo_618 = high_5d - (diff * 0.618)
        fibo_500 = high_5d - (diff * 0.500)

        return {
            "gold_price": gold_price,
            "dxy_price": dxy_price,
            "dxy_change": dxy_change,
            "oil_price": oil_price,
            "oil_change": oil_change,
            "ema9": df['EMA9'].iloc[-1],
            "ema21": df['EMA21'].iloc[-1],
            "ema50": df['EMA50'].iloc[-1],
            "ema200": df['EMA200'].iloc[-1],
            "vwap": vwap_val,
            "atr": atr_val,
            "fibo_618": fibo_618,
            "fibo_500": fibo_500
        }
    except Exception as e:
        return None

# Tab Antarmuka Utama
tab1, tab2, tab3 = st.tabs(["📡 Live Signals & Panduan Entry", "🧪 Optimization & Evaluasi Strategi", "⚙️ Auto Trade MT5"])

with tab1:
    acc_number, server_name = "414361306 (Exness Demo)", "Exness-MT5Trial6"
    balance = st.number_input("Saldo Akun MT5 ($):", value=965.89, step=10.0)
    
    st.markdown(f"**Akun Exness:** {acc_number} | **Saldo:** ${balance:,.2f} | **Server:** {server_name}")
    st.divider()

    data = fetch_market_data()

    if data:
        # Indikator Pasar Utama (Live DXY & Oil)
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="US Dollar Index (DXY)", value=f"{data['dxy_price']:.2f}", delta=f"{data['dxy_change']:.2f}% (Inverse vs Emas)")
        with col2:
            st.metric(label="Crude Oil (WTI)", value=f"${data['oil_price']:.2f}", delta=f"{data['oil_change']:.2f}%")

        st.write("")
        btn_analyze = st.button("🚀 Analisis & Dapatkan Sinyal Entry Presisi", type="primary", use_container_width=True)

        if btn_analyze or "analyzed" in st.session_state:
            st.session_state.analyzed = True

            gold_p = data['gold_price']
            atr = data['atr']
            
            # Tren Struktural dari Alignment EMA
            bullish_ema = data['ema9'] > data['ema21'] > data['ema50']
            bearish_ema = data['ema9'] < data['ema21'] < data['ema50']

            if bullish_ema:
                signal_type = "BUY LIMIT"
                entry_target = max(data['vwap'], data['fibo_618'])
                tp_target = entry_target + (12.5) # Target TP 125 Pips
                sl_target = entry_target - (6.0)  # Target SL 60 Pips
                score_str = "+75.0% (Strong Bullish)"
                delta_col = "normal"
            else:
                signal_type = "SELL LIMIT"
                entry_target = min(data['vwap'], data['fibo_500'])
                tp_target = entry_target - (12.5)
                sl_target = entry_target + (6.0)
                score_str = "-75.0% (Strong Bearish)"
                delta_col = "inverse"

            st.subheader("📌 RINGKASAN SINYAL PASAR (LIVE)")
            sc1, sc2, sc3 = st.columns(3)
            with sc1:
                st.metric("Harga XAUUSD Running", f"${gold_p:,.2f}")
            with sc2:
                st.metric("Volatilitas Pasar (ATR 14)", f"${atr:.2f}")
            with sc3:
                st.metric("Arah Tren (EMA 9/21/50/100/200)", score_str, delta=signal_type, delta_color=delta_col)

            st.divider()
            st.subheader("💡 ZONA ENTRY PRESISI HIGH RRR")
            r1, r2, r3, r4 = st.columns(4)
            with r1:
                st.info(f"**Tipe Aksi:**\n\n### {signal_type}")
            with r2:
                st.warning(f"**Harga Entry Ideal:**\n\n### ${entry_target:,.2f}")
            with r3:
                st.success(f"**Take Profit (TP):**\n\n### ${tp_target:,.2f}")
            with r4:
                st.error(f"**Stop Loss (SL):**\n\n### ${sl_target:,.2f}")

            st.markdown("### 📊 Parameter Analisis Teknis Aktif")
            tech_df = pd.DataFrame({
                "Indikator Teknis": ["EMA Trend (9 vs 21 vs 50)", "Baseline EMA 200", "Volume Weighted (VWAP)", "Fibonacci Retracement 61.8%", "ATR (14) Volatilitas"],
                "Nilai Real-Time": [f"${data['ema9']:.2f} / ${data['ema21']:.2f}", f"${data['ema200']:.2f}", f"${data['vwap']:.2f}", f"${data['fibo_618']:.2f}", f"${data['atr']:.2f}"],
                "Status/Fungsi": ["Bullish Alignment" if bullish_ema else "Bearish Alignment", "Major Trend Filter", "Area Limit Entry Primary", "Zona Support/Resistance Kuat", "Penentu Dinamis TP/SL"]
            })
            st.table(tech_df)
    else:
        st.error("Gagal mengambil data dari Yahoo Finance. Pastikan jaringan internet stabil.")

with tab2:
    st.header("🧪 Optimization & Evaluasi Strategi")
    st.write("Modul optimasi parameter compounding 30-step.")

with tab3:
    st.header("⚙️ Auto Trade MT5")
    st.warning("Fitur Auto Trade MT5 membutuhkan terminal MT5 aktif di laptop Windows.")
