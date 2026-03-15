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
import json

# ==========================================
# [중요] 구글 앱스 스크립트 웹 앱 URL 설정
# ==========================================
API_URL = "https://script.google.com/macros/s/AKfycbyCXNo6L5fBUD1ysDXGfGsSaEAVEZGXgqRBiL_U8vqyLhwJJN4ELeBa68ZNB6XSDWMI/exec"

# ==========================================
# 1. 앱 기본 설정 & UI 스타일링
# ==========================================
st.set_page_config(page_title="My Asset Hub V35", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem; padding-left: 1rem; padding-right: 1rem; }
    p, .stMarkdown, div[data-testid="stText"] { font-size: 1.1rem !important; }
    .stMetric label { font-size: 1rem !important; }
    .stMetric value { font-size: 1.8rem !important; }
    .goal-red { color: #E74C3C; font-weight: 900; font-size: 1.4rem; }
    .goal-green { color: #2ECC71; font-weight: 900; font-size: 1.4rem; }
    .green-text { color: #2ECC71; font-size: 0.95em; margin-bottom: 10px; font-weight: 500; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. 클라우드 데이터 동기화 엔진 (Sync Engine)
# ==========================================
def load_cloud_data(sheet_name):
    try:
        res = requests.get(f"{API_URL}?sheetName={sheet_name}", timeout=10)
        return res.json()
    except: return []

def save_cloud_data(data, sheet_name):
    try:
        payload = {"sheetName": sheet_name, "data": data}
        requests.post(API_URL, data=json.dumps(payload), timeout=10)
        return True
    except: return False

# 최초 실행 시 데이터 불러오기
if 'stocks' not in st.session_state: st.session_state['stocks'] = load_cloud_data('stocks')
if 'savings' not in st.session_state: st.session_state['savings'] = load_cloud_data('savings')
if 'config' not in st.session_state: 
    cfg = load_cloud_data('config')
    st.session_state['config'] = cfg[0] if cfg else {"target_asset": 1000000000, "risk_levels": "초고위험,위험,중립,안전"}

active_risks = [r.strip() for r in st.session_state['config'].get('risk_levels', "초고위험,위험,중립,안전").split(',') if r.strip()]

def sort_and_save():
    # 리스크 순서 정렬 가중치 부여
    def get_risk_weight(r):
        try: return active_risks.index(r)
        except: return 99
    
    # 정렬: 1순위 리스크 등급, 2순위 평가액(평단가*수량) 큰 순
    st.session_state['stocks'].sort(key=lambda x: (get_risk_weight(x.get('리스크')), -(float(x.get('매수평단가', 0)) * float(x.get('보유수량', 0)))))
    save_cloud_data(st.session_state['stocks'], 'stocks')
    save_cloud_data(st.session_state['savings'], 'savings')
    save_cloud_data([st.session_state['config']], 'config')

# ==========================================
# 3. 시간(KST 03:00 기준) 및 수집 엔진
# ==========================================
kst_now = datetime.utcnow() + timedelta(hours=9)
logic_date_str = (kst_now - timedelta(days=1)).strftime('%Y-%m-%d') if kst_now.hour < 3 else kst_now.strftime('%Y-%m-%d')

@st.cache_data(ttl=86400)
def load_market_data():
    dfs = []
    try:
        df_krx = fdr.StockListing('KRX'); df_krx['시장'] = 'KRX'; dfs.append(df_krx[['Code', 'Name', '시장']])
        df_etf = fdr.StockListing('ETF/KR'); df_etf['시장'] = 'ETF/KR'; dfs.append(df_etf[['Symbol', 'Name', '시장']].rename(columns={'Symbol':'Code'}))
        for mkt in ['NASDAQ', 'NYSE', 'AMEX']:
            df_us = fdr.StockListing(mkt); df_us['시장'] = mkt; dfs.append(df_us[['Symbol', 'Name', '시장']].rename(columns={'Symbol':'Code'}))
    except: pass
    return pd.concat(dfs, ignore_index=True) if dfs else None

@st.cache_data(ttl=600)
def get_exchange_rate():
    try:
        res = requests.get("https://www.google.com/finance/quote/USD-KRW", headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(res.text, 'html.parser')
        return float(soup.select_one('.YMlKec.fxKbKc').text.replace(',', ''))
    except: return 1350.0

@st.cache_data(ttl=300)
def get_price(ticker):
    if ticker.startswith("KRW-"):
        try: return requests.get(f"https://api.upbit.com/v1/ticker?markets={ticker}").json()[0]['trade_price']
        except: return 0.0
    clean_ticker = ticker.replace('.KS', '').replace('.KQ', '')
    markets = [f"{clean_ticker}:KRX", f"{clean_ticker}:KOSDAQ", f"{clean_ticker}:NASDAQ", f"{clean_ticker}:NYSE", f"{clean_ticker}:NYSEARCA"]
    for gf_ticker in markets:
        try:
            res = requests.get(f"https://www.google.com/finance/quote/{gf_ticker}", headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
            if 'YMlKec fxKbKc' in res.text:
                soup = BeautifulSoup(res.text, 'html.parser')
                return float(soup.select_one('.YMlKec.fxKbKc').text.replace('₩', '').replace('$', '').replace(',', ''))
        except: pass
    return 0.0

exchange_rate = get_exchange_rate()

# ==========================================
# 4. 사이드바 (컨트롤러)
# ==========================================
st.sidebar.title("🛠️ 컨트롤러")
st.sidebar.metric("💵 실시간 환율 (구글 기준)", f"{exchange_rate:,.2f} 원")

with st.sidebar.expander("⚙️ 시스템 및 목표 설정"):
    current_tgt = int(st.session_state['config'].get('target_asset', 1000000000))
    new_target_str = st.text_input("목표 금액 (원)", value=f"{current_tgt:,}")
    if st.button("목표 저장"):
        st.session_state['config']['target_asset'] = int(new_target_str.replace(",", ""))
        sort_and_save(); st.rerun()

st.sidebar.markdown("### ➕ 투자 자산 추가")
asset_input = st.sidebar.text_input("🔍 종목/티커 검색", placeholder="예: 삼성전자, SCHD")
if asset_input:
    options = []
    coin_map = {"비트코인": "KRW-BTC", "이더리움": "KRW-ETH", "리플": "KRW-XRP", "솔라나": "KRW-SOL"}
    for k, v in coin_map.items():
        if k in asset_input: options.append(f"[가상화폐] {k} ({v})")
    df_m = load_market_data()
    if df_m is not None:
        mask = df_m['Name'].str.contains(asset_input, case=False, na=False) | df_m['Code'].str.contains(asset_input, case=False, na=False)
        for _, r in df_m[mask].head(20).iterrows(): options.append(f"[{r['시장']}] {r['Name']} ({r['Code']})")
    if re.match(r"^[A-Za-z0-9]+$", asset_input.strip()):
        options.append(f"[미국/해외 직접입력] {asset_input.upper()} ({asset_input.upper()})")
    
    options = list(dict.fromkeys(options))
    if options:
        selected = st.sidebar.selectbox("💡 정확한 종목 선택", options)
        m = re.match(r"\[(.*?)\] (.*) \((.*?)\)", selected)
        if m:
            sel_market, sel_name, sel_code = m.group(1), m.group(2), m.group(3)
            curr_label = "원 ₩" if (sel_market == '가상화폐' or sel_market in ['KRX', 'ETF/KR']) else "달러 $"
            raw_p = st.sidebar.text_input(f"매수 단가 ({curr_label})", value="0")
            new_p = float(raw_p.replace(',', '')) if raw_p.replace(',', '').replace('.','').isdigit() else 0.0
            new_q = st.sidebar.number_input("보유 수량", min_value=0.0, step=0.01)
            risk_lv = st.sidebar.selectbox("리스크 분류 선택", active_risks)
            
            if st.sidebar.button("투자 자산 저장", use_container_width=True):
                existing = next((i for i, s in enumerate(st.session_state['stocks']) if s.get('티커') == sel_code), None)
                if existing is not None:
                    old = st.session_state['stocks'][existing]
                    final_q = old.get('보유수량', 0) + new_qty
                    final_p = ((old.get('매수평단가', 0) * old.get('보유수량', 0)) + (new_p * new_q)) / final_q if final_q > 0 else 0
                    st.session_state['stocks'][existing].update({'매수평단가': final_p, '보유수량': final_q})
                else:
                    st.session_state['stocks'].append({"종목명": sel_name, "티커": sel_code, "매수평단가": new_p, "보유수량": new_q, "해외여부": (curr_label == "달러 $"), "리스크": risk_lv})
                sort_and_save(); st.rerun()

with st.sidebar.expander("⚙️ 리스크 분류 추가/수정"):
    risk_df = pd.DataFrame({"리스크 명칭": active_risks})
    edited_risk = st.data_editor(risk_df, num_rows="dynamic", use_container_width=True, hide_index=True)
    if st.button("✔️ 분류 저장"):
        st.session_state['config']['risk_levels'] = ",".join(edited_risk['리스크 명칭'].dropna().tolist())
        sort_and_save(); st.rerun()

with st.sidebar.expander("🏦 은행 자산 추가"):
    b_type = st.selectbox("종류", ["적금", "주택청약", "예금", "파킹통장"])
    b_name = st.text_input("통장이름")
    raw_m = st.text_input("월 납입액 (원)", value="1,000,000")
    b_curr = st.number_input("현재 회차", min_value=1)
    b_total = st.number_input("총 만기 회차", min_value=1)
    b_rate = st.number_input("연 이율 (%)", min_value=0.0, step=0.1, value=3.0)
    if st.button("은행 자산 저장"):
        st.session_state['savings'].append({"종류": b_type, "상품명": b_name, "월납입액": int(raw_m.replace(',','')), "현재회차": b_curr, "총회차": b_total, "이율": b_rate})
        sort_and_save(); st.rerun()

# ==========================================
# 5. 메인 로직 & 대시보드
# ==========================================
st.title("💰 My Asset Hub V35")

risk_group = {r: 0 for r in active_risks}; risk_group["고정(은행)"] = 0
port_group = {"가상화폐": 0, "해외 주식": 0, "국내 주식": 0} 
stock_disp = []; total_buy = 0 

for idx, s in enumerate(st.session_state['stocks']):
    ticker, is_foreign, buy_p, qty = s.get('티커'), s.get('해외여부'), float(s.get('매수평단가', 0)), float(s.get('보유수량', 0))
    curr = get_price(ticker)
    curr_krw = curr * exchange_rate if is_foreign else curr
    buy_amt = buy_p * qty * (exchange_rate if is_foreign else 1)
    eval_amt = curr_krw * qty
    total_buy += buy_amt
    
    if ticker.startswith("KRW-"): port_group["가상화폐"] += eval_amt
    elif is_foreign: port_group["해외 주식"] += eval_amt
    else: port_group["국내 주식"] += eval_amt
    
    risk_cat = s.get('리스크', active_risks[0])
    risk_group[risk_cat] = risk_group.get(risk_cat, 0) + eval_amt
    
    profit = (eval_amt - buy_amt) / buy_amt * 100 if buy_amt > 0 else 0
    stock_disp.append({"ID": idx, "종목명": s.get('종목명'), "티커": ticker, "매수": buy_amt, "평가": eval_amt, "수익률": profit, "리스크": risk_cat, "현재가": curr, "해외": is_foreign, "매수평단가": buy_p, "보유수량": qty})

total_sav_val = 0; total_bank_principal = 0; fixed_sav_val = 0
for sav in st.session_state['savings']:
    amt = int(sav.get('월납입액', 0)) * int(sav.get('현재회차', 1))
    total_sav_val += amt; total_buy += amt
    total_bank_principal += (int(sav.get('월납입액', 0)) * int(sav.get('총회차', 1)))
    if sav.get('종류') in ["적금", "주택청약"]: fixed_sav_val += amt
risk_group["고정(은행)"] += total_sav_val

grand_total = sum(port_group.values()) + total_sav_val

# 히스토리 저장 (구글 시트 연동)
history_data = load_cloud_data('history')
history_df = pd.DataFrame(history_data) if history_data else pd.DataFrame(columns=["날짜", "총자산"])
if grand_total > 0:
    if not history_df.empty and logic_date_str in history_df['날짜'].values:
        history_df.loc[history_df['날짜'] == logic_date_str, '총자산'] = grand_total
    else:
        history_df = pd.concat([history_df, pd.DataFrame([{"날짜": logic_date_str, "총자산": grand_total}])], ignore_index=True)
    save_cloud_data(history_df.to_dict('records'), 'history')

# 대시보드 UI
target = st.session_state['config'].get('target_asset', 1000000000)
achieved = (grand_total / target * 100) if target > 0 else 0
if achieved < 100: st.markdown(f"### 🏆 목표 ({target:,.0f}원) | <span class='goal-red'>{100-achieved:.1f}% 남음 🔥</span>", unsafe_allow_html=True)
else: st.markdown(f"### 🏆 목표 ({target:,.0f}원) | <span class='goal-green'>🎉 {achieved-100:.1f}% 초과 달성 🎉</span>", unsafe_allow_html=True)
st.progress(min(achieved / 100, 1.0))

c1, c2, c3 = st.columns(3)
c1.metric("총 자산", f"{grand_total:,.0f}원")
c2.metric("매수 원금", f"{total_buy:,.0f}원")
c3.metric("수익금", f"{grand_total-total_buy:,.0f}원", f"{(grand_total-total_buy)/total_buy*100:.1f}%" if total_buy>0 else "0%")

st.markdown("---")
tab1, tab2, tab3 = st.tabs(["📊 대시보드", "📋 자산 관리", "⚖️ 리밸런싱"])

with tab1:
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        fig1 = go.Figure(data=[go.Pie(labels=["가상화폐", "해외 주식", "국내 주식", "은행(안전)"], values=[port_group["가상화폐"], port_group["해외 주식"], port_group["국내 주식"], total_sav_val], hole=.4, sort=False)])
        fig1.update_layout(title="포트폴리오 비중", margin=dict(l=10, r=10, t=30, b=10), height=300)
        st.plotly_chart(fig1, use_container_width=True)
    with col_p2:
        colors = ['#E74C3C', '#F39C12', '#3498DB', '#2ECC71', '#9B59B6', '#1ABC9C', '#34495E']
        fig2 = go.Figure(data=[go.Pie(labels=list(risk_group.keys()), values=list(risk_group.values()), hole=.4, marker_colors=colors)])
        fig2.update_layout(title="리스크 다각화", margin=dict(l=10, r=10, t=30, b=10), height=300)
        st.plotly_chart(fig2, use_container_width=True)
    
    if not history_df.empty:
        st.subheader("🚀 자산 성장 타임라인")
        fig_line = px.area(history_df, x="날짜", y="총자산", markers=True, color_discrete_sequence=['#2E86C1'])
        fig_line.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_line, use_container_width=True, config={'staticPlot': True})

with tab2:
    st.subheader(f"📈 투자 자산 내역 (총 평가: {sum(x['평가'] for x in stock_disp):,.0f}원)")
    for s in stock_disp:
        c_i, c_e, c_d = st.columns([6, 0.7, 0.7])
        with c_i:
            cur_s = "$" if s['해외'] else "₩"
            st.markdown(f"**{s['종목명']} ({s['티커']})** | **[{s['리스크']}]** | {'🔥' if s['수익률']>0 else '❄️'} **{s['수익률']:.2f}%**")
            st.markdown(f"<div class='green-text'>↳ 평단가(수수료제외): <b>{s['매수평단가']:,.2f}{cur_s}</b> | 수량: <b>{s['보유수량']:.2f}</b> | 평가: <b>{s['평가']:,.0f}원</b></div>", unsafe_allow_html=True)
        with c_e:
            if st.button("✏️", key=f"e_{s['ID']}"): st.session_state[f"em_{s['ID']}"] = not st.session_state.get(f"em_{s['ID']}", False)
        with c_d:
            if st.button("🗑️", key=f"d_{s['ID']}"): st.session_state['stocks'].pop(s['ID']); sort_and_save(); st.rerun()
        if st.session_state.get(f"em_{s['ID']}", False):
            new_p = st.number_input("평단가 수정", value=float(s['매수평단가']), key=f"np_{s['ID']}")
            new_q = st.number_input("수량 수정", value=float(s['보유수량']), key=f"nq_{s['ID']}")
            if st.button("저장", key=f"sv_{s['ID']}"):
                st.session_state['stocks'][s['ID']].update({'매수평단가': new_p, '보유수량': new_q})
                sort_and_save(); st.rerun()
    
    st.divider()
    st.subheader(f"🏦 은행 자산 내역 (총 원금: {total_bank_principal:,.0f}원)")
    for i, sav in enumerate(st.session_state['savings']):
        c_i, c_e, c_d = st.columns([6, 0.7, 0.7])
        with c_i:
            st.markdown(f"**[{sav['종류']}] {sav['상품명']}** (연 {sav['이율']}%) | 원금: {int(sav['월납입액'])*int(sav['총회차']):,.0f}원")
            prog = min(1.0, int(sav['현재회차'])/int(sav['총회차']))
            st.markdown(f"<div class='green-text'>↳ {sav['현재회차']}/{sav['총회차']}개월 진행 중</div>", unsafe_allow_html=True)
            st.progress(prog)
        with c_e:
            if st.button("✏️", key=f"eb_{i}"): st.session_state[f"ebm_{i}"] = not st.session_state.get(f"ebm_{i}", False)
        with c_d:
            if st.button("🗑️", key=f"db_{i}"): st.session_state['savings'].pop(i); sort_and_save(); st.rerun()

with tab3:
    st.subheader("⚖️ 1단계: 비중 설정")
    fixed_p = round(fixed_sav_val/grand_total*100, 1) if grand_total>0 else 0
    cols = st.columns(len(active_risks) + 1)
    tgt_w = {}
    for i, r in enumerate(active_risks): tgt_w[r] = cols[i].number_input(f"{r}", value=0.0, step=1.0)
    cols[-1].number_input("고정(은행)", value=float(fixed_p), disabled=True)
    
    if abs(sum(tgt_w.values()) + fixed_p - 100.0) < 0.1:
        st.success("✅ 100% 일치. 2단계 활성화")
        st.divider()
        st.subheader("🔬 2단계: 세부 조율")
        # 리밸런싱 로직 (기존과 동일하되 세션 데이터 사용)
        re_items = []
        for s in stock_disp: re_items.append({"자산군": s['리스크'], "종목명": s['종목명'], "현재금액": int(s['평가']), "수익률": s['수익률'], "티커": s['티커'], "현재가": s['현재가']})
        for sv in st.session_state['savings']:
            grp = "고정(은행)" if sv['종류'] in ["적금", "주택청약"] else active_risks[-1]
            re_items.append({"자산군": grp, "종목명": sv['상품명'], "현재금액": int(sv['월납입액'])*int(sv['현재회차']), "수익률": 0.0, "티커": "SAV", "현재가": 0})
        
        rdf = pd.DataFrame(re_items)
        if not rdf.empty:
            rdf['💡 목표(%)'] = rdf.apply(lambda x: round((x['현재금액']/grand_total*100),1), axis=1)
            edited = st.data_editor(rdf[['자산군', '종목명', '현재금액', '💡 목표(%)']], use_container_width=True, hide_index=True)
            if st.button("🚀 3단계: 액션 플랜 생성"):
                st.info("여기에 최종 매수/매도 가이드가 표시됩니다.")
    else:
        st.warning(f"합계 {sum(tgt_w.values())+fixed_p}%입니다. 100%를 맞춰주세요.")
