import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import yfinance as yf
from datetime import datetime
import os
import requests
from bs4 import BeautifulSoup

# ==========================================
# 1. 앱 기본 설정 & 모바일 최적화 UI
# ==========================================
st.set_page_config(page_title="My Asset Hub V25", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem; padding-left: 1rem; padding-right: 1rem; }
    p, .stMarkdown, div[data-testid="stText"] { font-size: 1.1rem !important; }
    .stMetric label { font-size: 1rem !important; }
    .stMetric value { font-size: 1.8rem !important; }
    .stDataFrame { font-size: 1rem !important; }
    .goal-red { color: #E74C3C; font-weight: 900; font-size: 1.4rem; }
    .goal-green { color: #2ECC71; font-weight: 900; font-size: 1.4rem; }
    </style>
    """, unsafe_allow_html=True)

STOCKS_FILE = 'my_stocks.csv'
SAVINGS_FILE = 'my_savings.csv'
HISTORY_FILE = 'asset_history.csv'
CONFIG_FILE = 'app_config.csv'

def load_data(file_name):
    if os.path.exists(file_name): return pd.read_csv(file_name).to_dict('records')
    return []
def save_data(data, file_name):
    pd.DataFrame(data).to_csv(file_name, index=False)

if 'stocks' not in st.session_state: st.session_state['stocks'] = load_data(STOCKS_FILE)
if 'savings' not in st.session_state: st.session_state['savings'] = load_data(SAVINGS_FILE)
if 'config' not in st.session_state: 
    cfg = load_data(CONFIG_FILE)
    st.session_state['config'] = cfg[0] if cfg else {"target_asset": 1000000000}

# ==========================================
# 2. 데이터 수집 엔진 (3중 우회 방어막 적용)
# ==========================================
@st.cache_data(ttl=600)
def get_exchange_rate():
    try:
        url = "https://finance.naver.com/marketindex/exchangeDetail.naver?marketindexCd=FX_USDKRW"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        return float(soup.select_one('.no_today .value').text.replace(',', ''))
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
        url = f"https://api.upbit.com/v1/ticker?markets={market}"
        return requests.get(url).json()[0]['trade_price'], []
    except: return 0, []

def verify_and_get_ticker(input_val):
    input_val = input_val.strip()
    upper_val = input_val.upper()
    
    # 강력한 위장 헤더 (스트림릿 클라우드 차단 우회용)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        'Referer': 'https://finance.naver.com/'
    }
    
    # 0. 코인 및 직접 티커 입력 검사
    coin_map = {"비트코인": "KRW-BTC", "BTC": "KRW-BTC", "이더리움": "KRW-ETH", "ETH": "KRW-ETH"}
    for key, val in coin_map.items():
        if key in upper_val: return val, val.replace("KRW-", "")
    if upper_val.startswith("KRW-"): return upper_val, upper_val.replace("KRW-", "")
    
    if len(upper_val) == 6 and upper_val.isalnum():
        for suffix in [".KS", ".KQ"]:
            try:
                if not yf.Ticker(upper_val + suffix).history(period="1d").empty: 
                    return upper_val + suffix, yf.Ticker(upper_val + suffix).info.get('shortName', upper_val)
            except: pass
    try:
        if not yf.Ticker(upper_val).history(period="1d").empty: 
            return upper_val, yf.Ticker(upper_val).info.get('shortName', upper_val)
    except: pass

    # 1. 1차 시도: 네이버 자동완성 API (가장 정확하고 빠름)
    try:
        url_ac = f"https://ac.finance.naver.com/ac?q={input_val}&q_enc=utf-8&st=111&frm=stock&r_format=json&r_enc=utf-8&r_unicode=0&t_koreng=1&req=1"
        res_ac = requests.get(url_ac, headers=headers, timeout=5).json()
        if res_ac.get('items') and len(res_ac['items'][0]) > 0:
            kor_name = res_ac['items'][0][0][0][0]
            ticker_code = res_ac['items'][0][0][1][0]
            for suffix in [".KS", ".KQ"]:
                try:
                    if not yf.Ticker(ticker_code + suffix).history(period="1d").empty:
                        return ticker_code + suffix, kor_name
                except: pass
    except: pass

    # 2. 2차 시도: 네이버 검색 페이지 크롤링 (API 차단 시 우회)
    try:
        url_search = f"https://finance.naver.com/search/searchList.naver?query={input_val}"
        res_search = requests.get(url_search, headers=headers, timeout=5)
        soup = BeautifulSoup(res_search.text, 'html.parser')
        first_row = soup.select_one('.tbl_search tbody tr')
        if first_row:
            a_tag = first_row.select_one('td.tit a')
            if a_tag:
                ticker_code = a_tag['href'].split('code=')[-1]
                kor_name = a_tag.text.strip()
                for suffix in [".KS", ".KQ"]:
                    try:
                        if not yf.Ticker(ticker_code + suffix).history(period="1d").empty:
                            return ticker_code + suffix, kor_name
                    except: pass
    except: pass

    # 3. 3차 시도: 야후 파이낸스 글로벌 검색 API (해외 주식 및 최후의 수단)
    try:
        url_yahoo = f"https://query2.finance.yahoo.com/v1/finance/search?q={input_val}"
        res_yahoo = requests.get(url_yahoo, headers=headers, timeout=5).json()
        if 'quotes' in res_yahoo and len(res_yahoo['quotes']) > 0:
            for q in res_yahoo['quotes']:
                if q.get('quoteType') in ['EQUITY', 'ETF']:
                    return q['symbol'], q.get('shortname', input_val)
            return res_yahoo['quotes'][0]['symbol'], res_yahoo['quotes'][0].get('shortname', input_val)
    except: pass
    
    return None, None

exchange_rate = get_exchange_rate()

# ==========================================
# ⬅️ 사이드바 & 자산 추가 로직
# ==========================================
st.sidebar.title("🛠️ 컨트롤러")

with st.sidebar.expander("⚙️ 목표 자산 설정", expanded=False):
    current_tgt = int(st.session_state['config'].get('target_asset', 1000000000))
    new_target_str = st.text_input("목표 금액 (원)", value=f"{current_tgt:,}")
    if st.button("업데이트"):
        try:
            st.session_state['config']['target_asset'] = int(new_target_str.replace(",", ""))
            save_data([st.session_state['config']], CONFIG_FILE)
            st.rerun()
        except: st.error("숫자만 입력!")

st.sidebar.markdown("### ➕ 투자 자산 추가")
asset_input = st.sidebar.text_input("🔍 종목/티커 검색", placeholder="예: 삼성전자, 카카오, AAPL")
# [롤백 완료] 네이버 주식창 하이퍼링크 복구
st.sidebar.markdown("[👉 종목코드 찾기 (네이버 주식창)](https://finance.naver.com/)", unsafe_allow_html=True)

if asset_input:
    with st.spinner("종목 검색 중 (최대 5초 소요)..."):
        valid_ticker, valid_name = verify_and_get_ticker(asset_input)
    if valid_ticker:
        st.sidebar.success(f"✅ {valid_name} ({valid_ticker})")
        is_crypto = valid_ticker.startswith("KRW-")
        is_foreign = not (valid_ticker.endswith(".KS") or valid_ticker.endswith(".KQ") or is_crypto)
        
        existing_idx = next((i for i, s in enumerate(st.session_state['stocks']) if s.get('티커') == valid_ticker), None)
        btn_label = "➕ 물타기/불타기 합산" if existing_idx is not None else "투자 자산 저장"
        
        currency_label = "원 ₩" if (is_crypto or not is_foreign) else "달러 $"
        new_price = st.sidebar.number_input(f"매수 단가 ({currency_label})", min_value=0, step=1000, format="%d")
        new_qty = st.sidebar.number_input("보유 수량", min_value=0.0, step=0.01)
        risk_level = st.sidebar.selectbox("리스크 분류", ["초고위험 (코인/레버리지)", "위험 (개별주식)", "중립 (지수ETF)", "안전 (금/국채)"])
        
        if st.sidebar.button(btn_label, use_container_width=True):
            if existing_idx is not None:
                old = st.session_state['stocks'][existing_idx]
                old_p = old.get('매수평단가', 0)
                old_q = old.get('보유수량', 0)
                final_qty = old_q + new_qty
                final_price = ((old_p * old_q) + (new_price * new_qty)) / final_qty if final_qty > 0 else 0
                st.session_state['stocks'][existing_idx].update({'매수평단가': final_price, '보유수량': final_qty})
            else:
                st.session_state['stocks'].append({"종목명": valid_name, "티커": valid_ticker, "매수평단가": new_price, "보유수량": new_qty, "해외여부": is_foreign, "리스크": risk_level.split(" ")[0]})
            save_data(st.session_state['stocks'], STOCKS_FILE)
            st.rerun()
    else:
        st.sidebar.error("⚠️ 검색 실패. 일시적인 차단일 수 있으니 티커(예: 005930.KS)를 직접 입력해주세요.")

with st.sidebar.expander("🏦 은행 자산 추가", expanded=False):
    bank_type = st.selectbox("종류", ["적금", "주택청약", "예금", "파킹통장"])
    sav_name = st.text_input("통장이름")
    sav_monthly = st.number_input("월 납입액", min_value=0, step=10000, format="%d")
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
today_str = datetime.now().strftime('%Y-%m-%d')

port_group = {"가상화폐": 0, "해외 주식": 0, "국내 주식": 0} 
risk_group = {"초고위험": 0, "위험": 0, "중립": 0, "안전": 0}
stock_display = []
total_buy = 0 

for idx, stock in enumerate(st.session_state['stocks']):
    ticker = stock.get('티커', '')
    is_crypto = ticker.startswith("KRW-")
    is_foreign = stock.get('해외여부', False)
    buy_p = stock.get('매수평단가', 0)
    qty = stock.get('보유수량', 0)
    
    if is_crypto:
        curr, _ = get_upbit_data(ticker)
        buy_amt = buy_p * qty
    else:
        curr, _ = get_stock_data(ticker)
        curr = curr * exchange_rate if is_foreign else curr
        buy_amt = buy_p * qty * (exchange_rate if is_foreign else 1)
    
    eval_amt = curr * qty
    total_buy += buy_amt
    
    if is_crypto: port_group["가상화폐"] += eval_amt
    elif is_foreign: port_group["해외 주식"] += eval_amt
    else: port_group["국내 주식"] += eval_amt
        
    risk_cat = stock.get('리스크', '위험')
    if risk_cat in risk_group: risk_group[risk_cat] += eval_amt
    
    profit_r = (eval_amt - buy_amt) / buy_amt * 100 if buy_amt > 0 else 0
    stock_display.append({
        "ID": idx, "종목명": stock.get('종목명', 'Unknown'), "티커": ticker, 
        "매수": buy_amt, "평가": eval_amt, "수익률": profit_r, 
        "리스크": risk_cat, "현재가": curr, "해외": is_foreign,
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
    principal = sav_monthly * sav_tot
    
    total_sav_val += amt
    total_buy += amt
    total_bank_principal += principal
    if bank_type in ["적금", "주택청약"]: fixed_sav_val += amt

grand_total = sum(port_group.values()) + total_sav_val
risk_group["안전"] += total_sav_val

history_df = pd.DataFrame(load_data(HISTORY_FILE)) if load_data(HISTORY_FILE) else pd.DataFrame(columns=["날짜", "총자산"])
if grand_total > 0:
    if not history_df.empty and today_str in history_df['날짜'].values:
        history_df.loc[history_df['날짜'] == today_str, '총자산'] = grand_total
    else:
        history_df = pd.concat([history_df, pd.DataFrame([{"날짜": today_str, "총자산": grand_total}])], ignore_index=True)
    save_data(history_df.to_dict('records'), HISTORY_FILE)

target = st.session_state['config'].get('target_asset', 1000000000)
achieved_pct = (grand_total / target * 100) if target > 0 else 0

if achieved_pct < 100:
    rem_pct = 100.0 - achieved_pct
    status_html = f"<span class='goal-red'>목표까지 {rem_pct:.1f}% 남았습니다! 🔥</span>"
else:
    excess_pct = achieved_pct - 100.0
    status_html = f"<span class='goal-green'>🎉 목표를 {excess_pct:.1f}% 초과 달성하였습니다! 🎉</span>"

st.markdown(f"### 🏆 목표 자산 ({target:,.0f}원) 현황")
st.markdown(status_html, unsafe_allow_html=True)
st.progress(min(achieved_pct / 100, 1.0))

c1, c2, c3 = st.columns(3)
c1.metric("총 자산", f"{grand_total:,.0f}원")
c2.metric("매수 원금", f"{total_buy:,.0f}원")
c3.metric("수익금", f"{grand_total-total_buy:,.0f}원", f"{(grand_total-total_buy)/total_buy*100:.1f}%" if total_buy>0 else "0%")

st.markdown("---")

tab1, tab2, tab3 = st.tabs(["📊 대시보드", "📋 자산 관리 (순서 변경)", "⚖️ 리밸런싱 (3-Step)"])

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
        risk_labels = ["초고위험", "위험", "중립", "안전"]
        risk_vals = [risk_group["초고위험"], risk_group["위험"], risk_group["중립"], risk_group["안전"]]
        fig2 = go.Figure(data=[go.Pie(labels=risk_labels, values=risk_vals, hole=.4, sort=False, direction='clockwise', marker_colors=['#E74C3C','#F39C12','#3498DB','#2ECC71'])])
        fig2.update_traces(textposition='inside', textinfo='percent', textfont_size=16) 
        fig2.update_layout(margin=dict(l=5, r=5, t=10, b=10), height=300, showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5))
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader("🚀 자산 성장 타임라인")
    if not history_df.empty:
        time_view = st.radio("보기 옵션", ["일별", "월별", "연별"], horizontal=True)
        history_df['날짜'] = pd.to_datetime(history_df['날짜'])
        min_date = history_df['날짜'].min()
        max_date = pd.to_datetime(today_str)
        if pd.notnull(min_date):
            idx_dates = pd.date_range(min_date, max_date)
            plot_df = history_df.set_index('날짜').reindex(idx_dates).ffill().reset_index()
            plot_df.rename(columns={'index': '날짜'}, inplace=True)
        else:
            plot_df = history_df.copy()
            
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
    st.subheader(f"📈 투자 자산 내역 (총 매수: {total_stock_buy:,.0f}원 | 총 평가: {total_stock_eval:,.0f}원)")
    st.caption("💡 오른쪽 🔼/🔽 버튼을 눌러 원하는 순서대로 자산을 정렬할 수 있습니다.")
    
    for idx, item in enumerate(stock_display):
        c_i, c_up, c_dn, c_e, c_d = st.columns([5, 0.7, 0.7, 0.7, 0.7])
        with c_i:
            profit_sign = "🔥" if item['수익률'] > 0 else "❄️"
            st.markdown(f"**{item['종목명']} ({item['티커']})** | 등급: **[{item['리스크']}]** | {profit_sign} **{item['수익률']:.2f}%**")
            cur_sym = "$" if item['해외'] and not item['티커'].startswith("KRW-") else "₩"
            st.caption(f"↳ 매수단가: **{item['매수평단가']:,.2f}{cur_sym}** | 수량: **{item['보유수량']:.2f}개**")
        
        with c_up:
            if st.button("🔼", key=f"up_{idx}") and idx > 0:
                st.session_state['stocks'][idx-1], st.session_state['stocks'][idx] = st.session_state['stocks'][idx], st.session_state['stocks'][idx-1]
                save_data(st.session_state['stocks'], STOCKS_FILE); st.rerun()
        with c_dn:
            if st.button("🔽", key=f"dn_{idx}") and idx < len(st.session_state['stocks'])-1:
                st.session_state['stocks'][idx+1], st.session_state['stocks'][idx] = st.session_state['stocks'][idx], st.session_state['stocks'][idx+1]
                save_data(st.session_state['stocks'], STOCKS_FILE); st.rerun()
        with c_e:
            if st.button("✏️", key=f"e_{idx}"): st.session_state[f"em_{idx}"] = not st.session_state.get(f"em_{idx}", False)
        with c_d:
            if st.button("🗑️", key=f"d_{idx}"): st.session_state['stocks'].pop(idx); save_data(st.session_state['stocks'], STOCKS_FILE); st.rerun()
            
        if st.session_state.get(f"em_{idx}", False):
            new_p = st.number_input("평단가", value=float(st.session_state['stocks'][idx].get('매수평단가', 0)), key=f"np_{idx}")
            new_q = st.number_input("수량", value=float(st.session_state['stocks'][idx].get('보유수량', 0)), key=f"nq_{idx}")
            if st.button("저장", key=f"sv_{idx}"):
                st.session_state['stocks'][idx].update({'매수평단가': new_p, '보유수량': new_q})
                save_data(st.session_state['stocks'], STOCKS_FILE); st.rerun()
                
    st.divider()
    st.subheader(f"🏦 은행 자산 내역 (총 원금: {total_bank_principal:,.0f}원)")
    
    for idx, sav in enumerate(st.session_state['savings']):
        c_i, c_up, c_dn, c_e, c_d = st.columns([5, 0.7, 0.7, 0.7, 0.7])
        with c_i:
            bank_type = sav.get('종류', '적금')
            principal = sav.get('월납입액', 0) * sav.get('총회차', 1)
            rate = sav.get('이율', 3.0)
            exp_int = principal * (rate / 100) * ((sav.get('총회차', 1) + 1) / 2 / 12 if bank_type == "적금" else sav.get('총회차', 1) / 12)
            st.markdown(f"**[{bank_type}] {sav.get('상품명', '이름없음')}** (연 **{rate}%**) | 만기 시 예상 이자: **+ {exp_int:,.0f}원**")
            
            c_month = sav.get('현재회차', 0)
            t_month = sav.get('총회차', 1)
            rem_m = t_month - c_month
            if rem_m <= 0:
                st.caption("↳ 🎉 **만기 달성!** 축하합니다!")
                st.progress(1.0)
            else:
                st.caption(f"↳ 총 {t_month}개월 중 **{c_month}개월 차** (남음: **{rem_m}개월**)")
                st.progress(min(1.0, max(0.0, c_month / t_month if t_month > 0 else 0)))
                
        with c_up:
            if st.button("🔼", key=f"sup_{idx}") and idx > 0:
                st.session_state['savings'][idx-1], st.session_state['savings'][idx] = st.session_state['savings'][idx], st.session_state['savings'][idx-1]
                save_data(st.session_state['savings'], SAVINGS_FILE); st.rerun()
        with c_dn:
            if st.button("🔽", key=f"sdn_{idx}") and idx < len(st.session_state['savings'])-1:
                st.session_state['savings'][idx+1], st.session_state['savings'][idx] = st.session_state['savings'][idx], st.session_state['savings'][idx+1]
                save_data(st.session_state['savings'], SAVINGS_FILE); st.rerun()
        with c_e:
            if st.button("✏️", key=f"es_{idx}"): st.session_state[f"esm_{idx}"] = not st.session_state.get(f"esm_{idx}", False)
        with c_d:
            if st.button("🗑️", key=f"ds_{idx}"): st.session_state['savings'].pop(idx); save_data(st.session_state['savings'], SAVINGS_FILE); st.rerun()
            
        if st.session_state.get(f"esm_{idx}", False):
            c_e1, c_e2, c_e3, c_e4 = st.columns(4)
            new_m = c_e1.number_input("월 납입액", value=int(sav.get('월납입액', 0)), step=10000, key=f"sm_{idx}")
            new_c = c_e2.number_input("현재 회차", value=int(sav.get('현재회차', 1)), step=1, key=f"sc_{idx}")
            new_r = c_e3.number_input("이율(%)", value=float(sav.get('이율', 3.0)), step=0.1, key=f"sr_{idx}")
            if c_e4.button("✔️ 저장", key=f"ssv_{idx}"):
                st.session_state['savings'][idx].update({'월납입액': new_m, '현재회차': new_c, '이율': new_r})
                st.session_state[f"esm_{idx}"] = False
                save_data(st.session_state['savings'], SAVINGS_FILE); st.rerun()

with tab3:
    # --- [Step 1: 그룹 설정] ---
    st.subheader("⚖️ 1단계: 그룹별 목표 설정")
    fixed_p = round(fixed_sav_val/grand_total*100, 1) if grand_total>0 else 0
    st.info(f"🔒 고정 자산(적금/청약) 비중: **{fixed_p}%**")
    
    rcols = st.columns(5)
    t1 = rcols[0].number_input("1.초고위험", value=0.0, step=1.0)
    t2 = rcols[1].number_input("2.위험", value=0.0, step=1.0)
    t3 = rcols[2].number_input("3.중립", value=0.0, step=1.0)
    t4 = rcols[3].number_input("4.안전(유동)", value=0.0, step=1.0)
    t5 = rcols[4].number_input("5.안전(고정)", value=float(fixed_p), disabled=True)
    
    total_tgt_sum = round(t1 + t2 + t3 + t4 + float(fixed_p), 1)
    
    if abs(total_tgt_sum - 100.0) >= 0.2:
        st.warning(f"⚠️ 현재 1단계 합계: **{total_tgt_sum}%** 입니다. 정확히 100%가 되어야 2단계 세부 조율이 활성화됩니다.")
    else:
        st.success(f"✅ 1단계 완료: 비중 합계 100% 일치")
        st.divider()
        
        # --- [Step 2: 종목 세부 조율] ---
        st.subheader("🔬 2단계: 종목별 세부 조율")
        st.caption("1단계에서 설정한 자산군 비중 내에서, 각 종목의 세부 목표 비중을 조절하세요.")
        
        r_map = {"초고위험": "1. 초고위험", "위험": "2. 위험", "중립": "3. 중립", "안전": "4. 안전(유동)"}
        re_items = []
        for s in stock_display:
            re_items.append({"자산군": r_map.get(s['리스크'], "기타"), "종목명": s['종목명'], "현재금액": int(s['평가']), "현재가": s['현재가'], "티커": s['티커']})
        for sv in st.session_state['savings']:
            b_type = sv.get('종류', '적금')
            grp = "5. 안전(고정)" if b_type in ["적금", "주택청약"] else "4. 안전(유동)"
            re_items.append({"자산군": grp, "종목명": f"[{b_type}] {sv.get('상품명', '은행')}", "현재금액": int(sv.get('월납입액',0)*sv.get('현재회차',1)), "현재가": 0, "티커": "SAV"})
        
        rdf = pd.DataFrame(re_items)
        target_map = {"1. 초고위험": t1, "2. 위험": t2, "3. 중립": t3, "4. 안전(유동)": t4, "5. 안전(고정)": t5}
        
        def color_risk(val):
            colors = {'1. 초고위험': '#FFCDD2', '2. 위험': '#FFE0B2', '3. 중립': '#BBDEFB', '4. 안전(유동)': '#C8E6C9', '5. 안전(고정)': '#F5F5F5'}
            return f'background-color: {colors.get(val, "")}'

        if not rdf.empty:
            default_targets = []
            for idx, row in rdf.iterrows():
                grp = row['자산군']
                if grp == "5. 안전(고정)": default_targets.append(round(row['현재금액']/grand_total*100, 1) if grand_total>0 else 0)
                else:
                    grp_tgt = target_map.get(grp, 0)
                    grp_sum = rdf[rdf['자산군'] == grp]['현재금액'].sum()
                    val = (row['현재금액']/grp_sum)*grp_tgt if grp_sum > 0 else 0
                    default_targets.append(round(val, 1))
            rdf['💡 목표(%)'] = default_targets
            
            try: styled_rdf = rdf.drop(columns=['현재가', '티커']).style.map(color_risk, subset=['자산군'])
            except: styled_rdf = rdf.drop(columns=['현재가', '티커']).style.applymap(color_risk, subset=['자산군'])

            # 2단계 에디터 출력
            edited = st.data_editor(styled_rdf, use_container_width=True, hide_index=True,
                                   column_config={"💡 목표(%)": st.column_config.NumberColumn(min_value=0.0, max_value=100.0, step=0.1)})
            
            # 2단계 검증 로직 (1단계 비중과 일치하는지)
            is_step2_valid = True
            validation_msgs = []
            for grp, grp_tgt in target_map.items():
                if grp == "5. 안전(고정)": continue
                grp_sum = edited[edited['자산군'] == grp]['💡 목표(%)'].sum()
                diff = round(grp_tgt - grp_sum, 1)
                if abs(diff) > 0.1: # 소수점 오차 방어
                    is_step2_valid = False
                    validation_msgs.append(f"[{grp}] 1단계 목표 {grp_tgt}% 🆚 현재 조율합계 {grp_sum:.1f}% ({abs(diff):.1f}% {'부족' if diff > 0 else '초과'})")
            
            if not is_step2_valid:
                st.error("⚠️ 아래 자산군의 2단계 비중 합계를 1단계 목표와 똑같이 맞춰주세요.")
                for msg in validation_msgs:
                    st.write(f" - {msg}")
            else:
                st.success("✅ 자산군별 조율이 1단계 목표 비중과 완벽히 일치합니다.")
                
            # [핵심 수정] 3단계 버튼 도입
            if st.button("🚀 3단계: 최종 액션플랜 생성 및 적용", use_container_width=True, type="primary"):
                if is_step2_valid:
                    st.session_state['rebal_applied'] = True
                    st.session_state['edited_rebal_df'] = edited.copy()
                else:
                    st.error("2단계 비중을 모두 맞춘 후 버튼을 눌러주세요.")
            
            # --- [Step 3: 액션 플랜] ---
            if st.session_state.get('rebal_applied', False) and 'edited_rebal_df' in st.session_state:
                st.divider()
                st.subheader("🎯 3단계: 최종 리밸런싱 액션 플랜")
                final_edited = st.session_state['edited_rebal_df']
                
                final_edited['목표금액'] = (grand_total * (final_edited['💡 목표(%)'] / 100)).astype(int)
                final_edited['차액'] = final_edited['목표금액'] - final_edited['현재금액']
                final_edited['현재가'] = rdf['현재가']
                final_edited['티커'] = rdf['티커']
                
                def get_action(row):
                    if row['자산군'] == "5. 안전(고정)": return "🔒 유지", "-"
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
                display_df = final_edited[['자산군', '종목명', '현재금액', '목표금액', '액션', '수량가이드']]
                
                try: f_style = display_df.style.map(color_risk, subset=['자산군']).format({"현재금액": "{:,.0f}", "목표금액": "{:,.0f}"})
                except: f_style = display_df.style.applymap(color_risk, subset=['자산군']).format({"현재금액": "{:,.0f}", "목표금액": "{:,.0f}"})
                st.dataframe(f_style, hide_index=True, use_container_width=True)
