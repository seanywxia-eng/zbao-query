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
st.sidebar.header("查询设置")
query_mode = st.sidebar.radio("选择模式", ["单日详细", "时间段表格"])

# 核心处理函数：彻底解决数据嵌套导致的 None 问题
def fetch_data(symbol, start_d, end_d):
    # 下载数据
    df = yf.download(symbol, start=start_d, end=end_d)
    if df.empty:
        return None
    
    # 关键步骤：如果数据包含多层索引（新版 yfinance 特色），则将其拍平
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    return df

if query_mode == "单日详细":
    query_date = st.sidebar.date_input("选择日期", datetime.now() - timedelta(days=2))
    if st.sidebar.button("开始查询"):
        # 抓取数据（多查几天确保能抓到）
        df = fetch_data(ticker_symbol, query_date, query_date + timedelta(days=5))
        
        if df is not None:
            # 取第一行有效数据
            row = df.iloc[0]
            op = float(row['Open'])
            cp = float(row['Close'])
            hi = float(row['High'])
            lo = float(row['Low'])
            vo = float(row['Volume'])
            
            # 显示指标
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("开盘价", f"${op:.4f}")
            c2.metric("收盘价", f"${cp:.4f}")
            c3.metric("最高价", f"${hi:.4f}")
            c4.metric("最低价", f"${lo:.4f}")
            
            st.markdown("---")
            m1, m2, m3 = st.columns(3)
            m1.metric("成交量", f"{int(vo):,}")
            m2.metric("估算成交额", f"${((op + cp)/2 * vo):,.2f}")
            m3.metric("收盘总市值", f"${(cp * SHARES_OUTSTANDING):,.2f}")
        else:
            st.warning("未能获取到数据，请确保日期不是周末或节假日。")

else:
    sd = st.sidebar.date_input("开始日期", datetime.now() - timedelta(days=30))
    ed = st.sidebar.date_input("结束日期", datetime.now())
    
    if st.sidebar.button("生成报表"):
        df = fetch_data(ticker_symbol, sd, ed)
        if df is not None:
            # 计算派生字段
            df['成交额(估算)'] = ((df['Open'] + df['Close']) / 2) * df['Volume']
            df['收盘总市值'] = df['Close'] * SHARES_OUTSTANDING
            
            # 选择要显示的列
            display_cols = ['Open', 'Close', 'High', 'Low', 'Volume', '成交额(估算)', '收盘总市值']
            final_df = df[display_cols].copy()
            
            st.subheader("历史数据明细")
            # 这里的格式化确保不会出现 None
            st.dataframe(final_df.style.format("{:,.2f}"), use_container_width=True)
            st.line_chart(final_df['Close'])
        else:
            st.error("未找到相关数据。")

st.caption("注：若数据仍显示不正常，请尝试将开始日期往前调 1-2 天。")
