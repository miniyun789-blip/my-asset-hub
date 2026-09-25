// My Asset Hub v0.6.0 — public market data only. No holdings, quantities or personal files.
const VERSION='0.6.0-dev';
const BUILD='20260926-01';
const JSONH={'content-type':'application/json; charset=utf-8','cache-control':'no-store','x-content-type-options':'nosniff'};
const out=(data,status=200)=>new Response(JSON.stringify(data),{status,headers:JSONH});
let master=null,masterAt=0;const quotes=new Map();
async function yjson(url){const r=await fetch(url,{headers:{'User-Agent':'Mozilla/5.0','Accept':'application/json'},signal:AbortSignal.timeout(12000)});if(!r.ok)throw Error(`시세 제공처 응답 ${r.status}`);return r.json()}
async function catalog(env){if(master&&Date.now()-masterAt<3600000)return master;const r=await env.ASSETS.fetch(new Request('https://assets.local/data/catalog.json'));if(!r.ok)throw Error('시장 목록을 불러올 수 없습니다.');const data=await r.json();if(!Array.isArray(data.instruments)||!data.instruments.length)throw Error('시장 목록이 비어 있습니다.');master=data;masterAt=Date.now();return data}
export function marketOf(q){const ex=(q.exchange||'').toUpperCase(),s=q.symbol||'';if(s.endsWith('.KS'))return 'KRX';if(s.endsWith('.KQ'))return 'KOSDAQ';if(['NMS','NGM','NCM','NAS','NASDAQ'].includes(ex)||ex.includes('NASDAQ'))return 'NASDAQ';if(['NYQ','NYS','NYSE'].includes(ex))return 'NYSE';if(['ASE','AMEX'].includes(ex))return 'AMEX';if(['PCX','ARC','NYSEARCA'].includes(ex))return 'NYSEARCA';if(['BTS','BATS'].includes(ex))return 'BATS';return ''}
export async function search(q,market,offset,env){
 const data=await catalog(env),needle=q.toLocaleLowerCase();
 const matchMarket=x=>market==='ALL'||x.market===market||(market==='KRX'&&['KOSPI','KOSDAQ','KONEX','KRX'].includes(x.market))||(market==='CRYPTO'&&x.market==='UPBIT');
 let results=data.instruments.filter(x=>matchMarket(x)&&(!needle||`${x.name} ${x.ticker} ${x.symbol} ${x.englishName||''}`.toLocaleLowerCase().includes(needle)));
 const exact=x=>x.ticker.toLowerCase()===needle||x.name.toLowerCase()===needle;
 if(needle)results=[...results.filter(exact),...results.filter(x=>!exact(x))];
 let fallbackError='';
 if(!results.length&&q&&market!=='CRYPTO'){
  try{const d=await yjson(`https://query1.finance.yahoo.com/v1/finance/search?q=${encodeURIComponent(q)}&quotesCount=30&newsCount=0`);results=(d.quotes||[]).filter(x=>['EQUITY','ETF'].includes(x.quoteType)&&marketOf(x)).map(x=>({name:x.longname||x.shortname||x.symbol,ticker:x.symbol.replace(/\.(KS|KQ)$/,''),symbol:x.symbol,market:marketOf(x),currency:/\.(KS|KQ)$/.test(x.symbol)?'KRW':'USD'})).filter(matchMarket)}catch(e){fallbackError=e.message}
 }
 return {results:results.slice(offset,offset+50),total:results.length,offset,generatedAt:data.generatedAt,coverage:data.coverage,warning:fallbackError,source:'공개 시장 목록 + Yahoo 보완 검색'};
}
function finitePrice(x){const n=Number(x);if(!Number.isFinite(n)||n<=0)throw Error('유효한 시세가 없습니다. 기존 가격을 유지합니다.');return n}
export async function quote(symbol,market='',expectedCurrency=''){
 symbol=symbol.trim().toUpperCase();if(!/^[A-Z0-9.^=/-]{1,30}$/.test(symbol))throw Error('티커 형식이 올바르지 않습니다.');
 const key=[symbol,market,expectedCurrency].join('|'),cached=quotes.get(key);if(cached&&Date.now()-cached.saved<60000)return {...cached.data,cached:true};
 let result;
 if(symbol.startsWith('KRW-')){const d=await yjson(`https://api.upbit.com/v1/ticker?markets=${encodeURIComponent(symbol)}`);if(!d[0])throw Error('Upbit 종목이 없습니다.');result={symbol,price:finitePrice(d[0].trade_price),currency:'KRW',source:'Upbit',asOf:new Date(d[0].trade_timestamp).toISOString(),kind:'최근 체결가'}}
 else{
  let symbols=[symbol];if(/^[0-9A-Z]{6}$/.test(symbol)&& (expectedCurrency==='KRW'||/^[0-9]{6}$/.test(symbol))){symbols=market==='KOSDAQ'?[symbol+'.KQ']:['KOSPI','ETF/KR'].includes(market)?[symbol+'.KS']:[symbol+'.KS',symbol+'.KQ']}
  else if(expectedCurrency==='USD')symbols=[symbol.replace('.','-')];
  let lastError;for(const s of symbols){try{const d=await yjson(`https://${s==='KRW=X'?'query2':'query1'}.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(s)}?range=5d&interval=1d`),m=d.chart?.result?.[0]?.meta;if(!m)throw Error('시세 응답이 비어 있습니다.');if(!['USD','KRW'].includes(m.currency))throw Error('지원하지 않는 통화입니다.');if(expectedCurrency&&m.currency!==expectedCurrency)throw Error('자산 통화와 시세 통화가 다릅니다.');result={symbol:s,price:finitePrice(m.regularMarketPrice),currency:m.currency,source:'Yahoo Finance',asOf:new Date(m.regularMarketTime*1000).toISOString(),kind:'최근 정규장 가격 · 지연 가능'};break}catch(e){lastError=e}}
  if(!result)throw lastError||Error('시세 조회 실패');
 }
 if(expectedCurrency&&result.currency!==expectedCurrency)throw Error('자산 통화와 시세 통화가 다릅니다.');result.fetchedAt=new Date().toISOString();quotes.set(key,{saved:Date.now(),data:result});if(quotes.size>1000)quotes.delete(quotes.keys().next().value);return result;
}
export async function fx(){const q=await quote('KRW=X','','KRW');return {...q,pair:'USD/KRW',rate:q.price}}
export default {async fetch(request,env){const u=new URL(request.url);if(!u.pathname.startsWith('/api/'))return env.ASSETS.fetch(request);
 const origin=request.headers.get('Origin'),allowed=(env.ALLOWED_ORIGIN||'').split(',').map(x=>x.trim()).filter(Boolean);if(origin&&origin!==u.origin&&!allowed.includes(origin))return out({error:'허용되지 않은 앱 주소입니다.'},403);
 const cors=origin?{'access-control-allow-origin':origin,'vary':'Origin'}:{};
 if(request.method==='OPTIONS')return new Response(null,{status:204,headers:{...cors,'access-control-allow-methods':'GET, OPTIONS','access-control-allow-headers':'accept'}});
 let response;
 try{if(request.method!=='GET')response=out({error:'GET만 지원합니다.'},405);
 else if(u.pathname==='/api/health')response=out({ok:true,version:VERSION,build:BUILD});
 else if(u.pathname==='/api/search'){const offset=Number(u.searchParams.get('offset')||0);if(!Number.isInteger(offset)||offset<0)throw Error('검색 페이지 값이 잘못되었습니다.');response=out(await search((u.searchParams.get('q')||'').trim().slice(0,100),u.searchParams.get('market')||'ALL',offset,env));}
 else if(u.pathname==='/api/quote'||u.pathname==='/api/crypto')response=out(await quote(u.searchParams.get('ticker')||u.searchParams.get('symbol')||'',u.searchParams.get('market')||'',u.searchParams.get('currency')||''));
 else if(u.pathname==='/api/fx')response=out(await fx());else response=out({error:'API 경로가 없습니다.'},404);
 }catch(e){response=out({error:e.message},502)}
 for(const[k,v]of Object.entries(cors))response.headers.set(k,v);return response;
}};
