import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import io

# 页面配置
st.set_page_config(page_title="美股行情导出系统", layout="wide")

st.title("📊 美股行情查询系统 (含涨跌幅)")

# --- 侧边栏配置 ---
st.sidebar.header("查询参数")
ticker_input = st.sidebar.text_input("请输入股票代码", value="ZBAO").upper()
query_mode = st.sidebar.radio("选择查询模式", ["单日详细信息", "时间段历史报表"])

# 数据抓取与清洗函数
def fetch_data(symbol, start_d, end_d):
    try:
        # 为了计算第一天的涨跌幅，我们需要多往前抓几天数据
        df = yf.download(symbol, start=start_d - timedelta(days=7), end=end_d)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # 计算核心指标
        df['涨跌额'] = df['Close'].diff()
        df['涨跌幅(%)'] = df['Close'].pct_change() * 100
        df['成交额(估算)'] = ((df['Open'] + df['Close']) / 2) * df['Volume']
        
        # 过滤掉为了计算涨跌幅而多抓取的日期，只保留用户要的区间
        df = df[df.index >= pd.to_datetime(start_d)]
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

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=True, sheet_name='数据报表')
    return output.getvalue()

if ticker_input:
    shares = get_shares_outstanding(ticker_input)
    
    if query_mode == "单日详细信息":
        target_date = st.sidebar.date_input("选择日期", datetime.now() - timedelta(days=2))
        if st.sidebar.button("开始查询"):
            # 获取数据（fetch_data内部会自动处理前一交易日对比）
            df = fetch_data(ticker_input, target_date, target_date + timedelta(days=1))
            
            if df is not None and not df.empty:
                row = df.iloc[0]
                cp = float(row['Close'])
                op = float(row['Open'])
                hi = float(row['High'])
                lo = float(row['Low'])
                vo = float(row['Volume'])
                amount = float(row['成交额(估算)'])
                change_pct = float(row['涨跌幅(%)'])
                
                st.subheader(f"{ticker_input} - {target_date.strftime('%Y年%m月%d日')} 行情详细")
                
                # 第一排：基础价格与涨跌
                c1, c2, c3, c4 = st.columns(4)
                # 涨跌幅显示颜色处理
                delta_str = f"{change_pct:+.2f}%"
                c1.metric("收盘价", f"${cp:.2f}", delta=delta_str)
                c2.metric("开盘价", f"${op:.2f}")
                c3.metric("最高价", f"${hi:.2f}")
                c4.metric("最低价", f"${lo:.2f}")
                
                # 第二排：成交与市值
                st.markdown("---")
                m1, m2, m3 = st.columns(3)
                m1.metric("成交量", f"{int(vo):,}")
                m2.metric("成交额(估算)", f"${amount:,.2f}")
                if shares:
                    m3.metric("当日总市值", f"${(cp * shares):,.2f}")
            else:
                st.warning("该日期无交易数据，请尝试选择工作日。")

    else:
        sd = st.sidebar.date_input("开始日期", datetime.now() - timedelta(days=30))
        ed = st.sidebar.date_input("结束日期", datetime.now())
        
        if st.sidebar.button("生成报表"):
            df = fetch_data(ticker_input, sd, ed)
            if df is not None:
                if shares:
                    df['总市值'] = df['Close'] * shares
                
                # 整理报表列顺序
                cols = ['Open', 'High', 'Low', 'Close', '涨跌幅(%)', 'Volume', '成交额(估算)']
                if shares: cols.append('总市值')
                final_df = df[cols]
                
                st.subheader(f"{ticker_input} 历史数据报表")
                
                # 下载按钮
                st.download_button(
                    label="📥 导出 Excel 报表",
                    data=to_excel(final_df),
                    file_name=f"{ticker_input}_报表.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
                # 表格美化显示
                st.dataframe(final_df.style.format({
                    'Open': '{:.2f}', 'High': '{:.2f}', 'Low': '{:.2f}', 
                    'Close': '{:.2f}', '涨跌幅(%)': '{:+.2f}%', 
                    'Volume': '{:,.0f}', '成交额(估算)': '{:,.2f}', '总市值': '{:,.2f}'
                }), use_container_width=True)
                
                st.line_chart(df['Close'])
