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
import threading

# ==========================================
# [중요] 대표님 전용 구글 앱스 스크립트 웹 앱 URL
# ==========================================
API_URL = "https://script.google.com/macros/s/AKfycbx6-L0Rl4GlpZloBZ79M9mqHYSnSTOCaaHjVnhF5mYKcPF42QaShH0A54vD6WUz4O45/exec"

# ==========================================
# 1. 앱 기본 설정 & UI 스타일링
# ==========================================
st.set_page_config(page_title="My Asset Hub V40", layout="wide")

st.markdown("""
    <style>
    .block-container { 
        padding-top: 1.5rem; 
        padding-left: 1rem; 
        padding-right: 1rem; 
    }
    p, .stMarkdown, div[data-testid="stText"] { 
        font-size: 1.1rem !important; 
    }
    .stMetric label { font-size: 1rem !important; }
    .stMetric value { font-size: 1.8rem !important; }
    .stDataFrame { font-size: 1rem !important; }
    .goal-red { color: #E74C3C; font-weight: 900; font-size: 1.4rem; }
    .goal-green { color: #2ECC71; font-weight: 900; font-size: 1.4rem; }
    .green-text { 
        color: #2ECC71; 
        font-size: 0.95em; 
        margin-bottom: 10px; 
        font-weight: 500; 
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. 클라우드 고속 동기화 엔진 (Batch Sync)
# ==========================================
def load_cloud_data(sheet_name):
    try:
        res = requests.get(f"{API_URL}?sheetName={sheet_name}", timeout=8)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list):
                return data
        return []
    except Exception as e:
        return []

def save_all_to_cloud():
    try:
        payload = {
            "stocks": st.session_state['stocks'],
            "savings": st.session_state['savings'],
            "config": [st.session_state['config']]
        }
        res = requests.post(API_URL, data=json.dumps(payload), timeout=15)
        if res.status_code == 200:
            return True
        else:
            return False
    except Exception as e:
        return False

# 최초 실행 시 데이터 불러오기
if 'stocks' not in st.session_state: 
    with st.spinner("구글 금고에서 자산 정보 가져오는 중..."):
        st.session_state['stocks'] = load_cloud_data('stocks')

if 'savings' not in st.session_state: 
    st.session_state['savings'] = load_cloud_data('savings')

if 'config' not in st.session_state: 
    cfg = load_cloud_data('config')
    if cfg:
        st.session_state['config'] = cfg[0]
    else:
        st.session_state['config'] = {
            "target_asset": 1000000000, 
            "risk_levels": "초고위험,위험,중립,안전", 
            "auto_save": True
        }

# 리스크 분류 리스트 파싱
raw_risks = st.session_state['config'].get('risk_levels', "초고위험,위험,중립,안전")
active_risks = [r.strip() for r in raw_risks.split(',') if r.strip()]

def get_risk_weight(r):
    try: 
        return active_risks.index(r)
    except ValueError: 
        return 99

def sort_and_save():
    # 정렬: 리스크 등급 순 -> 평가액 큰 순 (내림차순)
    st.session_state['stocks'].sort(
        key=lambda x: (
            get_risk_weight(x.get('리스크')), 
            -(float(x.get('매수평단가', 0)) * float(x.get('보유수량', 0)))
        )
    )
    
    # 자동 저장 토글이 켜져 있을 때만 동기화
    if st.session_state['config'].get('auto_save', True):
        return save_all_to_cloud()
    return True

# ==========================================
# 3. 데이터 수집 엔진 (구글 파이낸스 & KRX)
# ==========================================
kst_now = datetime.utcnow() + timedelta(hours=9)
if kst_now.hour < 3:
    logic_date_str = (kst_now - timedelta(days=1)).strftime('%Y-%m-%d')
else:
    logic_date_str = kst_now.strftime('%Y-%m-%d')

@st.cache_data(ttl=86400)
def load_market_data():
    dfs = []
    try:
        df_krx = fdr.StockListing('KRX')
        df_krx['시장'] = 'KRX'
        dfs.append(df_krx[['Code', 'Name', '시장']])
        
        df_etf = fdr.StockListing('ETF/KR')
        df_etf['시장'] = 'ETF/KR'
        dfs.append(df_etf[['Symbol', 'Name', '시장']].rename(columns={'Symbol':'Code'}))
        
        for mkt in ['NASDAQ', 'NYSE', 'AMEX']:
            df_us = fdr.StockListing(mkt)
            df_us['시장'] = mkt
            dfs.append(df_us[['Symbol', 'Name', '시장']].rename(columns={'Symbol':'Code'}))
            
    except Exception as e:
        pass
        
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return None

@st.cache_data(ttl=600)
def get_exchange_rate():
    try:
        res = requests.get("https://www.google.com/finance/quote/USD-KRW", headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(res.text, 'html.parser')
        price_str = soup.select_one('.YMlKec.fxKbKc').text
        return float(price_str.replace(',', ''))
    except Exception as e:
        return 1350.0

@st.cache_data(ttl=300)
def get_price(ticker):
    # [핵심 수정] 엑셀에서 넘어온 빈칸(None, NaN) 방어 로직
    if ticker is None or pd.isna(ticker):
        return 0.0
        
    # 문자로 강제 변환 및 공백 제거
    ticker = str(ticker).strip()
    
    if not ticker:
        return 0.0

    # 1. 가상화폐 (업비트)
    if ticker.startswith("KRW-"):
        try: 
            url = f"https://api.upbit.com/v1/ticker?markets={ticker}"
            res_json = requests.get(url).json()
            return float(res_json[0]['trade_price'])
        except Exception as e: 
            return 0.0
            
    # 2. 일반 주식/ETF (구글 파이낸스)
    clean_ticker = ticker.replace('.KS', '').replace('.KQ', '')
    markets = [
        f"{clean_ticker}:KRX", 
        f"{clean_ticker}:KOSDAQ", 
        f"{clean_ticker}:NASDAQ", 
        f"{clean_ticker}:NYSE", 
        f"{clean_ticker}:NYSEARCA"
    ]
    
    for gf_ticker in markets:
        try:
            url = f"https://www.google.com/finance/quote/{gf_ticker}"
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
            if 'YMlKec fxKbKc' in res.text:
                soup = BeautifulSoup(res.text, 'html.parser')
                price_str = soup.select_one('.YMlKec.fxKbKc').text
                clean_price = price_str.replace('₩', '').replace('$', '').replace(',', '')
                return float(clean_price)
        except Exception as e: 
            pass
            
    return 0.0

exchange_rate = get_exchange_rate()

# ==========================================
# 4. 사이드바 (컨트롤러)
# ==========================================
with st.sidebar:
    st.title("🛠️ 컨트롤러")
    st.metric("💵 실시간 환율 (구글 기준)", f"{exchange_rate:,.2f} 원")
    
    st.divider()
    
    # 동기화 스위치
    auto_save_val = st.toggle(
        "🔄 실시간 클라우드 동기화", 
        value=st.session_state['config'].get('auto_save', True)
    )
    st.session_state['config']['auto_save'] = auto_save_val
    
    if not auto_save_val:
        if st.button("🚀 지금 즉시 엑셀로 보내기", use_container_width=True, type="primary"):
            with st.spinner("구글 시트에 고속 동기화 중..."):
                if save_all_to_cloud(): 
                    st.toast("✅ 엑셀 동기화 성공!")
                else: 
                    st.error("❌ 연결 실패. 네트워크 상태를 확인하세요.")
                    
    st.divider()

with st.sidebar.expander("⚙️ 시스템 및 목표 설정"):
    current_tgt = int(st.session_state['config'].get('target_asset', 1000000000))
    new_tgt_str = st.text_input("목표 금액 (원)", value=f"{current_tgt:,}")
    
    if st.button("목표 저장"):
        try:
            st.session_state['config']['target_asset'] = int(new_tgt_str.replace(",", ""))
            sort_and_save()
            st.rerun()
        except ValueError:
            st.error("숫자와 콤마만 입력해주세요.")

st.sidebar.markdown("### ➕ 투자 자산 추가")
asset_input = st.sidebar.text_input("🔍 종목/티커 검색", placeholder="예: 삼성전자, SCHD, 리플")

if asset_input:
    options = []
    coin_map = {
        "비트코인": "KRW-BTC", 
        "이더리움": "KRW-ETH", 
        "리플": "KRW-XRP", 
        "솔라나": "KRW-SOL", 
        "도지코인": "KRW-DOGE"
    }
    
    for k, v in coin_map.items():
        if k in asset_input.upper(): 
            options.append(f"[가상화폐] {k} ({v})")
            
    df_m = load_market_data()
    if df_m is not None:
        mask = df_m['Name'].str.contains(asset_input, case=False, na=False) | df_m['Code'].str.contains(asset_input, case=False, na=False)
        for _, r in df_m[mask].head(20).iterrows(): 
            options.append(f"[{r['시장']}] {r['Name']} ({r['Code']})")
            
    if re.match(r"^[A-Za-z0-9]+$", asset_input.strip()):
        options.append(f"[해외 직접입력] {asset_input.upper()} ({asset_input.upper()})")
    
    options = list(dict.fromkeys(options))
    
    if options:
        selected = st.sidebar.selectbox("💡 정확한 종목 선택", options)
        m = re.match(r"\[(.*?)\] (.*) \((.*?)\)", selected)
        
        if m:
            sel_market = m.group(1)
            sel_name = m.group(2)
            sel_code = m.group(3)
            
            is_foreign = (sel_market in ['NASDAQ', 'NYSE', 'AMEX', '해외 직접입력'])
            curr_label = "달러 $" if is_foreign else "원 ₩"
            
            raw_p = st.sidebar.text_input(f"매수 단가 ({curr_label})", value="0")
            
            try: 
                new_p = float(raw_p.replace(',', ''))
            except ValueError: 
                new_p = 0.0
                
            new_q = st.sidebar.number_input("보유 수량", min_value=0.0, step=0.01)
            risk_lv = st.sidebar.selectbox("리스크 분류 선택", active_risks)
            
            if st.sidebar.button("투자 자산 저장", use_container_width=True):
                existing_idx = next((i for i, s in enumerate(st.session_state['stocks']) if str(s.get('티커', '')) == sel_code), None)
                
                if existing_idx is not None:
                    old_stock = st.session_state['stocks'][existing_idx]
                    old_q = float(old_stock.get('보유수량', 0))
                    old_p = float(old_stock.get('매수평단가', 0))
                    
                    final_q = old_q + new_q
                    if final_q > 0:
                        final_p = ((old_p * old_q) + (new_p * new_q)) / final_q 
                    else:
                        final_p = 0
                        
                    st.session_state['stocks'][existing_idx].update({
                        '매수평단가': final_p, 
                        '보유수량': final_q
                    })
                else:
                    st.session_state['stocks'].append({
                        "종목명": sel_name, 
                        "티커": sel_code, 
                        "매수평단가": new_p, 
                        "보유수량": new_q, 
                        "해외여부": is_foreign, 
                        "리스크": risk_lv
                    })
                
                if sort_and_save(): 
                    st.toast("✅ 자산 업데이트 완료!")
                st.rerun()

with st.sidebar.expander("⚙️ 리스크 분류 관리"):
    risk_df = pd.DataFrame({"리스크 명칭": active_risks})
    edited_risk = st.data_editor(risk_df, num_rows="dynamic", use_container_width=True, hide_index=True)
    if st.button("✔️ 분류 저장"):
        new_risk_str = ",".join(edited_risk['리스크 명칭'].dropna().tolist())
        st.session_state['config']['risk_levels'] = new_risk_str
        sort_and_save()
        st.rerun()

with st.sidebar.expander("🏦 은행 자산 추가"):
    b_type = st.selectbox("종류", ["적금", "주택청약", "예금", "파킹통장"])
    b_name = st.text_input("통장이름")
    raw_m = st.text_input("월 납입액 (원)", value="1,000,000")
    b_curr = st.number_input("현재 회차", min_value=1)
    b_total = st.number_input("총 만기 회차", min_value=1)
    b_rate = st.number_input("연 이율 (%)", min_value=0.0, step=0.1, value=3.0)
    
    if st.button("은행 자산 저장"):
        try: 
            m_val = int(raw_m.replace(',', ''))
        except ValueError: 
            m_val = 0
            
        st.session_state['savings'].append({
            "종류": b_type, 
            "상품명": b_name, 
            "월납입액": m_val, 
            "현재회차": b_curr, 
            "총회차": b_total, 
            "이율": b_rate
        })
        sort_and_save()
        st.rerun()

# ==========================================
# 5. 메인 대시보드 연산
# ==========================================
st.title("💰 My Asset Hub V40")

# 초기화
risk_group = {r: 0 for r in active_risks}
risk_group["고정(은행)"] = 0
port_group = {"가상화폐": 0, "해외 주식": 0, "국내 주식": 0} 
stock_disp = []
total_buy = 0 

# 주식 자산 연산
for idx, s in enumerate(st.session_state['stocks']):
    ticker = str(s.get('티커', '')).strip()
    is_foreign = s.get('해외여부', False)
    buy_p = float(s.get('매수평단가', 0))
    qty = float(s.get('보유수량', 0))
    
    curr = get_price(ticker)
    curr_krw = curr * exchange_rate if is_foreign else curr
    buy_amt = buy_p * qty * (exchange_rate if is_foreign else 1)
    eval_amt = curr_krw * qty
    
    total_buy += buy_amt
    
    if ticker.startswith("KRW-"): 
        port_group["가상화폐"] += eval_amt
    elif is_foreign: 
        port_group["해외 주식"] += eval_amt
    else: 
        port_group["국내 주식"] += eval_amt
    
    risk_cat = s.get('리스크', active_risks[0] if active_risks else '기타')
    risk_group[risk_cat] = risk_group.get(risk_cat, 0) + eval_amt
    
    if buy_amt > 0:
        profit = (eval_amt - buy_amt) / buy_amt * 100 
    else:
        profit = 0
        
    stock_disp.append({
        "ID": idx, 
        "종목명": s.get('종목명'), 
        "티커": ticker, 
        "매수": buy_amt, 
        "평가": eval_amt, 
        "수익률": profit, 
        "리스크": risk_cat, 
        "현재가": curr, 
        "해외": is_foreign, 
        "매수평단가": buy_p, 
        "보유수량": qty
    })

# 은행 자산 연산
total_sav_val = 0
total_bank_principal = 0
fixed_sav_val = 0

for sav in st.session_state['savings']:
    m_val = int(sav.get('월납입액', 0))
    c_val = int(sav.get('현재회차', 0))
    t_val = int(sav.get('총회차', 1))
    
    amt = m_val * c_val
    total_sav_val += amt
    total_buy += amt
    total_bank_principal += (m_val * t_val)
    
    if sav.get('종류') in ["적금", "주택청약"]: 
        fixed_sav_val += amt

risk_group["고정(은행)"] += total_sav_val

grand_total = sum(port_group.values()) + total_sav_val

# 히스토리 동기화 (Background Thread)
history_data = load_cloud_data('history')
if history_data:
    history_df = pd.DataFrame(history_data)
else:
    history_df = pd.DataFrame(columns=["날짜", "총자산"])

if grand_total > 0:
    if not history_df.empty and logic_date_str in history_df['날짜'].values:
        history_df.loc[history_df['날짜'] == logic_date_str, '총자산'] = grand_total
    else:
        new_row = pd.DataFrame([{"날짜": logic_date_str, "총자산": grand_total}])
        history_df = pd.concat([history_df, new_row], ignore_index=True)
    
    def save_history_bg():
        try:
            payload = {
                "sheetName": "history", 
                "data": history_df.to_dict('records')
            }
            requests.post(API_URL, data=json.dumps(payload), timeout=5)
        except Exception as e:
            pass
            
    threading.Thread(target=save_history_bg).start()

# 대시보드 상단 메트릭
target = st.session_state['config'].get('target_asset', 1000000000)
if target > 0:
    achieved = (grand_total / target * 100) 
else:
    achieved = 0

if achieved < 100: 
    st.markdown(f"### 🏆 목표 ({target:,.0f}원) | <span class='goal-red'>{100-achieved:.1f}% 남음 🔥</span>", unsafe_allow_html=True)
else: 
    st.markdown(f"### 🏆 목표 ({target:,.0f}원) | <span class='goal-green'>🎉 {achieved-100:.1f}% 초과 달성 🎉</span>", unsafe_allow_html=True)
st.progress(min(achieved / 100, 1.0))

c1, c2, c3 = st.columns(3)
c1.metric("총 자산", f"{grand_total:,.0f}원")
c2.metric("매수 원금", f"{total_buy:,.0f}원")

if total_buy > 0:
    profit_amt = grand_total - total_buy
    profit_pct = (profit_amt) / total_buy * 100
    c3.metric("수익금", f"{profit_amt:,.0f}원", f"{profit_pct:.1f}%")
else:
    c3.metric("수익금", "0원", "0%")

st.markdown("---")

tab1, tab2, tab3 = st.tabs(["📊 대시보드", "📋 자산 관리", "⚖️ 리밸런싱 (3-Step)"])

with tab1:
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        port_labels = ["가상화폐", "해외 주식", "국내 주식", "은행(안전)"]
        port_values = [port_group["가상화폐"], port_group["해외 주식"], port_group["국내 주식"], total_sav_val]
        port_colors = ['#F39C12', '#9B59B6', '#3498DB', '#1ABC9C']
        
        fig1 = go.Figure(data=[go.Pie(
            labels=port_labels, 
            values=port_values, 
            hole=.4, 
            sort=False, 
            marker_colors=port_colors
        )])
        fig1.update_layout(title="포트폴리오 비중", height=320, margin=dict(t=40, b=10))
        st.plotly_chart(fig1, use_container_width=True)
        
    with col_p2:
        risk_labels = list(risk_group.keys())
        risk_values = list(risk_group.values())
        risk_colors = ['#E74C3C', '#F39C12', '#3498DB', '#2ECC71', '#9B59B6', '#1ABC9C', '#34495E']
        
        fig2 = go.Figure(data=[go.Pie(
            labels=risk_labels, 
            values=risk_values, 
            hole=.4, 
            marker_colors=risk_colors
        )])
        fig2.update_layout(title="리스크 다각화", height=320, margin=dict(t=40, b=10))
        st.plotly_chart(fig2, use_container_width=True)
    
    if not history_df.empty:
        st.subheader("🚀 자산 성장 타임라인 (03:00 KST)")
        fig_line = px.area(
            history_df, 
            x="날짜", 
            y="총자산", 
            markers=True, 
            color_discrete_sequence=['#2E86C1']
        )
        fig_line.update_layout(height=300, margin=dict(t=10, b=10))
        st.plotly_chart(fig_line, use_container_width=True, config={'staticPlot': True})

with tab2:
    total_eval = sum(x['평가'] for x in stock_disp)
    st.subheader(f"📈 투자 자산 내역 (총 평가: {total_eval:,.0f}원)")
    
    # 정렬 (리스크 가중치 -> 평가액 내림차순)
    stock_disp.sort(key=lambda x: (get_risk_weight(x['리스크']), -x['평가']))
    
    for s in stock_disp:
        c_i, c_e, c_d = st.columns([6, 0.7, 0.7])
        with c_i:
            cur_s = "$" if s['해외'] else "₩"
            profit_icon = '🔥' if s['수익률'] > 0 else '❄️'
            
            st.markdown(f"**{s['종목명']} ({s['티커']})** | **[{s['리스크']}]** | {profit_icon} **{s['수익률']:.2f}%**")
            
            # [복구 유지] 초록색 폰트 테마 적용
            green_html = f"""
            <div class='green-text'>
                ↳ 평단가(수수료제외): <b>{s['매수평단가']:,.2f}{cur_s}</b> | 
                수량: <b>{s['보유수량']:.2f}</b> | 
                평가: <b>{s['평가']:,.0f}원</b>
            </div>
            """
            st.markdown(green_html, unsafe_allow_html=True)
            
        with c_e:
            if st.button("✏️", key=f"e_{s['ID']}"): 
                st.session_state[f"em_{s['ID']}"] = not st.session_state.get(f"em_{s['ID']}", False)
        with c_d:
            if st.button("🗑️", key=f"d_{s['ID']}"): 
                st.session_state['stocks'].pop(s['ID'])
                sort_and_save()
                st.rerun()
                
        if st.session_state.get(f"em_{s['ID']}", False):
            new_p = st.number_input("평단가 수정", value=float(s['매수평단가']), key=f"np_{s['ID']}")
            new_q = st.number_input("수량 수정", value=float(s['보유수량']), key=f"nq_{s['ID']}")
            if st.button("저장", key=f"sv_{s['ID']}"):
                st.session_state['stocks'][s['ID']].update({
                    '매수평단가': new_p, 
                    '보유수량': new_q
                })
                sort_and_save()
                st.rerun()
    
    st.divider()
    st.subheader(f"🏦 은행 자산 내역 (총 원금: {total_bank_principal:,.0f}원)")
    
    for i, sav in enumerate(st.session_state['savings']):
        c_i, c_e, c_d = st.columns([6, 0.7, 0.7])
        with c_i:
            s_type = sav.get('종류', '정보없음')
            s_name = sav.get('상품명', '이름없음')
            s_rate = sav.get('이율', 0)
            
            m_v = int(sav.get('월납입액', 0))
            c_v = int(sav.get('현재회차', 0))
            t_v = int(sav.get('총회차', 1))
            
            total_principal = m_v * t_v
            
            st.markdown(f"**[{s_type}] {s_name}** (연 {s_rate}%) | 원금: {total_principal:,.0f}원")
            
            # [복구 유지] 초록색 폰트 테마 적용
            st.markdown(f"<div class='green-text'>↳ {c_v}/{t_v}개월 진행 중</div>", unsafe_allow_html=True)
            
            if t_v > 0:
                st.progress(min(1.0, c_v / t_v))
            else:
                st.progress(0)
                
        with c_e:
            if st.button("✏️", key=f"eb_{i}"): 
                st.session_state[f"ebm_{i}"] = not st.session_state.get(f"ebm_{i}", False)
        with c_d:
            if st.button("🗑️", key=f"db_{i}"): 
                st.session_state['savings'].pop(i)
                sort_and_save()
                st.rerun()

with tab3:
    st.subheader("⚖️ 1단계: 비중 설정")
    if grand_total > 0:
        fixed_p = round(fixed_sav_val / grand_total * 100, 1) 
    else:
        fixed_p = 0
        
    cols = st.columns(len(active_risks) + 1)
    tgt_w = {}
    
    for i, r in enumerate(active_risks): 
        tgt_w[r] = cols[i].number_input(f"{r}", value=0.0, step=1.0)
        
    cols[-1].number_input("고정(은행)", value=float(fixed_p), disabled=True)
    
    total_input = round(sum(tgt_w.values()) + fixed_p, 1)
    
    if abs(total_input - 100.0) < 0.2:
        st.success(f"✅ 100% 일치 (현재 {total_input}%)")
        st.divider()
        st.subheader("🔬 2단계: 세부 조율")
        
        re_items = []
        for s in stock_disp: 
            re_items.append({
                "자산군": s['리스크'], 
                "종목명": s['종목명'], 
                "현재금액": int(s['평가']), 
                "현재가": s['현재가']
            })
            
        for sv in st.session_state['savings']:
            if sv.get('종류') in ["적금", "주택청약"]:
                grp = "고정(은행)"
            else:
                grp = active_risks[-1]
                
            re_items.append({
                "자산군": grp, 
                "종목명": sv.get('상품명'), 
                "현재금액": int(sv.get('월납입액', 0)) * int(sv.get('현재회차', 0)), 
                "현재가": 0
            })
        
        # 없는 자산군 표시 로직
        existing_grps = set(x['자산군'] for x in re_items)
        for g in active_risks:
            if g not in existing_grps: 
                re_items.append({
                    "자산군": g, 
                    "종목명": "💡 신규 자산 필요", 
                    "현재금액": 0, 
                    "현재가": 0
                })

        rdf = pd.DataFrame(re_items)
        
        # [복구 유지] 2단계 파스텔 매트릭스 색상 적용 함수
        def style_rebal(df):
            cp = ['#FFCDD2','#FFE0B2','#BBDEFB','#C8E6C9','#E1BEE7','#D7CCC8']
            sdf = pd.DataFrame('', index=df.index, columns=df.columns)
            
            for i, row in df.iterrows():
                try: 
                    ix = active_risks.index(row['자산군'])
                except ValueError: 
                    ix = -1
                    
                if ix != -1:
                    color = cp[ix % len(cp)]
                else:
                    color = '#F5F5F5'
                    
                sdf.iloc[i] = f'background-color: {color}'
                
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
                st.divider()
                st.subheader("🎯 3단계: 액션 플랜")
                
                rf = st.session_state['rebal_df']
                rf['목표금액'] = (grand_total * (rf['💡 목표(%)'] / 100)).astype(int)
                rf['차액'] = rf['목표금액'] - rf['현재금액']
                
                def get_act(row):
                    if row['자산군'] == "고정(은행)": 
                        return "🔒 유지", "-"
                        
                    d = row['차액']
                    if d > 10000: 
                        guide = f"약 {d/row['현재가']:.2f}주" if row['현재가'] > 0 else "-"
                        return f"🟢 매수 (+{d:,.0f}원)", guide
                        
                    if d < -10000: 
                        guide = f"약 {abs(d)/row['현재가']:.2f}주" if row['현재가'] > 0 else "-"
                        return f"🔴 매도 ({abs(d):,.0f}원)", guide
                        
                    return "유지", "-"
                    
                rf[['액션', '가이드']] = rf.apply(get_act, axis=1, result_type='expand')
                
                display_cols = ['자산군', '종목명', '현재금액', '목표금액', '액션', '가이드']
                st.dataframe(rf[display_cols], hide_index=True)
    else:
        st.warning(f"합계 {total_input}%입니다. 100%를 맞춰주세요!")
