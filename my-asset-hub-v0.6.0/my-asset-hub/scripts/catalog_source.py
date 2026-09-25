"""Market adapter. Failures never produce a zero quote or erase cached catalogs."""
from __future__ import annotations
import concurrent.futures as futures
import csv
import io
import json
import math
import re
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POOL = futures.ThreadPoolExecutor(max_workers=8)
MARKETS = ('KRX', 'ETF/KR', 'NASDAQ', 'NYSE', 'AMEX', 'NYSEARCA', 'BATS', 'IEX', 'CRYPTO')


def now():
    return datetime.now(timezone.utc).isoformat()


def get_json(url, timeout=12):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 AssetHub/2.0', 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def positive(value):
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError('유효한 가격이 없습니다.')
    return value


def stock_listing(market):
    if market == 'CRYPTO':
        return [{'ticker': x['market'], 'name': x['korean_name'], 'englishName': x['english_name'], 'market': 'UPBIT', 'currency': 'KRW'}
                for x in get_json('https://api.upbit.com/v1/market/all') if x['market'].startswith('KRW-')]
    import FinanceDataReader as fdr
    frame = fdr.StockListing(market)
    rows = []
    for raw in frame.to_dict('records'):
        code = str(raw.get('Code', raw.get('Symbol', ''))).strip()
        if not code or code.lower() == 'nan':
            continue
        kr = market in ('KRX', 'ETF/KR')
        if kr and code.isdigit():
            code = code.zfill(6)
        exchange = str(raw.get('Market', 'KRX' if kr else market))
        if exchange.upper().startswith('KOSDAQ'):
            exchange = 'KOSDAQ'
        elif exchange.upper().startswith('KOSPI'):
            exchange = 'KOSPI'
        if exchange not in ('KOSPI', 'KOSDAQ', 'KONEX'):
            exchange = 'ETF/KR' if market == 'ETF/KR' else market
        rows.append({'ticker': code, 'name': str(raw.get('Name', code)), 'market': exchange, 'currency': 'KRW' if kr else 'USD'})
    if not rows:
        raise ValueError('종목 목록이 비어 있습니다.')
    return rows


def nasdaq_fallback(market):
    filename = 'nasdaqlisted.txt' if market == 'NASDAQ' else 'otherlisted.txt'
    url = 'https://www.nasdaqtrader.com/dynamic/SymDir/' + filename
    with urllib.request.urlopen(url, timeout=15) as response:
        content = response.read().decode('utf-8')
    result = []
    for row in csv.DictReader(io.StringIO(content), delimiter='|'):
        ticker = row.get('Symbol') if market == 'NASDAQ' else row.get('ACT Symbol')
        if not ticker or row.get('Test Issue') != 'N':
            continue
        if market != 'NASDAQ' and row.get('Exchange') != {'NYSE':'N','AMEX':'A','NYSEARCA':'P','BATS':'Z','IEX':'V'}[market]:
            continue
        result.append({'ticker': ticker, 'name': row['Security Name'], 'market': market, 'currency': 'USD'})
    if not result and market != 'IEX':
        raise ValueError('대체 종목 목록이 비어 있습니다.')
    return result


class MarketService:
    def __init__(self, path=None):
        self.path = Path(path or ROOT / 'data' / 'catalog.json')
        self.lock = threading.RLock()
        self.catalog = {}
        self.status = {}
        self.refreshing = False
        self.quotes = {}
        try:
            stored = json.loads(self.path.read_text(encoding='utf-8'))
            self.catalog, self.status = stored['catalog'], stored['status']
        except (OSError, ValueError, KeyError):
            pass

    def refresh(self):
        with self.lock:
            if self.refreshing:
                return
            self.refreshing = True
        threading.Thread(target=self._refresh, daemon=True).start()

    def _refresh(self):
        def fetch(market):
            if market in ('NASDAQ','NYSE','AMEX','NYSEARCA','BATS','IEX'):
                return nasdaq_fallback(market), 'NasdaqTrader'
            try:
                return stock_listing(market), 'FinanceDataReader' if market != 'CRYPTO' else 'Upbit'
            except Exception:
                if market in ('NASDAQ', 'NYSE', 'AMEX'):
                    return nasdaq_fallback(market), 'NasdaqTrader'
                raise
        jobs = {POOL.submit(fetch, market): market for market in MARKETS}
        try:
            for job in futures.as_completed(jobs, timeout=90):
                market = jobs[job]
                try:
                    rows, source = job.result()
                    with self.lock:
                        self.catalog[market] = rows
                        self.status[market] = {'count': len(rows), 'updatedAt': now(), 'source': source, 'error': None}
                except Exception as exc:
                    with self.lock:
                        self.status[market] = {**self.status.get(market, {}), 'count': len(self.catalog.get(market, [])), 'error': type(exc).__name__ + ': 목록 갱신 실패. 이전 목록을 유지합니다.'}
        except futures.TimeoutError:
            with self.lock:
                for job, market in jobs.items():
                    if not job.done():
                        job.cancel()
                        self.status[market] = {**self.status.get(market, {}), 'count': len(self.catalog.get(market, [])), 'error': '목록 요청 시간 초과. 이전 목록을 유지합니다.'}
        finally:
            with self.lock:
                self.refreshing = False
                try:
                    self.path.parent.mkdir(parents=True, exist_ok=True)
                    tmp = self.path.with_suffix('.tmp')
                    tmp.write_text(json.dumps({'catalog': self.catalog, 'status': self.status}, ensure_ascii=False), encoding='utf-8')
                    tmp.replace(self.path)
                except OSError:
                    pass

    def search(self, query='', market='ALL', offset=0):
        with self.lock:
            items = {}
            for group, rows in self.catalog.items():
                for row in rows:
                    if market not in ('ALL', group, row['market']):
                        continue
                    key = (row['currency'], row['ticker'])
                    if query and query.casefold() not in (row['ticker'] + ' ' + row['name'] + ' ' + row.get('englishName', '')).casefold():
                        continue
                    items.setdefault(key, row)
            found = sorted(items.values(), key=lambda x: (x['ticker'].casefold() != query.casefold() and x['name'].casefold() != query.casefold(), x['name']))
            return {'items': found[offset:offset+50], 'total': len(found), 'offset': offset, 'refreshing': self.refreshing, 'coverage': self.status}

    def quote(self, ticker, market='', currency='KRW'):
        ticker = str(ticker).strip().upper()
        if not re.fullmatch(r'[A-Z0-9.^=/-]{1,30}', ticker):
            raise ValueError('티커 형식을 확인하세요.')
        if currency not in ('KRW', 'USD'):
            raise ValueError('KRW/USD만 지원합니다.')
        key = (ticker, market, currency)
        with self.lock:
            cached = self.quotes.get(key)
            if cached and time.time() - cached[0] < 60:
                return {**cached[1], 'cached': True}
        if ticker.startswith('KRW-'):
            raw = get_json('https://api.upbit.com/v1/ticker?markets=' + urllib.parse.quote(ticker))[0]
            result = {'ticker': ticker, 'price': positive(raw['trade_price']), 'currency': 'KRW', 'asOf': datetime.fromtimestamp(raw['trade_timestamp']/1000, timezone.utc).isoformat(), 'source': 'Upbit', 'kind': '최근 체결가'}
        else:
            if currency == 'KRW' and re.fullmatch(r'[0-9A-Z]{6}', ticker):
                candidates = [ticker + '.KQ'] if market == 'KOSDAQ' else [ticker + '.KS'] if market in ('KOSPI', 'ETF/KR') else [ticker + '.KS', ticker + '.KQ']
            else:
                candidates = [ticker.replace('.', '-') if currency == 'USD' and not ticker.endswith(('.KS', '.KQ')) else ticker]
            result = None
            for symbol in candidates:
                try:
                    raw = get_json('https://query1.finance.yahoo.com/v8/finance/chart/' + urllib.parse.quote(symbol, safe='') + '?interval=1d&range=5d')
                    chart = raw['chart']['result'][0]
                    meta = chart['meta']
                    actual_currency = meta['currency']
                    if actual_currency != currency:
                        raise ValueError('통화 불일치')
                    price = positive(meta['regularMarketPrice'])
                    asof = datetime.fromtimestamp(meta['regularMarketTime'], timezone.utc).isoformat()
                    result = {'ticker': ticker, 'providerSymbol': symbol, 'price': price, 'currency': actual_currency, 'asOf': asof, 'source': 'Yahoo Finance', 'kind': '최근 정규장 가격(지연 가능)'}
                    break
                except Exception:
                    continue
            if not result:
                raise ValueError('시세를 가져오지 못했습니다. 마지막 값을 유지합니다.')
        result['fetchedAt'] = now()
        with self.lock:
            self.quotes[key] = (time.time(), result)
        return result

    def batch(self, items):
        if not isinstance(items, list) or len(items) > 100:
            raise ValueError('한 번에 최대 100개를 조회할 수 있습니다.')
        jobs = {POOL.submit(self.quote, x.get('ticker', ''), x.get('market', ''), x.get('currency', 'KRW')): x.get('id') for x in items}
        result = []
        try:
            for job in futures.as_completed(jobs, timeout=80):
                ident = jobs[job]
                try:
                    result.append({'id': ident, 'ok': True, **job.result()})
                except Exception as exc:
                    result.append({'id': ident, 'ok': False, 'error': str(exc)})
        except futures.TimeoutError:
            completed = {x['id'] for x in result}
            for job, ident in jobs.items():
                if ident not in completed:
                    job.cancel()
                    result.append({'id': ident, 'ok': False, 'error': '조회 시간이 초과되었습니다. 마지막 값을 유지합니다.'})
        return result
