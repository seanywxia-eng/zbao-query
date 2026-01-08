import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# 页面设置
st.set_page_config(page_title="ZBAO 数据查询", layout="wide")
st.title("📈 ZBAO (致保科技) 股价查询")

# 固定参数
SHARES_OUTSTANDING = 33270000 
ticker_symbol = "ZBAO"

# 侧边栏
query_mode = st.sidebar.radio("选择模式", ["单日详细", "时间段表格"])

# 核心处理函数：确保提取到的是纯数字
def clean_val(val):
    try:
        # 如果是列表或序列，取第一个值；否则直接转为浮点数
        if hasattr(val, '__iter__'):
            return float(val[0])
        return float(val)
    except:
        return 0.0

if query_mode == "单日详细":
    query_date = st.sidebar.date_input("选择日期", datetime.now() - timedelta(days=1))
    if st.sidebar.button("开始查询"):
        # 抓取数据
        df = yf.download(ticker_symbol, start=query_date, end=query_date + timedelta(days=5))
        
        if not df.empty:
            # 提取第一行并强制转换为纯数字
            row = df.iloc[0]
            op = clean_val(row['Open'])
            cp = clean_val(row['Close'])
            hi = clean_val(row['High'])
            lo = clean_val(row['Low'])
            vo = clean_val(row['Volume'])
            
            # 1. 价格指标卡
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("开盘价", f"${op:.4f}")
            c2.metric("收盘价", f"${cp:.4f}")
            c3.metric("最高价", f"${hi:.4f}")
            c4.metric("最低价", f"${lo:.4f}")
            
            # 2. 交易与市值卡
            st.markdown("---")
            m1, m2, m3 = st.columns(3)
            m1.metric("成交量", f"{int(vo):,}")
            m2.metric("估算成交额", f"${((op + cp)/2 * vo):,.2f}")
            m3.metric("收盘总市值", f"${(cp * SHARES_OUTSTANDING):,.2f}")
        else:
            st.warning("所选日期或其后几天无交易数据（请避开周末）。")

else:
    sd = st.sidebar.date_input("开始日期", datetime.now() - timedelta(days=30))
    ed = st.sidebar.date_input("结束日期", datetime.now())
    
    if st.sidebar.button("生成报表"):
        df = yf.download(ticker_symbol, start=sd, end=ed)
        if not df.empty:
            # 转换所有列为标准数字格式，防止表格显示出错
            for col in ['Open', 'Close', 'High', 'Low', 'Volume']:
                df[col] = df[col].apply(clean_val)
            
            df['成交额(估算)'] = ((df['Open'] + df['Close']) / 2) * df['Volume']
            df['收盘总市值'] = df['Close'] * SHARES_OUTSTANDING
            
            st.subheader("历史数据明细")
            st.dataframe(df.style.format("${:.2f}"), use_container_width=True)
            st.line_chart(df['Close'])
        else:
            st.error("未找到相关数据。")

st.caption("数据来源：Yahoo Finance | 市值计算基于 33.27M 固定股本")
