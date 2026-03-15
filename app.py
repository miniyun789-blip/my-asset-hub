import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import os
import requests
from bs4 import BeautifulSoup
import re
import FinanceDataReader as fdr

# ==========================================
# 1. 앱 기본 설정 & UI 스타일링
# ==========================================
st.set_page_config(page_title="My Asset Hub V34", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem; padding-left: 1rem; padding-right: 1rem; }
    p, .stMarkdown, div[data-testid="stText"] { font-size: 1.1rem !important; }
    .stMetric label { font-size: 1rem !important; }
    .stMetric value { font-size: 1.8rem !important; }
    .stDataFrame { font-size: 1rem !important; }
    .goal-red { color: #E74C3C; font-weight: 900; font-size: 1.4rem; }
    .goal-green { color: #2ECC71; font-weight: 900; font-size: 1.4rem; }
    .green-text { color: #2ECC71; font-size: 0.95em; margin-bottom: 10px; font-weight: 500; }
    </style>
    """, unsafe_allow_html=True)

STOCKS_FILE = 'my_stocks.csv'
SAVINGS_FILE = 'my_savings.csv'
HISTORY_FILE = 'asset_history.csv'
CONFIG_FILE = 'app_config.csv'

if 'edited_rebal_df' in st.session_state: del st.session_state['edited_rebal_df']
st.session_state['rebal_applied'] = False

def load_data(file_name):
    if os.path.exists(file_name): return pd.read_csv(file_name).to_dict('records')
    return []
def save_data(data, file_name):
    pd.DataFrame(data).to_csv(file_name, index=False)

if 'stocks' not in st.session_state: st.session_state['stocks'] = load_data(STOCKS_FILE)
if 'savings' not in st.session_state: st.session_state['savings'] = load_data(SAVINGS_FILE)
if 'config' not in st.session_state: 
    cfg = load_data(CONFIG_FILE)
    st.session_state['config'] = cfg[0] if cfg else {
        "target_asset": 1000000000, 
        "risk_levels": "초고위험,위험,중립,안전"
    }

active_risks = [r.strip() for r in st.session_state['config'].get('risk_levels', "초고위험,위험,중립,안전").split(',') if r.strip()]

def sort_assets():
    st.session_state['stocks'].sort(key=lambda x: active_risks.index(x.get('리스크', active_risks[0])) if x.get('리스크') in active_risks else 99)
    st.session_state['stocks'].sort(key=lambda x: x.get('매수평단가', 0) * x.get('보유수량', 0), reverse=True)
    save_data(st.session_state['stocks'], STOCKS_FILE)

# ==========================================
# 2. 시간(KST 03:00 기준) 및 수집 엔진
# ==========================================
kst_now = datetime.utcnow() + timedelta(hours=9)
if kst_now.hour < 3: logic_date_str = (kst_now - timedelta(days=1)).strftime('%Y-%m-%d')
else: logic_date_str = kst_now.strftime('%Y-%m-%d')

@st.cache_data(ttl=86400)
def load_market_data():
    dfs = []
    try:
        df_krx = fdr.StockListing('KRX')
        df_krx['시장'] = 'KRX'
        dfs.append(df_krx[['Code', 'Name', '시장']])
    except: pass
    try:
        df_etf = fdr.StockListing('ETF/KR')
        df_etf['시장'] = 'ETF/KR'
        dfs.append(df_etf[['Symbol', 'Name', '시장']].rename(columns={'Symbol':'Code'}))
    except: pass
    for mkt in ['NASDAQ', 'NYSE', 'AMEX']:
        try:
            df_us = fdr.StockListing(mkt)
            df_us['시장'] = mkt
            dfs.append(df_us[['Symbol', 'Name', '시장']].rename(columns={'Symbol':'Code'}))
        except: pass
    if dfs:
        total_df = pd.concat(dfs, ignore_index=True)
        total_df['Name'] = total_df['Name'].astype(str)
        total_df['Code'] = total_df['Code'].astype(str)
        return total_df
    return None

@st.cache_data(ttl=600)
def get_exchange_rate():
    try:
        url = "https://www.google.com/finance/quote/USD-KRW"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(res.text, 'html.parser')
        return float(soup.select_one('.YMlKec.fxKbKc').text.replace(',', ''))
    except: return 1350.0

@st.cache_data(ttl=300)
def get_price(ticker):
    if ticker.startswith("KRW-"):
        try: return requests.get(f"https://api.upbit.com/v1/ticker?markets={ticker}").json()[0]['trade_price']
        except: return 0.0
    
    clean_ticker = ticker.replace('.KS', '').replace('.KQ', '')
    df = load_market_data()
    markets_to_try = []
    if df is not None:
        match = df[df['Code'] == clean_ticker]
        if not match.empty:
            mkt = match.iloc[0]['시장']
            if mkt in ['KRX', 'ETF/KR']: markets_to_try = [f"{clean_ticker}:KRX", f"{clean_ticker}:KOSDAQ"]
            elif mkt in ['NASDAQ', 'NYSE', 'AMEX']: markets_to_try = [f"{clean_ticker}:{mkt}"]
    if not markets_to_try: markets_to_try = [f"{clean_ticker}:KRX", f"{clean_ticker}:NASDAQ", f"{clean_ticker}:NYSE", f"{clean_ticker}:NYSEARCA", f"{clean_ticker}:AMEX"]
        
    for gf_ticker in markets_to_try:
        try:
            res = requests.get(f"https://www.google.com/finance/quote/{gf_ticker}", headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
            if res.status_code == 200 and 'YMlKec fxKbKc' in res.text:
                soup = BeautifulSoup(res.text, 'html.parser')
                return float(soup.select_one('.YMlKec.fxKbKc').text.replace('₩', '').replace('$', '').replace(',', ''))
        except: pass
    return 0.0

exchange_rate = get_exchange_rate()

# ==========================================
# ⬅️ 사이드바 & 자산 추가 로직
# ==========================================
st.sidebar.title("🛠️ 컨트롤러")
st.sidebar.metric("💵 실시간 환율 (구글 기준)", f"{exchange_rate:,.2f} 원")

with st.sidebar.expander("⚙️ 시스템 및 목표 설정", expanded=False):
    current_tgt = int(st.session_state['config'].get('target_asset', 1000000000))
    new_target_str = st.text_input("목표 금액 (원)", value=f"{current_tgt:,}")
    if st.button("설정 업데이트"):
        try:
            st.session_state['config']['target_asset'] = int(new_target_str.replace(",", ""))
            save_data([st.session_state['config']], CONFIG_FILE)
            st.rerun()
        except: st.error("금액은 숫자와 콤마만 입력해주세요!")

st.sidebar.markdown("### ➕ 투자 자산 추가")
asset_input = st.sidebar.text_input("🔍 종목/티커 검색", placeholder="예: 삼성전자, SCHD")
st.sidebar.markdown("[👉 구글 파이낸스 주식 검색](https://www.google.com/finance/?hl=ko)", unsafe_allow_html=True)

if asset_input:
    options = []
    coin_map = {"비트코인": "KRW-BTC", "BTC": "KRW-BTC", "이더리움": "KRW-ETH", "ETH": "KRW-ETH", "리플": "KRW-XRP", "솔라나": "KRW-SOL", "도지코인": "KRW-DOGE"}
    for k, v in coin_map.items():
        if k in asset_input.upper() or asset_input.upper() in k:
            options.append(f"[가상화폐] {k} ({v})")
            
    df_market = load_market_data()
    if df_market is not None:
        mask = df_market['Name'].str.contains(asset_input, case=False, na=False) | df_market['Code'].str.contains(asset_input, case=False, na=False)
        for _, r in df_market[mask].head(30).iterrows():
            options.append(f"[{r['시장']}] {r['Name']} ({r['Code']})")
            
    if re.match(r"^[A-Za-z0-9]+$", asset_input.strip()):
        upper_val = asset_input.strip().upper()
        options.append(f"[미국/해외 직접입력] {upper_val} ({upper_val})")
        
    options = list(dict.fromkeys(options))
            
    if options:
        selected_str = st.sidebar.selectbox("💡 정확한 종목을 선택하세요", options)
        match = re.match(r"\[(.*?)\] (.*) \((.*?)\)", selected_str)
        if match:
            sel_market, sel_name, sel_code = match.group(1), match.group(2), match.group(3)
            is_crypto = (sel_market == '가상화폐')
            is_foreign = sel_market in ['NASDAQ', 'NYSE', 'AMEX', '미국/해외 직접입력']
            
            existing_idx = next((i for i, s in enumerate(st.session_state['stocks']) if s.get('티커') == sel_code), None)
            btn_label = "➕ 물타기/불타기 합산" if existing_idx is not None else "투자 자산 저장"
            
            currency_label = "원 ₩" if (is_crypto or not is_foreign) else "달러 $"
            
            raw_price = st.sidebar.text_input(f"매수 단가 ({currency_label})", value="0")
            try: new_price = float(raw_price.replace(',', ''))
            except: new_price = 0.0
            
            new_qty = st.sidebar.number_input("보유 수량", min_value=0.0, step=0.01)
            risk_level = st.sidebar.selectbox("리스크 분류 선택", active_risks)
            
            if st.sidebar.button(btn_label, use_container_width=True):
                if existing_idx is not None:
                    old = st.session_state['stocks'][existing_idx]
                    final_qty = old.get('보유수량', 0) + new_qty
                    final_price = ((old.get('매수평단가', 0) * old.get('보유수량', 0)) + (new_price * new_qty)) / final_qty if final_qty > 0 else 0
                    st.session_state['stocks'][existing_idx].update({'매수평단가': final_price, '보유수량': final_qty})
                else:
                    st.session_state['stocks'].append({"종목명": sel_name, "티커": sel_code, "매수평단가": new_price, "보유수량": new_qty, "해외여부": is_foreign, "리스크": risk_level})
                sort_assets()
                st.rerun()
    else:
        st.sidebar.warning("⚠️ 검색 결과가 없습니다.")

# [핵심 수정 1] 리스크 분류를 자산 추가 하단으로 이동 및 엑셀형 편집기 도입
with st.sidebar.expander("⚙️ 리스크 분류 추가/수정"):
    st.caption("표 빈칸을 클릭해 항목을 추가하거나, 휴지통 아이콘을 눌러 삭제하세요.")
    risk_df = pd.DataFrame({"리스크 명칭": active_risks})
    edited_risk = st.data_editor(risk_df, num_rows="dynamic", use_container_width=True, hide_index=True)
    if st.button("✔️ 분류 항목 저장"):
        new_risks = edited_risk['리스크 명칭'].dropna().tolist()
        new_risks = [r.strip() for r in new_risks if r.strip()]
        if new_risks:
            st.session_state['config']['risk_levels'] = ",".join(new_risks)
            save_data([st.session_state['config']], CONFIG_FILE)
            st.rerun()
        else:
            st.error("최소 1개의 리스크 분류가 필요합니다.")

with st.sidebar.expander("🏦 은행 자산 추가", expanded=False):
    bank_type = st.selectbox("종류", ["적금", "주택청약", "예금", "파킹통장"])
    sav_name = st.text_input("통장이름")
    raw_monthly = st.text_input("월 납입액 (원)", value="1,000,000")
    try: sav_monthly = int(raw_monthly.replace(',', ''))
    except: sav_monthly = 0
    sav_curr = st.number_input("현재 회차", min_value=1)
    sav_total = st.number_input("총 만기 회차", min_value=1)
    sav_rate = st.number_input("연 이율 (%)", min_value=0.0, step=0.1, value=3.0)
    if st.button("은행 자산 저장", use_container_width=True):
        st.session_state['savings'].append({"종류": bank_type, "상품명": sav_name, "월납입액": sav_monthly, "현재회차": sav_curr, "총회차": sav_total, "이율": sav_rate})
        save_data(st.session_state['savings'], SAVINGS_FILE)
        st.rerun()

# ==========================================
# 🖥️ 메인 대시보드 연산
# ==========================================
st.title("💰 My Asset Hub")

risk_group = {r: 0 for r in active_risks}
risk_group["고정(은행)"] = 0
port_group = {"가상화폐": 0, "해외 주식": 0, "국내 주식": 0} 
stock_display = []
total_buy = 0 

for idx, stock in enumerate(st.session_state['stocks']):
    ticker = stock.get('티커', '')
    is_crypto = ticker.startswith("KRW-")
    is_foreign = stock.get('해외여부', False)
    buy_p = stock.get('매수평단가', 0)
    qty = stock.get('보유수량', 0)
    
    curr = get_price(ticker)
    
    if is_crypto: buy_amt = buy_p * qty
    else:
        curr_krw = curr * exchange_rate if is_foreign else curr
        buy_amt = buy_p * qty * (exchange_rate if is_foreign else 1)
        curr = curr_krw 
        
    eval_amt = curr * qty
    total_buy += buy_amt
    
    if is_crypto: port_group["가상화폐"] += eval_amt
    elif is_foreign: port_group["해외 주식"] += eval_amt
    else: port_group["국내 주식"] += eval_amt
        
    risk_cat = stock.get('리스크', active_risks[0] if active_risks else '기타')
    if risk_cat in risk_group: risk_group[risk_cat] += eval_amt
    else: risk_group[risk_cat] = eval_amt
    
    profit_r = (eval_amt - buy_amt) / buy_amt * 100 if buy_amt > 0 else 0
    stock_display.append({
        "ID": idx, "종목명": stock.get('종목명', 'Unknown'), "티커": ticker, 
        "매수": buy_amt, "평가": eval_amt, "수익률": profit_r, 
        "리스크": risk_cat, "현재가": curr / exchange_rate if is_foreign else curr, "해외": is_foreign,
        "매수평단가": buy_p, "보유수량": qty
    })

total_sav_val = 0
fixed_sav_val = 0
total_bank_principal = 0

for sav in st.session_state['savings']:
    bank_type = sav.get('종류', '적금')
    sav_monthly = sav.get('월납입액', 0)
    sav_curr = sav.get('현재회차', 1)
    sav_tot = sav.get('총회차', 1)
    
    amt = sav_monthly * sav_curr
    total_sav_val += amt
    total_buy += amt
    total_bank_principal += (sav_monthly * sav_tot)
    if bank_type in ["적금", "주택청약"]: fixed_sav_val += amt

grand_total = sum(port_group.values()) + total_sav_val
risk_group["고정(은행)"] += total_sav_val

history_df = pd.DataFrame(load_data(HISTORY_FILE)) if load_data(HISTORY_FILE) else pd.DataFrame(columns=["날짜", "총자산"])
if grand_total > 0:
    if not history_df.empty and logic_date_str in history_df['날짜'].values:
        history_df.loc[history_df['날짜'] == logic_date_str, '총자산'] = grand_total
    else:
        history_df = pd.concat([history_df, pd.DataFrame([{"날짜": logic_date_str, "총자산": grand_total}])], ignore_index=True)
    save_data(history_df.to_dict('records'), HISTORY_FILE)

def get_risk_priority(r):
    try: return active_risks.index(r)
    except: return 999
stock_display.sort(key=lambda x: (get_risk_priority(x['리스크']), -x['평가']))

target = st.session_state['config'].get('target_asset', 1000000000)
achieved_pct = (grand_total / target * 100) if target > 0 else 0

if achieved_pct < 100: st.markdown(f"### 🏆 목표 ({target:,.0f}원) | <span class='goal-red'>{100-achieved_pct:.1f}% 남음 🔥</span>", unsafe_allow_html=True)
else: st.markdown(f"### 🏆 목표 ({target:,.0f}원) | <span class='goal-green'>🎉 {achieved_pct-100:.1f}% 초과 달성 🎉</span>", unsafe_allow_html=True)
st.progress(min(achieved_pct / 100, 1.0))

c1, c2, c3 = st.columns(3)
c1.metric("총 자산", f"{grand_total:,.0f}원")
c2.metric("매수 원금", f"{total_buy:,.0f}원")
c3.metric("수익금", f"{grand_total-total_buy:,.0f}원", f"{(grand_total-total_buy)/total_buy*100:.1f}%" if total_buy>0 else "0%")

st.markdown("---")

tab1, tab2, tab3 = st.tabs(["📊 대시보드", "📋 자산 관리", "⚖️ 커스텀 리밸런싱"])

# [핵심 수정 2] 오리지널 강렬한 원색 컬러 팔레트로 롤백
def get_risk_color(idx):
    palette = ['#E74C3C', '#F39C12', '#3498DB', '#2ECC71', '#9B59B6', '#1ABC9C', '#34495E']
    return palette[idx % len(palette)]

with tab1:
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.subheader("⚖️ 포트폴리오 비중")
        port_labels = ["가상화폐", "해외 주식", "국내 주식", "은행(안전)"]
        port_vals = [port_group["가상화폐"], port_group["해외 주식"], port_group["국내 주식"], total_sav_val]
        fig1 = go.Figure(data=[go.Pie(labels=port_labels, values=port_vals, hole=.4, sort=False, direction='clockwise', marker_colors=['#F39C12', '#9B59B6', '#3498DB', '#1ABC9C'])])
        fig1.update_traces(textposition='inside', textinfo='percent', textfont_size=16) 
        fig1.update_layout(margin=dict(l=5, r=5, t=10, b=10), height=300, showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5))
        st.plotly_chart(fig1, use_container_width=True)
        
    with col_p2:
        st.subheader("🛡️ 리스크 다각화")
        risk_labels = list(risk_group.keys())
        risk_vals = list(risk_group.values())
        risk_colors = [get_risk_color(i) if i < len(active_risks) else '#BDC3C7' for i in range(len(risk_labels))]
        fig2 = go.Figure(data=[go.Pie(labels=risk_labels, values=risk_vals, hole=.4, sort=False, direction='clockwise', marker_colors=risk_colors)])
        fig2.update_traces(textposition='inside', textinfo='percent', textfont_size=16) 
        fig2.update_layout(margin=dict(l=5, r=5, t=10, b=10), height=300, showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5))
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader("🚀 자산 성장 타임라인")
    if not history_df.empty:
        time_view = st.radio("보기 옵션", ["일별", "월별", "연별"], horizontal=True)
        history_df['날짜'] = pd.to_datetime(history_df['날짜'])
        min_date = history_df['날짜'].min()
        max_date = pd.to_datetime(logic_date_str)
        if pd.notnull(min_date):
            idx_dates = pd.date_range(min_date, max_date)
            plot_df = history_df.set_index('날짜').reindex(idx_dates).ffill().reset_index()
            plot_df.rename(columns={'index': '날짜'}, inplace=True)
        else: plot_df = history_df.copy()
            
        if time_view == "일별":
            fig_line = px.area(plot_df, x="날짜", y="총자산", markers=True, color_discrete_sequence=['#2E86C1'])
            fig_line.update_xaxes(tickformat="%m.%d", tickangle=-45)
        elif time_view == "월별":
            plot_df['날짜'] = plot_df['날짜'].dt.to_period('M').dt.to_timestamp()
            plot_df = plot_df.groupby('날짜')['총자산'].last().reset_index()
            fig_line = px.area(plot_df, x="날짜", y="총자산", markers=True, color_discrete_sequence=['#2E86C1'])
            fig_line.update_xaxes(tickmode='array', tickvals=plot_df['날짜'], tickformat="%y.%m", tickangle=-45)
        elif time_view == "연별":
            plot_df['날짜'] = plot_df['날짜'].dt.to_period('Y').dt.to_timestamp()
            plot_df = plot_df.groupby('날짜')['총자산'].last().reset_index()
            fig_line = px.area(plot_df, x="날짜", y="총자산", markers=True, color_discrete_sequence=['#2E86C1'])
            fig_line.update_xaxes(tickmode='array', tickvals=plot_df['날짜'], tickformat="%Y", tickangle=0)
            
        fig_line.update_layout(margin=dict(l=5, r=5, t=10, b=10), height=300, hovermode=False, dragmode=False)
        st.plotly_chart(fig_line, use_container_width=True, config={'staticPlot': True})

with tab2:
    total_stock_buy = sum(item['매수'] for item in stock_display)
    total_stock_eval = sum(item['평가'] for item in stock_display)
    st.subheader(f"📈 투자 자산 내역 (총 평가: {total_stock_eval:,.0f}원)")
    st.caption("💡 시스템이 자산 등급 순서 및 평가액 내림차순으로 자동 정렬합니다.")
    
    for item in stock_display:
        idx = item['ID']
        c_i, c_e, c_d = st.columns([6, 0.7, 0.7])
        with c_i:
            profit_sign = "🔥" if item['수익률'] > 0 else "❄️"
            st.markdown(f"**{item['종목명']} ({item['티커']})** | 등급: **[{item['리스크']}]** | {profit_sign} **{item['수익률']:.2f}%**")
            cur_sym = "$" if item['해외'] else "₩"
            # [핵심 수정 3] 초록색 폰트 강제 적용
            st.markdown(f"<div class='green-text'>↳ 💰 매수 평단가 (수수료 제외): <b>{item['매수평단가']:,.2f}{cur_sym}</b> | 수량: <b>{item['보유수량']:.2f}개</b> | 평가액: <b>{item['평가']:,.0f}원</b></div>", unsafe_allow_html=True)
        
        with c_e:
            if st.button("✏️", key=f"e_{idx}"): st.session_state[f"em_{idx}"] = not st.session_state.get(f"em_{idx}", False)
        with c_d:
            if st.button("🗑️", key=f"d_{idx}"): st.session_state['stocks'].pop(idx); save_data(st.session_state['stocks'], STOCKS_FILE); st.rerun()
            
        if st.session_state.get(f"em_{idx}", False):
            raw_p = st.text_input("평단가 변경", value=f"{st.session_state['stocks'][idx].get('매수평단가', 0):.2f}", key=f"np_{idx}")
            try: new_p = float(raw_p.replace(',', ''))
            except: new_p = 0.0
            new_q = st.number_input("수량 변경", value=float(st.session_state['stocks'][idx].get('보유수량', 0)), key=f"nq_{idx}")
            if st.button("저장", key=f"sv_{idx}"):
                st.session_state['stocks'][idx].update({'매수평단가': new_p, '보유수량': new_q})
                save_data(st.session_state['stocks'], STOCKS_FILE); st.rerun()
                
    st.divider()
    st.subheader(f"🏦 은행 자산 내역 (총 원금: {total_bank_principal:,.0f}원)")
    
    for idx, sav in enumerate(st.session_state['savings']):
        c_i, c_e, c_d = st.columns([6, 0.7, 0.7])
        with c_i:
            bank_type = sav.get('종류', '적금')
            principal = sav.get('월납입액', 0) * sav.get('총회차', 1)
            rate = sav.get('이율', 3.0)
            exp_int = principal * (rate / 100) * ((sav.get('총회차', 1) + 1) / 2 / 12 if bank_type == "적금" else sav.get('총회차', 1) / 12)
            st.markdown(f"**[{bank_type}] {sav.get('상품명', '이름없음')}** (연 **{rate}%**) | 원금: **{principal:,.0f}원**")
            
            c_month = sav.get('현재회차', 0)
            t_month = sav.get('총회차', 1)
            rem_m = t_month - c_month
            if rem_m <= 0:
                # [핵심 수정 3] 초록색 폰트 강제 적용
                st.markdown(f"<div class='green-text'>↳ 🎉 <b>만기 달성!</b> (예상 이자: <b>+ {exp_int:,.0f}원</b>)</div>", unsafe_allow_html=True)
                st.progress(1.0)
            else:
                st.markdown(f"<div class='green-text'>↳ 총 {t_month}개월 중 <b>{c_month}개월 차</b> (남음: <b>{rem_m}개월</b>)</div>", unsafe_allow_html=True)
                st.progress(min(1.0, max(0.0, c_month / t_month if t_month > 0 else 0)))
                
        with c_e:
            if st.button("✏️", key=f"es_{idx}"): st.session_state[f"esm_{idx}"] = not st.session_state.get(f"esm_{idx}", False)
        with c_d:
            if st.button("🗑️", key=f"ds_{idx}"): st.session_state['savings'].pop(idx); save_data(st.session_state['savings'], SAVINGS_FILE); st.rerun()
            
        if st.session_state.get(f"esm_{idx}", False):
            c_e1, c_e2, c_e3, c_e4 = st.columns(4)
            raw_m = c_e1.text_input("월 납입액", value=f"{sav.get('월납입액', 0)}", key=f"sm_{idx}")
            try: new_m = int(raw_m.replace(',', ''))
            except: new_m = 0
            new_c = c_e2.number_input("현재 회차", value=int(sav.get('현재회차', 1)), step=1, key=f"sc_{idx}")
            new_r = c_e3.number_input("이율(%)", value=float(sav.get('이율', 3.0)), step=0.1, key=f"sr_{idx}")
            if c_e4.button("✔️ 저장", key=f"ssv_{idx}"):
                st.session_state['savings'][idx].update({'월납입액': new_m, '현재회차': new_c, '이율': new_r})
                st.session_state[f"esm_{idx}"] = False
                save_data(st.session_state['savings'], SAVINGS_FILE); st.rerun()

with tab3:
    st.subheader("⚖️ 1단계: 동적 그룹별 목표 설정")
    fixed_p = round(fixed_sav_val/grand_total*100, 1) if grand_total>0 else 0
    st.info(f"🔒 고정 자산(적금/청약) 비중: **{fixed_p}%**")
    
    cols = st.columns(len(active_risks) + 1)
    tgt_weights = {}
    for i, r in enumerate(active_risks):
        tgt_weights[r] = cols[i].number_input(f"{i+1}. {r}", value=0.0, step=1.0)
    cols[-1].number_input(f"{len(active_risks)+1}. 고정(은행)", value=float(fixed_p), disabled=True)
    
    total_tgt_sum = round(sum(tgt_weights.values()) + float(fixed_p), 1)
    
    if abs(total_tgt_sum - 100.0) >= 0.1:
        st.warning(f"⚠️ 현재 1단계 합계: **{total_tgt_sum}%** 입니다. 정확히 100%가 되어야 2단계 세부 조율이 활성화됩니다.")
    else:
        st.success(f"✅ 1단계 완료: 비중 합계 100% 일치")
        st.divider()
        
        st.subheader("🔬 2단계: 종목별 세부 조율")
        re_items = []
        for s in stock_display:
            re_items.append({
                "자산군": s['리스크'], "종목명": s['종목명'], "현재금액_raw": int(s['평가']), 
                "수익률": s['수익률'], "현재가": s['현재가'], "티커": s['티커']
            })
        for sv in st.session_state['savings']:
            b_type = sv.get('종류', '적금')
            grp = "고정(은행)" if b_type in ["적금", "주택청약"] else active_risks[-1]
            re_items.append({
                "자산군": grp, "종목명": f"[{b_type}] {sv.get('상품명', '은행')}", 
                "현재금액_raw": int(sv.get('월납입액',0)*sv.get('현재회차',1)), "수익률": 0.0, "현재가": 0, "티커": "SAV"
            })
            
        existing_groups = set(item['자산군'] for item in re_items)
        for grp in active_risks:
            if grp not in existing_groups:
                re_items.append({
                    "자산군": grp, "종목명": "💡 신규 자산 배분 필요", "현재금액_raw": 0, 
                    "수익률": 0.0, "현재가": 0, "티커": "NEW"
                })
        
        rdf = pd.DataFrame(re_items)
        
        # [핵심 수정 2] 2단계 색상도 파스텔 원색 계열로 롤백 및 적용
        def highlight_matrix(df):
            bg_palette = ['#FFCDD2', '#FFE0B2', '#BBDEFB', '#C8E6C9', '#E1BEE7', '#D7CCC8']
            style_df = pd.DataFrame('', index=df.index, columns=df.columns)
            for i, row in df.iterrows():
                try: color_idx = active_risks.index(row['자산군'])
                except: color_idx = 99
                color = bg_palette[color_idx % len(bg_palette)] if color_idx != 99 else '#F5F5F5'
                style_df.iloc[i] = f'background-color: {color}'
            return style_df

        if not rdf.empty:
            rdf['sort_key'] = rdf['자산군'].apply(get_risk_priority)
            rdf.sort_values(by=['sort_key', '현재금액_raw'], ascending=[True, False], inplace=True)
            rdf.reset_index(drop=True, inplace=True)
            
            def format_amt_profit(row):
                if row['티커'] in ['SAV', 'NEW']: return f"{row['현재금액_raw']:,.0f}원"
                else:
                    sign = "+" if row['수익률'] > 0 else ""
                    return f"{row['현재금액_raw']:,.0f}원 ({sign}{row['수익률']:.2f}%)"
            rdf['현재 금액(수익률)'] = rdf.apply(format_amt_profit, axis=1)

            default_targets = []
            for idx, row in rdf.iterrows():
                grp = row['자산군']
                if grp == "고정(은행)": default_targets.append(round(row['현재금액_raw']/grand_total*100, 1) if grand_total>0 else 0)
                else:
                    grp_tgt = tgt_weights.get(grp, 0)
                    grp_sum = rdf[rdf['자산군'] == grp]['현재금액_raw'].sum()
                    val = (row['현재금액_raw']/grp_sum)*grp_tgt if grp_sum > 0 else 0
                    default_targets.append(round(val, 1))
            rdf['💡 목표(%)'] = default_targets
            
            display_cols = ['자산군', '종목명', '현재 금액(수익률)', '💡 목표(%)']
            styled_rdf = rdf[display_cols].style.apply(highlight_matrix, axis=None)

            edited = st.data_editor(styled_rdf, use_container_width=True, hide_index=True,
                                   column_config={"💡 목표(%)": st.column_config.NumberColumn(min_value=0.0, max_value=100.0, step=0.1)})
            
            is_step2_valid = True
            validation_msgs = []
            for grp, grp_tgt in tgt_weights.items():
                grp_sum = edited[edited['자산군'] == grp]['💡 목표(%)'].sum()
                diff = round(grp_tgt - grp_sum, 1)
                if abs(diff) > 0.1: 
                    is_step2_valid = False
                    validation_msgs.append(f"[{grp}] 1단계 목표 {grp_tgt}% 🆚 조율합계 {grp_sum:.1f}% ({abs(diff):.1f}% {'부족' if diff > 0 else '초과'})")
            
            if not is_step2_valid:
                st.error("⚠️ 아래 자산군의 2단계 비중 합계를 1단계 목표와 똑같이 맞춰주세요.")
                for msg in validation_msgs: st.write(f" - {msg}")
            else:
                st.success("✅ 자산군별 조율이 1단계 목표 비중과 완벽히 일치합니다.")
                
            if st.button("🚀 3단계: 최종 액션플랜 생성 및 적용", use_container_width=True, type="primary"):
                if is_step2_valid:
                    st.session_state['rebal_applied'] = True
                    calc_df = rdf.copy()
                    calc_df['💡 목표(%)'] = edited['💡 목표(%)'].values
                    st.session_state['edited_rebal_df'] = calc_df
                else:
                    st.error("2단계 비중을 모두 맞춘 후 버튼을 눌러주세요.")
            
            if st.session_state.get('rebal_applied', False) and 'edited_rebal_df' in st.session_state:
                st.divider()
                st.subheader("🎯 3단계: 최종 리밸런싱 액션 플랜")
                final_edited = st.session_state['edited_rebal_df']
                
                final_edited['목표금액'] = (grand_total * (final_edited['💡 목표(%)'] / 100)).astype(int)
                final_edited['차액'] = final_edited['목표금액'] - final_edited['현재금액_raw']
                
                def get_action(row):
                    if row['자산군'] == "고정(은행)": return "🔒 유지", "-"
                    d = row['차액']
                    p = row['현재가']
                    c = row['티커'].startswith("KRW-")
                    if d > 10000:
                        s = f" (약 {d/p:,.2f}개)" if (c and p > 0) else (f" (약 {int(d/p):,}주)" if p > 0 else "")
                        return f"🟢 매수 (+{d:,.0f}원)", s
                    elif d < -10000:
                        s = f" (약 {abs(d)/p:,.2f}개)" if (c and p > 0) else (f" (약 {int(abs(d)/p):,}주)" if p > 0 else "")
                        return f"🔴 매도 ({abs(d):,.0f}원)", s
                    return "유지", "-"
                    
                final_edited[['액션', '수량가이드']] = final_edited.apply(get_action, axis=1, result_type='expand')
                final_edited.rename(columns={'현재금액_raw': '현재금액(원)'}, inplace=True)
                display_df = final_edited[['자산군', '종목명', '현재금액(원)', '목표금액', '액션', '수량가이드']]
                
                try: f_style = display_df.style.apply(highlight_matrix, axis=None).format({"현재금액(원)": "{:,.0f}", "목표금액": "{:,.0f}"})
                except: f_style = display_df.style.apply(highlight_matrix, axis=None).format({"현재금액(원)": "{:,.0f}", "목표금액": "{:,.0f}"})
                st.dataframe(f_style, hide_index=True, use_container_width=True)
