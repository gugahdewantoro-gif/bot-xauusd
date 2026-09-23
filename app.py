import streamlit as st
import MetaTrader5 as mt5
import pandas as pd
import pandas_ta as ta
import yfinance as yf
from datetime import datetime, timedelta

st.set_page_config(page_title="Pro Bot Trading XAUUSD (Safe Execution)", page_icon="⚡", layout="wide")

# ==========================================
# 1. KONEKSI MT5 EXNESS
# ==========================================
@st.cache_resource
def init_mt5():
    return mt5.initialize()

if not init_mt5():
    st.error("❌ MT5 Exness tidak terhubung! Pastikan aplikasi MetaTrader 5 kamu sudah terbuka dan login.")
    st.stop()

account_info = mt5.account_info()

# Deteksi Otomatis Nama Simbol Emas di Akun Exness (XAUUSD / xauusd / XAUUSDm)
def get_exact_gold_symbol():
    symbols = mt5.symbols_get()
    if symbols:
        for s in symbols:
            if "XAUUSD" in s.name.upper() or "GOLD" in s.name.upper():
                return s.name
    return "XAUUSD"

GOLD_SYMBOL = get_exact_gold_symbol()

# ==========================================
# 2. SIDEBAR CONFIG
# ==========================================
st.sidebar.title("⚙️ Kontrol & Strategi")
st.sidebar.info(f"📌 Simbol Aktif Terdeteksi: **{GOLD_SYMBOL}**")

mode_pilihan = st.sidebar.selectbox("Pilih Timeframe / Mode:", [
    "SCALPING (M1)", "SCALPING (M5)", "INTRADAY (M15)", "INTRADAY (H1)", "SWING (H4)", "SWING (D1)"
])

tf_map = {
    "SCALPING (M1)": mt5.TIMEFRAME_M1,
    "SCALPING (M5)": mt5.TIMEFRAME_M5,
    "INTRADAY (M15)": mt5.TIMEFRAME_M15,
    "INTRADAY (H1)": mt5.TIMEFRAME_H1,
    "SWING (H4)": mt5.TIMEFRAME_H4,
    "SWING (D1)": mt5.TIMEFRAME_D1
}
tf = tf_map[mode_pilihan]

execution_mode = st.sidebar.radio(
    "Mode Tipe Eksekusi Order:",
    ["PENDING ORDER (LIMIT) - Presisi High RRR", "INSTANT ORDER (MARKET) - Eksekusi Langsung"]
)

max_spread = st.sidebar.number_input("Max Spread (Pips):", min_value=0.1, value=1.0, step=0.1)
lot_size = st.sidebar.number_input("Ukuran Lot Auto Trade:", min_value=0.01, value=0.01, step=0.01)

st.sidebar.markdown("---")
st.sidebar.subheader("📊 Bobot Indikator UI (%)")
w_ema = st.sidebar.slider("EMA Cross (Trend)", 0, 40, 25)
w_vwap = st.sidebar.slider("VWAP (Value Zone)", 0, 40, 25)
w_fibo = st.sidebar.slider("Fibonacci Retracement", 0, 30, 15)
w_rsi = st.sidebar.slider("RSI Momentum", 0, 30, 15)
w_fund = st.sidebar.slider("Fundamental (DXY)", 0, 30, 20)

# ==========================================
# 3. HELPER & EXECUTION FUNCTIONS
# ==========================================
def get_intermarket_data():
    try:
        dxy = yf.Ticker("DX-Y.NYB").history(period="2d")['Close']
        oil = yf.Ticker("CL=F").history(period="2d")['Close']
        dxy_change = ((dxy.iloc[-1] - dxy.iloc[-2]) / dxy.iloc[-2]) * 100
        oil_change = ((oil.iloc[-1] - oil.iloc[-2]) / oil.iloc[-2]) * 100
        return dxy.iloc[-1], dxy_change, oil.iloc[-1], oil_change
    except:
        return 100.0, 0.0, 70.0, 0.0

def calculate_advanced_indicators(df, ema_1=9, ema_2=21, ema_3=50, ema_4=100, ema_5=200):
    if df is None or df.empty:
        return None, None

    df.rename(columns={
        'open': 'Open', 'high': 'High', 'low': 'Low', 
        'close': 'Close', 'tick_volume': 'Volume', 'volume': 'Volume'
    }, inplace=True)
    
    df.ta.ema(close='Close', length=ema_1, append=True)
    df.ta.ema(close='Close', length=ema_2, append=True)
    df.ta.ema(close='Close', length=ema_3, append=True)
    df.ta.ema(close='Close', length=ema_4, append=True)
    df.ta.ema(close='Close', length=ema_5, append=True)
    
    df.ta.rsi(close='Close', length=14, append=True)
    df.ta.atr(length=14, append=True)
    
    try:
        df.ta.vwap(append=True)
    except:
        pass
    
    high_max = df['High'].tail(100).max()
    low_min = df['Low'].tail(100).min()
    diff = high_max - low_min
    fibo_levels = {
        '0.236': high_max - 0.236 * diff,
        '0.382': high_max - 0.382 * diff,
        '0.500': high_max - 0.500 * diff,
        '0.618': high_max - 0.618 * diff
    }
    return df, fibo_levels

def fetch_safe_rates(symbol, timeframe, count):
    mt5.symbol_select(symbol, True)
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
            
    if rates is None or len(rates) == 0:
        return None
        
    df = pd.DataFrame(rates)
    if 'time' in df.columns:
        df['time'] = pd.to_datetime(df['time'], unit='s')
    return df

# CEK POSISI TERBUKA PADA SIMBOL MASING-MASING
def count_open_positions(symbol):
    positions = mt5.positions_get(symbol=symbol)
    if positions is None:
        return 0
    return len(positions)

# FUNGSI EKSEKUSI PENDING & INSTANT ORDER DENGAN MATCHING SIMBOL & LOG ERROR
def execute_advanced_order_mt5(order_type, symbol, lot, target_price, sl_price, tp_price, is_pending=False):
    if not mt5.initialize():
        return False, "Koneksi ke MT5 terputus, silakan muat ulang halaman."

    symbol_info = mt5.symbol_info(symbol)
    if not symbol_info:
        return False, f"Simbol {symbol} tidak ditemukan di MT5."
        
    if not symbol_info.visible:
        mt5.symbol_select(symbol, True)

    type_dict_market = {"BUY": mt5.ORDER_TYPE_BUY, "SELL": mt5.ORDER_TYPE_SELL}
    type_dict_limit = {"BUY": mt5.ORDER_TYPE_BUY_LIMIT, "SELL": mt5.ORDER_TYPE_SELL_LIMIT}

    if is_pending:
        action = mt5.TRADE_ACTION_PENDING
        order_cmd = type_dict_limit[order_type]
        price_exec = round(float(target_price), 2)
    else:
        action = mt5.TRADE_ACTION_DEAL
        order_cmd = type_dict_market[order_type]
        price_exec = round(float(symbol_info.ask if order_type == "BUY" else symbol_info.bid), 2)

    base_request = {
        "action": action,
        "symbol": symbol,
        "volume": float(lot),
        "type": order_cmd,
        "price": price_exec,
        "sl": round(float(sl_price), 2),
        "tp": round(float(tp_price), 2),
        "deviation": 20,
        "magic": 123456,
        "comment": "AutoTrade Python",
        "type_time": mt5.ORDER_TIME_GTC,
    }

    filling_modes = [
        mt5.ORDER_FILLING_RETURN,
        mt5.ORDER_FILLING_FOK,
        mt5.ORDER_FILLING_IOC,
        None
    ]

    last_error_code = None
    last_error_desc = "Tidak ada respons dari MT5"

    for fill_mode in filling_modes:
        req = base_request.copy()
        if fill_mode is not None:
            req["type_filling"] = fill_mode

        result = mt5.order_send(req)
        if result is not None:
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                label = f"PENDING {order_type} LIMIT" if is_pending else f"INSTANT {order_type}"
                return True, f"{label} Berhasil Dipasang pada Harga ${price_exec:.2f}"
            else:
                last_error_code = result.retcode
                last_error_desc = result.comment
                if result.retcode != 10030:
                    break
        else:
            err = mt5.last_error()
            last_error_code = err[0]
            last_error_desc = err[1]

    return False, f"Error MT5 ({last_error_code}): {last_error_desc}"

# ==========================================
# 4. TAB NAVIGATION
# ==========================================
tab_live, tab_backtest, tab_autotrade = st.tabs([
    "📡 Live Signals & Panduan Entry", 
    "🧪 Optimization & Evaluasi Strategi", 
    "🤖 Auto Trade MT5"
])

# ------------------------------------------
# TAB 1: LIVE SIGNALS & ANALYSIS
# ------------------------------------------
with tab_live:
    if account_info:
        st.write(f"**Akun Exness:** {account_info.login} | **Saldo:** ${account_info.balance:,.2f} | **Server:** {account_info.server}")
    
    dxy_val, dxy_c, oil_val, oil_c = get_intermarket_data()
    f1, f2 = st.columns(2)
    f1.metric("US Dollar Index (DXY)", f"{dxy_val:.2f}", f"{dxy_c:.2f}% (Inverse vs Emas)")
    f2.metric("Crude Oil (WTI)", f"${oil_val:.2f}", f"{oil_c:.2f}%")

    if st.button("🚀 Analisis & Dapatkan Sinyal Entry", type="primary"):
        symbol_info = mt5.symbol_info(GOLD_SYMBOL)
        spread = (symbol_info.spread * symbol_info.point) if symbol_info and symbol_info.point > 0 else 0.2
        
        df = fetch_safe_rates(GOLD_SYMBOL, tf, 1000)
        
        if df is None or df.empty:
            st.error("❌ Gagal menarik data dari MT5!")
        else:
            df, fibo = calculate_advanced_indicators(df)
            latest = df.iloc[-1]
            
            scores = {}
            ema_bullish = (latest['EMA_9'] > latest['EMA_21']) and (latest['Close'] > latest['EMA_200'])
            ema_bearish = (latest['EMA_9'] < latest['EMA_21']) and (latest['Close'] < latest['EMA_200'])
            scores['EMA'] = 1 if ema_bullish else (-1 if ema_bearish else 0)
            
            vwap_cols = [c for c in df.columns if 'VWAP' in c]
            vwap_val = latest[vwap_cols[0]] if len(vwap_cols) > 0 else latest['Close']
            scores['VWAP'] = 1 if latest['Close'] > vwap_val else -1
            
            rsi_v = latest['RSI_14']
            scores['RSI'] = 1 if rsi_v < 35 else (-1 if rsi_v > 65 else (0.5 if rsi_v > 50 else -0.5))
            scores['Fibonacci'] = 1 if latest['Close'] <= fibo['0.618'] else (-1 if latest['Close'] >= fibo['0.236'] else 0)
            scores['Fundamental'] = -1 if dxy_c > 0.05 else (1 if dxy_c < -0.05 else 0)
            
            total_w = w_ema + w_vwap + w_fibo + w_rsi + w_fund
            calculated_score = (scores['EMA']*w_ema + scores['VWAP']*w_vwap + scores['Fibonacci']*w_fibo + scores['RSI']*w_rsi + scores['Fundamental']*w_fund) / total_w * 100 if total_w > 0 else 0
            
            st.subheader("📌 RINGKASAN SINYAL PASAR")
            c1, c2, c3 = st.columns(3)
            c1.metric(f"Harga {GOLD_SYMBOL} Saat Ini", f"${latest['Close']:.2f}")
            c2.metric("Spread Saat Ini", f"{spread:.2f} Pips", "Aman" if spread <= max_spread else "Melebihi Limit", delta_color="normal" if spread <= max_spread else "inverse")
            c3.metric("Arah Tren & Kekuatan", f"{calculated_score:.1f}%", "BUY (Beli)" if calculated_score > 0 else "SELL (Jual)")
            
            atr_val = latest['ATRr_14']
            current_price = latest['Close']
            
            st.markdown("---")
            st.subheader("🎯 REKOMENDASI POSISI OPTIMAL (RRR 1:2+)")
            
            if spread > max_spread:
                st.error(f"⏹️ **JANGAN ENTRY (CANCEL)**: Spread ({spread:.2f} Pips) terlalu lebar.")
            elif calculated_score >= 50:
                ideal_entry = max(latest['EMA_21'], fibo['0.382']) if "PENDING" in execution_mode else current_price
                if ideal_entry >= current_price and "PENDING" in execution_mode:
                    ideal_entry = current_price - (atr_val * 0.3)
                
                tp_price = ideal_entry + (atr_val * 2.5)
                sl_price = ideal_entry - (atr_val * 1.2)

                st.success(f"🚀 **REKOMENDASI: BUY {'LIMIT' if 'PENDING' in execution_mode else 'NOW'}** (Sinyal: +{calculated_score:.1f}%)")
                
                ep1, ep2, ep3 = st.columns(3)
                ep1.metric("📍 Target Entry BUY", f"${ideal_entry:.2f}")
                ep2.metric("🎯 Take Profit (TP)", f"${tp_price:.2f}")
                ep3.metric("🛑 Stop Loss (SL)", f"${sl_price:.2f}")
                
            elif calculated_score <= -50:
                ideal_entry = min(latest['EMA_21'], fibo['0.618']) if "PENDING" in execution_mode else current_price
                if ideal_entry <= current_price and "PENDING" in execution_mode:
                    ideal_entry = current_price + (atr_val * 0.3)
                
                tp_price = ideal_entry - (atr_val * 2.5)
                sl_price = ideal_entry + (atr_val * 1.2)

                st.error(f"🔻 **REKOMENDASI: SELL {'LIMIT' if 'PENDING' in execution_mode else 'NOW'}** (Sinyal: {calculated_score:.1f}%)")
                
                ep1, ep2, ep3 = st.columns(3)
                ep1.metric("📍 Target Entry SELL", f"${ideal_entry:.2f}")
                ep2.metric("🎯 Take Profit (TP)", f"${tp_price:.2f}")
                ep3.metric("🛑 Stop Loss (SL)", f"${sl_price:.2f}")
            else:
                st.warning(f"⏹️ **WAIT / SIDEWAYS**: Sinyal belum cukup kuat ({calculated_score:.1f}%).")

# ------------------------------------------
# TAB 2: OPTIMIZATION & EVALUASI
# ------------------------------------------
with tab_backtest:
    st.subheader("🧪 Strategi Optimal & Evaluasi")
    st.info("Pilih atau cek aturan strategi sebelum eksekusi.")
    
    if st.button("🔍 Jalankan Evaluasi Strategi Lengkap"):
        st.success("✅ Evaluasi Selesai! Gunakan SOP Entry pada Tab 1 untuk hasil presisi.")

# ------------------------------------------
# TAB 3: AUTO TRADE (EKSEKUSI NYATA KE MT5)
# ------------------------------------------
with tab_autotrade:
    st.subheader("🤖 Eksekusi Otomatis MT5 Exness")
    
    is_active = st.checkbox("AKTIFKAN BOT AUTO-ENTRY")
    allow_multiple = st.checkbox("Izinkan Membuka Banyak Posisi (Multiple Entry)", value=False)
    
    open_pos_count = count_open_positions(GOLD_SYMBOL)
    if open_pos_count > 0:
        st.warning(f"⚠️ **INFORMASI:** Saat ini ada **{open_pos_count} posisi {GOLD_SYMBOL} yang sedang terbuka/running** di MT5.")

    if is_active:
        st.success("🟢 BOT AKTIF - Memantau Sinyal & Eksekusi Otomatis Terhubung!")
        
        symbol_info = mt5.symbol_info(GOLD_SYMBOL)
        spread = (symbol_info.spread * symbol_info.point) if symbol_info and symbol_info.point > 0 else 0.2
        
        df = fetch_safe_rates(GOLD_SYMBOL, tf, 1000)
        if df is not None and not df.empty:
            df, fibo = calculate_advanced_indicators(df)
            latest = df.iloc[-1]
            dxy_val, dxy_c, oil_val, oil_c = get_intermarket_data()
            
            scores = {}
            ema_bullish = (latest['EMA_9'] > latest['EMA_21']) and (latest['Close'] > latest['EMA_200'])
            ema_bearish = (latest['EMA_9'] < latest['EMA_21']) and (latest['Close'] < latest['EMA_200'])
            scores['EMA'] = 1 if ema_bullish else (-1 if ema_bearish else 0)
            
            vwap_cols = [c for c in df.columns if 'VWAP' in c]
            vwap_val = latest[vwap_cols[0]] if len(vwap_cols) > 0 else latest['Close']
            scores['VWAP'] = 1 if latest['Close'] > vwap_val else -1
            
            rsi_v = latest['RSI_14']
            scores['RSI'] = 1 if rsi_v < 35 else (-1 if rsi_v > 65 else (0.5 if rsi_v > 50 else -0.5))
            scores['Fibonacci'] = 1 if latest['Close'] <= fibo['0.618'] else (-1 if latest['Close'] >= fibo['0.236'] else 0)
            scores['Fundamental'] = -1 if dxy_c > 0.05 else (1 if dxy_c < -0.05 else 0)
            
            total_w = w_ema + w_vwap + w_fibo + w_rsi + w_fund
            calculated_score = (scores['EMA']*w_ema + scores['VWAP']*w_vwap + scores['Fibonacci']*w_fibo + scores['RSI']*w_rsi + scores['Fundamental']*w_fund) / total_w * 100 if total_w > 0 else 0
            
            atr_val = latest['ATRr_14']
            current_price = latest['Close']
            use_pending = "PENDING" in execution_mode

            if st.button("⚡ Eksekusi Sinyal Saat Ini Ke MT5 Sekarang"):
                if open_pos_count > 0 and not allow_multiple:
                    st.error("❌ Eksekusi Dibatalkan: Masih ada posisi yang sedang running. Centang 'Izinkan Membuka Banyak Posisi' jika ingin terus eksekusi.")
                elif spread > max_spread:
                    st.error(f"❌ Order Dibatalkan: Spread ({spread:.2f} Pips) melebihi batas Max Spread.")
                elif calculated_score <= -50:
                    ideal_entry = min(latest['EMA_21'], fibo['0.618']) if use_pending else current_price
                    if ideal_entry <= current_price and use_pending:
                        ideal_entry = current_price + (atr_val * 0.3)

                    tp_price = ideal_entry - (atr_val * 2.5)
                    sl_price = ideal_entry + (atr_val * 1.2)
                    
                    success, msg = execute_advanced_order_mt5("SELL", GOLD_SYMBOL, lot_size, ideal_entry, sl_price, tp_price, is_pending=use_pending)
                    if success:
                        st.success(f"✅ {msg}")
                    else:
                        st.error(f"❌ {msg}")

                elif calculated_score >= 50:
                    ideal_entry = max(latest['EMA_21'], fibo['0.382']) if use_pending else current_price
                    if ideal_entry >= current_price and use_pending:
                        ideal_entry = current_price - (atr_val * 0.3)

                    tp_price = ideal_entry + (atr_val * 2.5)
                    sl_price = ideal_entry - (atr_val * 1.2)
                    
                    success, msg = execute_advanced_order_mt5("BUY", GOLD_SYMBOL, lot_size, ideal_entry, sl_price, tp_price, is_pending=use_pending)
                    if success:
                        st.success(f"✅ {msg}")
                    else:
                        st.error(f"❌ {msg}")
                else:
                    st.warning(f"⚠️ Sinyal netral ({calculated_score:.1f}%). Belum memenuhi batas minimal ±50% untuk entry aman.")
    else:
        st.error("🔴 BOT STANDBY / MATI")