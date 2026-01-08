import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 页面配置
st.set_page_config(page_title="ZBAO 股价查询系统", layout="wide")

st.title("📈 ZBAO (Zhibao Technology) 股价信息查询系统")
st.markdown("查询纳斯达克上市公司 **ZBAO** 的历史股价、成交信息及市值。")

# 侧边栏配置
st.sidebar.header("查询参数")
ticker_symbol = "ZBAO"
query_type = st.sidebar.selectbox("选择查询模式", ["单日查询", "时间段查询"])

# 获取总股本 (用于计算市值)
@st.cache_data
def get_stock_info():
    stock = yf.Ticker(ticker_symbol)
    return stock.info

stock_info = get_stock_info()
shares_outstanding = stock_info.get('sharesOutstanding', 33270000) # 若获取失败则使用默认值

if query_type == "单日查询":
    target_date = st.sidebar.date_input("选择日期", datetime.now() - timedelta(days=1))
    if st.sidebar.button("查询"):
        # 获取数据 (需要获取前后两天确保覆盖)
        start_d = target_date
        end_d = target_date + timedelta(days=1)
        df = yf.download(ticker_symbol, start=start_d, end=end_d)
        
        if not df.empty:
            row = df.iloc[0]
            mkt_cap = row['Close'] * shares_outstanding
            turnover = ((row['Open'] + row['Close']) / 2) * row['Volume']
            
            # 友好显示
            cols = st.columns(4)
            cols[0].metric("开盘价", f"${row['Open']:.4f}")
            cols[1].metric("最高价", f"${row['High']:.4f}")
            cols[2].metric("最低价", f"${row['Low']:.4f}")
            cols[3].metric("收盘价", f"${row['Close']:.4f}")
            
            cols2 = st.columns(3)
            cols2[0].metric("成交量", f"{int(row['Volume']):,}")
            cols2[1].metric("估算成交额", f"${turnover:,.2f}")
            cols2[2].metric("收盘总市值", f"${mkt_cap:,.2f}")
        else:
            st.error("该日期无交易数据（可能是周末或节假日）。")

else:
    col_date = st.sidebar.columns(2)
    start_date = col_date[0].date_input("开始日期", datetime.now() - timedelta(days=30))
    end_date = col_date[1].date_input("结束日期", datetime.now())
    
    if st.sidebar.button("生成表格"):
        df = yf.download(ticker_symbol, start=start_date, end=end_date)
        if not df.empty:
            # 数据加工
            df['成交额(估算)'] = ((df['Open'] + df['Close']) / 2) * df['Volume']
            df['收盘后总市值'] = df['Close'] * shares_outstanding
            
            # 格式化表格
            display_df = df[['Open', 'Close', 'High', 'Low', 'Volume', '成交额(估算)', '收盘后总市值']].copy()
            display_df.index = display_df.index.strftime('%Y-%m-%d')
            
            st.subheader(f"{start_date} 至 {end_date} 数据报表")
            st.dataframe(display_df.style.format("${:.2f}"), use_container_width=True)
            
            # 绘制趋势图
            fig = go.Figure(data=[go.Candlestick(x=df.index,
                            open=df['Open'], high=df['High'],
                            low=df['Low'], close=df['Close'])])
            fig.update_layout(title="价格走势 K 线图", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("所选时间段内没有数据。")

st.info("注：市值计算基于最新公开的发行股本数。成交额为基于均价的估算值。")