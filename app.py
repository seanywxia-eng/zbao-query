import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import io

# 页面配置
st.set_page_config(page_title="美股行情导出系统", layout="wide")

st.title("📊 美股行情查询与导出系统")

# --- 侧边栏配置 ---
st.sidebar.header("查询参数")
ticker_input = st.sidebar.text_input("请输入股票代码", value="ZBAO").upper()
query_mode = st.sidebar.radio("选择查询模式", ["单日详细信息", "时间段历史报表"])

def fetch_data(symbol, start_d, end_d):
    try:
        df = yf.download(symbol, start=start_d, end=end_d)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except Exception as e:
        st.error(f"数据抓取失败: {e}")
        return None

@st.cache_data(ttl=3600)
def get_shares_outstanding(symbol):
    try:
        info = yf.Ticker(symbol).info
        return info.get('sharesOutstanding', None)
    except: return None

# 导出 Excel 的核心函数
def to_excel(df):
    output = io.BytesIO()
    # 使用 ExcelWriter 写入内存
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=True, sheet_name='Sheet1')
    return output.getvalue()

if ticker_input:
    shares = get_shares_outstanding(ticker_input)
    
    if query_mode == "单日详细信息":
        target_date = st.sidebar.date_input("选择日期", datetime.now() - timedelta(days=2))
        if st.sidebar.button("开始查询"):
            df = fetch_data(ticker_input, target_date, target_date + timedelta(days=5))
            if df is not None:
                row = df.iloc[0]
                op, cp = float(row['Open']), float(row['Close'])
                vo = float(row['Volume'])
                
                st.subheader(f"{ticker_input} 行情简报")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("收盘价", f"${cp:.2f}")
                c2.metric("开盘价", f"${op:.2f}")
                c3.metric("成交量", f"{int(vo):,}")
                if shares:
                    c4.metric("当日市值", f"${(cp * shares):,.2f}")
            else:
                st.warning("无数据。")

    else:
        # 时间段查询模式
        sd = st.sidebar.date_input("开始日期", datetime.now() - timedelta(days=30))
        ed = st.sidebar.date_input("结束日期", datetime.now())
        
        if st.sidebar.button("生成报表"):
            df = fetch_data(ticker_input, sd, ed)
            if df is not None:
                # 数据处理
                df['成交额(估算)'] = ((df['Open'] + df['Close']) / 2) * df['Volume']
                if shares:
                    df['总市值'] = df['Close'] * shares
                
                st.subheader(f"{ticker_input} 历史数据明细")
                
                # --- 导出按钮逻辑 ---
                excel_data = to_excel(df)
                st.download_button(
                    label="📥 点击下载 Excel 报表",
                    data=excel_data,
                    file_name=f"{ticker_input}_{sd}_to_{ed}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
                # 显示预览表格
                st.dataframe(df.style.format("{:,.2f}"), use_container_width=True)
                st.line_chart(df['Close'])
