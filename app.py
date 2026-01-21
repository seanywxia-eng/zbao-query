import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import io

# 页面配置
st.set_page_config(page_title="ZBAO及美股查询终端", layout="wide")

st.title("📊 股票行情查询系统 (含流通与总市值)")

# --- 侧边栏 ---
st.sidebar.header("查询设置")
ticker_input = st.sidebar.text_input("股票代码", value="ZBAO").upper()
query_mode = st.sidebar.radio("模式", ["单日详细", "时间段报表"])

# --- 核心：快速获取股本数据 (带缓存避免卡顿) ---
@st.cache_data(ttl=3600)
def get_company_shares(symbol):
    """获取总股本和流通股本，失败时返回None"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        total_shares = info.get('sharesOutstanding')
        # floatShares 是雅虎提供的流通股本字段
        float_shares = info.get('floatShares') 
        return total_shares, float_shares
    except:
        return None, None

def fetch_price_data(symbol, start_d, end_d):
    """获取价格数据，做了拍平处理"""
    try:
        # 多抓几天用于计算涨跌幅
        df = yf.download(symbol, start=start_d - timedelta(days=7), end=end_d)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df['涨跌幅(%)'] = df['Close'].pct_change() * 100
        df['成交额'] = ((df['Open'] + df['Close']) / 2) * df['Volume']
        return df[df.index >= pd.to_datetime(start_d)]
    except:
        return None

# --- 执行逻辑 ---
if ticker_input:
    # 1. 尝试获取股本信息（因为有缓存，这步通常很快）
    with st.spinner('正在获取股本数据...'):
        total_s, float_s = get_company_shares(ticker_input)

    if query_mode == "单日详细":
        target_date = st.sidebar.date_input("选择日期", datetime.now() - timedelta(days=2))
        if st.sidebar.button("查询"):
            df = fetch_price_data(ticker_input, target_date, target_date + timedelta(days=1))
            
            if df is not None and not df.empty:
                row = df.iloc[0]
                cp = float(row['Close'])
                
                st.subheader(f"{ticker_input} - {target_date} 详细数据")
                
                # 指标展示
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("收盘价", f"${cp:.2f}", f"{row['涨跌幅(%)']:+.2f}%")
                c2.metric("开盘价", f"${row['Open']:.2f}")
                c3.metric("最高价", f"${row['High']:.2f}")
                c4.metric("最低价", f"${row['Low']:.2f}")
                
                st.markdown("---")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("成交量", f"{int(row['Volume']):,}")
                m2.metric("成交额", f"${row['成交额']:,.2f}")
                
                # 市值计算（如果拿不到数据则友好提示）
                m3.metric("总市值", f"${(cp * total_s):,.2f}" if total_s else "数据受限")
                m4.metric("流通市值", f"${(cp * float_s):,.2f}" if float_s else "数据受限")
                
                if not total_s:
                    st.info("💡 提示：雅虎财经有时不公开小盘股的实时流通股数据，建议手动对比财报。")
            else:
                st.warning("未找到该日期数据。")

    else:
        sd = st.sidebar.date_input("开始日期", datetime.now() - timedelta(days=30))
        ed = st.sidebar.date_input("结束日期", datetime.now())
        
        if st.sidebar.button("生成报表"):
            df = fetch_price_data(ticker_input, sd, ed)
            if df is not None:
                # 批量计算市值
                if total_s: df['总市值'] = df['Close'] * total_s
                if float_s: df['流通市值'] = df['Close'] * float_s
                
                st.subheader(f"{ticker_input} 历史报表")
                
                # 导出按钮
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=True)
                st.download_button("📥 导出 Excel", data=output.getvalue(), file_name=f"{ticker_input}.xlsx")
                
                # 动态格式化表格
                format_dict = {'Open': '{:.2f}', 'Close': '{:.2f}', '涨跌幅(%)': '{:+.2f}%', '成交额': '{:,.2f}'}
                if total_s: format_dict['总市值'] = '{:,.0f}'
                if float_s: format_dict['流通市值'] = '{:,.0f}'
                
                st.dataframe(df.style.format(format_dict, na_rep="-"), use_container_width=True)
            else:
                st.error("抓取失败。")
