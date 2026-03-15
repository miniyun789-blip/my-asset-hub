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
st.set_page_config(page_title="My Asset Hub V21", layout="wide")

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
# 2. 데이터 수집 엔진 (네이버/업비트/야후)
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

@st.cache_data(ttl=3600)
def fetch_company_name(ticker):
    try:
        info = yf.Ticker(ticker).info
        return info.get('shortName') or info.get('longName') or ticker
    except: return ticker

def verify_and_get_ticker(input_val):
    input_val = input_val.strip()
    upper_val = input_val.upper()
    
    # 1. 코인 체크
    coin_map = {"비트코인": "KRW-BTC", "BTC": "KRW-BTC", "이더리움": "KRW-ETH", "ETH": "KRW-ETH"}
    for key, val in coin_map.items():
        if key in upper_val: return val, val.replace("KRW-", "")
    if upper_val.startswith("KRW-"): return upper_val, upper_val.replace("KRW-", "")
    
    # 2. 직접 티커(알파벳/숫자 6자리) 입력 체크
    if len(upper_val) == 6 and upper_val.isalnum():
        for suffix in [".KS", ".KQ"]:
            try:
                if not yf.Ticker(upper_val + suffix).history(period="1d").empty: 
                    return upper_val + suffix, fetch_company_name(upper_val + suffix)
            except: pass
    try:
        if not yf.Ticker(upper_val).history(period="1d").empty: 
            return upper_val, fetch_company_name(upper_val)
    except: pass

    # 3. [신규 로직] 네이버 금융 API로 한글 종목명 자동 검색
    try:
        url = f"https://ac.finance.naver.com/ac?q={input_val}&q_enc=utf-8&st=111&frm=stock&r_format=json&r_enc=utf-8&r_unicode=0&t_koreng=1&req=1"
        res = requests.get(url, timeout=3).json()
        if res.get('items') and res['items'][0]:
            best_match = res['items'][0][0] # 예: ['삼성전자', ['005930'], ...]
            kor_name = best_match[0][0]
            ticker_code = best_match[1][0]
            for suffix in [".KS", ".KQ"]:
                try:
                    if not yf.Ticker(ticker_code + suffix).history(period="1d").empty:
                        return ticker_code + suffix, kor_name
                except: pass
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
asset_input = st.sidebar.text_input("🔍 종목/티커 검색", placeholder="예: 삼성전자, 카카오, AAPL, BTC")
st.sidebar.markdown("[👉 종목코드 찾기 (네이버)](https://finance.naver.com/)")

if asset_input:
    with st.spinner("종목 검색 중..."):
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
        st.sidebar.error("⚠️ 검색 실패. 정확한 이름이나 티커를 입력해 주세요.")

with st.sidebar.expander("🏦 은행 자산 추가", expanded=False):
    bank_type = st.selectbox("종류", ["적금", "주택청약", "예금", "파킹통장"])
    # [수정] 라벨을 통장이름으로 변경
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

port_group = {"국내 주식": 0, "해외 주식": 0, "가상화폐": 0}
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
for sav in st.session_state['savings']:
    bank_type = sav.get('종류', '적금')
    sav_monthly = sav.get('월납입액', 0)
    sav_curr = sav.get('현재회차', 1)
    amt = sav_monthly * sav_curr
    total_sav_val += amt
    total_buy += amt
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
rem_pct = max(100.0 - (grand_total/target*100), 0.0)
status_color = "goal-green" if rem_pct == 0 else "goal-red"
st.markdown(f"### 🏆 목표 자산 ({target:,.0f}원) 현황")
st.markdown(f"<span class='{status_color}'>목표까지 {rem_pct:.1f}% 남았습니다! {'🎉' if rem_pct==0 else '🔥'}</span>", unsafe_allow_html=True)
st.progress(min(grand_total/target, 1.0))

c1, c2, c3 = st.columns(3)
c1.metric("총 자산", f"{grand_total:,.0f}원")
c2.metric("매수 원금", f"{total_buy:,.0f}원")
c3.metric("수익금", f"{grand_total-total_buy:,.0f}원", f"{(grand_total-total_buy)/total_buy*100:.1f}%" if total_buy>0 else "0%")

st.markdown("---")

tab1, tab2, tab3 = st.tabs(["📊 대시보드", "📋 자산 관리", "⚖️ 리밸런싱"])

with tab1:
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.subheader("⚖️ 포트폴리오 비중")
        fig1 = go.Figure(data=[go.Pie(labels=list(port_group.keys())+['은행(안전)'], values=list(port_group.values())+[total_sav_val], hole=.4)])
        fig1.update_traces(textposition='inside', textinfo='percent', textfont_size=16) 
        fig1.update_layout(margin=dict(l=5, r=5, t=10, b=10), height=300, showlegend=True, 
                          legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5))
        st.plotly_chart(fig1, use_container_width=True)
        
    with col_p2:
        st.subheader("🛡️ 리스크 다각화")
        fig2 = go.Figure(data=[go.Pie(labels=list(risk_group.keys()), values=list(risk_group.values()), hole=.4, marker_colors=['#E74C3C','#F39C12','#3498DB','#2ECC71'])])
        fig2.update_traces(textposition='inside', textinfo='percent', textfont_size=16) 
        fig2.update_layout(margin=dict(l=5, r=5, t=10, b=10), height=300, showlegend=True,
                          legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5))
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader("🚀 자산 성장 타임라인")
    if not history_df.empty:
        time_view = st.radio("보기 옵션", ["일별", "월별", "연별"], horizontal=True)
        history_df['날짜'] = pd.to_datetime(history_df['날짜'])
        plot_df = history_df.copy()
        
        if time_view == "일별":
            fig_line = px.area(plot_df, x="날짜", y="총자산", markers=True, color_discrete_sequence=['#2E86C1'])
            fig_line.update_xaxes(tickformat="%m.%d", tickangle=-45)
        elif time_view == "월별":
            plot_df['날짜'] = plot_df['날짜'].dt.to_period('M').dt.to_timestamp()
            plot_df = plot_df.groupby('날짜')['총자산'].last().reset_index()
            fig_line = px.area(plot_df, x="날짜", y="총자산", markers=True, color_discrete_sequence=['#2E86C1'])
            fig_line.update_xaxes(tickformat="%y.%m", tickangle=-45)
        elif time_view == "연별":
            plot_df['날짜'] = plot_df['날짜'].dt.to_period('Y').dt.to_timestamp()
            plot_df = plot_df.groupby('날짜')['총자산'].last().reset_index()
            fig_line = px.area(plot_df, x="날짜", y="총자산", markers=True, color_discrete_sequence=['#2E86C1'])
            fig_line.update_xaxes(tickformat="%Y", tickangle=0)
            
        fig_line.update_layout(margin=dict(l=5, r=5, t=10, b=10), height=300, hovermode="x unified")
        st.plotly_chart(fig_line, use_container_width=True)

with tab2:
    st.subheader("📈 투자 자산 내역")
    for item in stock_display:
        c_i, c_e, c_d = st.columns([5, 1, 1])
        with c_i:
            profit_sign = "🔥" if item['수익률'] > 0 else "❄️"
            st.markdown(f"**{item['종목명']} ({item['티커']})** | 등급: **[{item['리스크']}]** | {profit_sign} **{item['수익률']:.2f}%**")
            cur_sym = "$" if item['해외'] and not item['티커'].startswith("KRW-") else "₩"
            st.caption(f"↳ 매수단가: **{item['매수평단가']:,.2f}{cur_sym}** | 수량: **{item['보유수량']:.2f}개** | 매수금액: **{item['매수']:,.0f}원** | 평가액: **{item['평가']:,.0f}원**")
        with c_e:
            if st.button("✏️", key=f"e_{item['ID']}"): st.session_state[f"em_{item['ID']}"] = not st.session_state.get(f"em_{item['ID']}", False)
        with c_d:
            if st.button("🗑️", key=f"d_{item['ID']}"): st.session_state['stocks'].pop(item['ID']); save_data(st.session_state['stocks'], STOCKS_FILE); st.rerun()
        if st.session_state.get(f"em_{item['ID']}", False):
            new_p = st.number_input("평단가", value=float(st.session_state['stocks'][item['ID']].get('매수평단가', 0)), key=f"np_{item['ID']}")
            new_q = st.number_input("수량", value=float(st.session_state['stocks'][item['ID']].get('보유수량', 0)), key=f"nq_{item['ID']}")
            if st.button("저장", key=f"sv_{item['ID']}"):
                st.session_state['stocks'][item['ID']].update({'매수평단가': new_p, '보유수량': new_q})
                save_data(st.session_state['stocks'], STOCKS_FILE); st.rerun()
                
    st.divider()
    st.subheader("🏦 은행 자산 내역")
    for idx, sav in enumerate(st.session_state['savings']):
        c_i, c_e, c_d = st.columns([5, 1, 1])
        with c_i:
            bank_type = sav.get('종류', '적금')
            principal = sav.get('월납입액', 0) * sav.get('총회차', 1)
            rate = sav.get('이율', 3.0)
            multiplier = (sav.get('총회차', 1) + 1) / 2 / 12 if bank_type == "적금" else sav.get('총회차', 1) / 12
            exp_int = principal * (rate / 100) * multiplier
            st.markdown(f"**[{bank_type}] {sav.get('상품명', '이름없음')}** (연 **{rate}%**) | 원금: **{principal:,.0f}원** | 만기 시 예상 이자: **+ {exp_int:,.0f}원**")
            
            # [수정] 만기 달성 체크 및 UI 에러(progress > 1.0) 방어
            c_month = sav.get('현재회차', 0)
            t_month = sav.get('총회차', 1)
            rem_m = t_month - c_month
            
            if rem_m <= 0:
                st.caption("↳ 🎉 **만기 달성!** 축하합니다!")
                st.progress(1.0)
            else:
                st.caption(f"↳ 총 {t_month}개월 중 **{c_month}개월 차** 진행 중 (만기까지 **{rem_m}개월** 남음)")
                prog_val = min(1.0, max(0.0, c_month / t_month if t_month > 0 else 0))
                st.progress(prog_val)
                
        with c_e:
            if st.button("✏️", key=f"es_{idx}"): st.session_state[f"esm_{idx}"] = not st.session_state.get(f"esm_{idx}", False)
        with c_d:
            if st.button("🗑️", key=f"ds_{idx}"): st.session_state['savings'].pop(idx); save_data(st.session_state['savings'], SAVINGS_FILE); st.rerun()
        if st.session_state.get(f"esm_{idx}", False):
            col_e1, col_e2, col_e3, col_e4 = st.columns(4)
            new_m = col_e1.number_input("월 납입액", value=int(sav.get('월납입액', 0)), step=10000, key=f"sm_{idx}")
            new_c = col_e2.number_input("현재 회차", value=int(sav.get('현재회차', 1)), step=1, key=f"sc_{idx}")
            new_r = col_e3.number_input("이율(%)", value=float(sav.get('이율', 3.0)), step=0.1, key=f"sr_{idx}")
            if col_e4.button("✔️ 저장", key=f"ssv_{idx}"):
                st.session_state['savings'][idx].update({'월납입액': new_m, '현재회차': new_c, '이율': new_r})
                st.session_state[f"esm_{idx}"] = False
                save_data(st.session_state['savings'], SAVINGS_FILE); st.rerun()

with tab3:
    st.subheader("⚖️ 1단계: 그룹별 목표 설정")
    fixed_p = round(fixed_sav_val/grand_total*100, 1) if grand_total>0 else 0
    st.info(f"🔒 고정 자산(적금/청약) 비중: **{fixed_p}%**")
    
    rcols = st.columns(5)
    t1 = rcols[0].number_input("1.초고위험", value=0.0, step=1.0)
    t2 = rcols[1].number_input("2.위험", value=0.0, step=1.0)
    t3 = rcols[2].number_input("3.중립", value=0.0, step=1.0)
    t4 = rcols[3].number_input("4.안전(유동)", value=0.0, step=1.0)
    t5 = rcols[4].number_input("5.안전(고정)", value=float(fixed_p), disabled=True)
    
    if abs(t1+t2+t3+t4+t5-100) < 0.2:
        st.success("✅ 비중 합계 100% 일치")
        st.divider()
        st.subheader("🔬 2단계: 종목별 세부 조율")
        
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

            edited = st.data_editor(styled_rdf, use_container_width=True, hide_index=True,
                                   column_config={"💡 목표(%)": st.column_config.NumberColumn(min_value=0.0, max_value=100.0, step=0.1)})
            
            edited['목표금액'] = (grand_total * (edited['💡 목표(%)'] / 100)).astype(int)
            edited['차액'] = edited['목표금액'] - edited['현재금액']
            edited['현재가'] = rdf['현재가']
            edited['티커'] = rdf['티커']
            
            def get_action(row):
                if row['자산군'] == "5. 안전(고정)": return "🔒 유지", "-"
                d = row['차액']
                p = row['현재가']
                c = row['티커'].startswith("KRW-")
                if d > 10000:
                    s = f" (약 {d/p:,.2f}개)" if c else (f" (약 {int(d/p):,}주)" if p>0 else "")
                    return f"🟢 매수 (+{d:,.0f}원)", s
                elif d < -10000:
                    s = f" (약 {abs(d)/p:,.2f}개)" if c else (f" (약 {int(abs(d)/p):,}주)" if p>0 else "")
                    return f"🔴 매도 ({abs(d):,.0f}원)", s
                return "유지", "-"
                
            edited[['액션', '수량가이드']] = edited.apply(get_action, axis=1, result_type='expand')
            final_df = edited[['자산군', '종목명', '현재금액', '목표금액', '액션', '수량가이드']]
            
            try: f_style = final_df.style.map(color_risk, subset=['자산군']).format({"현재금액": "{:,.0f}", "목표금액": "{:,.0f}"})
            except: f_style = final_df.style.applymap(color_risk, subset=['자산군']).format({"현재금액": "{:,.0f}", "목표금액": "{:,.0f}"})
            st.dataframe(f_style, hide_index=True, use_container_width=True)
            st.info("💡 자산군 열을 클릭하면 위험도 순으로 자동 정렬됩니다.")
