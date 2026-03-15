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
# [중요] 1단계에서 새로 만든 웹 앱 URL을 여기에 넣으세요
# ==========================================
API_URL = "https://script.google.com/macros/s/AKfycbx6-L0Rl4GlpZloBZ79M9mqHYSnSTOCaaHjVnhF5mYKcPF42QaShH0A54vD6WUz4O45/exec"

# ==========================================
# 1. 앱 기본 설정 & UI 스타일링
# ==========================================
st.set_page_config(page_title="My Asset Hub V37", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem; padding-left: 1rem; padding-right: 1rem; }
    p, .stMarkdown, div[data-testid="stText"] { font-size: 1.1rem !important; }
    .stMetric label { font-size: 1rem !important; }
    .stMetric value { font-size: 1.8rem !important; }
    .goal-red { color: #E74C3C; font-weight: 900; font-size: 1.4rem; }
    .goal-green { color: #2ECC71; font-weight: 900; font-size: 1.4rem; }
    .green-text { color: #2ECC71; font-size: 0.95em; font-weight: 500; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. 클라우드 데이터 동기화 엔진 (디버깅 강화)
# ==========================================
def load_cloud_data(sheet_name):
    try:
        res = requests.get(f"{API_URL}?sheetName={sheet_name}", timeout=10)
        if res.status_code == 200:
            return res.json()
        return []
    except: return []

def save_cloud_data(data, sheet_name):
    try:
        payload = {"sheetName": sheet_name, "data": data}
        res = requests.post(API_URL, data=json.dumps(payload), timeout=15)
        if res.status_code == 200:
            return True
        else:
            st.error(f"⚠️ 구글 응답 에러 ({res.status_code}): {res.text}")
            return False
    except Exception as e:
        st.error(f"❌ 통신 실패: {str(e)}")
        return False

# 초기 데이터 로드
if 'stocks' not in st.session_state: st.session_state['stocks'] = load_cloud_data('stocks')
if 'savings' not in st.session_state: st.session_state['savings'] = load_cloud_data('savings')
if 'config' not in st.session_state: 
    cfg = load_cloud_data('config')
    st.session_state['config'] = cfg[0] if cfg else {"target_asset": 1000000000, "risk_levels": "초고위험,위험,중립,안전"}

active_risks = [r.strip() for r in st.session_state['config'].get('risk_levels', "초고위험,위험,중립,안전").split(',') if r.strip()]

def sort_and_save():
    def get_risk_weight(r):
        try: return active_risks.index(r)
        except: return 99
    st.session_state['stocks'].sort(key=lambda x: (get_risk_weight(x.get('리스크')), -(float(x.get('매수평단가', 0)) * float(x.get('보유수량', 0)))))
    
    # 3개 데이터 동시 저장 시도
    s1 = save_cloud_data(st.session_state['stocks'], 'stocks')
    s2 = save_cloud_data(st.session_state['savings'], 'savings')
    s3 = save_cloud_data([st.session_state['config']], 'config')
    return s1 and s2 and s3

# ==========================================
# 3. 데이터 수집 엔진
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
            try:
                df_us = fdr.StockListing(mkt); df_us['시장'] = mkt; dfs.append(df_us[['Symbol', 'Name', '시장']].rename(columns={'Symbol':'Code'}))
            except: pass
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
# 4. 사이드바 (컨트롤러 & 진단)
# ==========================================
with st.sidebar:
    st.title("🛠️ 컨트롤러")
    st.metric("💵 실시간 환율", f"{exchange_rate:,.2f} 원")
    
    st.divider()
    st.markdown("### ➕ 투자 자산 추가")
    asset_input = st.text_input("🔍 종목/티커 검색", placeholder="예: 삼성전자, SCHD")
    
    if asset_input:
        options = []
        coin_map = {"비트코인": "KRW-BTC", "이더리움": "KRW-ETH", "리플": "KRW-XRP", "솔라나": "KRW-SOL"}
        for k, v in coin_map.items():
            if k in asset_input: options.append(f"[가상화폐] {k} ({v})")
        df_m = load_market_data()
        if df_m is not None:
            mask = df_m['Name'].str.contains(asset_input, case=False, na=False) | df_m['Code'].str.contains(asset_input, case=False, na=False)
            for _, r in df_m[mask].head(20).iterrows(): options.append(f"[{r['시장']}] {r['Name']} ({r['Code']})")
        if re.match(r"^[A-Za-z0-9]+$", asset_input.strip()): options.append(f"[해외 직접입력] {asset_input.upper()} ({asset_input.upper()})")
        
        if options:
            selected = st.selectbox("💡 종목 선택", list(dict.fromkeys(options)))
            m = re.match(r"\[(.*?)\] (.*) \((.*?)\)", selected)
            if m:
                sel_market, sel_name, sel_code = m.group(1), m.group(2), m.group(3)
                curr_label = "달러 $" if sel_market in ['NASDAQ', 'NYSE', 'AMEX', '해외 직접입력'] else "원 ₩"
                raw_p = st.text_input(f"매수 단가 ({curr_label})", value="0")
                new_p = float(raw_p.replace(',', '')) if raw_p.replace(',', '').replace('.','').isdigit() else 0.0
                new_q = st.number_input("보유 수량", min_value=0.0, step=0.01)
                risk_lv = st.selectbox("리스크 분류", active_risks)
                
                if st.button("내 자산으로 저장", use_container_width=True):
                    st.session_state['stocks'].append({"종목명": sel_name, "티커": sel_code, "매수평단가": new_p, "보유수량": new_q, "해외여부": (curr_label=="달러 $"), "리스크": risk_lv})
                    if sort_and_save(): st.success("구글 시트 저장 완료!"); st.rerun()

    st.divider()
    st.markdown("### ☁️ 클라우드 연결 진단")
    if st.button("🚀 지금 즉시 엑셀로 저장하기", use_container_width=True):
        with st.spinner("구글 시트에 동기화 중..."):
            if sort_and_save(): st.toast("✅ 엑셀 동기화 성공!")

# (이하 탭 UI 로직은 V36과 동일하게 유지 - 가독성을 위해 생략)
# [성민 대표님, 아래 코드는 대시보드와 자산관리 탭 출력 부분입니다. V36의 내용을 그대로 붙여넣으시면 됩니다.]
# ... (기존 코드의 tab1, tab2, tab3 내용 삽입)
