
(() => {
  'use strict';
  const KEY='my-asset-hub-html-v1';
  const defaults=()=>({version:2,config:{target:1000000000,fx:1350,refreshMinutes:5,risks:['초고위험','위험','중립','안전']},stocks:[],savings:[],history:[],riskTargets:{},allocations:{}});
  const $=s=>document.querySelector(s);
  const money=n=>`${Math.round(Number(n)||0).toLocaleString('ko-KR')}원`;
  const num=n=>Number.isFinite(Number(n))?Number(n):0;
  const safe=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const uid=()=>globalThis.crypto?.randomUUID?.()||`id-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const today=()=>new Date(Date.now()+6*3600000).toISOString().slice(0,10); // KST 03:00 경계
  function finite(value,label,{nullable=false,min=0}={}){
    if(nullable&&(value===''||value==null))return null;
    if(value===''||value==null)throw Error(`${label}: 값이 비어 있습니다.`);
    const n=Number(typeof value==='string'?value.replace(/,/g,''):value);
    if(!Number.isFinite(n)||n<min)throw Error(`${label}: ${min} 이상의 숫자를 입력하세요.`);
    return n;
  }
  function bool(v){if(v===true||v===1||String(v).toLowerCase()==='true')return true;if(v===false||v===0||v==null||v===''||String(v).toLowerCase()==='false')return false;throw Error('해외여부는 TRUE/FALSE여야 합니다.')}
  function normalize(raw){
    if(!raw||typeof raw!=='object'||Array.isArray(raw))throw Error('JSON 형식을 확인해 주세요.');
    for(const k of ['stocks','savings','history'])if(raw[k]!=null&&!Array.isArray(raw[k]))throw Error(`${k}: 목록 형식이 아닙니다.`);
    const cfg=Array.isArray(raw.config)?raw.config[0]||{}:raw.config||{};
    let risks=Array.isArray(cfg.risks)?cfg.risks:String(cfg.risk_levels||'초고위험,위험,중립,안전').split(',');
    risks=risks.map(x=>String(x).trim()).filter(Boolean);
    if(!risks.length||new Set(risks).size!==risks.length||risks.includes('고정(은행)'))throw Error('리스크 분류는 중복 없이 입력하고 고정(은행)은 제외하세요.');
    const stocks=(raw.stocks||[]).map((s,i)=>{
      const foreign=bool(s.foreign??s['해외여부']);let ticker=String(s.ticker??s['티커']??'').trim().toUpperCase();if(!foreign&&/^\d{1,6}$/.test(ticker))ticker=ticker.padStart(6,'0');
      const item={id:String(s.id||uid()),name:String(s.name??s['종목명']??'').trim(),ticker,buy:finite(s.buy??s['매수평단가'],`투자 ${i+1} 평단`),quantity:finite(s.quantity??s['보유수량'],`투자 ${i+1} 수량`),price:finite(s.price??s['현재가'],`투자 ${i+1} 현재가`,{nullable:true}),foreign,risk:String(s.risk??s['리스크']??risks[0]),buyFx:finite(s.buyFx??s['매수환율'],'매수환율',{nullable:true,min:0.01}),market:String(s.market??s['시장']??(ticker.endsWith('.KQ')?'KOSDAQ':ticker.endsWith('.KS')?'KOSPI':foreign?'US':'KRX')),quoteAsOf:String(s.quoteAsOf||''),quoteSource:String(s.quoteSource||''),quoteKind:String(s.quoteKind||''),quoteError:String(s.quoteError||'')};
      if(!item.name)throw Error(`투자 ${i+1}: 종목명이 비어 있습니다.`);if(item.ticker.startsWith('KRW-')&&foreign)throw Error('KRW 가상화폐는 KRW 통화를 선택하세요.');
      item.ticker=item.ticker.replace(/\.(KS|KQ)$/,'');if(!risks.includes(item.risk))risks.push(item.risk);return item;
    });
    if(!risks.includes('안전'))risks.push('안전');
    const savings=(raw.savings||[]).map((s,i)=>{const item={id:String(s.id||uid()),type:String(s.type??s['종류']??'적금'),name:String(s.name??s['상품명']??'').trim(),amount:finite(s.amount??s['금액']??s['월납입액'],`은행 ${i+1} 금액`),current:finite(s.current??s['현재회차']??1,'현재회차'),total:finite(s.total??s['총회차']??1,'총회차',{min:1}),rate:finite(s.rate??s['이율']??0,'이율')};if(!item.name||!['적금','주택청약','예금','파킹통장'].includes(item.type))throw Error('은행 상품명·종류를 확인하세요.');if(!Number.isInteger(item.current)||!Number.isInteger(item.total)||(['적금','주택청약'].includes(item.type)&&item.current>item.total))throw Error('납입 회차는 정수이며 현재 회차는 총 회차 이하여야 합니다.');return item});
    const ids=[...stocks,...savings].map(s=>s.id);if(new Set(ids).size!==ids.length)throw Error('중복 ID가 있습니다. 새 자산의 ID를 비워 두세요.');
    const history=(raw.history||[]).map(h=>{const date=String(h.date??h['날짜']??'').slice(0,10);if(!/^\d{4}-\d{2}-\d{2}$/.test(date)||new Date(date+'T00:00:00Z').toISOString().slice(0,10)!==date)throw Error('자산 기록 날짜를 확인하세요.');return {date,total:finite(h.total??h['총자산'],'기록 총자산')}});
    const parseTargets=(obj)=>{if(typeof obj==='string')obj=JSON.parse(obj);const result=Object.create(null);for(const [k,v]of Object.entries(obj||{})){const n=finite(v,'목표 비중');if(n>100)throw Error('목표 비중은 100 이하입니다.');result[k]=n}return result};
    return {version:2,config:{target:finite(cfg.target??cfg.target_asset??1e9,'목표금액',{min:1}),fx:finite(cfg.fx??1350,'환율',{min:.01}),risks,refreshMinutes:[0,5,15,30].includes(Number(cfg.refreshMinutes))?Number(cfg.refreshMinutes):5,fxAsOf:String(cfg.fxAsOf||''),fxSource:String(cfg.fxSource||'수동'),fxError:String(cfg.fxError||'')},stocks,savings,history:[...new Map(history.map(h=>[h.date,h])).values()].sort((a,b)=>a.date.localeCompare(b.date)),riskTargets:parseTargets(raw.riskTargets??cfg.riskTargets),allocations:parseTargets(raw.allocations??cfg.allocations)};
  }
  let state,storageBlocked=false;try{const saved=localStorage.getItem(KEY);state=saved?normalize(JSON.parse(saved)):defaults()}catch(e){state=defaults();storageBlocked=true;alert(`저장 데이터에 오류가 있어 덮어쓰기를 중지했습니다. 엑셀·백업에서 복원하세요.\n${e.message}`)}
  let period='day',tab='dashboard',editType='',editId=null,editQuoteMeta=null;
  function toast(msg){const el=$('#toast');el.textContent=msg;el.classList.remove('hidden');setTimeout(()=>el.classList.add('hidden'),3200)}
  function calc(){
    const fx=state.config.fx;
    const stocks=state.stocks.map(s=>{const p=s.price===null?s.buy:s.price;const value=p*s.quantity*(s.foreign?fx:1);const cost=s.buy*s.quantity*(s.foreign?(s.buyFx||fx):1);return {...s,value,cost,quote:p,estimated:s.price===null}});
    const banks=state.savings.map(s=>({...s,value:s.amount*(['예금','파킹통장'].includes(s.type)?1:s.current),fixed:!['예금','파킹통장'].includes(s.type)}));
    const stockTotal=stocks.reduce((a,s)=>a+s.value,0),bankTotal=banks.reduce((a,s)=>a+s.value,0),cost=stocks.reduce((a,s)=>a+s.cost,0)+bankTotal;
    return {stocks,banks,stockTotal,bankTotal,cost,total:stockTotal+bankTotal};
  }
  function persist({record=true}={}){
    if(storageBlocked){toast('기존 데이터 보호를 위해 저장이 중지되었습니다. 백업 파일로 복원하세요.');render();return false}
    if(record){const total=calc().total,date=today();if(total>0||state.history.length){const at=state.history.findIndex(h=>h.date===date);if(at>=0)state.history[at].total=total;else state.history.push({date,total});state.history.sort((a,b)=>a.date.localeCompare(b.date));}}
    try{localStorage.setItem(KEY,JSON.stringify(state));$('#save-status').textContent='이 기기에 저장';render();return true}catch(e){$('#save-status').textContent='저장 실패';toast('저장 공간을 확인한 뒤 JSON 백업을 만드세요.');return false}
  }
  function donut(items,label){const nonzero=items.filter(x=>x.value>0),total=nonzero.reduce((a,x)=>a+x.value,0);if(!total)return '<div class="empty" style="width:100%">자산을 추가하면 비중이 표시됩니다.</div>';
    let cursor=0;const gradient=nonzero.map(x=>{const start=cursor;cursor+=x.value/total*100;return `${x.color} ${start}% ${cursor}%`}).join(',');return `<div class="donut" style="background:conic-gradient(${gradient})"><div class="donut-inner"><div><b>${label}</b><small>${nonzero.length}개 항목</small></div></div></div><div class="legend">${nonzero.map(x=>`<div class="legend-row"><span class="dot" style="background:${x.color}"></span><span>${safe(x.name)}</span><b>${(x.value/total*100).toFixed(1)}%</b></div>`).join('')}</div>`}
  const colors=['#53d9c1','#699efe','#f5b962','#ba92fa','#fa829b','#89d3e8','#c4d679'];
  function renderHistory(){let entries=state.history.slice().sort((a,b)=>a.date.localeCompare(b.date));if(period!=='day'){const grouped=new Map();for(const h of entries)grouped.set(period==='month'?h.date.slice(0,7):h.date.slice(0,4),h);entries=[...grouped.values()]}
    if(!entries.length){$('#history-view').innerHTML='<div class="empty">기록이 아직 없습니다.</div>';return}
    const vals=entries.map(x=>x.total),lo=Math.min(...vals),hi=Math.max(...vals),pad=Math.max((hi-lo)*.15,hi*.02,1),min=Math.max(0,lo-pad),max=hi+pad;
    const width=Math.max(300,$('#history-view').clientWidth||800),left=15,right=width-15;const x=i=>entries.length===1?width/2:left+i*(right-left)/(entries.length-1),y=v=>180-(v-min)/(max-min)*135;
    const points=entries.map((h,i)=>`${x(i)},${y(h.total)}`).join(' ');
    $('#history-view').innerHTML=`<svg class="history-svg" viewBox="0 0 ${width} 225" role="img" aria-label="${safe(period==='day'?'일별':period==='month'?'월별':'연별')} 자산 기록"><line x1="${left}" y1="180" x2="${right}" y2="180" stroke="#42607b"/><line x1="${left}" y1="45" x2="${right}" y2="45" stroke="#30445f" stroke-dasharray="4"/><text x="${left}" y="35" fill="#92aac2" font-size="13">${safe(money(max))}</text><polyline points="${points}" fill="none" stroke="#55dfc4" stroke-width="3" stroke-linejoin="round"/>${entries.length<=35?entries.map((h,i)=>`<circle cx="${x(i)}" cy="${y(h.total)}" r="4" fill="#78f3dc"><title>${safe(h.date)}: ${safe(money(h.total))}</title></circle>`).join(''):''}<text x="${left}" y="209" fill="#91aac3" font-size="12">${safe(entries[0].date)}</text><text x="${right}" y="209" text-anchor="end" fill="#91aac3" font-size="12">${safe(entries.at(-1).date)}</text></svg>`;
  }
  function render(){const c=calc(),target=state.config.target;
    $('#hero-total').textContent=money(c.total);$('#goal-value').textContent=money(target);$('#goal-fill').style.width=`${Math.min(100,c.total/target*100)}%`;$('#goal-message').textContent=`${(c.total/target*100).toFixed(1)}% 달성 · ${c.total>=target?'목표 달성':`${money(target-c.total)} 남음`}`;
    $('#stock-total').textContent=money(c.stockTotal);$('#bank-total').textContent=money(c.bankTotal);const delta=c.total-c.cost;$('#profit-total').textContent=`${delta>=0?'+':''}${money(delta)}`;$('#profit-total').className=delta<0?'negative':'positive';
    const parts=[{name:'가상화폐',value:c.stocks.filter(s=>s.ticker.toUpperCase().startsWith('KRW-')).reduce((a,s)=>a+s.value,0),color:colors[2]},{name:'해외 주식',value:c.stocks.filter(s=>s.foreign&&!s.ticker.toUpperCase().startsWith('KRW-')).reduce((a,s)=>a+s.value,0),color:colors[3]},{name:'국내 주식',value:c.stocks.filter(s=>!s.foreign&&!s.ticker.toUpperCase().startsWith('KRW-')).reduce((a,s)=>a+s.value,0),color:colors[1]},{name:'은행',value:c.bankTotal,color:colors[0]}];$('#portfolio-viz').innerHTML=donut(parts,'자산 유형');
    const risks=state.config.risks.map((name,i)=>({name,value:c.stocks.filter(s=>s.risk===name).reduce((a,s)=>a+s.value,0)+(name==='안전'?c.banks.filter(s=>!s.fixed).reduce((a,s)=>a+s.value,0):0),color:colors[i%colors.length]}));const others=c.stocks.filter(s=>!state.config.risks.includes(s.risk)).reduce((a,s)=>a+s.value,0);if(others)risks.push({name:'기타',value:others,color:'#9aacbc'});risks.push({name:'고정(은행)',value:c.banks.filter(s=>s.fixed).reduce((a,s)=>a+s.value,0),color:'#71889e'});$('#risk-viz').innerHTML=donut(risks,'리스크');
    $('#stock-count').textContent=`${c.stocks.length}개`;$('#bank-count').textContent=`${c.banks.length}개`;
    $('#stock-list').innerHTML=c.stocks.length?c.stocks.map(s=>`<div class="row"><div class="row-main"><div class="row-title">${safe(s.name)} <span class="muted">${safe(s.ticker)}</span></div><div class="row-sub">${safe(s.risk)} · ${s.quantity.toLocaleString('ko-KR',{maximumFractionDigits:8})}주/개 · 평단 ${s.buy.toLocaleString('ko-KR')} ${s.foreign?'USD':'KRW'}${s.estimated?' · 현재가 미입력(평단 적용)':''}<span class="quote-meta">${safe(s.quoteError||`${s.quoteSource||'수동 입력'} · ${s.quoteAsOf?new Date(s.quoteAsOf).toLocaleString('ko-KR'):'기준 시각 없음'}`)}</span></div></div><div class="row-value"><strong>${money(s.value)}</strong><small class="${s.value-s.cost<0?'negative':'positive'}">${s.cost?`${((s.value-s.cost)/s.cost*100).toFixed(1)}%`:'—'}</small><div class="row-actions"><button class="btn small" data-edit="stock" data-id="${safe(s.id)}">수정</button><button class="btn small danger" data-delete="stock" data-id="${safe(s.id)}">삭제</button></div></div></div>`).join(''):'<div class="empty">등록된 투자 자산이 없습니다.</div>';
    $('#bank-list').innerHTML=c.banks.length?c.banks.map(s=>`<div class="row"><div class="row-main"><div class="row-title">${safe(s.name)} <span class="muted">${safe(s.type)}</span></div><div class="row-sub">${s.fixed?`${s.current}/${s.total}회 납입 · 회차당 ${money(s.amount)}`:`현재 잔액 ${money(s.amount)}`} · 연 ${s.rate}% (이자 미반영)</div></div><div class="row-value"><strong>${money(s.value)}</strong><div class="row-actions"><button class="btn small" data-edit="bank" data-id="${safe(s.id)}">수정</button><button class="btn small danger" data-delete="bank" data-id="${safe(s.id)}">삭제</button></div></div></div>`).join(''):'<div class="empty">등록된 은행 자산이 없습니다.</div>';
    renderHistory();renderRebalance(c);renderMarketStatus();
  }
  function renderRebalance(c){const fixed=c.banks.filter(s=>s.fixed).reduce((a,s)=>a+s.value,0),fixedPct=c.total?fixed/c.total*100:0;
    $('#risk-targets').innerHTML=state.config.risks.map(r=>{const current=(c.stocks.filter(s=>s.risk===r).reduce((a,s)=>a+s.value,0)+(r==='안전'?c.banks.filter(s=>!s.fixed).reduce((a,s)=>a+s.value,0):0))/Math.max(c.total,1)*100;return `<div class="target-row"><span>${safe(r)}</span><span class="right muted">현재 ${current.toFixed(1)}%</span><label class="field"><span class="sr-only">${safe(r)} 목표</span><input type="number" min="0" max="100" step="0.1" data-risk="${safe(r)}" value="${num(state.riskTargets[r])}"></label></div>`}).join('')+`<div class="target-row"><span>고정(은행)</span><span></span><strong>${fixedPct.toFixed(1)}%</strong></div>`;
    const riskSum=state.config.risks.reduce((a,r)=>a+num(state.riskTargets[r]),0)+fixedPct;$('#target-sum').textContent=`목표 합계 ${riskSum.toFixed(1)}% / 100% ${Math.abs(riskSum-100)>.15?'· 리스크별 목표를 조정하세요.':'· 목표가 일치합니다.'}`;
    $('#rebalance-basis').innerHTML=`총자산 <b>${money(c.total)}</b><br>고정 은행 자산 <b>${money(fixed)}</b> (${fixedPct.toFixed(1)}%)<br>입력 환율 <b>1 USD = ${state.config.fx.toLocaleString('ko-KR')} KRW</b><br><br>매수·매도 수량은 최종 저장 가격으로 계산합니다. 현재가를 비워 둔 경우 평단이 사용되므로 수량 안내를 확인하세요.`;
    const items=[...c.stocks.map(s=>({...s,kind:'stock',group:s.risk})),...c.banks.filter(s=>!s.fixed).map(s=>({...s,kind:'bank',group:'안전'})),...c.banks.filter(s=>s.fixed).map(s=>({...s,kind:'fixed',group:'고정(은행)'}))];
    $('#allocation-list').innerHTML=items.length?items.map(s=>{const fixedItem=s.kind==='fixed',current=c.total?s.value/c.total*100:0,target=fixedItem?current:num(state.allocations[s.id]),diff=c.total*target/100-s.value,validPrice=s.kind==='stock'&&s.quote>0;const unit=validPrice?Math.abs(diff)/(s.quote*(s.foreign?state.config.fx:1)):0;const act=fixedItem?'유지 (고정)':Math.abs(diff)<=10000?'유지':`${diff>0?'매수':'매도'} ${money(Math.abs(diff))}${validPrice?` · 약 ${unit.toLocaleString('ko-KR',{maximumFractionDigits:3})}주/개`:''}`;return `<div class="allocation"><div><b>${safe(s.name)}</b><br><small>${safe(s.group)} · 현재 ${current.toFixed(1)}%</small></div><div class="amount right">현재 ${money(s.value)}<br><small>목표 ${money(c.total*target/100)}</small><br><small>차이 ${money(diff)}</small></div><label class="field"><span class="sr-only">${safe(s.name)} 목표 비중</span><input type="number" min="0" max="100" step="0.1" data-allocation="${safe(s.id)}" value="${target.toFixed(1)}" ${fixedItem?'disabled':''}></label><div class="action">${safe(act)}</div></div>`}).join(''):'<div class="empty">자산을 추가하면 계획을 세울 수 있습니다.</div>';
    const allocSum=items.reduce((a,s)=>a+(s.kind==='fixed'?(c.total?s.value/c.total*100:0):num(state.allocations[s.id])),0);$('#allocation-sum').textContent=`종목별 목표 합계 ${allocSum.toFixed(1)}% / 100% ${Math.abs(allocSum-100)>.15?'· 목표를 조정하세요.':'· 목표가 일치합니다.'}`;
    const mismatch=state.config.risks.filter(r=>Math.abs(items.filter(s=>s.group===r).reduce((a,s)=>a+num(state.allocations[s.id]),0)-num(state.riskTargets[r]))>.15);
    if(!c.total||Math.abs(riskSum-100)>.15||Math.abs(allocSum-100)>.15||mismatch.length){
      document.querySelectorAll('#allocation-list .action').forEach(x=>x.textContent='목표 비중 확인 필요');
      if(mismatch.length)$('#allocation-sum').textContent+=` · 그룹 목표와 불일치: ${mismatch.join(', ')}`;
    }

  }
  const field=(name,label,value,type='text',extra='')=>`<label class="field">${label}<input name="${name}" type="${type}" value="${safe(value??'')}" ${extra}></label>`;
  function openEditor(type,id=null,selected=null){editType=type;editId=id;const obj=(type==='stock'?state.stocks:state.savings).find(x=>x.id===id)||selected||{};editQuoteMeta=type==='stock'&&id?{quoteAsOf:obj.quoteAsOf||'',quoteSource:obj.quoteSource||'',quoteKind:obj.quoteKind||'',quoteError:obj.quoteError||''}:null;$('#editor-title').textContent=`${id?'수정':'추가'} · ${type==='stock'?'투자 자산':'은행 자산'}`;
    if(type==='stock'){$('#editor-fields').innerHTML=`<div style="grid-column:1/-1"><button type="button" class="btn primary" id="open-market-search">종목/티커 검색</button></div>`+field('name','종목명',obj.name,'text','required')+field('ticker','티커 (선택)',obj.ticker)+field('market','시장 (검색으로 자동 입력)',obj.market||'')+field('buy','매수 단가',obj.buy??'','number','min="0" step="any" required')+field('quantity','보유 수량',obj.quantity??'','number','min="0" step="any" required')+field('price','현재가 (자동 조회)',obj.price,'number','min="0" step="any" readonly placeholder="종목 선택 시 자동 조회"')+`<label class="field">통화<select name="foreign"><option value="false" ${!obj.foreign?'selected':''}>KRW (국내·가상화폐)</option><option value="true" ${obj.foreign?'selected':''}>USD (해외 주식)</option></select></label>`+field('buyFx','매수 당시 USD/KRW 환율 (선택)',obj.buyFx,'number','min="1" step="any"')+`<label class="field">리스크 분류<select name="risk">${[...new Set([...state.config.risks,...(obj.risk?[obj.risk]:[])])].map(r=>`<option value="${safe(r)}" ${obj.risk===r?'selected':''}>${safe(r)}</option>`).join('')}</select></label>`}
    else{$('#editor-fields').innerHTML=`<label class="field">종류<select name="type">${['적금','주택청약','예금','파킹통장'].map(t=>`<option ${obj.type===t?'selected':''}>${t}</option>`).join('')}</select></label>`+field('name','상품명',obj.name,'text','required')+field('amount','회차별 납입액 또는 현재 잔액 (원)',obj.amount??'','number','min="0" step="1" required')+field('current','현재 납입 회차',obj.current??1,'number','min="0" step="1" required')+field('total','총 만기 회차',obj.total??1,'number','min="1" step="1" required')+field('rate','연 이율 (%) · 평가액에 미반영',obj.rate??0,'number','min="0" step="any" required')+`<p class="hint" style="grid-column:1/-1">예금·파킹통장은 입력한 현재 잔액을 그대로 사용합니다. 적금·주택청약은 회차별 납입액 × 현재 회차로 계산합니다.</p>`}
    $('#editor').showModal()}
  $('#editor-form').addEventListener('submit',e=>{e.preventDefault();const f=new FormData(e.currentTarget),val=k=>String(f.get(k)||'').trim(),n=k=>Number(f.get(k));let item;if(editType==='stock'){item={id:editId||uid(),name:val('name'),ticker:val('ticker').toUpperCase(),buy:n('buy'),quantity:n('quantity'),price:val('price')===''?null:n('price'),foreign:val('foreign')==='true',risk:val('risk'),market:val('market')||(val('foreign')==='true'?'US':'KRX'),buyFx:val('buyFx')===''?null:n('buyFx')};if(item.foreign&&item.buyFx!==null&&item.buyFx<=0){toast('매수 환율은 0보다 커야 합니다.');return}}
    else item={id:editId||uid(),type:val('type'),name:val('name'),amount:n('amount'),current:n('current'),total:n('total'),rate:n('rate')};const arr=editType==='stock'?state.stocks:state.savings;const idx=arr.findIndex(x=>x.id===editId);
    if(editType==='stock'){
      if(item.ticker.endsWith('.KQ'))item.market='KOSDAQ';if(item.ticker.endsWith('.KS'))item.market='KOSPI';item.ticker=item.ticker.replace(/\.(KS|KQ)$/,'');if(!item.foreign&&/^\d{1,6}$/.test(item.ticker))item.ticker=item.ticker.padStart(6,'0');
      const old=arr[idx];if(editQuoteMeta)Object.assign(item,editQuoteMeta);else if(old&&old.price===item.price&&old.ticker===item.ticker&&old.foreign===item.foreign)Object.assign(item,{quoteAsOf:old.quoteAsOf,quoteSource:old.quoteSource,quoteError:old.quoteError,quoteKind:old.quoteKind});else Object.assign(item,{quoteAsOf:'',quoteSource:'자동 조회 대기',quoteError:'',quoteKind:''});
      const same=idx<0&&item.ticker?arr.find(x=>x.ticker===item.ticker&&x.foreign===item.foreign):null;
      if(same){if(!confirm('이미 보유한 종목입니다. 입력한 수량을 추가 매수로 합산하고 가중 평단을 계산할까요?'))return;
        const q=same.quantity+item.quantity,usdCost=same.buy*same.quantity+item.buy*item.quantity,krwCost=same.buy*same.quantity*(same.buyFx||state.config.fx)+item.buy*item.quantity*(item.buyFx||state.config.fx);
        item={...same,quantity:q,buy:q?usdCost/q:0,buyFx:same.foreign&&usdCost?krwCost/usdCost:null,risk:item.risk};
        const next=structuredClone(state);next.stocks[next.stocks.findIndex(x=>x.id===same.id)]=item;try{state=normalize(next)}catch(err){toast(err.message);return}$('#editor').close();if(persist())toast('추가 매수를 합산했습니다.');return;
      }
    }
    const next=structuredClone(state),dest=editType==='stock'?next.stocks:next.savings;if(idx<0)dest.push(item);else dest[idx]=item;
    try{state=normalize(next)}catch(err){toast(err.message);return}$('#editor').close();if(persist()){toast('자산이 저장되었습니다.');if(editType==='stock'&&item.ticker&&navigator.onLine)setTimeout(()=>refreshMarket(false),0)}});
  document.addEventListener('click',async e=>{const t=e.target.closest('button');if(!t)return;if(t.dataset.close!==undefined){t.closest('dialog').close();return}if(t.dataset.tab){tab=t.dataset.tab;document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('active',x.dataset.tab===tab));document.querySelectorAll('.panel').forEach(x=>x.classList.toggle('active',x.id===tab));if(tab==='dashboard')renderHistory();return}if(t.dataset.period){period=t.dataset.period;document.querySelectorAll('[data-period]').forEach(x=>x.classList.toggle('selected',x.dataset.period===period));renderHistory();return}if(t.id==='open-market-search'){openMarketSearch();return}if(t.dataset.marketPick!==undefined){const x=$('#market-results')._items?.[Number(t.dataset.marketPick)];if(x){const f=$('#editor-form');const ticker=x.ticker||x.symbol;const currency=x.currency==='USD'?'USD':'KRW';f.elements.name.value=x.name||x.symbol;f.elements.ticker.value=ticker;f.elements.market.value=x.market;f.elements.foreign.value=currency==='USD'?'true':'false';f.elements.price.value='';editQuoteMeta=null;$('#market-search').close();toast('종목 선택 완료 · 현재가 조회 중…');try{const q=await api(`/api/quote?ticker=${encodeURIComponent(ticker)}&market=${encodeURIComponent(x.market||'')}&currency=${currency}`);if(Number.isFinite(q.price)&&q.price>0&&q.currency===currency){f.elements.price.value=q.price;editQuoteMeta={quoteAsOf:q.asOf||new Date().toISOString(),quoteSource:q.source||'자동 시세',quoteKind:q.kind||'',quoteError:''};toast(`${x.name||ticker} 현재가 ${Number(q.price).toLocaleString('ko-KR')} ${currency} 자동 입력`)}else throw Error('가격·통화 검증 실패')}catch(err){editQuoteMeta={quoteAsOf:'',quoteSource:'',quoteKind:'',quoteError:String(err.message||err)};toast('현재가 조회 실패 · 저장 후 자동 갱신을 다시 시도합니다.')}}return}if(t.dataset.edit){openEditor(t.dataset.edit,t.dataset.id);return}if(t.dataset.delete){const arr=t.dataset.delete==='stock'?state.stocks:state.savings;const entry=arr.find(x=>x.id===t.dataset.id);if(entry&&confirm(`${entry.name} 자산을 삭제할까요?`)){arr.splice(arr.indexOf(entry),1);delete state.allocations[entry.id];if(persist())toast('삭제했습니다.')}return}});
  $('#add-stock').onclick=()=>openEditor('stock');$('#add-bank').onclick=()=>openEditor('bank');$('#backup-btn').onclick=()=>$('#backup').showModal();$('#refresh-market').onclick=()=>refreshMarket(true);$('#settings-btn').onclick=()=>{const f=$('#settings-form');f.elements.target.value=state.config.target;f.elements.fx.value=state.config.fx;f.elements.risks.value=state.config.risks.join(', ');f.elements.refreshMinutes.value=state.config.refreshMinutes??5;$('#settings').showModal()};
  $('#settings-form').onsubmit=e=>{e.preventDefault();const f=e.currentTarget,risks=f.elements.risks.value.split(',').map(x=>x.trim()).filter(Boolean);if(!risks.length||new Set(risks).size!==risks.length){toast('리스크 분류를 중복 없이 입력하세요.');return}if(!risks.includes('안전')||risks.includes('고정(은행)')||state.stocks.some(s=>!risks.includes(s.risk))){toast('사용 중인 분류와 안전 분류는 유지하고 고정(은행)은 제외하세요.');return}
    const fx=Number(f.elements.fx.value);state.config={...state.config,target:Number(f.elements.target.value),fx,risks,refreshMinutes:Number(f.elements.refreshMinutes.value),...(fx!==state.config.fx?{fxSource:'수동 입력',fxAsOf:new Date().toISOString(),fxError:''}:{})};$('#settings').close();if(persist()){startRefreshTimer();toast('설정이 저장되었습니다.')}};
  document.addEventListener('change',e=>{if(e.target.dataset.risk!==undefined){state.riskTargets[e.target.dataset.risk]=Math.max(0,Math.min(100,num(e.target.value)));persist({record:false})}if(e.target.dataset.allocation!==undefined){state.allocations[e.target.dataset.allocation]=Math.max(0,Math.min(100,num(e.target.value)));persist({record:false})}});
  $('#export-btn').onclick=()=>{const blob=new Blob([JSON.stringify(state,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`my-asset-hub-${today()}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
  const APP_VERSION='0.6.0';
  let refreshBusy=false,autoTimer=null,searchTimer=null,searchOffset=0,searchSequence=0,pendingImport=null;
  const API_BASE=String(window.ASSET_HUB_API_BASE||'').replace(/\/$/,'');
  async function api(path){const ctl=new AbortController(),timer=setTimeout(()=>ctl.abort(),20000);try{const r=await fetch(API_BASE+path,{signal:ctl.signal,headers:{accept:'application/json'},cache:'no-store'});const d=await r.json();if(!r.ok||d.error)throw Error(d.error||`API ${r.status}`);return d}finally{clearTimeout(timer)}}
  function renderMarketStatus(){const cfg=state.config;$('#market-status').textContent=`${navigator.onLine?'온라인':'오프라인 · 저장값 사용'} · USD/KRW ${cfg.fx.toLocaleString('ko-KR')} · ${cfg.fxSource||'초기 예시값(자동 조회 대기)'}${cfg.fxAsOf?' · '+new Date(cfg.fxAsOf).toLocaleString('ko-KR'):''}${cfg.fxError?' · 환율 조회 실패, 이전값 유지':''}`;}
  function startRefreshTimer(){clearInterval(autoTimer);if(state.config.refreshMinutes>0)autoTimer=setInterval(()=>{if(navigator.onLine&&!document.hidden)refreshMarket(false)},state.config.refreshMinutes*60000)}
  async function refreshMarket(show=true){if(refreshBusy||storageBlocked)return;refreshBusy=true;$('#refresh-market').disabled=true;const before=state;let success=0,failed=0;try{
    const fx=await api('/api/fx').then(value=>({value}),error=>({error}));if(state!==before)return;
    if(fx.value&&Number.isFinite(fx.value.rate)&&fx.value.rate>0){Object.assign(state.config,{fx:fx.value.rate,fxSource:fx.value.source,fxAsOf:fx.value.asOf,fxError:''});success++}else{state.config.fxError='환율 실패';failed++}
    const items=state.stocks.filter(s=>s.ticker);let cursor=0;
    await Promise.all(Array.from({length:Math.min(4,items.length)},async()=>{while(cursor<items.length){const s=items[cursor++];try{const q=await api(`/api/quote?ticker=${encodeURIComponent(s.ticker)}&market=${encodeURIComponent(s.market||'')}&currency=${s.foreign?'USD':'KRW'}`);if(state!==before)return;if(!Number.isFinite(q.price)||q.price<=0||q.currency!==(s.foreign?'USD':'KRW'))throw Error('가격·통화 검증 실패');Object.assign(s,{price:q.price,quoteAsOf:q.asOf,quoteSource:q.source,quoteKind:q.kind,quoteError:''});success++}catch(e){if(state!==before)return;s.quoteError='조회 실패 · 마지막 가격 유지';failed++}}}));
    if(state!==before){if(show)toast('입력 내용이 변경되었습니다. 시세를 다시 갱신하세요.');return}persist();if(show||failed)toast(`시세·환율 성공 ${success} / 실패 ${failed}${failed?' · 저장된 값 유지':''}`);
   }catch(e){if(show)toast(e.message)}finally{refreshBusy=false;$('#refresh-market').disabled=false}}
  function openMarketSearch(){const d=$('#market-search');d.showModal();$('#market-query').value='';searchOffset=0;$('#market-results').innerHTML='<div class="empty">종목명 또는 티커를 입력하세요.</div>';$('#market-query').focus()}
  async function searchMarket(q){const seq=++searchSequence,box=$('#market-results');box.innerHTML='<div class="empty">검색 중…</div>';try{const data=await api(`/api/search?q=${encodeURIComponent(q)}&market=${encodeURIComponent($('#market-filter').value)}&offset=${searchOffset}`);if(seq!==searchSequence)return;box._items=data.results||[];box.innerHTML=box._items.length?box._items.map((x,i)=>`<button type="button" class="btn" data-market-pick="${i}" style="text-align:left;white-space:normal">${safe(x.name)} · ${safe(x.ticker||x.symbol)} · ${safe(x.market)}</button>`).join(''):'<div class="empty">검색 결과가 없습니다. 직접 티커 입력도 가능합니다.</div>';$('#search-status').textContent=`${data.total??box._items.length}개 · 시장목록 ${data.generatedAt?.slice(0,10)||'조회 중'}${data.warning?' · 보완 검색 실패':''}`;$('#more-market').disabled=searchOffset+50>=(data.total||0)}catch(e){if(seq!==searchSequence)return;box._items=[];box.innerHTML='<div class="empty">검색 API에 연결하지 못했습니다. 온라인 연결·Worker 주소를 확인하세요.</div>';$('#search-status').textContent=e.message;$('#more-market').disabled=true}}
  $('#market-query').oninput=e=>{clearTimeout(searchTimer);searchSequence++;searchOffset=0;const q=e.target.value.trim();searchTimer=setTimeout(()=>searchMarket(q),300)};
  $('#market-filter').onchange=()=>{searchOffset=0;searchMarket($('#market-query').value.trim())};$('#more-market').onclick=()=>{searchOffset+=50;searchMarket($('#market-query').value.trim())};
  $('#distribute').onclick=()=>{const c=calc();for(const r of state.config.risks){const items=[...c.stocks.filter(s=>s.risk===r),...(r==='안전'?c.banks.filter(s=>!s.fixed):[])],sum=items.reduce((a,s)=>a+s.value,0);for(const s of items)state.allocations[s.id]=num(state.riskTargets[r])*(sum?s.value/sum:1/items.length)}persist({record:false})};
  const EXCEL_HEADERS={
    '투자자산':['ID','종목명','티커','시장','통화','매수평단가','보유수량','현재가','매수환율','리스크','가격기준시각','가격출처','가격유형','해외여부'],
    '은행자산':['ID','종류','상품명','금액','현재회차','총회차','이율'],
    '설정':['항목','값'], '자산기록':['날짜','총자산'], '리스크목표':['리스크','목표비중'], '종목목표':['ID','목표비중']
  };
  function workbookRows(){return {
    '투자자산':state.stocks.map(s=>[s.id,s.name,s.ticker,s.market,s.foreign?'USD':'KRW',s.buy,s.quantity,s.price,s.buyFx,s.risk,s.quoteAsOf||'',s.quoteSource||'',s.quoteKind||'',s.foreign]),
    '은행자산':state.savings.map(s=>[s.id,s.type,s.name,s.amount,s.current,s.total,s.rate]),
    '설정':[['target_asset',state.config.target],['fx',state.config.fx],['risk_levels',state.config.risks.join(',')],['refreshMinutes',state.config.refreshMinutes||0],['fxAsOf',state.config.fxAsOf||''],['fxSource',state.config.fxSource||'수동']],
    '자산기록':state.history.map(h=>[h.date,h.total]),'리스크목표':state.config.risks.map(r=>[r,num(state.riskTargets[r])]),'종목목표':Object.entries(state.allocations)
  }}
  function exportExcel(){if(!globalThis.XLSX){toast('엑셀 모듈을 불러오지 못했습니다. JSON 백업을 사용하세요.');return}
    const wb=XLSX.utils.book_new(),rows=workbookRows();for(const [name,headers]of Object.entries(EXCEL_HEADERS)){const ws=XLSX.utils.aoa_to_sheet([headers,...rows[name]]);ws['!cols']=headers.map(h=>({wch:h==='종목명'||h==='상품명'?28:h==='ID'?38:h.includes('시각')?28:17}));ws['!autofilter']={ref:XLSX.utils.encode_range({s:{r:0,c:0},e:{r:rows[name].length,c:headers.length-1}})};XLSX.utils.book_append_sheet(wb,ws,name)}
    XLSX.writeFile(wb,`MyAssetHub-${today()}.xlsx`);
  }
  function readWorkbook(wb){
    if(wb.Sheets.stocks||wb.Sheets.savings){
      const rows=n=>wb.Sheets[n]?XLSX.utils.sheet_to_json(wb.Sheets[n],{defval:''}):[];
      const stocks=rows('stocks').map(s=>{const ticker=String(s['티커']??s.ticker??'').replace(/\.(KS|KQ)$/,'');const existing=state.stocks.find(x=>x.ticker===ticker);return {...s,id:s.id||existing?.id||uid(),price:s['현재가']??s.price,buyFx:s['매수환율']??s.buyFx,market:s['시장']??s.market}});
      const savings=rows('savings').map(s=>({...s,id:s.id||state.savings.find(x=>x.name===s['상품명']&&x.type===s['종류'])?.id||uid(),amount:s['금액']??s['월납입액']??s.amount}));
      const c=rows('config')[0]||{},cfg={...state.config,...c,target:c['목표금액']??c.target??c.target_asset??state.config.target,fx:c['USD_KRW']??c.fx??state.config.fx,risks:c['리스크분류']?String(c['리스크분류']).split(','):c.risk_levels?String(c.risk_levels).split(','):state.config.risks};
      return normalize({stocks,savings,config:cfg,history:wb.Sheets.history?rows('history'):state.history,riskTargets:state.riskTargets,allocations:state.allocations});
    }
    for(const name of ['투자자산','은행자산','설정'])if(!wb.Sheets[name])throw Error(`${name} 시트가 없습니다. 앱에서 내려받은 엑셀을 사용하세요.`);
    const read=name=>{if(!wb.Sheets[name])return null;const sheet=wb.Sheets[name],range=XLSX.utils.decode_range(sheet['!ref']||'A1');if(range.e.r>20000||range.e.c>50)throw Error('시트 크기가 너무 큽니다.');
      const arr=XLSX.utils.sheet_to_json(sheet,{header:1,defval:'',raw:true});if(EXCEL_HEADERS[name].some((h,i)=>arr[0]?.[i]!==h&&!(name==='투자자산'&&h==='해외여부'&&arr[0]?.[i]==null)))throw Error(`${name} 머리글이 변경되었습니다.`);
      for(let r=1;r<=range.e.r;r++)for(let c=0;c<EXCEL_HEADERS[name].length;c++){const cell=sheet[XLSX.utils.encode_cell({r,c})];if(cell?.f)throw Error(`${name} ${r+1}행: 가져오기 영역의 수식은 값으로 붙여넣어 주세요.`)}
      return arr.slice(1).filter(row=>row.some(v=>v!==''&&v!=null));
    };
    const cfg=Object.fromEntries(read('설정'));
    const stocks=read('투자자산').map(r=>{if(!['KRW','USD'].includes(String(r[4]).toUpperCase()))throw Error('투자자산 통화는 KRW 또는 USD입니다.');if(r[13]!==undefined&&r[13]!==''&&bool(r[13])!==(String(r[4]).toUpperCase()==='USD'))throw Error('통화와 해외여부가 일치하지 않습니다.');return {id:r[0],name:r[1],ticker:String(r[2]),market:r[3],foreign:String(r[4]).toUpperCase()==='USD',buy:r[5],quantity:r[6],price:r[7],buyFx:r[8],risk:r[9],quoteAsOf:r[10],quoteSource:r[11],quoteKind:r[12]}});
    const savings=read('은행자산').map(r=>({id:r[0],type:r[1],name:r[2],amount:r[3],current:r[4],total:r[5],rate:r[6]}));
    const historyRows=read('자산기록');const history=historyRows===null?state.history:historyRows.map(r=>{let date=r[0];if(typeof date==='number'){const d=XLSX.SSF.parse_date_code(date);date=`${d.y}-${String(d.m).padStart(2,'0')}-${String(d.d).padStart(2,'0')}`}return {date,total:r[1]}});
    return normalize({stocks,savings,config:cfg,history,riskTargets:Object.fromEntries(read('리스크목표')||Object.entries(state.riskTargets)),allocations:Object.fromEntries(read('종목목표')||Object.entries(state.allocations))});
  }
  function previewImport(incoming,label){pendingImport=incoming;const incomingIDs=new Set([...incoming.stocks,...incoming.savings].map(s=>s.id)),oldIDs=new Set([...state.stocks,...state.savings].map(s=>s.id));
    $('#import-summary').textContent=`${label}: 투자 ${incoming.stocks.length}개 · 은행 ${incoming.savings.length}개 · 기록 ${incoming.history.length}개. 새 ID ${[...incomingIDs].filter(x=>!oldIDs.has(x)).length}개 / 기존 ID ${[...incomingIDs].filter(x=>oldIDs.has(x)).length}개 / 빠지는 ID ${[...oldIDs].filter(x=>!incomingIDs.has(x)).length}개.`;
    for(const dlg of document.querySelectorAll('dialog[open]'))dlg.close();$('#import-preview').showModal();
  }
  $('#restore-previous').onclick=()=>{try{const raw=localStorage.getItem(KEY+'-recovery');if(!raw)throw Error('아직 복구 사본이 없습니다.');previewImport(normalize(JSON.parse(raw)),'직전 데이터')}catch(e){toast(e.message)}};
  $('#excel-export-btn').onclick=exportExcel;
  $('#excel-import-file').onchange=async e=>{try{const file=e.target.files[0];if(!file)return;if(file.size>10_000_000)throw Error('10MB 이하의 엑셀을 사용하세요.');const wb=XLSX.read(await file.arrayBuffer(),{type:'array'});previewImport(readWorkbook(wb),'엑셀')}catch(err){alert('가져오기 실패: '+err.message)}finally{e.target.value=''}};
  $('#import-file').onchange=async e=>{try{const file=e.target.files[0];if(!file)return;if(file.size>5_000_000)throw Error('5MB 이하의 JSON을 사용하세요.');const raw=JSON.parse(await file.text());if(!Object.hasOwn(raw,'stocks')||!Object.hasOwn(raw,'savings'))throw Error('자산 백업 파일이 아닙니다.');previewImport(normalize({...raw,history:raw.history??state.history}),'JSON')}catch(err){alert('복원 실패: '+err.message)}finally{e.target.value=''}};
  $('#apply-import').onclick=()=>{if(!pendingImport)return;const previous=state,wasBlocked=storageBlocked;try{const raw=localStorage.getItem(KEY);if(raw)localStorage.setItem(KEY+'-recovery',raw);state=pendingImport;storageBlocked=false;if(!persist({record:false,cloud:false}))throw Error('저장 공간이 부족합니다.');pendingImport=null;$('#import-preview').close();startRefreshTimer();toast('백업 데이터를 적용했습니다.')}catch(e){state=previous;storageBlocked=wasBlocked;render();alert('적용 실패: '+e.message)}};
  $('#raw-backup').onclick=()=>{const raw=localStorage.getItem(KEY);if(!raw){toast('저장 원본이 없습니다.');return}const url=URL.createObjectURL(new Blob([raw],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='my-asset-hub-recovery-raw.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
  let installPrompt=null;
  window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();installPrompt=e;$('#install-app').hidden=false});
  $('#install-app').onclick=async()=>{if(!installPrompt)return;await installPrompt.prompt();await installPrompt.userChoice;installPrompt=null;$('#install-app').hidden=true};
  $('#install-guide').onclick=()=>alert('Android: Chrome의 메뉴 → 앱 설치 또는 홈 화면에 추가.\niPhone: Safari의 공유 → 홈 화면에 추가 → 웹 앱으로 열기.\nHTTPS로 배포된 주소에서 설치하세요. 설치 전·후 저장소가 다를 수 있으므로 JSON 백업 후 필요하면 복원하세요.');
  $('#update-app').hidden=true;

  // v0.6.0 recovery: remove legacy service workers/caches that could break navigation.
  // PWA installation continues via the web app manifest; offline caching is temporarily disabled for stability.
  if('serviceWorker'in navigator&&location.protocol!=='file:'){
    window.addEventListener('load',async()=>{
      try{
        const regs=await navigator.serviceWorker.getRegistrations();
        await Promise.all(regs.map(r=>r.unregister()));
        if('caches'in window){
          const keys=await caches.keys();
          await Promise.all(keys.filter(k=>k.startsWith('my-asset-hub-')).map(k=>caches.delete(k)));
        }
      }catch(e){console.warn('legacy PWA cleanup failed',e)}
    });
  }
  window.addEventListener('resize',()=>{if(tab==='dashboard')renderHistory()});window.addEventListener('online',()=>{renderMarketStatus();refreshMarket(false)});window.addEventListener('offline',renderMarketStatus);
  window.addEventListener('storage',e=>{if(e.key===KEY&&e.newValue){try{state=normalize(JSON.parse(e.newValue));render()}catch{toast('다른 탭의 데이터를 확인하세요.')}}});
  // Testable existing calculations. No personal data leaves the device through this interface.
  window.AssetHub={version:APP_VERSION,normalize,calc,workbookRows,readWorkbook,getState:()=>structuredClone(state)};
  if(storageBlocked)render();else persist();startRefreshTimer();if(navigator.onLine)setTimeout(()=>refreshMarket(false),800);
})();
