import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import io

st.set_page_config(page_title="ZBAO及美股专业查询", layout="wide")
st.title("📊 美股行情专业查询终端")

# --- 侧边栏 ---
st.sidebar.header("1. 标的设定")
ticker_input = st.sidebar.text_input("股票代码", value="ZBAO").upper()

st.sidebar.header("2. 股本校准 (如自动获取不准请在此修改)")
# 尝试自动获取作为默认值
@st.cache_data(ttl=3600)
def get_default_shares(symbol):
    try:
        t = yf.Ticker(symbol)
        info = t.info
        return info.get('sharesOutstanding', 33270000), info.get('floatShares', 10000000)
    except:
        return 33270000, 10000000

auto_total, auto_float = get_default_shares(ticker_input)

# 用户手动微调股本（默认显示自动抓取的，用户可改）
manual_total = st.sidebar.number_input("总股本 (股)", value=int(auto_total), step=10000)
manual_float = st.sidebar.number_input("流通股本 (股)", value=int(auto_float) if auto_float else int(manual_total*0.3), step=10000)

st.sidebar.header("3. 查询设置")
query_mode = st.sidebar.radio("模式", ["单日详细", "时间段报表"])

# --- 数据处理 ---
def fetch_price_data(symbol, start_d, end_d):
    try:
        df = yf.download(symbol, start=start_d - timedelta(days=7), end=end_d)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df['涨跌幅(%)'] = df['Close'].pct_change() * 100
        df['成交额'] = ((df['Open'] + df['Close']) / 2) * df['Volume']
        return df[df.index >= pd.to_datetime(start_d)]
    except:
        return None

# --- 显示逻辑 ---
if ticker_input:
    if query_mode == "单日详细":
        target_date = st.sidebar.date_input("选择日期", datetime.now() - timedelta(days=2))
        if st.sidebar.button("执行查询"):
            df = fetch_price_data(ticker_input, target_date, target_date + timedelta(days=1))
            if df is not None and not df.empty:
                row = df.iloc[-1]
                cp = float(row['Close'])
                
                # 计算市值
                total_mkt_cap = cp * manual_total
                float_mkt_cap = cp * manual_float
                
                st.subheader(f"{ticker_input} - {target_date} 数据看板")
                
                # 第一排
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("收盘价", f"${cp:.2f}", f"{row['涨跌幅(%)']:+.2f}%")
                c2.metric("开盘价", f"${row['Open']:.2f}")
                c3.metric("最高价", f"${row['High']:.2f}")
                c4.metric("最低价", f"${row['Low']:.2f}")
                
                # 第二排
                st.markdown("---")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("成交量", f"{int(row['Volume']):,}")
                m2.metric("成交额", f"${row['成交额']:,.2f}")
                m3.metric("总市值", f"${total_mkt_cap:,.2f}")
                m4.metric("流通市值", f"${float_mkt_cap:,.2f}")
                
                st.caption(f"注：当前计算基于总股本 {manual_total:,}，流通股本 {manual_float:,}")
            else:
                st.warning("暂无交易数据，请检查日期。")

    else:
        sd = st.sidebar.date_input("开始日期", datetime.now() - timedelta(days=30))
        ed = st.sidebar.date_input("结束日期", datetime.now())
        if st.sidebar.button("生成报表"):
            df = fetch_price_data(ticker_input, sd, ed)
            if df is not None:
                # 批量计算
                df['总市值'] = df['Close'] * manual_total
                df['流通市值'] = df['Close'] * manual_float
                
                st.subheader(f"{ticker_input} 历史数据明细")
                
                # 下载按钮
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=True)
                st.download_button("📥 导出 Excel 报表", data=output.getvalue(), file_name=f"{ticker_input}_data.xlsx")
                
                # 表格美化
                st.dataframe(df.style.format({
                    'Open': '{:.2f}', 'Close': '{:.2f}', '涨跌幅(%)': '{:+.2f}%', 
                    '成交额': '{:,.2f}', '总市值': '{:,.2f}', '流通市值': '{:,.2f}'
                }), use_container_width=True)
                
                st.line_chart(df['Close'])
