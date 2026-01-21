import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import io

# 页面配置
st.set_page_config(page_title="美股专业数据终端", layout="wide")

# CSS 样式：美化单日卡片显示
st.markdown("""
    <style>
    .metric-card { background-color: #f8f9fa; border: 1px solid #edeff1; padding: 15px; border-radius: 10px; text-align: center; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .metric-label { font-size: 14px; color: #5f6368; margin-bottom: 5px; }
    .metric-value { font-size: 19px; font-weight: bold; color: #1a73e8; }
    .source-tag { font-size: 10px; color: #9aa0a6; margin-top: 4px; }
    .up-change { color: #089981; }
    .down-change { color: #f23645; }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 美股行情专业查询终端")

# --- 侧边栏 ---
st.sidebar.header("1. 标的设定")
ticker_input = st.sidebar.text_input("股票代码", value="ZBAO").upper()

# 核心：带缓存的股本抓取函数
@st.cache_data(ttl=3600)
def get_shares_data(symbol):
    """获取股本逻辑：雅虎数据 -> ZBAO预设 -> None"""
    try:
        t = yf.Ticker(symbol)
        info = t.info
        total = info.get('sharesOutstanding')
        float_s = info.get('floatShares')
        
        # 针对 ZBAO 的特殊兜底
        if symbol == "ZBAO" and not total:
            return 33270000, 10000000, "系统内置预设值"
        
        source = "雅虎实时数据" if total else "未查询到最新数据"
        return total, float_s, source
    except:
        return None, None, "数据查询受限"

# 预获取数据
auto_total, auto_float, data_source = get_shares_data(ticker_input)

st.sidebar.header("2. 股本校准")
use_manual = st.sidebar.toggle("启用手动校准", value=False)

if use_manual:
    # 启用手动时，用户输入的数字将覆盖全局
    final_total = st.sidebar.number_input("手动总股本", value=int(auto_total) if auto_total else 33270000)
    final_float = st.sidebar.number_input("手动流通股本", value=int(auto_float) if auto_float else 10000000)
    current_source = "用户手动输入"
else:
    final_total = auto_total
    final_float = auto_float
    current_source = data_source

st.sidebar.header("3. 查询设置")
query_mode = st.sidebar.radio("模式", ["单日详细", "时间段报表"])

def fetch_price_data(symbol, start_d, end_d):
    try:
        # 抓取数据（多抓几天用于涨跌幅计算）
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
                chg = float(row['涨跌幅(%)'])
                chg_class = "up-change" if chg >= 0 else "down-change"
                
                st.subheader(f"{ticker_input} - {target_date} 数据看板")
                
                # 价格行
                c1, c2, c3, c4 = st.columns(4)
                with c1: st.markdown(f'<div class="metric-card"><div class="metric-label">收盘价</div><div class="metric-value">${cp:.2f} <span class="{chg_class}" style="font-size:14px;">({chg:+.2f}%)</span></div></div>', unsafe_allow_html=True)
                with c2: st.markdown(f'<div class="metric-card"><div class="metric-label">开盘价</div><div class="metric-value">${row["Open"]:.2f}</div></div>', unsafe_allow_html=True)
                with c3: st.markdown(f'<div class="metric-card"><div class="metric-label">最高价</div><div class="metric-value">${row["High"]:.2f}</div></div>', unsafe_allow_html=True)
                with c4: st.markdown(f'<div class="metric-card"><div class="metric-label">最低价</div><div class="metric-value">${row["Low"]:.2f}</div></div>', unsafe_allow_html=True)
                
                # 市值行
                st.write("")
                m1, m2, m3, m4 = st.columns(4)
                with m1: st.markdown(f'<div class="metric-card"><div class="metric-label">成交量</div><div class="metric-value">{int(row["Volume"]):,}</div></div>', unsafe_allow_html=True)
                with m2: st.markdown(f'<div class="metric-card"><div class="metric-label">成交额 (估算)</div><div class="metric-value">${row["成交额"]:,.2f}</div></div>', unsafe_allow_html=True)
                
                val_total = f"${(cp * final_total):,.2f}" if final_total else "数据缺失"
                with m3: st.markdown(f'<div class="metric-card"><div class="metric-label">总市值</div><div class="metric-value">{val_total}</div><div class="source-tag">来源: {current_source}</div></div>', unsafe_allow_html=True)
                
                val_float = f"${(cp * final_float):,.2f}" if final_float else "数据缺失"
                with m4: st.markdown(f'<div class="metric-card"><div class="metric-label">流通市值</div><div class="metric-value">{val_float}</div><div class="source-tag">来源: {current_source}</div></div>', unsafe_allow_html=True)
            else:
                st.warning("暂无交易数据，请尝试选择工作日。")

    else:
        # 时间段查询模式
        sd = st.sidebar.date_input("开始日期", datetime.now() - timedelta(days=30))
        ed = st.sidebar.date_input("结束日期", datetime.now())
        if st.sidebar.button("生成报表"):
            df = fetch_price_data(ticker_input, sd, ed)
            if df is not None:
                # 核心计算：总市值与流通市值（逻辑与单日一致）
                if final_total:
                    df['总市值'] = df['Close'] * final_total
                if final_float:
                    df['流通市值'] = df['Close'] * final_float
                
                st.subheader(f"{ticker_input} 历史行情与市值明细")
                st.info(f"📊 当前市值计算股本来源：{current_source}")
                
                # 准备 Excel 导出
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=True)
                st.download_button("📥 导出 Excel 报表", data=output.getvalue(), file_name=f"{ticker_input}_历史报表.xlsx")
                
                # 动态显示列：如果有市值数据则显示
                display_df = df.copy()
                format_dict = {
                    'Open': '{:.2f}', 'High': '{:.2f}', 'Low': '{:.2f}', 'Close': '{:.2f}', 
                    '涨跌幅(%)': '{:+.2f}%', 'Volume': '{:,.0f}', '成交额': '{:,.2f}'
                }
                if '总市值' in df.columns: format_dict['总市值'] = '{:,.2f}'
                if '流通市值' in df.columns: format_dict['流通市值'] = '{:,.2f}'
                
                st.dataframe(display_df.style.format(format_dict, na_rep="-"), use_container_width=True)
                
                # 价格趋势
                st.line_chart(df['Close'])
            else:
                st.error("数据抓取失败，请稍后再试或检查代码。")
