import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from binance.client import Client

# -----------------------------
# إعداد Streamlit
# -----------------------------
st.set_page_config(page_title="Crypto Order Flow Live", layout="wide", page_icon="📊")
st.title("📊 Crypto Order Flow Live")

# -----------------------------
# الشريط الجانبي
# -----------------------------
st.sidebar.header("الإعدادات")

symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AUXUSDT", "EURUSDT"]
intervals = ["1m", "5m", "15m", "1h", "4h"]

symbol = st.sidebar.selectbox("اختر العملة:", symbols)
interval = st.sidebar.selectbox("اختر الفريم:", intervals)
refresh_rate = st.sidebar.slider("سرعة التحديث (ثواني):", 5, 60, 15)

# API Keys - ضع مفاتيحك هنا
API_KEY = "YOUR_API_KEY"
API_SECRET = "YOUR_API_SECRET"

use_real_data = st.sidebar.checkbox("استخدام بيانات حقيقية من Binance", value=True)

# تحديث تلقائي
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=refresh_rate*1000, key="auto_refresh")

# -----------------------------
# جلب البيانات من Binance
# -----------------------------
client = Client(API_KEY, API_SECRET)

def get_klines(symbol, interval, limit=100):
    try:
        klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
        df = pd.DataFrame(klines, columns=[
            "open_time","open","high","low","close","volume","close_time",
            "quote_asset_volume","number_of_trades","taker_buy_base_asset_volume",
            "taker_buy_quote_asset_volume","ignore"
        ])
        df['datetime'] = pd.to_datetime(df['open_time'], unit='ms')
        for col in ["open","high","low","close","volume"]:
            df[col] = df[col].astype(float)
        return df[['datetime','open','high','low','close','volume']]
    except:
        st.error("خطأ في جلب بيانات الشموع")
        return pd.DataFrame()

def get_trades(symbol, limit=200):
    try:
        trades = client.get_recent_trades(symbol=symbol, limit=limit)
        df = pd.DataFrame(trades)
        df['price'] = df['price'].astype(float)
        df['qty'] = df['qty'].astype(float)
        df['side'] = df['isBuyerMaker'].apply(lambda x: "Sell" if x else "Buy")
        df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
        return df[['price','qty','side','timestamp']]
    except:
        st.warning("استخدام بيانات محاكاة")
        return pd.DataFrame()

# -----------------------------
# جلب البيانات
# -----------------------------
if use_real_data:
    historical_data = get_klines(symbol, interval)
    trades_data = get_trades(symbol)
else:
    historical_data = pd.DataFrame()
    trades_data = pd.DataFrame()

# -----------------------------
# المقاييس الرئيسية
# -----------------------------
st.subheader("📈 المقاييس الرئيسية")
if not trades_data.empty:
    buys = trades_data[trades_data['side']=="Buy"]
    sells = trades_data[trades_data['side']=="Sell"]
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("الحجم الكلي", f"{trades_data['qty'].sum():.2f}")
    with col2:
        st.metric("الشراء", f"{buys['qty'].sum():.2f}")
    with col3:
        st.metric("البيع", f"{sells['qty'].sum():.2f}")
    with col4:
        ratio = buys['qty'].sum() / sells['qty'].sum() if sells['qty'].sum()>0 else 1
        st.metric("النسبة", f"{ratio:.2f}")

# -----------------------------
# Heatmap مبسط
# -----------------------------
st.subheader("🔥 توزيع الصفقات حسب السعر")
if not trades_data.empty and not historical_data.empty:
    price_min = historical_data['low'].min()
    price_max = historical_data['high'].max()
    price_levels = np.linspace(price_min, price_max, 20)
    volume_at_price = []
    for i in range(len(price_levels)-1):
        low_price = price_levels[i]
        high_price = price_levels[i+1]
        volume = trades_data[(trades_data['price']>=low_price)&(trades_data['price']<high_price)]['qty'].sum()
        volume_at_price.append(volume)
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7,0.3])
    fig.add_trace(go.Candlestick(
        x=historical_data['datetime'],
        open=historical_data['open'],
        high=historical_data['high'],
        low=historical_data['low'],
        close=historical_data['close'],
        name="السعر"
    ), row=1, col=1)
    
    fig.add_trace(go.Bar(
        x=price_levels[:-1],
        y=volume_at_price,
        name="حجم الصفقات",
        marker_color='orange'
    ), row=2, col=1)
    
    fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# تدفق الأوامر
# -----------------------------
st.subheader(f"📊 {symbol} - Order Flow ({interval})")
fig_main = go.Figure()
if not historical_data.empty:
    fig_main.add_trace(go.Candlestick(
        x=historical_data['datetime'],
        open=historical_data['open'],
        high=historical_data['high'],
        low=historical_data['low'],
        close=historical_data['close'],
        name="السعر"
    ))

if not trades_data.empty:
    buys = trades_data[trades_data['side']=="Buy"]
    sells = trades_data[trades_data['side']=="Sell"]
    if not buys.empty:
        fig_main.add_trace(go.Scatter(x=buys['timestamp'], y=buys['price'], mode='markers', name='شراء',
                                      marker=dict(color='green', size=8, symbol='triangle-up')))
    if not sells.empty:
        fig_main.add_trace(go.Scatter(x=sells['timestamp'], y=sells['price'], mode='markers', name='بيع',
                                      marker=dict(color='red', size=8, symbol='triangle-down')))
fig_main.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False, yaxis_title="السعر")
st.plotly_chart(fig_main, use_container_width=True)

# -----------------------------
# آخر الصفقات
# -----------------------------
st.subheader("🔄 آخر الصفقات")
if not trades_data.empty:
    display_df = trades_data.tail(15).copy()
    display_df['time'] = display_df['timestamp'].dt.strftime('%H:%M:%S')
    display_df['qty'] = display_df['qty'].round(4)
    display_df['price'] = display_df['price'].round(4)
    display_df = display_df[['time','side','qty','price']]
    st.dataframe(display_df, use_container_width=True, height=400)

# -----------------------------
# تذييل الصفحة
# -----------------------------
st.markdown("---")
st.markdown(f"""
<div style='text-align:center; color:gray; font-size:12px; padding:10px;'>
Crypto Order Flow Live | آخر تحديث: {datetime.now().strftime("%H:%M:%S")}
</div>
""", unsafe_allow_html=True)