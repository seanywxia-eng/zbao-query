import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 页面配置
st.set_page_config(page_title="ZBAO 数据查询", layout="wide")

st.title("📈 ZBAO (致保科技) 股价查询")

# --- 这里是关键修改：直接设置 ZBAO 的总股本，避免调用出错的 info 接口 ---
# 根据公开信息，ZBAO 总股本约为 33,270,000 股
SHARES_OUTSTANDING = 33270000 

# 侧边栏
st.sidebar.header("查询设置")
query_mode = st.sidebar.radio("选择模式", ["单日详细", "时间段表格"])

ticker_symbol = "ZBAO"

if query_mode == "单日详细":
    query_date = st.sidebar.date_input("选择日期", datetime.now() - timedelta(days=1))
    if st.sidebar.button("开始查询"):
        # 抓取两天数据以确保包含目标日
        data = yf.download(ticker_symbol, start=query_date, end=query_date + timedelta(days=2))
        
        if not data.empty:
            # 这里的 .iloc[0] 表示取选定日期的那一行
            day_data = data.iloc[0]
            close_price = float(day_data['Close'])
            vol = int(day_data['Volume'])
            avg_price = (float(day_data['Open']) + close_price) / 2
            
            # 显示指标
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("开盘价", f"${day_data['Open']:.4f}")
            c2.metric("收盘价", f"${close_price:.4f}")
            c3.metric("最高价", f"${day_data['High']:.4f}")
            c4.metric("最低价", f"${day_data['Low']:.4f}")
            
            c5, c6, c7 = st.columns(3)
            c5.metric("成交量", f"{vol:,}")
            c6.metric("估算成交额", f"${(avg_price * vol):,.2f}")
            c7.metric("总市值", f"${(close_price * SHARES_OUTSTANDING):,.2f}")
        else:
            st.warning("该日期没有交易数据，请尝试选择工作日。")

else:
    col_d = st.sidebar.columns(2)
    start_d = col_d[0].date_input("开始", datetime.now() - timedelta(days=30))
    end_d = col_d[1].date_input("结束", datetime.now())
    
    if st.sidebar.button("生成报表"):
        df = yf.download(ticker_symbol, start=start_d, end=end_d)
        if not df.empty:
            # 计算额外列
            df['成交额(估算)'] = ((df['Open'] + df['Close']) / 2) * df['Volume']
            df['总市值'] = df['Close'] * SHARES_OUTSTANDING
            
            # 格式化并显示表格
            st.dataframe(df.style.format("${:.2f}"), use_container_width=True)
            
            # 简单的趋势线
            st.line_chart(df['Close'])
        else:
            st.error("未找到相关数据。")

st.caption("注：市值基于固定股本数 33.27M 计算；成交额为估算值。数据来源: Yahoo Finance")
