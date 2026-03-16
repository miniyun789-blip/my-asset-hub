import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import re
import FinanceDataReader as fdr
import json
import threading
import concurrent.futures

# [자동 로그인 쿠키 매니저]
try:
    import extra_streamlit_components as stx
    HAS_STX = True
except ImportError:
    HAS_STX = False

# ==========================================
# 🔒 보안 설정
# ==========================================
SECRET_PASSCODE = "SM2026"

# ==========================================
# 1. 앱 기본 설정
# ==========================================
st.set_page_config(page_title="My Asset Hub (v1.46)", layout="wide", initial_sidebar_state="expanded")

# ==========================================
# 2. 입장 및 인증 시스템 (쿠키 & 상태 관리)
# ==========================================
cookie_manager = stx.CookieManager() if HAS_STX else None

query_params = st.query_params
if 'api_url' not in st.session_state: st.session_state.api_url = query_params.get("api_url", "")
if 'passcode' not in st.session_state: st.session_state.passcode = query_params.get("passcode", "")
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'show_guide' not in st.session_state: st.session_state.show_guide = False

if HAS_STX:
    saved_url = cookie_manager.get(cookie="my_api_url")
    saved_pass = cookie_manager.get(cookie="my_passcode")
    if saved_url and saved_pass:
        st.session_state.api_url = saved_url
        st.session_state.passcode = saved_pass
        st.session_state.authenticated = True

def login():
    if st.session_state.temp_passcode == SECRET_PASSCODE and st.session_state.temp_api_url.startswith("https://script.google.com/"):
        st.session_state.passcode = st.session_state.temp_passcode
        st.session_state.api_url = st.session_state.temp_api_url
        st.session_state.authenticated = True
        if HAS_STX:
            cookie_manager.set("my_api_url", st.session_state.api_url, max_age=31536000)
            cookie_manager.set("my_passcode", st.session_state.passcode, max_age=31536000)
        st.query_params["passcode"] = st.session_state.passcode
        st.query_params["api_url"] = st.session_state.api_url
    else:
        st.error("❌ Private password가 틀렸거나, URL ID 형식이 올바르지 않습니다.")

def toggle_guide(): st.session_state.show_guide = not st.session_state.show_guide

if st.session_state.passcode == SECRET_PASSCODE and st.session_state.api_url.startswith("https://script.google.com/"):
    st.session_state.authenticated = True

# ------------------------------------------
# 🛑 미인증 사용자 화면
# ------------------------------------------
if not st.session_state.authenticated:
    st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="stHeader"] { display: none !important; }
    .stApp { background-color: #0B0E14; background-image: radial-gradient(circle at 50% 0%, #1a1c2e 0%, #0B0E14 70%); color: #FFFFFF; }
    .block-container { padding-top: 10vh !important; max-width: 500px !important; }
    .stTextInput>div>div>input { background-color: #1A1C23 !important; color: white !important; border: 1px solid #2D3748 !important; border-radius: 8px !important; padding: 12px !important; }
    .stButton>button[kind="primary"] { background: linear-gradient(90deg, #7c3aed 0%, #4f46e5 100%) !important; color: white !important; border: none !important; border-radius: 8px !important; padding: 10px !important; font-weight: bold !important; }
    .stButton>button[kind="secondary"] { background-color: #1A1C23 !important; color: #A0AEC0 !important; border: 1px solid #2D3748 !important; border-radius: 8px !important; }
    .stButton>button[kind="secondary"]:hover { color: #FFFFFF !important; border-color: #4f46e5 !important; }
    .guide-card { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 20px; margin-bottom: 20px; color: #c9d1d9; font-size: 0.95em; line-height: 1.6; }
    .terminal-box { background-color: #010409; border: 1px solid #30363d; border-radius: 10px; padding: 15px; margin-bottom: 20px; box-shadow: 0 8px 16px rgba(0,0,0,0.5); overflow-x: auto; }
    .terminal-header { display: flex; gap: 8px; margin-bottom: 12px; }
    .dot { width: 12px; height: 12px; border-radius: 50%; } .dot.red { background-color: #ff5f56; } .dot.yellow { background-color: #ffbd2e; } .dot.green { background-color: #27c93f; }
    </style>
    """, unsafe_allow_html=True)

    if not st.session_state.show_guide:
        st.markdown("<h1 style='text-align:center; font-size:2.5rem; margin-bottom:5px; font-weight:800; letter-spacing: -1px;'>Sign in</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:#8b949e; margin-bottom:40px; font-size:1rem;'>My Asset Hub Private Lounge</p>", unsafe_allow_html=True)
        st.text_input("URL ID", key="temp_api_url", value=st.session_state.api_url, placeholder="https://script.google.com/...")
        st.text_input("Private password", type="password", key="temp_passcode", value=st.session_state.passcode, placeholder="초대 코드를 입력하세요")
        st.markdown("<br>", unsafe_allow_html=True)
        st.button("Sign in", on_click=login, type="primary", use_container_width=True)
        st.markdown("<div style='text-align:center; margin-top:50px;'>", unsafe_allow_html=True)
        st.button("URL ID 생성방법 ✨", on_click=toggle_guide, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown("<h2 style='text-align:center; font-size:1.8rem; margin-bottom:30px; font-weight: 700;'>✨ URL ID 생성방법</h2>", unsafe_allow_html=True)
        st.markdown("<div class='guide-card'><h4 style='color:#58a6ff; margin-top:0;'>STEP 1: 구글 시트 준비</h4>1. 구글 드라이브에서 <b>새 스프레드시트</b>를 생성합니다.<br>2. 상단 메뉴 <b>[확장 프로그램] ➡️ [Apps Script]</b>를 클릭합니다.</div>", unsafe_allow_html=True)
        st.markdown("<div class='guide-card'><h4 style='color:#58a6ff; margin-top:0;'>STEP 2: 엔진 코드 붙여넣기</h4>3. 열린 창의 내용을 지우고, 아래 코드를 복사하여 덮어씌웁니다.</div>", unsafe_allow_html=True)
        st.markdown("""
        <div class='terminal-box'>
            <div class='terminal-header'><div class='dot red'></div><div class='dot yellow'></div><div class='dot green'></div></div>
            <pre style="margin:0; font-family:'Consolas', monospace; font-size:0.85em; color:#3fb950; white-space:pre;"><code>function doPost(e) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var params = JSON.parse(e.postData.contents);
  for (var sheetName in params) {
    var data = params[sheetName];
    var sheet = ss.getSheetByName(sheetName) || ss.insertSheet(sheetName);
    sheet.clear();
    if (data && data.length > 0) {
      var headers = Object.keys(data[0]);
      var values = [headers];
      data.forEach(function(item) { values.push(headers.map(function(h) { return item[h]; })); });
      sheet.getRange(1, 1, values.length, headers.length).setValues(values);
    }
  }
  return ContentService.createTextOutput("Success");
}
function doGet(e) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(e.parameter.sheetName);
  if (!sheet) return ContentService.createTextOutput("[]").setMimeType(ContentService.MimeType.JSON);
  var values = sheet.getDataRange().getValues();
  if (values.length < 2) return ContentService.createTextOutput("[]").setMimeType(ContentService.MimeType.JSON);
  var headers = values[0];
  var jsonArray = values.slice(1).map(function(row) {
    var obj = {}; headers.forEach(function(h, i) { obj[h] = row[i]; }); return obj;
  });
  return ContentService.createTextOutput(JSON.stringify(jsonArray)).setMimeType(ContentService.MimeType.JSON);
}</code></pre>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div class='guide-card'><h4 style='color:#58a6ff; margin-top:0;'>STEP 3: 배포 및 권한 승인</h4>4. 우측 상단 <b>[배포] ➡️ [새 배포]</b> 클릭<br>5. 설정 후 배포!<br><br><span style='color:#ff7b72;'>⚠️ <b>\"Google hasn’t verified this app\"</b> 해결:</span><br>&nbsp;&nbsp;↳ <b>[Advanced (고급)]</b> ➡️ <b>[Go to 프로젝트]</b> ➡️ <b>[Allow (허용)]</b><br>6. 발급된 <b>웹 앱 URL</b>을 복사하여 로그인 화면에 붙여넣으세요!</div>", unsafe_allow_html=True)
        st.button("⬅️ 로그인 화면으로 돌아가기", on_click=toggle_guide, use_container_width=True)
    st.stop()

# ==========================================
# 🟢 메인 자산 관리 앱 로직 (v1.46)
# ==========================================
st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem !important; max-width: 100% !important; }
    p, .stMarkdown, div[data-testid="stText"] { font-size: 1.1rem !important; }
    .goal-red { color: #E74C3C; font-weight: 900; font-size: 1.4rem; }
    .goal-green { color: #2ECC71; font-weight: 900; font-size: 1.4rem; }
    .green-text { color: #2ECC71; font-size: 0.95em; margin-bottom: 10px; font-weight: 500; }
    .info-card { background-color: #F8FAFC; padding: 20px; border-radius: 10px; border-left: 5px solid #3B82F6; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

API_URL = st.session_state.api_url

def load_cloud_data(sheet_name):
    try:
        res = requests.get(f"{API_URL}?sheetName={sheet_name}", timeout=8)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list): return data
        return []
    except: return []

def save_all_to_cloud():
    try:
        payload = {"stocks": st.session_state['stocks'], "savings": st.session_state['savings'], "config": [st.session_state['config']]}
        res = requests.post(API_URL, data=json.dumps(payload), timeout=15)
        return res.status_code == 200
    except: return False

if 'stocks' not in st.session_state: 
    with st.spinner("구글 금고에서 자산 정보 동기화 중..."): st.session_state['stocks'] = load_cloud_data('stocks')
if 'savings' not in st.session_state: st.session_state['savings'] = load_cloud_data('savings')
if 'config' not in st.session_state: 
    cfg = load_cloud_data('config')
    st.session_state['config'] = cfg[0] if cfg else {"target_asset": 1000000000, "risk_levels": "초고위험,위험,중립,안전", "auto_save": True}

raw_risks = st.session_state['config'].get('risk_levels', "초고위험,위험,중립,안전")
active_risks = [r.strip() for r in raw_risks.split(',') if r.strip()]

def get_risk_weight(r):
    try: return active_risks.index(r)
    except ValueError: return 99

def sort_and_save():
    st.session_state['stocks'].sort(key=lambda x: (get_risk_weight(x.get('리스크')), -(float(x.get('매수평단가', 0)) * float(x.get('보유수량', 0)))))
    if st.session_state['config'].get('auto_save', True): return save_all_to_cloud()
    return True

kst_now = datetime.utcnow() + timedelta(hours=9)
logic_date_str = (kst_now - timedelta(days=1)).strftime('%Y-%m-%d') if kst_now.hour < 3 else kst_now.strftime('%Y-%m-%d')

@st.cache_data(ttl=86400)
def load_market_data():
    dfs = []
    markets = ['KRX', 'ETF/KR', 'NASDAQ', 'NYSE']
    def fetch_mkt(m):
        try:
            df = fdr.StockListing(m)
            df['시장'] = m
            if 'Symbol' in df.columns: df = df.rename(columns={'Symbol':'Code'})
            return df[['Code', 'Name', '시장']]
        except: return pd.DataFrame()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results = executor.map(fetch_mkt, markets)
        for res in results:
            if not res.empty: dfs.append(res)
    return pd.concat(dfs, ignore_index=True) if dfs else None

@st.cache_data(ttl=600)
def get_exchange_rate():
    try:
        res = requests.get("https://www.google.com/finance/quote/USD-KRW", headers={'User-Agent': 'Mozilla/5.0'})
        return float(BeautifulSoup(res.text, 'html.parser').select_one('.YMlKec.fxKbKc').text.replace(',', ''))
    except: return 1350.0

def get_price(ticker):
    if not ticker or pd.isna(ticker): return 0.0
    ticker = str(ticker).strip()
    if ticker.startswith("KRW-"):
        try: return float(requests.get(f"https://api.upbit.com/v1/ticker?markets={ticker}").json()[0]['trade_price'])
        except: return 0.0
    clean_ticker = ticker.replace('.KS', '').replace('.KQ', '')
    for gf_ticker in [f"{clean_ticker}:KRX", f"{clean_ticker}:KOSDAQ", f"{clean_ticker}:NASDAQ", f"{clean_ticker}:NYSE", f"{clean_ticker}:NYSEARCA"]:
        try:
            res = requests.get(f"https://www.google.com/finance/quote/{gf_ticker}", headers={'User-Agent': 'Mozilla/5.0'}, timeout=2)
            if 'YMlKec fxKbKc' in res.text: return float(BeautifulSoup(res.text, 'html.parser').select_one('.YMlKec.fxKbKc').text.replace('₩', '').replace('$', '').replace(',', ''))
        except: pass
    return 0.0

@st.cache_data(ttl=120)
def get_all_prices_concurrently(tickers):
    prices = {}
    def fetch_task(t): return t, get_price(t)
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(fetch_task, t) for t in set(tickers)]
        for future in concurrent.futures.as_completed(futures):
            t, p = future.result()
            prices[t] = p
    return prices

exchange_rate = get_exchange_rate()
all_tickers_to_fetch = [str(s.get('티커', '')).strip() for s in st.session_state['stocks']]
price_dict = get_all_prices_concurrently(all_tickers_to_fetch)

with st.sidebar:
    st.title("🛠️ 컨트롤러")
    st.metric("💵 실시간 환율", f"{exchange_rate:,.2f} 원")
    st.divider()
    auto_save_val = st.toggle("🔄 실시간 동기화", value=st.session_state['config'].get('auto_save', True))
    st.session_state['config']['auto_save'] = auto_save_val
    if not auto_save_val:
        if st.button("🚀 즉시 동기화", use_container_width=True, type="primary"):
            with st.spinner("동기화 중..."):
                if save_all_to_cloud(): st.toast("✅ 동기화 성공!")
                else: st.error("❌ 연결 실패")
    
    if st.button("🚪 다른 금고로 로그인", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.api_url = ""
        st.query_params.clear()
        if HAS_STX:
            cookie_manager.delete("my_api_url")
            cookie_manager.delete("my_passcode")
        st.rerun()
    st.divider()

with st.sidebar.expander("⚙️ 시스템 및 목표 설정"):
    current_tgt = int(st.session_state['config'].get('target_asset', 1000000000))
    new_tgt_str = st.text_input("목표 금액 (원)", value=f"{current_tgt:,}")
    if st.button("목표 저장"):
        try:
            st.session_state['config']['target_asset'] = int(new_tgt_str.replace(",", ""))
            sort_and_save(); st.rerun()
        except: st.error("숫자만 입력해주세요.")

st.sidebar.markdown("### ➕ 투자 자산 추가")
asset_input = st.sidebar.text_input("🔍 종목/티커 검색", placeholder="예: 삼성전자 (2글자 이상 입력)")

if asset_input and len(asset_input) >= 2:
    options = []
    coin_map = {"비트코인": "KRW-BTC", "이더리움": "KRW-ETH", "리플": "KRW-XRP"}
    for k, v in coin_map.items():
        if k in asset_input.upper(): options.append(f"[가상화폐] {k} ({v})")
    
    df_m = load_market_data()
    if df_m is not None:
        mask = df_m['Name'].str.contains(asset_input, case=False, na=False) | df_m['Code'].str.contains(asset_input, case=False, na=False)
        for _, r in df_m[mask].head(20).iterrows(): options.append(f"[{r['시장']}] {r['Name']} ({r['Code']})")
    if re.match(r"^[A-Za-z0-9]+$", asset_input.strip()): options.append(f"[해외 직접입력] {asset_input.upper()} ({asset_input.upper()})")
    options = list(dict.fromkeys(options))
    
    if options:
        selected = st.sidebar.selectbox("💡 종목 선택", options)
        m = re.match(r"\[(.*?)\] (.*) \((.*?)\)", selected)
        if m:
            sel_market, sel_name, sel_code = m.group(1), m.group(2), m.group(3)
            is_foreign = (sel_market in ['NASDAQ', 'NYSE', 'AMEX', '해외 직접입력'])
            raw_p = st.sidebar.text_input(f"매수 단가 ({'$' if is_foreign else '₩'})", value="0")
            try: new_p = float(raw_p.replace(',', ''))
            except: new_p = 0.0
            new_q = st.sidebar.number_input("보유 수량", min_value=0.0, step=0.01)
            risk_lv = st.sidebar.selectbox("리스크 분류", active_risks)
            
            if st.sidebar.button("자산 저장", use_container_width=True):
                existing_idx = next((i for i, s in enumerate(st.session_state['stocks']) if str(s.get('티커', '')) == sel_code), None)
                if existing_idx is not None:
                    old_stock = st.session_state['stocks'][existing_idx]
                    old_q, old_p = float(old_stock.get('보유수량', 0)), float(old_stock.get('매수평단가', 0))
                    final_q = old_q + new_q
                    final_p = ((old_p * old_q) + (new_p * new_q)) / final_q if final_q > 0 else 0
                    st.session_state['stocks'][existing_idx].update({'매수평단가': final_p, '보유수량': final_q})
                else:
                    st.session_state['stocks'].append({"종목명": sel_name, "티커": sel_code, "매수평단가": new_p, "보유수량": new_q, "해외여부": is_foreign, "리스크": risk_lv})
                if sort_and_save(): st.toast("✅ 자산 업데이트 완료!")
                st.rerun()

with st.sidebar.expander("⚙️ 리스크 분류 관리"):
    risk_df = pd.DataFrame({"리스크 명칭": active_risks})
    edited_risk = st.data_editor(risk_df, num_rows="dynamic", use_container_width=True, hide_index=True)
    if st.button("✔️ 분류 저장"):
        st.session_state['config']['risk_levels'] = ",".join(edited_risk['리스크 명칭'].dropna().tolist())
        sort_and_save(); st.rerun()

with st.sidebar.expander("🏦 은행 자산 추가"):
    b_type = st.selectbox("종류", ["적금", "주택청약", "예금", "파킹통장"])
    b_name = st.text_input("통장이름")
    raw_m = st.text_input("월 납입액/총액 (원)", value="1000000")
    b_curr = st.number_input("현재 회차 (예금/파킹통장은 1)", min_value=1)
    b_total = st.number_input("총 만기 회차", min_value=1)
    b_rate = st.number_input("연 이율 (%)", min_value=0.0, step=0.1, value=3.0)
    if st.button("은행 자산 저장"):
        try: m_val = int(raw_m.replace(',', ''))
        except: m_val = 0
        st.session_state['savings'].append({"종류": b_type, "상품명": b_name, "월납입액": m_val, "현재회차": b_curr, "총회차": b_total, "이율": b_rate})
        sort_and_save(); st.rerun()

with st.sidebar: st.markdown("<br><br><div style='text-align: left; color: #BDC3C7; font-size: 0.8em;'>v1.46 (Integrity)</div>", unsafe_allow_html=True)

st.title("💰 My Asset Hub (Test Server)")

risk_group = {r: 0 for r in active_risks}; risk_group["고정(은행)"] = 0
port_group = {"가상화폐": 0, "해외 주식": 0, "국내 주식": 0} 
stock_disp = []; total_buy = 0 

for idx, s in enumerate(st.session_state['stocks']):
    ticker = str(s.get('티커', '')).strip()
    is_foreign = s.get('해외여부', False)
    buy_p = float(s.get('매수평단가', 0))
    qty = float(s.get('보유수량', 0))
    
    curr = price_dict.get(ticker, 0.0)
    curr_krw = curr * exchange_rate if is_foreign else curr
    buy_amt = buy_p * qty * (exchange_rate if is_foreign else 1)
    eval_amt = curr_krw * qty
    total_buy += buy_amt
    
    if ticker.startswith("KRW-"): port_group["가상화폐"] += eval_amt
    elif is_foreign: port_group["해외 주식"] += eval_amt
    else: port_group["국내 주식"] += eval_amt
    
    risk_cat = s.get('리스크', active_risks[0] if active_risks else '기타')
    risk_group[risk_cat] = risk_group.get(risk_cat, 0) + eval_amt
    profit = (eval_amt - buy_amt) / buy_amt * 100 if buy_amt > 0 else 0
    stock_disp.append({"ID": idx, "종목명": s.get('종목명'), "티커": ticker, "매수": buy_amt, "평가": eval_amt, "수익률": profit, "리스크": risk_cat, "현재가": curr, "해외": is_foreign, "매수평단가": buy_p, "보유수량": qty})

# [수정 3] 은행 자산 리스크 분리 (예금/파킹통장 -> 안전)
total_sav_val = 0; total_bank_principal = 0; fixed_sav_val = 0
for sav in st.session_state['savings']:
    m_val = int(sav.get('월납입액', 0)); c_val = int(sav.get('현재회차', 0)); t_val = int(sav.get('총회차', 1))
    amt = m_val * c_val
    total_sav_val += amt; total_buy += amt; total_bank_principal += (m_val * t_val)
    
    if sav.get('종류') in ["예금", "파킹통장"]:
        risk_group["안전"] = risk_group.get("안전", 0) + amt
    else: # 적금, 주택청약
        fixed_sav_val += amt
        risk_group["고정(은행)"] += amt

grand_total = sum(port_group.values()) + total_sav_val

# [수정 1] 역사적 데이터(History) 및 타임라인 로직 복구
history_data = load_cloud_data('history')
history_df = pd.DataFrame(history_data) if history_data else pd.DataFrame(columns=["날짜", "총자산"])
if grand_total > 0:
    if not history_df.empty and logic_date_str in history_df['날짜'].values:
        history_df.loc[history_df['날짜'] == logic_date_str, '총자산'] = grand_total
    else:
        history_df = pd.concat([history_df, pd.DataFrame([{"날짜": logic_date_str, "총자산": grand_total}])], ignore_index=True)
    def save_history_bg():
        try: requests.post(API_URL, data=json.dumps({"sheetName": "history", "data": history_df.to_dict('records')}), timeout=5)
        except: pass
    threading.Thread(target=save_history_bg).start()

target = st.session_state['config'].get('target_asset', 1000000000)
achieved = (grand_total / target * 100) if target > 0 else 0
if achieved < 100: st.markdown(f"### 🏆 목표 ({target:,.0f}원) | <span class='goal-red'>{100-achieved:.1f}% 남음 🔥</span>", unsafe_allow_html=True)
else: st.markdown(f"### 🏆 목표 ({target:,.0f}원) | <span class='goal-green'>🎉 {achieved-100:.1f}% 초과 달성 🎉</span>", unsafe_allow_html=True)
st.progress(min(achieved / 100, 1.0))

c1, c2, c3 = st.columns(3)
c1.metric("총 자산", f"{grand_total:,.0f}원")
c2.metric("매수 원금", f"{total_buy:,.0f}원")
if total_buy > 0: c3.metric("수익금", f"{grand_total - total_buy:,.0f}원", f"{(grand_total - total_buy) / total_buy * 100:.1f}%")
else: c3.metric("수익금", "0원", "0%")

st.markdown("---")
tab1, tab2, tab3 = st.tabs(["📊 대시보드", "📋 자산 관리", "⚖️ 리밸런싱"])

with tab1:
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        fig1 = go.Figure(data=[go.Pie(labels=["가상화폐", "해외 주식", "국내 주식", "은행(안전)"], values=[port_group["가상화폐"], port_group["해외 주식"], port_group["국내 주식"], total_sav_val], hole=.4, sort=False, direction='clockwise', marker_colors=['#F39C12', '#9B59B6', '#3498DB', '#1ABC9C'])])
        fig1.update_layout(title="포트폴리오 비중", height=320, margin=dict(t=40, b=10))
        st.plotly_chart(fig1, use_container_width=True)
    with col_p2:
        pref_order = ["초고위험", "위험", "중립", "안전", "고정(은행)"]
        ordered_keys = sorted(risk_group.keys(), key=lambda x: pref_order.index(x) if x in pref_order else 99)
        ordered_vals = [risk_group[k] for k in ordered_keys]
        fig2 = go.Figure(data=[go.Pie(labels=ordered_keys, values=ordered_vals, hole=.4, sort=False, direction='clockwise', marker_colors=['#E74C3C', '#F39C12', '#3498DB', '#2ECC71', '#34495E', '#9B59B6', '#1ABC9C'])])
        fig2.update_layout(title="리스크 다각화", height=320, margin=dict(t=40, b=10))
        st.plotly_chart(fig2, use_container_width=True)
    
    # [수정 1 & 2] 타임라인 복구 및 자동 기록 가이드 추가
    st.divider()
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        st.subheader("🚀 자산 성장 타임라인")
    with col_t2:
        if st.button("💡 매일 자동 기록 가이드 보기"):
            st.session_state['show_history_guide'] = not st.session_state.get('show_history_guide', False)
            
    if st.session_state.get('show_history_guide', False):
        st.markdown("""
        <div class="info-card">
            <h4 style="margin-top:0; color:#3B82F6;">⏱️ 매일 새벽 3시, 내 자산 자동 기록하기</h4>
            <p style="font-size:0.95em; color:#334155; line-height:1.6;">
            앱에 접속하지 않아도 매일 자산 변동이 차트에 기록되게 하려면 <b>'구글 트리거'</b> 설정이 필요합니다.<br>
            1. 구글 시트 상단 메뉴에서 <b>[확장 프로그램] ➡️ [Apps Script]</b>를 클릭합니다.<br>
            2. 왼쪽 메뉴에서 시계 모양 아이콘 <b>[트리거]</b>를 클릭합니다.<br>
            3. 우측 하단 <b>[트리거 추가]</b> 파란색 버튼을 누릅니다.<br>
            4. 설정창에서 아래와 같이 맞추고 [저장]을 누릅니다.<br>
               &nbsp;&nbsp;↳ 실행할 함수: <b><code>doPost</code></b> (주의: doGet이 아님)<br>
               &nbsp;&nbsp;↳ 이벤트 소스: <b>시간 기반</b><br>
               &nbsp;&nbsp;↳ 트리거 기반 시간 유형: <b>일일 타이머</b><br>
               &nbsp;&nbsp;↳ 시간대: <b>오전 3시 ~ 4시</b>
            </p>
        </div>
        """, unsafe_allow_html=True)
        
    if not history_df.empty and len(history_df) > 1:
        fig_line = px.area(history_df, x="날짜", y="총자산", markers=True, color_discrete_sequence=['#2E86C1'])
        fig_line.update_layout(height=300, margin=dict(t=10, b=10))
        st.plotly_chart(fig_line, use_container_width=True, config={'staticPlot': True})
    else:
        st.info("📊 타임라인을 그리기 위한 데이터가 아직 충분하지 않습니다. (최소 2일 이상의 기록 필요)")

with tab2:
    st.subheader(f"📈 투자 자산 내역 (총 평가: {sum(x['평가'] for x in stock_disp):,.0f}원)")
    stock_disp.sort(key=lambda x: (get_risk_weight(x['리스크']), -x['평가']))
    for s in stock_disp:
        c_i, c_e, c_d = st.columns([6, 0.7, 0.7])
        with c_i:
            st.markdown(f"**{s['종목명']} ({s['티커']})** | **[{s['리스크']}]** | {'🔥' if s['수익률']>0 else '❄️'} **{s['수익률']:.2f}%**")
            st.markdown(f"<div class='green-text'>↳ 평단가: <b>{s['매수평단가']:,.2f}{'$' if s['해외'] else '₩'}</b> | 수량: <b>{s['보유수량']:.2f}</b> | 평가: <b>{s['평가']:,.0f}원</b></div>", unsafe_allow_html=True)
        with c_e:
            if st.button("✏️", key=f"e_{s['ID']}"): st.session_state[f"em_{s['ID']}"] = not st.session_state.get(f"em_{s['ID']}", False)
        with c_d:
            if st.button("🗑️", key=f"d_{s['ID']}"): st.session_state['stocks'].pop(s['ID']); sort_and_save(); st.rerun()
        if st.session_state.get(f"em_{s['ID']}", False):
            new_p = st.number_input("평단가 수정", value=float(s['매수평단가']), key=f"np_{s['ID']}")
            new_q = st.number_input("수량 수정", value=float(s['보유수량']), key=f"nq_{s['ID']}")
            if st.button("저장", key=f"sv_{s['ID']}"):
                st.session_state['stocks'][s['ID']].update({'매수평단가': new_p, '보유수량': new_q}); sort_and_save(); st.rerun()
    st.divider()
    st.subheader(f"🏦 은행 자산 내역 (총 원금: {total_bank_principal:,.0f}원)")
    for i, sav in enumerate(st.session_state['savings']):
        c_i, c_e, c_d = st.columns([6, 0.7, 0.7])
        with c_i:
            m_v, c_v, t_v = int(sav.get('월납입액', 0)), int(sav.get('현재회차', 0)), int(sav.get('총회차', 1))
            st.markdown(f"**[{sav.get('종류', '')}] {sav.get('상품명', '')}** (연 {sav.get('이율', 0)}%) | 원금: {m_v * t_v:,.0f}원")
            st.markdown(f"<div class='green-text'>↳ {c_v}/{t_v}개월 진행 중</div>", unsafe_allow_html=True)
            if t_v > 0: st.progress(min(1.0, c_v / t_v))
        with c_e:
            if st.button("✏️", key=f"eb_{i}"): st.session_state[f"ebm_{i}"] = not st.session_state.get(f"ebm_{i}", False)
        with c_d:
            if st.button("🗑️", key=f"db_{i}"): st.session_state['savings'].pop(i); sort_and_save(); st.rerun()
        if st.session_state.get(f"ebm_{i}", False):
            new_m = st.number_input("월 납입액 수정", value=m_v, step=10000, key=f"nbm_{i}")
            new_c = st.number_input("현재 회차 수정", value=c_v, step=1, key=f"nbc_{i}")
            if st.button("저장", key=f"sb_{i}"):
                st.session_state['savings'][i].update({'월납입액': new_m, '현재회차': new_c}); sort_and_save(); st.rerun()

with tab3:
    # [수정 4] 자산 배분 및 리밸런싱 교육용 UI 추가
    st.markdown("""
    <div class="info-card">
        <h4 style="margin-top:0; color:#3B82F6;">🧭 왜 자산 배분과 리밸런싱을 해야 할까요?</h4>
        <p style="font-size:0.95em; color:#334155; line-height:1.6;">
        <b>1. 완벽한 방어막 (리스크 헷지):</b> 주식 시장이 폭락할 때 안전 자산(예금, 파킹통장 등)이 전체 계좌의 손실을 방어합니다.<br>
        <b>2. 기계적인 수익 창출:</b> 가격이 올라 비중이 커진 자산을 팔고, 저렴해진 자산을 사들이는 '리밸런싱'을 통해 인간의 감정(공포와 탐욕)을 배제하고 <b>강제적인 '저점 매수, 고점 매도'</b>를 실행할 수 있습니다.
        </p>
        <a href="https://www.youtube.com/results?search_query=자산배분+리밸런싱" target="_blank" style="color:#2563EB; text-decoration:none; font-weight:bold;">🔗 자산배분과 리밸런싱의 마법 (유튜브 영상 찾아보기)</a>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("⚖️ 1단계: 목표 비중 설정")
    fixed_p = round(fixed_sav_val / grand_total * 100, 1) if grand_total > 0 else 0
    cols = st.columns(len(active_risks) + 1)
    tgt_w = {}
    for i, r in enumerate(active_risks): tgt_w[r] = cols[i].number_input(f"{r}", value=0.0, step=1.0)
    cols[-1].number_input("고정(은행)", value=float(fixed_p), disabled=True)
    total_input = round(sum(tgt_w.values()) + fixed_p, 1)
    if abs(total_input - 100.0) < 0.2:
        st.success(f"✅ 100% 일치 (현재 {total_input}%)")
        st.divider(); st.subheader("🔬 2단계: 세부 조율")
        re_items = [{"자산군": s['리스크'], "종목명": s['종목명'], "현재금액": int(s['평가']), "현재가": s['현재가']} for s in stock_disp]
        
        # [수정 3] 리밸런싱 목록에도 예금/파킹통장은 '안전'으로 분류
        for sv in st.session_state['savings']:
            if sv.get('종류') in ["예금", "파킹통장"]:
                re_items.append({"자산군": "안전", "종목명": sv.get('상품명'), "현재금액": int(sv.get('월납입액', 0)) * int(sv.get('현재회차', 1)), "현재가": 0})
            else:
                re_items.append({"자산군": "고정(은행)" if sv.get('종류') in ["적금", "주택청약"] else active_risks[-1], "종목명": sv.get('상품명'), "현재금액": int(sv.get('월납입액', 0)) * int(sv.get('현재회차', 0)), "현재가": 0})
        
        existing_grps = set(x['자산군'] for x in re_items)
        for g in active_risks:
            if g not in existing_grps: re_items.append({"자산군": g, "종목명": "💡 신규 자산 필요", "현재금액": 0, "현재가": 0})
        rdf = pd.DataFrame(re_items)
        def style_rebal(df):
            cp = ['#FFCDD2','#FFE0B2','#BBDEFB','#C8E6C9','#E1BEE7','#D7CCC8']
            sdf = pd.DataFrame('', index=df.index, columns=df.columns)
            for i, row in df.iterrows():
                try: ix = active_risks.index(row['자산군'])
                except: ix = -1
                sdf.iloc[i] = f"background-color: {cp[ix % len(cp)] if ix != -1 else '#F5F5F5'}"
            return sdf
        if not rdf.empty:
            rdf['💡 목표(%)'] = rdf.apply(lambda x: round((x['현재금액'] / grand_total * 100), 1), axis=1)
            rdf['sort_key'] = rdf['자산군'].apply(get_risk_weight)
            rdf.sort_values(['sort_key', '현재금액'], ascending=[True, False], inplace=True)
            styled_rdf = rdf[['자산군', '종목명', '현재금액', '💡 목표(%)']].style.apply(style_rebal, axis=None)
            edited = st.data_editor(styled_rdf, use_container_width=True, hide_index=True)
            if st.button("🚀 3단계: 액션 플랜 생성"):
                st.session_state['rebal_df'] = rdf.copy()
                st.session_state['rebal_df']['💡 목표(%)'] = edited['💡 목표(%)'].values
                st.session_state['rebal_go'] = True
            if st.session_state.get('rebal_go'):
                st.divider(); st.subheader("🎯 3단계: 액션 플랜")
                rf = st.session_state['rebal_df']
                rf['목표금액'] = (grand_total * (rf['💡 목표(%)'] / 100)).astype(int)
                rf['차액'] = rf['목표금액'] - rf['현재금액']
                def get_act(row):
                    if row['자산군'] == "고정(은행)": return "🔒 유지", "-"
                    d = row['차액']
                    if d > 10000: return f"🟢 매수 (+{d:,.0f}원)", f"약 {d/row['현재가']:.2f}주" if row['현재가'] > 0 else "-"
                    if d < -10000: return f"🔴 매도 ({abs(d):,.0f}원)", f"약 {abs(d)/row['현재가']:.2f}주" if row['현재가'] > 0 else "-"
                    return "유지", "-"
                rf[['액션', '가이드']] = rf.apply(get_act, axis=1, result_type='expand')
                st.dataframe(rf[['자산군', '종목명', '현재금액', '목표금액', '액션', '가이드']], hide_index=True)
    else: st.warning(f"합계 {total_input}%입니다. 100%를 맞춰주세요!")
