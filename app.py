import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import yfinance as yf
from datetime import datetime
import os
import requests

# ==========================================
# 1. 앱 기본 설정 & UI/UX 고도화
# ==========================================
st.set_page_config(page_title="My Asset Hub V17", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; }
    p, .stMarkdown, div[data-testid="stText"] { font-size: 1.15rem !important; }
    .stMetric label { font-size: 1.2rem !important; font-weight: bold; color: #555; }
    .stMetric value { font-size: 2.2rem !important; color: #111; }
    .stDataFrame { font-size: 1.15rem !important; }
    .goal-red { color: #E74C3C; font-weight: 900; font-size: 1.6rem; }
    .goal-green { color: #2ECC71; font-weight: 900; font-size: 1.6rem; }
    </style>
    """, unsafe_allow_html=True)

STOCKS_FILE = 'my_stocks.csv'
SAVINGS_FILE = 'my_savings.csv'
HISTORY_FILE = 'asset_history.csv'
CONFIG_FILE = 'app_config.csv'

def load_data(file_name):
    if os.path.exists(file_name): return pd.read_csv(file_name).to_dict('records')
    return []
def save_data(data, file_name): pd.DataFrame(data).to_csv(file_name, index=False)

if 'stocks' not in st.session_state: st.session_state['stocks'] = load_data(STOCKS_FILE)
if 'savings' not in st.session_state: st.session_state['savings'] = load_data(SAVINGS_FILE)
if 'config' not in st.session_state: 
    cfg = load_data(CONFIG_FILE)
    st.session_state['config'] = cfg[0] if cfg else {"target_asset": 1000000000}

# ==========================================
# 2. 데이터 수집 API
# ==========================================
ASSET_DICT = {"TIGER KRX금현물": "318010.KS", "0072R0": "318010.KS", "삼성전자": "005930.KS", "비트코인": "KRW-BTC"}

@st.cache_data(ttl=600)
def get_exchange_rate():
    try: return yf.Ticker("USDKRW=X").history(period="1d")['Close'].iloc[-1]
    except: return 1350.0

@st.cache_data(ttl=300)
def get_stock_data(ticker):
    try:
        hist = yf.Ticker(ticker).history(period='7d')
        return hist['Close'].iloc[-1], hist['Close'].tolist()
    except: return 0, [0]*7

@st.cache_data(ttl=300)
def get_upbit_data(market):
    try:
        url_ticker = f"https://api.upbit.com/v1/ticker?markets={market}"
        curr_price = requests.get(url_ticker).json()[0]['trade_price']
        return curr_price, []
    except: return 0, []

@st.cache_data(ttl=3600)
def fetch_company_name(ticker):
    try:
        info = yf.Ticker(ticker).info
        return info.get('shortName') or info.get('longName') or ticker
    except: return ticker

def verify_and_get_ticker(input_val):
    input_val = input_val.strip().upper()
    if input_val in ASSET_DICT: return ASSET_DICT[input_val], fetch_company_name(ASSET_DICT[input_val])
    coin_map = {"비트코인": "KRW-BTC", "BTC": "KRW-BTC", "이더리움": "KRW-ETH", "ETH": "KRW-ETH", "리플": "KRW-XRP", "XRP": "KRW-XRP"}
    for key, val in coin_map.items():
        if key in input_val: return val, val.replace("KRW-", "") + " (가상화폐)"
    if input_val.startswith("KRW-"): return input_val, input_val.replace("KRW-", "") + " (가상화폐)"
    
    if len(input_val) == 6 and input_val.isalnum():
        for suffix in [".KS", ".KQ"]:
            try:
                if not yf.Ticker(input_val + suffix).history(period="1d").empty: return input_val + suffix, fetch_company_name(input_val + suffix)
            except: pass
        return None, None
    try:
        if not yf.Ticker(input_val).history(period="1d").empty: return input_val, fetch_company_name(input_val)
    except: pass
    return None, None

exchange_rate = get_exchange_rate()

# ==========================================
# ⬅️ 사이드바: 자산 컨트롤러
# ==========================================
st.sidebar.title("🛠️ 자산 컨트롤러")
st.sidebar.info(f"💱 실시간 환율: **1달러 = {exchange_rate:,.1f}원**")

with st.sidebar.expander("⚙️ 내 목표 자산 설정", expanded=False):
    # [수정 완료] 콤마가 표시되는 텍스트 입력창으로 우회 로직 적용
    current_tgt = int(st.session_state['config'].get('target_asset', 1000000000))
    new_target_str = st.text_input("목표 자산 금액 (원)", value=f"{current_tgt:,}")
    
    if st.button("목표 업데이트"):
        try:
            clean_target = int(new_target_str.replace(",", "").replace(" ", ""))
            st.session_state['config']['target_asset'] = clean_target
            save_data([st.session_state['config']], CONFIG_FILE)
            st.rerun()
        except ValueError:
            st.error("⚠️ 숫자만 입력해 주세요.")
st.sidebar.markdown("---")

st.sidebar.markdown("### ➕ 투자 자산 추가")
asset_input = st.sidebar.text_input("🔍 종목 검색", placeholder="예: 0072R0, AAPL, 비트코인")
st.sidebar.markdown("[👉 네이버 증권에서 종목코드 찾기](https://finance.naver.com/)", unsafe_allow_html=True)

if asset_input:
    with st.spinner("종목 확인 중..."):
        valid_ticker, valid_name = verify_and_get_ticker(asset_input)
    if valid_ticker:
        st.sidebar.success(f"✅ 확인됨: **{valid_ticker}** ({valid_name})")
        is_crypto = valid_ticker.startswith("KRW-")
        is_foreign = not (valid_ticker.endswith(".KS") or valid_ticker.endswith(".KQ") or is_crypto)
        
        existing_idx = next((i for i, s in enumerate(st.session_state['stocks']) if s['티커'] == valid_ticker), None)
        if existing_idx is not None:
            st.sidebar.warning("⚠️ 이미 보유 중인 종목입니다. 추가 시 평단가와 수량이 병합(물타기)됩니다.")
            btn_label = "➕ 물타기/불타기 (합산 저장)"
        else:
            btn_label = "투자 자산 저장"
        
        currency_label = "원 ₩" if (is_crypto or not is_foreign) else "달러 $"
        new_price = st.sidebar.number_input(f"매수 평단가 ({currency_label})", min_value=0, step=1000, format="%d")
        new_qty = st.sidebar.number_input("보유 수량", min_value=0.0, step=0.01)
        risk_level = st.sidebar.selectbox("리스크 분류", ["초고위험 (코인/레버리지)", "위험 (개별주식)", "중립 (지수ETF)", "안전 (금/국채)"])
        
        if st.sidebar.button(btn_label, use_container_width=True):
            if existing_idx is not None:
                old_data = st.session_state['stocks'][existing_idx]
                old_tot = old_data['매수평단가'] * old_data['보유수량']
                new_tot = new_price * new_qty
                final_qty = old_data['보유수량'] + new_qty
                final_price = (old_tot + new_tot) / final_qty if final_qty > 0 else 0
                st.session_state['stocks'][existing_idx]['매수평단가'] = final_price
                st.session_state['stocks'][existing_idx]['보유수량'] = final_qty
            else:
                st.session_state['stocks'].append({
                    "종목명": valid_name, "티커": valid_ticker, "매수평단가": new_price, 
                    "보유수량": new_qty, "해외여부": is_foreign, "리스크": risk_level.split(" ")[0]
                })
            save_data(st.session_state['stocks'], STOCKS_FILE)
            st.rerun()
    else:
        st.sidebar.error("찾을 수 없습니다.")
st.sidebar.markdown("---")

with st.sidebar.expander("🏦 은행 자산 추가", expanded=False):
    bank_type = st.selectbox("자산 종류", ["적금", "주택청약", "예금", "파킹통장"])
    sav_name = st.text_input("은행 및 상품명")
    sav_monthly = st.number_input("월 납입액(예금은 총액)", min_value=0, step=10000, format="%d")
    sav_curr_month = st.number_input("현재 납입 회차", min_value=1, step=1)
    sav_total_month = st.number_input("총 만기 회차", min_value=1, step=1)
    sav_rate = st.number_input("연 이율 (%)", min_value=0.0, step=0.1, value=3.0)
    
    if st.button("은행 자산 저장", use_container_width=True):
        if sav_name:
            st.session_state['savings'].append({
                "종류": bank_type, "상품명": sav_name, "월납입액": sav_monthly, 
                "현재회차": sav_curr_month, "총회차": sav_total_month, "이율": sav_rate
            })
            save_data(st.session_state['savings'], SAVINGS_FILE)
            st.rerun()

# ==========================================
# 🖥️ 메인 대시보드 데이터 연산
# ==========================================
st.title("💰 My Asset Hub")
today_date = pd.to_datetime(datetime.now().strftime('%Y-%m-%d'))
today_str = today_date.strftime('%Y-%m-%d')

port_group = {"국내 주식 (국장)": 0, "해외 주식 (미장)": 0, "가상화폐 (코인)": 0}
risk_group = {"초고위험": 0, "위험": 0, "중립": 0, "안전": 0}
stock_display_data = []
total_buy_principal = 0 

for idx, stock in enumerate(st.session_state['stocks']):
    ticker = stock.get("티커", "")
    is_crypto = ticker.startswith("KRW-")
    is_foreign = stock.get("해외여부", False)
    
    buy_price = stock.get("매수평단가", 0)
    qty = stock.get("보유수량", 0)
    
    if is_crypto:
        curr_price, _ = get_upbit_data(ticker)
        display_price = curr_price
        buy_amount = buy_price * qty
    else:
        curr_price, _ = get_stock_data(ticker)
        display_price = curr_price * exchange_rate if is_foreign else curr_price
        buy_amount = buy_price * qty * (exchange_rate if is_foreign else 1)
    
    eval_amount = display_price * qty
    total_buy_principal += buy_amount
    
    if is_crypto: port_group["가상화폐 (코인)"] += eval_amount
    elif is_foreign: port_group["해외 주식 (미장)"] += eval_amount
    else: port_group["국내 주식 (국장)"] += eval_amount
        
    risk_category = stock.get("리스크", "위험")
    if risk_category in risk_group: risk_group[risk_category] += eval_amount
    
    profit_rate = ((eval_amount - buy_amount) / buy_amount * 100) if buy_amount > 0 else 0
    stock_display_data.append({
        "ID": idx, "종목명": stock.get("종목명", "Unknown"), "티커": ticker,
        "매수평단가": buy_price, "보유수량": qty, "매수금액": buy_amount, "해외여부": is_foreign,
        "현재가(원)": display_price, "수익률": profit_rate, "평가금액": eval_amount, "리스크": risk_category
    })

total_saving_value = 0
fixed_savings_value = 0 

for sav in st.session_state['savings']:
    bank_type = sav.get('종류', '적금')
    sav_amount = sav.get("월납입액", 0) * sav.get("현재회차", 0)
    total_saving_value += sav_amount
    total_buy_principal += sav_amount
    if bank_type in ["적금", "주택청약"]: fixed_savings_value += sav_amount

grand_total = sum(port_group.values()) + total_saving_value
risk_group["안전"] += total_saving_value
total_profit = grand_total - total_buy_principal
total_profit_rate = (total_profit / total_buy_principal * 100) if total_buy_principal > 0 else 0

# ==========================================
# ⚠️ [버그 픽스] 누락되었던 히스토리 기록 복구
# ==========================================
history_data = load_data(HISTORY_FILE)
history_df = pd.DataFrame(history_data) if history_data else pd.DataFrame(columns=["날짜", "총자산"])

if grand_total > 0:
    if not history_df.empty and today_str in history_df['날짜'].values:
        history_df.loc[history_df['날짜'] == today_str, '총자산'] = grand_total
    else:
        new_row = pd.DataFrame([{"날짜": today_str, "총자산": grand_total}])
        history_df = pd.concat([history_df, new_row], ignore_index=True)
    save_data(history_df.to_dict('records'), HISTORY_FILE)

if not history_df.empty:
    history_df['날짜'] = pd.to_datetime(history_df['날짜'])
# ==========================================

target_amount = st.session_state['config'].get('target_asset', 1000000000)
achieved_pct = (grand_total / target_amount * 100) if target_amount > 0 else 0
remaining_pct = 100.0 - achieved_pct

if remaining_pct > 0:
    status_html = f"<span class='goal-red'>목표까지 {remaining_pct:.1f}% 남았습니다! 🔥</span>"
else:
    status_html = f"<span class='goal-green'>🎉 목표 달성 완료! (초과: {abs(remaining_pct):.1f}%) 🎉</span>"

st.markdown(f"### 🏆 나의 목표 자산 ({target_amount:,.0f}원) 현황: {status_html}", unsafe_allow_html=True)
st.progress(min(achieved_pct / 100, 1.0))

col_t1, col_t2, col_t3, col_t4 = st.columns(4)
col_t1.metric("최종 목표 금액", f"{target_amount:,.0f}원")
col_t2.metric("현재 총 자산", f"{grand_total:,.0f}원", delta_color="off")
col_t3.metric("총 매수 원금", f"{total_buy_principal:,.0f}원")
col_t4.metric("합산 수익금", f"{total_profit:,.0f}원", f"{total_profit_rate:.2f}%")

st.markdown("---")

tab1, tab2, tab3 = st.tabs(["📊 대시보드 (비중 & 성장)", "📋 상세 자산 관리 (편집)", "⚖️ 2-Step 정밀 리밸런싱"])

with tab1:
    col_pie1, col_pie2 = st.columns(2)
    color_palette_assets = ['#2E86C1', '#8E44AD', '#F39C12', '#1ABC9C'] 
    color_palette_risk = ['#E74C3C', '#F1C40F', '#3498DB', '#2ECC71'] 
    
    with col_pie1:
        st.subheader("⚖️ 자산군 포트폴리오 비중")
        fig_pie = go.Figure(data=[go.Pie(labels=list(port_group.keys()) + ['은행 자산 (안전)'], values=list(port_group.values()) + [total_saving_value], hole=.4, marker_colors=color_palette_assets)])
        fig_pie.update_traces(textposition='outside', textinfo='percent+label', textfont_size=14)
        fig_pie.update_layout(margin=dict(t=10, b=0, l=0, r=0), height=380, showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with col_pie2:
        st.subheader("🛡️ 투자 리스크 다각화 현황")
        fig_risk = go.Figure(data=[go.Pie(labels=list(risk_group.keys()), values=list(risk_group.values()), hole=.4, marker_colors=color_palette_risk)])
        fig_risk.update_traces(textposition='outside', textinfo='percent+label', textfont_size=14)
        fig_risk.update_layout(margin=dict(t=10, b=0, l=0, r=0), height=380, showlegend=False)
        st.plotly_chart(fig_risk, use_container_width=True)

    st.divider()
    st.subheader("🚀 나의 자산 성장 타임라인")
    if grand_total > 0 and not history_df.empty:
        time_view = st.radio("보기 옵션", ["일별 (Daily)", "월별 (Monthly)", "연별 (Yearly)"], horizontal=True)
        plot_df = history_df.copy()
        
        if time_view == "일별 (Daily)":
            start_date = today_date - pd.Timedelta(days=31)
            end_date = today_date + pd.Timedelta(days=2) 
            tickvals = pd.date_range(start=start_date, end=end_date, freq='D')
            fig_hist = px.area(plot_df, x="날짜", y="총자산", markers=True, color_discrete_sequence=['#8E44AD'])
            fig_hist.update_xaxes(range=[start_date, end_date], tickvals=tickvals, tickformat="%y.%m.%d", tickfont=dict(size=12))
        elif time_view == "월별 (Monthly)":
            plot_df['날짜'] = plot_df['날짜'].dt.to_period('M').dt.to_timestamp()
            plot_df = plot_df.groupby('날짜')['총자산'].last().reset_index()
            start_month = today_date.replace(day=1) - pd.DateOffset(months=12)
            end_month = today_date.replace(day=1) + pd.DateOffset(months=2)
            tickvals = pd.date_range(start=start_month, end=end_month, freq='MS')
            fig_hist = px.area(plot_df, x="날짜", y="총자산", markers=True, color_discrete_sequence=['#8E44AD'])
            fig_hist.update_xaxes(range=[start_month, end_month], tickvals=tickvals, tickformat="%y.%m", tickfont=dict(size=14))
        elif time_view == "연별 (Yearly)":
            plot_df['날짜'] = plot_df['날짜'].dt.to_period('Y').dt.to_timestamp()
            plot_df = plot_df.groupby('날짜')['총자산'].last().reset_index()
            fig_hist = px.area(plot_df, x="날짜", y="총자산", markers=True, color_discrete_sequence=['#8E44AD'])
            fig_hist.update_xaxes(tickformat="%Y", tickfont=dict(size=14)) 

        fig_hist.update_yaxes(tickfont=dict(size=14))
        fig_hist.update_layout(margin=dict(t=10, b=0, l=0, r=0), height=380)
        st.plotly_chart(fig_hist, use_container_width=True)

with tab2:
    st.subheader("📈 투자 자산 내역 (편집 가능)")
    if stock_display_data:
        for item in stock_display_data:
            idx = item['ID']
            c_info, c_btn1, c_btn2 = st.columns([6, 1, 1])
            with c_info:
                profit_sign = "🔥" if item['수익률'] > 0 else "❄️"
                st.markdown(f"**{item['종목명']} ({item['티커']})** | 등급: **[{item['리스크']}]** | {profit_sign} **{item['수익률']:.2f}%**")
                cur_sym = "$" if item['해외여부'] and not item['티커'].startswith("KRW-") else "₩"
                st.caption(f"↳ 매수단가: **{item['매수평단가']:,.2f}{cur_sym}** | 수량: **{item['보유수량']:.2f}개** | 총 매수금액: **{item['매수금액']:,.0f}원** | 현재 평가금액: **{item['평가금액']:,.0f}원**")
            with c_btn1:
                if st.button("✏️ 편집", key=f"edit_btn_{idx}"):
                    st.session_state[f"edit_mode_{idx}"] = not st.session_state.get(f"edit_mode_{idx}", False)
            with c_btn2:
                if st.button("🗑️ 삭제", key=f"del_stk_{idx}"):
                    st.session_state['stocks'].pop(idx)
                    save_data(st.session_state['stocks'], STOCKS_FILE)
                    st.rerun()
            if st.session_state.get(f"edit_mode_{idx}", False):
                with st.container():
                    col_e1, col_e2, col_e3 = st.columns(3)
                    new_p = col_e1.number_input("수정 평단가", value=float(item['매수평단가']), format="%f", key=f"ep_{idx}")
                    new_q = col_e2.number_input("수정 수량", value=float(item['보유수량']), format="%f", key=f"eq_{idx}")
                    if col_e3.button("✔️ 저장", key=f"save_edit_{idx}"):
                        st.session_state['stocks'][idx]['매수평단가'] = new_p
                        st.session_state['stocks'][idx]['보유수량'] = new_q
                        st.session_state[f"edit_mode_{idx}"] = False
                        save_data(st.session_state['stocks'], STOCKS_FILE)
                        st.rerun()
    st.divider()
    
    st.subheader("🏦 은행 자산 내역 (편집 가능)")
    if st.session_state['savings']:
        for idx, sav in enumerate(st.session_state['savings']):
            c_info, c_btn1, c_btn2 = st.columns([6, 1, 1])
            with c_info:
                bank_type = sav.get('종류', '적금')
                principal = sav.get('월납입액', 0) * sav.get('총회차', 1)
                rate = sav.get('이율', 3.0)
                multiplier = (sav.get('총회차', 1) + 1) / 2 / 12 if bank_type == "적금" else sav.get('총회차', 1) / 12
                expected_interest = principal * (rate / 100) * multiplier
                st.markdown(f"**[{bank_type}] {sav.get('상품명', '이름없음')}** (연 **{rate}%**) | 원금: **{principal:,.0f}원** | 만기 시 예상 이자: **+ {expected_interest:,.0f}원**")
                rem_months = sav.get('총회차', 1) - sav.get('현재회차', 0)
                st.caption(f"↳ 총 {sav.get('총회차', 1)}개월 중 **{sav.get('현재회차', 0)}개월 차** 진행 중 (만기까지 **{rem_months}개월** 남음)")
            with c_btn1:
                if st.button("✏️ 편집", key=f"edit_sav_btn_{idx}"):
                    st.session_state[f"edit_sav_{idx}"] = not st.session_state.get(f"edit_sav_{idx}", False)
            with c_btn2:
                if st.button("🗑️ 삭제", key=f"del_sav_{idx}"):
                    st.session_state['savings'].pop(idx)
                    save_data(st.session_state['savings'], SAVINGS_FILE)
                    st.rerun()
            if st.session_state.get(f"edit_sav_{idx}", False):
                with st.container():
                    col_e1, col_e2, col_e3, col_e4 = st.columns(4)
                    new_m = col_e1.number_input("월 납입액", value=int(sav.get('월납입액', 0)), step=10000, key=f"es_m_{idx}")
                    new_c = col_e2.number_input("현재 회차", value=int(sav.get('현재회차', 1)), step=1, key=f"es_c_{idx}")
                    new_r = col_e3.number_input("이율(%)", value=float(sav.get('이율', 3.0)), step=0.1, key=f"es_r_{idx}")
                    if col_e4.button("✔️ 저장", key=f"save_sav_edit_{idx}"):
                        st.session_state['savings'][idx]['월납입액'] = new_m
                        st.session_state['savings'][idx]['현재회차'] = new_c
                        st.session_state['savings'][idx]['이율'] = new_r
                        st.session_state[f"edit_sav_{idx}"] = False
                        save_data(st.session_state['savings'], SAVINGS_FILE)
                        st.rerun()

with tab3:
    st.subheader("⚖️ 1단계: 리스크 그룹별 목표 비중 설정")
    fixed_pct = round((fixed_savings_value / grand_total * 100), 1) if grand_total > 0 else 0
    rem_pct = round(100.0 - fixed_pct, 1)
    
    st.info(f"🔒 **고정 자산 (적금 및 주택청약)** 비중은 전체의 **{fixed_pct}%**입니다. 나머지 **{rem_pct}%** 파이에 대해 목표를 분배해 주세요.")
    current_risk_pct = {k: (v / grand_total * 100) if grand_total > 0 else 0 for k, v in risk_group.items()}
    
    rc1, rc2, rc3, rc4, rc5 = st.columns(5)
    tgt_super = rc1.number_input("1. 초고위험 (%)", value=0.0, min_value=0.0, max_value=100.0, step=1.0)
    tgt_risk = rc2.number_input("2. 위험 (%)", value=0.0, min_value=0.0, max_value=100.0, step=1.0)
    tgt_neutral = rc3.number_input("3. 중립 (%)", value=0.0, min_value=0.0, max_value=100.0, step=1.0)
    tgt_safe_liquid = rc4.number_input("4. 안전/유동 (%)", value=0.0, min_value=0.0, max_value=100.0, step=1.0)
    tgt_safe_fixed = rc5.number_input("5. 안전/고정 (%)", value=float(fixed_pct), disabled=True, format="%.1f")
    
    total_tgt_group = round(tgt_super + tgt_risk + tgt_neutral + tgt_safe_liquid + fixed_pct, 1)
    
    if abs(total_tgt_group - 100.0) > 0.1:
        st.warning(f"⚠️ 1단계 비중 합계가 100%가 되어야 합니다. (현재 합계: {total_tgt_group}%)")
    else:
        st.success("✅ 1단계 설정 완료! 아래 2단계 표에서 각 열의 제목을 클릭하여 정렬해 보세요.")
        st.divider()
        st.subheader("🔬 2단계: 개별 종목 세부 비중 및 액션 플랜 (매매 수량 계산)")
        
        risk_num_map = {"초고위험": "1. 초고위험", "위험": "2. 위험", "중립": "3. 중립", "안전": "4. 안전(유동)"}
        rebal_items = []
        
        for item in stock_display_data:
            rebal_items.append({
                "자산군": risk_num_map.get(item['리스크'], "기타"), 
                "종목명": item['종목명'], 
                "티커": item['티커'], 
                "현재 금액(원)": int(item['평가금액']), 
                "현재가(참고용)": item['현재가(원)'] 
            })
        
        for sav in st.session_state['savings']:
            bank_type = sav.get('종류', '적금')
            grp_name = "5. 안전(고정)" if bank_type in ["적금", "주택청약"] else "4. 안전(유동)"
            rebal_items.append({
                "자산군": grp_name, "종목명": f"[{bank_type}] {sav.get('상품명', '은행자산')}", 
                "티커": "SAVING",
                "현재 금액(원)": int(sav.get('월납입액', 0) * sav.get('현재회차', 0)),
                "현재가(참고용)": 0
            })
            
        rebal_df = pd.DataFrame(rebal_items)
        
        if not rebal_df.empty and grand_total > 0:
            rebal_df['현재 비중(%)'] = (rebal_df['현재 금액(원)'] / grand_total * 100).round(1)
            target_map = {"1. 초고위험": tgt_super, "2. 위험": tgt_risk, "3. 중립": tgt_neutral, "4. 안전(유동)": tgt_safe_liquid, "5. 안전(고정)": fixed_pct}
            
            default_targets = []
            for idx, row in rebal_df.iterrows():
                grp = row['자산군']
                if grp == "5. 안전(고정)":
                    default_targets.append(row['현재 비중(%)']) 
                else:
                    grp_tgt = target_map.get(grp, 0)
                    grp_curr_sum = rebal_df[rebal_df['자산군'] == grp]['현재 금액(원)'].sum()
                    val = (row['현재 금액(원)'] / grp_curr_sum) * grp_tgt if grp_curr_sum > 0 else (grp_tgt / len(rebal_df[rebal_df['자산군'] == grp]) if len(rebal_df[rebal_df['자산군'] == grp]) > 0 else 0)
                    default_targets.append(round(val, 1))
                
            rebal_df['💡 목표 비중(%)'] = default_targets
            
            def highlight_risk(val):
                color = ''
                if val == '1. 초고위험': color = '#FFCDD2'
                elif val == '2. 위험': color = '#FFE0B2'
                elif val == '3. 중립': color = '#BBDEFB'
                elif val == '4. 안전(유동)': color = '#C8E6C9'
                elif val == '5. 안전(고정)': color = '#EEEEEE'
                return f'background-color: {color}'
            
            try: styled_rebal_df = rebal_df.drop(columns=['현재가(참고용)', '티커']).style.map(highlight_risk, subset=['자산군'])
            except: styled_rebal_df = rebal_df.drop(columns=['현재가(참고용)', '티커']).style.applymap(highlight_risk, subset=['자산군'])
            
            edited_df = st.data_editor(
                styled_rebal_df,
                column_config={
                    "자산군": st.column_config.TextColumn("자산군⬇️", disabled=True),
                    "종목명": st.column_config.TextColumn("종목명", disabled=True),
                    "현재 금액(원)": st.column_config.NumberColumn("현재 금액(원)", format="%d", disabled=True),
                    "현재 비중(%)": st.column_config.NumberColumn("현재 비중(%)", disabled=True),
                    "💡 목표 비중(%)": st.column_config.NumberColumn("💡 목표 비중(%)", min_value=0.0, max_value=100.0, step=0.1)
                },
                use_container_width=True, hide_index=True
            )
            
            all_valid = True
            for grp in ["1. 초고위험", "2. 위험", "3. 중립", "4. 안전(유동)", "5. 안전(고정)"]:
                grp_tgt = target_map[grp]
                grp_sum = edited_df[edited_df['자산군'] == grp]['💡 목표 비중(%)'].sum()
                if round(grp_tgt - grp_sum, 1) != 0 and grp != "5. 안전(고정)": all_valid = False
            
            if not all_valid:
                st.warning("⚠️ 각 그룹의 '2단계 합계'가 '1단계 목표'와 정확히 일치하도록 조절해 주세요.")
            else:
                st.success("🎉 완벽합니다! 최종 리밸런싱 액션 플랜(매매 수량 포함)이 생성되었습니다.")
                edited_df['목표 금액(원)'] = (grand_total * (edited_df['💡 목표 비중(%)'] / 100)).astype(int)
                edited_df['차액'] = edited_df['목표 금액(원)'] - edited_df['현재 금액(원)']
                edited_df['현재가'] = rebal_df['현재가(참고용)'] 
                edited_df['티커'] = rebal_df['티커']
                
                # 가상화폐 소수점 정밀 계산 로직 유지
                def get_action_and_shares(row):
                    if row['자산군'] == "5. 안전(고정)": return "🔒 고정", "-"
                    diff = row['차액']
                    price = row['현재가']
                    is_crypto = row['티커'].startswith("KRW-")
                    
                    if diff > 10000:
                        if price > 0:
                            shares = f" (약 {diff/price:,.2f}개)" if is_crypto else f" (약 {int(diff/price):,}주)"
                        else: shares = ""
                        return f"🟢 추가 매수 (+{diff:,.0f}원)", shares
                    elif diff < -10000:
                        if price > 0:
                            shares = f" (약 {abs(diff)/price:,.2f}개)" if is_crypto else f" (약 {int(abs(diff)/price):,}주)"
                        else: shares = ""
                        return f"🔴 부분 매도 ({abs(diff):,.0f}원)", shares
                    return "유지", "-"
                    
                edited_df[['액션 플랜', '매매 수량 가이드']] = edited_df.apply(get_action_and_shares, axis=1, result_type='expand')
                
                final_display = edited_df[['자산군', '종목명', '현재 금액(원)', '목표 금액(원)', '액션 플랜', '매매 수량 가이드']]
                try: final_styled_df = final_display.style.map(highlight_risk, subset=['자산군']).format({"현재 금액(원)": "{:,.0f}", "목표 금액(원)": "{:,.0f}"})
                except: final_styled_df = final_display.style.applymap(highlight_risk, subset=['자산군']).format({"현재 금액(원)": "{:,.0f}", "목표 금액(원)": "{:,.0f}"})
                    
                st.dataframe(final_styled_df, hide_index=True, use_container_width=True)