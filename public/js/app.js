
(() => {
  'use strict';
  const KEY='my-asset-hub-beta-v4', PREVIOUS_KEY='my-asset-hub-beta-v3', LEGACY_KEY='my-asset-hub-html-v1';
  const defaults=()=>normalize({version:4,config:{target:1e9,fx:1350,fxSource:'자동 조회 대기',refreshMinutes:5,riskGroups:Portfolio.labels.map((label,i)=>({id:'risk_'+(i+1),label})),risks:['risk_1','risk_2','risk_3','risk_4'],cashRiskId:'risk_4'},stocks:[],savings:[],history:[],cash:{amount:0},riskTargets:{},allocations:{}});
  const $=s=>document.querySelector(s);
  const money=n=>`${Math.round(Number(n)||0).toLocaleString('ko-KR')}원`;
  const num=n=>Number.isFinite(Number(String(n).replace(/,/g,'')))?Number(String(n).replace(/,/g,'')):0;
  const formatMoney=x=>String(typeof x==='number'?Math.round(x):x??'').replace(/[^\d]/g,'').replace(/\B(?=(\d{3})+(?!\d))/g,',');
  const safe=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const uid=()=>globalThis.crypto?.randomUUID?.()||`id-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const today=()=>Cashflow.kstDate(Date.now()); // Asia/Seoul calendar day
  function finite(value,label,{nullable=false,min=0}={}){
    if(nullable&&(value===''||value==null))return null;
    if(value===''||value==null)throw Error(`${label}: 값이 비어 있습니다.`);
    const n=Number(typeof value==='string'?value.replace(/,/g,''):value);
    if(!Number.isFinite(n)||n<min)throw Error(`${label}: ${min} 이상의 숫자를 입력하세요.`);
    return n;
  }
  function bool(v){if(v===true||v===1||String(v).toLowerCase()==='true')return true;if(v===false||v===0||v==null||v===''||String(v).toLowerCase()==='false')return false;throw Error('해외여부는 TRUE/FALSE여야 합니다.')}
  function normalizeLegacy(raw){
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
    const savings=(raw.savings||[]).map((s,i)=>{const item={id:String(s.id||uid()),type:String(s.type??s['종류']??'적금'),name:String(s.name??s['상품명']??'').trim(),amount:finite(s.amount??s['금액']??s['월납입액'],`은행 ${i+1} 금액`),current:finite(s.current??s['현재회차']??1,'현재회차'),total:finite(s.total??s['총회차']??1,'총회차',{min:1}),rate:finite(s.rate??s['이율']??0,'이율')};if(!item.name||!['현금','입출금통장','파킹통장','증권 예수금','예금','적금','주택청약','기타'].includes(item.type))throw Error('은행 상품명·종류를 확인하세요.');if(!Number.isInteger(item.current)||!Number.isInteger(item.total)||(['적금','주택청약'].includes(item.type)&&item.current>item.total))throw Error('납입 회차는 정수이며 현재 회차는 총 회차 이하여야 합니다.');return item});
    const ids=[...stocks,...savings].map(s=>s.id);if(new Set(ids).size!==ids.length)throw Error('중복 ID가 있습니다. 새 자산의 ID를 비워 두세요.');
    const history=(raw.history||[]).map(h=>{const date=String(h.date??h['날짜']??'').slice(0,10);if(!/^\d{4}-\d{2}-\d{2}$/.test(date)||new Date(date+'T00:00:00Z').toISOString().slice(0,10)!==date)throw Error('자산 기록 날짜를 확인하세요.');return {date,total:finite(h.total??h['총자산'],'기록 총자산')}});
    const parseTargets=(obj)=>{if(typeof obj==='string')obj=JSON.parse(obj);const result=Object.create(null);for(const [k,v]of Object.entries(obj||{})){const n=finite(v,'목표 비중');if(n>100)throw Error('목표 비중은 100 이하입니다.');result[k]=n}return result};
    return {version:2,config:{target:finite(cfg.target??cfg.target_asset??1e9,'목표금액',{min:1}),fx:finite(cfg.fx??1350,'환율',{min:.01}),risks,refreshMinutes:[0,5,15,30].includes(Number(cfg.refreshMinutes))?Number(cfg.refreshMinutes):5,fxAsOf:String(cfg.fxAsOf||''),fxSource:String(cfg.fxSource||'수동'),fxError:String(cfg.fxError||'')},stocks,savings,history:[...new Map(history.map(h=>[h.date,h])).values()].sort((a,b)=>a.date.localeCompare(b.date)),riskTargets:parseTargets(raw.riskTargets??cfg.riskTargets),allocations:parseTargets(raw.allocations??cfg.allocations)};
  }
  function normalize(raw){return Portfolio.migrate(raw,normalizeLegacy)}
  const riskLabel=id=>state.config.riskGroups.find(g=>g.id===id)?.label||id;
  let state,storageBlocked=false;
  try{const saved=localStorage.getItem(KEY),previous=localStorage.getItem(PREVIOUS_KEY),legacy=localStorage.getItem(LEGACY_KEY),raw=saved||previous||legacy;
    state=raw?normalize(JSON.parse(raw)):defaults();
    if(raw&&(!saved||Number(JSON.parse(raw).version)<4)&&!localStorage.getItem(KEY+'-before-migration'))localStorage.setItem(KEY+'-before-migration',raw);
  }catch(e){state=defaults();storageBlocked=true;alert('기존 원본을 보존하고 저장을 중지했습니다. '+e.message)}
  let activePlan=null,quantityLocked=new Set(),investmentExcluded=new Set(),riskDraft=[],riskMoves={};
  let period='day',tab='dashboard',editType='',editId=null,editQuoteMeta=null;
  function toast(msg){const el=$('#toast');el.textContent=msg;el.classList.remove('hidden');setTimeout(()=>el.classList.add('hidden'),3200)}
  function calc(){return Portfolio.calc(state)}
  function persist({record=true}={}){
    if(storageBlocked){toast('기존 데이터 보호를 위해 저장이 중지되었습니다. 백업 파일로 복원하세요.');render();return false}
    if(record){const total=calc().total,date=today();if(total>0||state.history.length){const at=state.history.findIndex(h=>h.date===date);if(at>=0)state.history[at].total=total;else state.history.push({date,total});state.history.sort((a,b)=>a.date.localeCompare(b.date));}}
    try{state.revision=(state.revision||0)+1;localStorage.setItem(KEY,JSON.stringify(state));$('#save-status').textContent='이 기기에 저장';render();return true}catch(e){$('#save-status').textContent='저장 실패';toast('저장 공간을 확인한 뒤 JSON 백업을 만드세요.');return false}
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
    $('#stock-total').textContent=money(c.stockTotal);$('#bank-total').textContent=money(c.bankTotal+c.cashTotal);const delta=c.total-c.cost;$('#profit-total').textContent=`${delta>=0?'+':''}${money(delta)}`;$('#profit-total').className=delta<0?'negative':'positive';
    const parts=[{name:'가상화폐',value:c.stocks.filter(s=>s.ticker.toUpperCase().startsWith('KRW-')).reduce((a,s)=>a+s.value,0),color:colors[2]},{name:'해외 주식',value:c.stocks.filter(s=>s.foreign&&!s.ticker.toUpperCase().startsWith('KRW-')).reduce((a,s)=>a+s.value,0),color:colors[3]},{name:'국내 주식',value:c.stocks.filter(s=>!s.foreign&&!s.ticker.toUpperCase().startsWith('KRW-')).reduce((a,s)=>a+s.value,0),color:colors[1]},{name:'은행',value:c.bankTotal,color:colors[0]},{name:'현금',value:c.cashTotal,color:colors[4]}];$('#portfolio-viz').innerHTML=donut(parts,'자산 유형');
    const risks=state.config.riskGroups.map((g,i)=>({name:g.label,value:Portfolio.items(state).filter(x=>x.risk===g.id).reduce((a,x)=>a+x.value,0),color:colors[i%colors.length]}));$('#risk-viz').innerHTML=donut(risks,'리스크');
    $('#stock-count').textContent=`${c.stocks.length}개`;$('#bank-count').textContent=`${c.banks.length+1}개`;
    $('#stock-list').innerHTML=c.stocks.length?state.config.riskGroups.map(g=>`<div class="card asset-group" data-group="${safe(g.id)}"><h3>${safe(g.label)}</h3>${c.stocks.filter(s=>s.risk===g.id).sort((a,b)=>(a.displayOrder??0)-(b.displayOrder??0)).map(s=>`<div class="row sortable-asset" data-asset-id="${safe(s.id)}" data-group="${safe(g.id)}"><button type="button" class="drag-handle" data-drag-id="${safe(s.id)}" aria-label="${safe(s.name)} 이동">≡</button><div class="row-main"><div class="row-title">${safe(s.name)} <span class="muted">${safe(s.ticker)}</span></div><div class="row-sub">${safe(riskLabel(s.risk))} · ${s.quantity.toLocaleString('ko-KR',{maximumFractionDigits:8})}주/개 · 평단 ${s.buyKrw.toLocaleString('ko-KR')} KRW${s.estimated?' · 현재가 미입력(평단 적용)':''}<span class="quote-meta">${safe(s.quoteError||`${s.quoteSource||'수동 입력'} · ${s.quoteAsOf?new Date(s.quoteAsOf).toLocaleString('ko-KR'):'기준 시각 없음'}`)}</span></div></div><div class="row-value"><strong>${money(s.value)}</strong><small class="${s.value-s.cost<0?'negative':'positive'}">${s.cost?`${((s.value-s.cost)/s.cost*100).toFixed(1)}%`:'—'}</small><div class="row-actions"><button class="btn small" data-edit="stock" data-id="${safe(s.id)}">수정</button><button class="btn small danger" data-delete="stock" data-id="${safe(s.id)}">삭제</button></div></div></div>`).join('')}</div>`).join(''):'<div class="empty">등록된 투자 자산이 없습니다.</div>';
    $('#bank-list').innerHTML=state.config.riskGroups.map(g=>{const assets=[...c.banks,{...state.cash,value:c.cashTotal,type:'현금',fixed:false,risk:state.config.cashRiskId}].filter(x=>x.risk===g.id).sort((a,b)=>(a.displayOrder??0)-(b.displayOrder??0));return `<div class="card asset-group" data-group="${safe(g.id)}"><h3>${safe(g.label)}</h3>${assets.map(x=>`<div class="row sortable-asset" data-asset-id="${safe(x.id)}" data-group="${safe(g.id)}"><button type="button" class="drag-handle" aria-label="${safe(x.name)} 이동" data-drag-id="${safe(x.id)}">≡</button><div class="row-main"><div class="row-title">${safe(x.name)} <span class="muted">${safe(x.type)}</span></div><div class="row-sub">현재 잔액 ${money(x.value)} · ${x.fixed?'고정자산':'유동자산'}${x.monthlyPayment?' · 월 납입 '+money(x.monthlyPayment):''}</div></div><div class="row-value"><strong>${money(x.value)}</strong><div class="row-actions"><button class="btn small" data-edit="${x.id==='cash'?'cash':'bank'}" data-id="${safe(x.id)}">수정</button>${x.id==='cash'?'':`<button class="btn small danger" data-delete="bank" data-id="${safe(x.id)}">삭제</button>`}</div></div></div>`).join('')}</div>`}).join('');
    $('#cash-value').textContent=money(c.cashTotal);renderHistory();renderRebalance(c);renderMarketStatus();renderTransactions();
  }
  function renderRebalance(c){
    const v=Portfolio.validateTargets(state),all=Portfolio.items(state);
    $('#risk-targets').innerHTML=state.config.riskGroups.map(g=>`<label class="target-row"><span>${safe(g.label)}</span><span>현재 ${(all.filter(x=>x.risk===g.id).reduce((a,x)=>a+x.value,0)/Math.max(c.total,1)*100).toFixed(1)}%</span><input aria-label="${safe(g.label)} 목표" type="number" min="0" max="100" step="any" data-risk="${g.id}" value="${num(state.riskTargets[g.id])}"></label>`).join('');
    $('#target-sum').textContent=`합계 ${v.sum.toFixed(1)}% / 100% · ${v.step1?'STEP 2 사용 가능':'100%를 맞추면 다음 단계가 열립니다.'}`;
    $('#step2').disabled=!v.step1;$('#step3').disabled=!v.step2;
    $('#allocation-list').innerHTML=state.config.riskGroups.map(g=>`<div class="card"><b>${safe(g.label)} · 목표 ${num(state.riskTargets[g.id]).toFixed(1)}%</b>${all.filter(x=>x.risk===g.id).map(x=>`<label class="target-row"><span>${safe(x.name)} · 현재 ${(x.value/Math.max(c.total,1)*100).toFixed(1)}%${x.kind==='bank'&&x.fixed?' (고정자산)':x.kind==='stock'?' · 현재 '+x.quantity+(x.ticker.startsWith('KRW-')?'개':'주'):''}</span>${x.kind==='stock'?`<label class="quantity-lock"><input type="checkbox" data-lock="${safe(x.id)}" ${quantityLocked.has(x.id)?'checked':''}> 수량 유지</label>`:''}<input aria-label="${safe(x.name)} 목표" type="number" min="0" max="100" step="any" data-allocation="${safe(x.id)}" value="${num(state.allocations[x.id]).toFixed(1)}" ${quantityLocked.has(x.id)?'disabled':''}><span>%</span></label>`).join('')}<small>그룹 목표 ${num(state.riskTargets[g.id]).toFixed(1)}% · 수량 유지 자산 예상 ${all.filter(x=>x.risk===g.id&&quantityLocked.has(x.id)).reduce((a,x)=>a+x.value/Math.max(c.total,1)*100,0).toFixed(1)}% · 입력 합계 ${v.groups.find(x=>x.id===g.id).sum.toFixed(1)}% ${v.groups.find(x=>x.id===g.id).valid?'✓ 설정 완료':''}</small></div>`).join('');
    $('#allocation-sum').textContent=v.step2?'목표 일치 · STEP 3 사용 가능':'그룹별 종목 합계를 해당 목표와 맞춰 주세요.';
    $('#rebalance-basis').textContent=`총자산 ${money(c.total)} · 현금 ${money(c.cashTotal)} · 은행 ${money(c.bankTotal)}. 유동 현금성 자산 ${money(Portfolio.liquidTotal(state))}에서 최소 현금을 남기고 사용합니다. 고정자산도 각 리스크 그룹의 100% 목표에 포함됩니다.`;
    $('#monthly-comparison').innerHTML=c.stocks.length?c.stocks.map(x=>{const current=x.value/Math.max(c.total,1)*100,target=num(state.allocations[x.id]);return `<div class="row"><span>${safe(x.name)}</span><b>${(current-target).toFixed(1)}%p</b></div>`}).join(''):'<p class="hint">투자 자산을 등록하고 리스크 목표 합계 100.0%를 맞추면 비교가 나타납니다.</p>';
    const exclusions=state.stocks.map(x=>`<label class="exclude-row"><input type="checkbox" data-exclude="${safe(x.id)}" ${investmentExcluded.has(x.id)?'checked':''}> ${safe(x.name)}</label>`).join('');$('#monthly-exclusions').innerHTML=exclusions;
    $('#plan-output').innerHTML='';$('#monthly-plan').innerHTML='';activePlan=null;
  }
  const field=(name,label,value,type='text',extra='')=>'<label class="field">'+label+'<input name="'+name+'" type="'+type+'" value="'+safe(type==='money'?formatMoney(value):value??'')+'" '+(type==='money'?'inputmode="numeric" data-money ':'')+extra+'></label>';
  let editorSearchTimer=null,editorSearchSeq=0,quoteSequence=0;
  function updateSelectedAssetSummary(){
    const f=$('#editor-form'),box=$('#selected-asset'),buyLabel=$('#buy-price-label');
    if(!f?.elements?.name||!box)return;
    const name=f.elements.name.value,ticker=f.elements.ticker.value,market=f.elements.market.value,foreign=f.elements.foreign.value==='true';
    const currency=foreign?'USD':'KRW';
    box.textContent=name?(name+' · '+ticker+' · '+market+' · '+currency):'종목명 또는 티커를 검색해서 선택하세요.';
    if(buyLabel)buyLabel.textContent='원화 기준 매수평단 (원/주·개)';
  }
  async function loadEditorQuote(){
    const f=$('#editor-form'),status=$('#editor-quote-status');
    if(!f?.elements?.ticker?.value)return;
    const sequence=++quoteSequence;const ticker=f.elements.ticker.value,market=f.elements.market.value,foreign=f.elements.foreign.value==='true',currency=foreign?'USD':'KRW';
    f.elements.price.value='';
    editQuoteMeta=null;
    if(status)status.textContent='현재가 조회 중…';
    try{
      const q=await api('/api/quote?ticker='+encodeURIComponent(ticker)+'&market='+encodeURIComponent(market||'')+'&currency='+currency);
      if(!Number.isFinite(q.price)||q.price<=0||q.currency!==currency)throw Error('가격·통화 검증 실패');
      if(sequence!==quoteSequence||f.elements.ticker.value!==ticker)return;
      f.elements.price.value=q.price;
      editQuoteMeta={quoteAsOf:q.asOf||new Date().toISOString(),quoteSource:q.source||'자동 시세',quoteKind:q.kind||'',quoteError:''};
      if(status)status.textContent='현재가 '+Number(q.price).toLocaleString('ko-KR')+' '+currency+' · '+(q.source||'자동 시세');
    }catch(err){
      if(sequence!==quoteSequence)return;
      editQuoteMeta={quoteAsOf:'',quoteSource:'',quoteKind:'',quoteError:String(err.message||err)};
      if(status)status.textContent='현재가 조회 실패 · 저장 전 다시 조회합니다.';
    }
  }
  async function applyEditorMarketSelection(x){
    const f=$('#editor-form');
    if(!f||!x)return;
    const ticker=x.ticker||x.symbol||'',currency=x.currency==='USD'?'USD':'KRW';
    f.elements.name.value=x.name||x.symbol||ticker;
    f.elements.ticker.value=ticker;
    f.elements.market.value=x.market||'';
    f.elements.foreign.value=currency==='USD'?'true':'false';
    const lookup=$('#asset-lookup'),results=$('#asset-lookup-results');
    if(lookup)lookup.value=f.elements.name.value;
    if(results){results.innerHTML='';results._items=[]}
    updateSelectedAssetSummary();
    await loadEditorQuote();
  }
  async function searchEditorMarket(q){
    const box=$('#asset-lookup-results');
    if(!box)return;
    q=String(q||'').trim();
    if(q.length<1){box.innerHTML='';return}
    const seq=++editorSearchSeq;
    box.innerHTML='<div class="empty">검색 중…</div>';
    try{
      const data=await api('/api/search?q='+encodeURIComponent(q)+'&market=ALL&offset=0');
      if(seq!==editorSearchSeq)return;
      box._items=data.results||[];
      box.innerHTML=box._items.length?box._items.slice(0,12).map((x,i)=>'<button type="button" class="btn" data-editor-market-pick="'+i+'" style="text-align:left;white-space:normal">'+safe(x.name)+' · '+safe(x.ticker||x.symbol)+' · '+safe(x.market)+'</button>').join(''):'<div class="empty">검색 결과가 없습니다.</div>';
    }catch(err){
      if(seq!==editorSearchSeq)return;
      box._items=[];
      box.innerHTML='<div class="empty">종목 검색 실패 · 네트워크를 확인하세요.</div>';
    }
  }
  function openEditor(type,id=null,selected=null){
    quoteSequence++;editorSearchSeq++;editType=type;editId=id;
    const obj=type==='cash'?state.cash:(type==='stock'?state.stocks:state.savings).find(x=>x.id===id)||selected||{};
    editQuoteMeta=type==='stock'&&id?{quoteAsOf:obj.quoteAsOf||'',quoteSource:obj.quoteSource||'',quoteKind:obj.quoteKind||'',quoteError:obj.quoteError||''}:null;
    $('#editor-title').textContent=(id?'수정':'추가')+' · '+(type==='stock'?'투자 자산':'은행 자산');
    if(type==='stock'){
      const currency=obj.foreign?'USD':'KRW';
      $('#editor-fields').innerHTML=
        '<label class="field" style="grid-column:1/-1">종목명 또는 티커 검색<input id="asset-lookup" type="search" autocomplete="off" placeholder="삼성전자, 005930, AAPL" value="'+safe(obj.name||'')+'"></label>'+
        '<div id="asset-lookup-results" class="list" style="grid-column:1/-1;max-height:220px;overflow:auto"></div>'+
        '<div id="selected-asset" class="notice" style="grid-column:1/-1"></div>'+
        '<input name="name" type="hidden" value="'+safe(obj.name||'')+'">'+
        '<input name="ticker" type="hidden" value="'+safe(obj.ticker||'')+'">'+
        '<input name="market" type="hidden" value="'+safe(obj.market||'')+'">'+
        '<input name="foreign" type="hidden" value="'+(obj.foreign?'true':'false')+'">'+
        '<label class="field"><span id="buy-price-label">매수 평단가 ('+currency+')</span><input name="buy" type="text" inputmode="numeric" data-money value="'+safe(formatMoney(obj.buyKrw??''))+'" required></label>'+
        '<label class="field">보유 수량<input name="quantity" type="number" value="'+safe(obj.quantity??'')+'" min="0" step="any" required></label>'+
        '<label class="field">현재가 (자동 조회)<input name="price" type="number" value="'+safe(obj.price??'')+'" min="0" step="any" readonly placeholder="종목 선택 시 자동 조회"></label>'+
        '<div id="editor-quote-status" class="hint" style="align-self:end">'+safe(obj.quoteError||((obj.price!=null&&obj.quoteSource)?('현재가 '+Number(obj.price).toLocaleString('ko-KR')+' '+currency+' · '+obj.quoteSource):'종목 선택 시 현재가가 자동 조회됩니다.'))+'</div>'+
        '<label class="field">리스크 분류<select name="risk">'+[...new Set([...state.config.risks,...(obj.risk?[obj.risk]:[])])].map(r=>'<option value="'+safe(r)+'" '+(obj.risk===r?'selected':'')+'>'+safe(riskLabel(r))+'</option>').join('')+'</select></label>'+
        '<p class="hint" style="grid-column:1/-1">종목명이나 티커 하나만 검색하면 종목명·티커·시장·통화·현재가가 자동으로 채워집니다. 해외 주식도 원화 기준 매수평단을 입력하세요. 현재 평가액 환율은 자동 적용합니다.</p>';
      updateSelectedAssetSummary();
    }else if(type==='cash'){
      $('#editor-fields').innerHTML=field('balance','현재 현금 잔액 (원)',obj.amount,'money','required');
    }else{
      $('#editor-fields').innerHTML='<label class="field">종류<select name="type">'+['현금','입출금통장','파킹통장','증권 예수금','예금','적금','주택청약','기타'].map(t=>'<option '+(obj.type===t?'selected':'')+'>'+t+'</option>').join('')+'</select></label>'+field('name','상품명',obj.name,'text','required')+field('balance','현재 잔액 (원)',obj.balance??obj.amount??0,'money','required')+'<label class="field">구분<select name="liquidityType"><option value="liquid">유동자산</option><option value="fixed">고정자산</option></select></label>'+field('rate','연 이율 (%) · 평가액에 미반영',obj.rate??0,'number','min="0" step="any" required')+'<div id="recurring-fields" class="fields" style="grid-column:1/-1">'+field('monthlyPayment','월 납입액',obj.monthlyPayment??0,'money')+field('paymentDay','납입일 (1~31일)',obj.paymentDay??1,'number','min="1" max="31"')+'<label class="field">자동 반영<select name="autoApply"><option value="false">OFF</option><option value="true">ON</option></select></label><label class="field">출금 대상<select name="sourceAssetId" id="saving-source"></select></label></div>';
    }
    if(type==='bank'){const f=$('#editor-form');f.elements.liquidityType.value=obj.liquidityType||(['적금','주택청약','예금'].includes(obj.type)?'fixed':'liquid');f.elements.autoApply.value=String(obj.autoApply===true);const source=$('#saving-source');source.innerHTML=[state.cash,...state.savings.filter(x=>x.id!==id&&x.liquidityType==='liquid')].map(x=>`<option value="${safe(x.id)}">${safe(x.name)}</option>`).join('');source.value=obj.sourceAssetId||'cash';const sync=()=>{const recurring=['적금','주택청약','기타'].includes(f.elements.type.value);$('#recurring-fields').hidden=!recurring;};f.elements.type.onchange=()=>{if(!id)f.elements.liquidityType.value=['적금','주택청약','예금'].includes(f.elements.type.value)?'fixed':'liquid';sync()};sync();}
    $('#editor').showModal();
    if(type==='stock'){
      const lookup=$('#asset-lookup');
      lookup.oninput=e=>{editorSearchSeq++;clearTimeout(editorSearchTimer);const q=e.target.value.trim();editorSearchTimer=setTimeout(()=>searchEditorMarket(q),250)};
      if(!id)lookup.focus();
    }
  }

  $('#editor-form').addEventListener('submit',async e=>{
    e.preventDefault();
    const form=e.currentTarget,fd=new FormData(form),val=k=>String(fd.get(k)||'').trim(),n=k=>Number(String(fd.get(k)).replace(/,/g,''));
    let item;
    if(editType==='cash'){try{const next=structuredClone(state),amount=finite(val('balance'),'현금'),delta=amount-next.cash.amount;next.cash.amount=amount;if(delta)next.cashflows.push({id:uid(),at:new Date().toISOString(),amount:delta,type:'manual-cash-adjustment'});if(commitState(next))$('#editor').close()}catch(error){toast(error.message)}return;}
    if(editType==='stock'){
      item={id:editId||uid(),name:val('name'),ticker:val('ticker').toUpperCase(),buyKrw:n('buy'),buy:n('buy')/(val('foreign')==='true'?state.config.fx:1),quantity:n('quantity'),price:val('price')===''?null:n('price'),foreign:val('foreign')==='true',risk:val('risk'),market:val('market')||(val('foreign')==='true'?'US':'KRX'),buyFx:val('foreign')==='true'?state.config.fx:null};
      if(!item.name||!item.ticker){toast('종목명 또는 티커를 검색해서 종목을 선택하세요.');return}
      if(!(item.price>0)){
        try{
          const currency=item.foreign?'USD':'KRW';
          const q=await api('/api/quote?ticker='+encodeURIComponent(item.ticker)+'&market='+encodeURIComponent(item.market||'')+'&currency='+currency);
          if(!Number.isFinite(q.price)||q.price<=0||q.currency!==currency)throw Error('가격·통화 검증 실패');
          item.price=q.price;
          editQuoteMeta={quoteAsOf:q.asOf||new Date().toISOString(),quoteSource:q.source||'자동 시세',quoteKind:q.kind||'',quoteError:''};
          if(form.elements.price)form.elements.price.value=q.price;
        }catch(err){
          toast('현재가를 불러오지 못했습니다. 잠시 후 다시 저장해 주세요.');
          return;
        }
      }
    }else{
      item={id:editId||uid(),type:val('type'),name:val('name'),balance:n('balance'),amount:n('balance'),current:1,total:1,rate:n('rate'),liquidityType:val('liquidityType'),monthlyPayment:['적금','주택청약','기타'].includes(val('type'))?n('monthlyPayment'):0,paymentDay:['적금','주택청약','기타'].includes(val('type'))?n('paymentDay'):1,autoApply:['적금','주택청약','기타'].includes(val('type'))&&val('autoApply')==='true',sourceAssetId:val('sourceAssetId')};
    }
    const arr=editType==='stock'?state.stocks:state.savings;
    const idx=arr.findIndex(x=>x.id===editId);if(editType==='bank'){item.risk=arr[idx]?.risk||state.config.cashRiskId;item.displayOrder=arr[idx]?.displayOrder??arr.length;}
    if(editType==='stock'){
      if(item.ticker.endsWith('.KQ'))item.market='KOSDAQ';
      if(item.ticker.endsWith('.KS'))item.market='KOSPI';
      item.ticker=item.ticker.replace(/\.(KS|KQ)$/,'');
      if(!item.foreign&&/^\d{1,6}$/.test(item.ticker))item.ticker=item.ticker.padStart(6,'0');
      const old=arr[idx];if(old&&formatMoney(old.buyKrw)===formatMoney(item.buyKrw))item.buyKrw=old.buyKrw;if(old&&old.buyKrw===item.buyKrw){item.buy=old.buy;item.buyFx=old.buyFx;}
      if(editQuoteMeta)Object.assign(item,editQuoteMeta);
      else if(old&&old.price===item.price&&old.ticker===item.ticker&&old.foreign===item.foreign)Object.assign(item,{quoteAsOf:old.quoteAsOf,quoteSource:old.quoteSource,quoteError:old.quoteError,quoteKind:old.quoteKind});
      else Object.assign(item,{quoteAsOf:new Date().toISOString(),quoteSource:'자동 시세',quoteError:'',quoteKind:''});
      const same=idx<0&&item.ticker?arr.find(x=>x.ticker===item.ticker&&x.foreign===item.foreign):null;
      if(same){
        if(!confirm('이미 보유한 종목입니다. 입력한 수량을 추가 매수로 합산하고 가중 평단을 계산할까요?'))return;
        const q=same.quantity+item.quantity,totalCost=same.buyKrw*same.quantity+item.buyKrw*item.quantity;
        const merged={...same,quantity:q,buyKrw:q?totalCost/q:0,risk:item.risk,price:item.price||same.price};
        if(editQuoteMeta)Object.assign(merged,editQuoteMeta);
        const next=structuredClone(state);
        next.stocks[next.stocks.findIndex(x=>x.id===same.id)]=merged;
        try{state=Portfolio.distribute(normalize(next),'equal',true)}catch(err){toast(err.message);return}
        $('#editor').close();
        if(persist())toast('추가 매수를 합산했습니다.');
        return;
      }
    }
    const next=structuredClone(state),dest=editType==='stock'?next.stocks:next.savings;
    if(idx<0)dest.push(item);else dest[idx]=item;
    try{state=Portfolio.distribute(normalize(next),'equal',true)}catch(err){toast(err.message);return}
    $('#editor').close();
    if(persist()){
      toast('자산이 저장되었습니다.');
      if(editType==='stock'&&item.ticker&&navigator.onLine)setTimeout(()=>refreshMarket(false),0);
    }
  });
  document.addEventListener('click',async e=>{
    const t=e.target.closest('button');
    if(!t)return;
    if(t.dataset.close!==undefined){t.closest('dialog').close();return}
    if(t.dataset.tab){
      tab=t.dataset.tab;
      document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('active',x.dataset.tab===tab));
      document.querySelectorAll('.panel').forEach(x=>x.classList.toggle('active',x.id===tab));
      if(tab==='dashboard')renderHistory();
      return;
    }
    if(t.dataset.period){
      period=t.dataset.period;
      document.querySelectorAll('[data-period]').forEach(x=>x.classList.toggle('selected',x.dataset.period===period));
      renderHistory();
      return;
    }
    if(t.dataset.editorMarketPick!==undefined){
      const x=$('#asset-lookup-results')._items?.[Number(t.dataset.editorMarketPick)];
      if(x)await applyEditorMarketSelection(x);
      return;
    }
    if(t.dataset.marketPick!==undefined){
      const x=$('#market-results')._items?.[Number(t.dataset.marketPick)];
      if(x){$('#market-search').close();await applyEditorMarketSelection(x)}
      return;
    }
    if(t.dataset.edit){if(t.dataset.edit==='cash')$('#edit-cash').click();else openEditor(t.dataset.edit,t.dataset.id);return}
    if(t.dataset.delete){
      const arr=t.dataset.delete==='stock'?state.stocks:state.savings;
      const entry=arr.find(x=>x.id===t.dataset.id);
      if(entry&&confirm(entry.name+' 자산을 삭제할까요?')){
        arr.splice(arr.indexOf(entry),1);
        delete state.allocations[entry.id];
        if(persist())toast('삭제했습니다.');
      }
      return;
    }
  });
  $('#add-stock').onclick=()=>openEditor('stock');$('#add-bank').onclick=()=>openEditor('bank');$('#backup-btn').onclick=()=>$('#backup').showModal();$('#refresh-market').onclick=()=>refreshMarket(true);$('#settings-btn').onclick=openSettings;
  $('#settings-form').onsubmit=saveSettings;
  document.addEventListener('change',e=>{if(e.target.dataset.risk!==undefined){state.riskTargets[e.target.dataset.risk]=Math.max(0,Math.min(100,num(e.target.value)));state=Portfolio.distribute(state,'equal',true);persist({record:false})}if(e.target.dataset.lock!==undefined){if(e.target.checked){quantityLocked.add(e.target.dataset.lock);const x=Portfolio.items(state).find(x=>x.id===e.target.dataset.lock);state.allocations[x.id]=x.value/Math.max(calc().total,1)*100}else quantityLocked.delete(e.target.dataset.lock);persist({record:false})}if(e.target.dataset.allocation!==undefined){state.allocations[e.target.dataset.allocation]=Math.max(0,Math.min(100,num(e.target.value)));persist({record:false})}});
  $('#export-btn').onclick=()=>{const blob=new Blob([JSON.stringify(state,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`my-asset-hub-${today()}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
  const APP_VERSION='0.8.0-beta.2';
  const BUILD_ID='20260928-beta-02';
  let refreshBusy=false,autoTimer=null,searchTimer=null,searchOffset=0,searchSequence=0,pendingImport=null;
  const API_BASE=String(window.ASSET_HUB_API_BASE||'').replace(/\/$/,'');
  async function api(path){const ctl=new AbortController(),timer=setTimeout(()=>ctl.abort(),20000);try{const r=await fetch(API_BASE+path,{signal:ctl.signal,headers:{accept:'application/json'},cache:'no-store'});const d=await r.json();if(!r.ok||d.error)throw Error(d.error||`API ${r.status}`);return d}finally{clearTimeout(timer)}}
  async function checkBuildStatus(){
    const el=$('#build-status'),versionEl=$('#version-label');
    if(versionEl)versionEl.textContent=`TEST · v${APP_VERSION} · build ${BUILD_ID}`;
    if(!el)return;
    el.textContent=`build ${BUILD_ID} 확인 중…`;
    try{
      const h=await api(`/api/health?_=${Date.now()}`);
      if(h.build===BUILD_ID){el.textContent=`build ${BUILD_ID} 적용됨`;el.title='현재 화면과 서버 빌드가 일치합니다.'}
      else if(h.build){el.textContent=`새 서버 build ${h.build} · 새로고침 필요`;el.title='현재 HTML/JS와 서버 빌드가 다릅니다.'}
      else{el.textContent=`build ${BUILD_ID} · 서버 구버전`;}
    }catch(e){el.textContent=`build ${BUILD_ID} · 서버 확인 실패`;el.title=e.message}
  }
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
  $('#distribute').onclick=()=>{state=Portfolio.distribute(state,'value');persist({record:false})};
  $('#equal-distribute').onclick=()=>{state=Portfolio.distribute(state,'equal');persist({record:false})};
  function openSettings(){riskDraft=structuredClone(state.config.riskGroups);riskMoves={};const f=$('#settings-form');for(const k of ['target','fx','monthlyInvestment','minCash','minCashMode','refreshMinutes'])f.elements[k].value=f.elements[k].dataset.money!==undefined?formatMoney(state.config[k]):state.config[k];f.elements.salaryAmount.value=formatMoney(state.config.salary.amount);f.elements.salaryDay.value=state.config.salary.day;f.elements.salaryAutoApply.value=String(state.config.salary.autoApply);f.elements.salaryTargetId.innerHTML=[state.cash,...state.savings.filter(x=>x.liquidityType==='liquid')].map(x=>`<option value="${safe(x.id)}">${safe(x.name)}</option>`).join('');f.elements.salaryTargetId.value=state.config.salary.targetId||'cash';renderRiskEditor(state.config.cashRiskId);$('#settings').showModal();}
  function renderRiskEditor(cashId=$('#cash-risk').value){$('#risk-editor').innerHTML=riskDraft.map(g=>`<div class="risk-edit-row"><input aria-label="분류 이름" data-risk-label="${g.id}" value="${safe(g.label)}"><input aria-label="분류 설명" data-risk-description="${g.id}" value="${safe(g.description)}" placeholder="설명"><button type="button" class="btn small danger" data-remove-risk="${g.id}">삭제·이동</button></div>`).join('');$('#cash-risk').innerHTML=riskDraft.map(g=>`<option value="${g.id}">${safe(g.label)}</option>`).join('');$('#cash-risk').value=riskDraft.some(g=>g.id===cashId)?cashId:riskDraft.at(-1).id;}
  $('#risk-editor').oninput=e=>{const id=e.target.dataset.riskLabel||e.target.dataset.riskDescription,g=riskDraft.find(g=>g.id===id);if(g)g[e.target.dataset.riskLabel?'label':'description']=e.target.value};
  let removingRisk=null;
  $('#risk-editor').onclick=e=>{const b=e.target.closest('[data-remove-risk]');if(!b)return;if(riskDraft.length<2){toast('최소 한 분류는 유지해야 합니다.');return}removingRisk=b.dataset.removeRisk;$('#risk-move-target').innerHTML=riskDraft.filter(g=>g.id!==removingRisk).map(g=>`<option value="${g.id}">${safe(g.label)}</option>`).join('');$('#risk-move').showModal()};
  $('#confirm-risk-move').onclick=()=>{const dest=$('#risk-move-target').value;for(const [k,v]of Object.entries(riskMoves))if(v===removingRisk)riskMoves[k]=dest;riskMoves[removingRisk]=dest;riskDraft=riskDraft.filter(g=>g.id!==removingRisk);const cashId=$('#cash-risk').value;renderRiskEditor(cashId===removingRisk?dest:cashId);$('#risk-move').close()};
  $('#add-risk').onclick=()=>{riskDraft.push({id:'risk_'+uid().replace(/-/g,''),label:'새 분류 '+(riskDraft.length+1),description:''});renderRiskEditor()};
  function saveSettings(e){e.preventDefault();try{const f=e.currentTarget;let next=Portfolio.renameRisks(state,riskDraft,f.elements.cashRiskId.value,riskMoves);for(const k of ['target','monthlyInvestment','minCash','refreshMinutes'])next.config[k]=num(f.elements[k].value);next.config.minCashMode=f.elements.minCashMode.value;next.config.salary={amount:num(f.elements.salaryAmount.value),day:num(f.elements.salaryDay.value),autoApply:f.elements.salaryAutoApply.value==='true',targetId:f.elements.salaryTargetId.value};next=normalize(next);if(commitState(next)){ $('#settings').close();$('#monthly-amount').value=formatMoney(state.config.monthlyInvestment);startRefreshTimer();toast('설정을 저장했습니다.')}}catch(e){toast(e.message)}}
  function commitState(next,{backupKey=null,record=true}={}){if(storageBlocked){toast('원본 보호 상태에서는 적용할 수 없습니다.');return false}const previous=state;try{const saved=localStorage.getItem(KEY);if(saved&&Number(JSON.parse(saved).revision)!==state.revision)throw Error('다른 화면에서 변경되었습니다. 새로고침 후 진행하세요.');next=normalize(next);if(backupKey)localStorage.setItem(backupKey,JSON.stringify({state:previous,transactionId:next.transactions.at(-1)?.id}));state=next;if(!persist({record}))throw Error('저장에 실패했습니다. 적용되지 않았습니다.');return true}catch(e){state=previous;render();toast(e.message);return false}}
  $('#edit-cash').onclick=()=>openEditor('cash','cash');
  document.addEventListener('change',e=>{const id=e.target.dataset.exclude;if(!id)return;if(e.target.checked)investmentExcluded.add(id);else investmentExcluded.delete(id);document.querySelectorAll(`[data-exclude="${CSS.escape(id)}"]`).forEach(box=>box.checked=e.target.checked);activePlan=null;$('#plan-output').innerHTML='설정이 변경되었습니다. 다시 계산하세요.';$('#monthly-plan').textContent='설정이 변경되었습니다. 다시 계산하세요.'});
  $('#calculate-plan').onclick=()=>{try{activePlan=Portfolio.plan(state,{mode:'rebalance',lockedIds:[...quantityLocked]});renderPlan(activePlan)}catch(e){activePlan=null;$('#plan-output').textContent=e.message}};
  function renderPlan(p,output='#plan-output'){
    $(output==='#plan-output'?'#monthly-plan':'#plan-output').innerHTML='';
    const trades=p.trades.filter(t=>t.delta),sell=trades.filter(t=>t.delta<0),buy=trades.filter(t=>t.delta>0);
    const list=arr=>arr.map(t=>`<div class="row"><b>${safe(t.name)}</b><span>${Math.abs(t.delta)} ${t.crypto?'개':'주'} · ${money(t.amount)}</span></div>`).join('')||'<p class="hint">없음</p>';
    $(output).innerHTML=p.warnings.map(x=>`<div class="notice warn">${safe(x)}</div>`).join('')+`<h3>실행 계획</h3>${p.mode==='rebalance'?'<h3>매도</h3>'+list(sell):''}<h3>매수</h3>${list(buy)}<h3>예상 잔여 현금성 자산 ${money(p.cashAfter)}</h3><details><summary>상세보기</summary>${p.trades.map(t=>`<div class="trade-card"><b>${safe(t.name)}</b><div class="trade-stats"><span>현재 ${t.currentPct.toFixed(1)}%</span><span>목표 ${t.targetPct.toFixed(1)}%</span><span>예상 ${t.afterPct.toFixed(1)}%</span><span>오차 ${(t.afterPct-t.targetPct).toFixed(1)}%p</span><span>수량 ${t.current} → ${t.target}</span><span>예상 거래 ${money(t.amount)}</span></div></div>`).join('')}</details><button class="btn primary" id="start-fills">${p.mode==='investment'?'구매 진행':'체결 입력'}</button>`;
    $(output+' #start-fills').onclick=openFills;
  }
  function openFills(){if(!activePlan)return;$('#fills-list').innerHTML=activePlan.trades.filter(t=>t.delta).sort((a,b)=>a.delta-b.delta).map(t=>`<div class="fill-card" data-fill-id="${safe(t.id)}"><b>${safe(t.name)} · ${t.delta<0?'매도':'매수'}</b><p>추천 ${Math.abs(t.delta)} × ${t.price} ${t.foreign?'USD':'KRW'}</p><div class="fields"><label class="field">실제 체결수량<input data-fill-qty type="number" min="0" max="${Math.abs(t.delta)}" step="${t.crypto?'0.00000001':'1'}" value="${Math.abs(t.delta)}" required></label><label class="field">실제 체결가격 (${t.foreign?'USD':'KRW'})<input data-fill-price type="${t.foreign?'number':'text'}" ${t.foreign?'step="any"':'inputmode="numeric" data-money'} value="${t.foreign?t.price:formatMoney(t.price)}" required></label><label class="field">수수료 (원)<input data-fill-fee type="text" inputmode="numeric" data-money value="0" required></label></div><button class="btn small" type="button" data-unfilled>미체결 (0)</button></div>`).join('')||'<p>거래 없이 투입금이 현금으로 기록됩니다.</p>';$('#fills-dialog').showModal();}
  $('#fills-list').onclick=e=>{const b=e.target.closest('[data-unfilled]');if(b){const row=b.closest('[data-fill-id]');row.querySelector('[data-fill-qty]').value=0;row.querySelector('[data-fill-fee]').value=0}};
  $('#fills-form').onsubmit=e=>{e.preventDefault();try{if(!activePlan)throw Error('자산 또는 시세가 변경되었습니다. 다시 계산하세요.');const p=activePlan,fills=[...document.querySelectorAll('[data-fill-id]')].map(row=>({id:row.dataset.fillId,quantity:num(row.querySelector('[data-fill-qty]').value),price:num(row.querySelector('[data-fill-price]').value),fee:num(row.querySelector('[data-fill-fee]').value)}));const next=Portfolio.execute(state,p,fills);if(!confirm(`${p.mode==='investment'?'투자':'리밸런싱'}를 완료하셨습니까?\n완료하면 보유수량, 평단가, 현금 및 투자 이력이 변경됩니다.`))return;if(commitState(next,{backupKey:KEY+'-before-'+p.mode})){activePlan=null;$('#fills-dialog').close();toast('실제 체결을 반영했습니다.')}}catch(e){alert(e.message)}};
  function undo(type){try{const raw=localStorage.getItem(KEY+'-before-'+type);if(!raw)throw Error('되돌릴 기록이 없습니다.');const saved=JSON.parse(raw);if(state.transactions.at(-1)?.id!==saved.transactionId)throw Error('가장 최근 실행만 되돌릴 수 있습니다. 이후 거래가 있습니다.');if(!confirm('직전 실행 전 전체 자산·설정·기록으로 복구합니다. 실행 이후 직접 수정한 내용도 되돌아갑니다. 계속할까요?'))return;const next=normalize(saved.state);next.revision=state.revision;if(commitState(next,{record:false})){localStorage.removeItem(KEY+'-before-'+type);toast('이전 상태를 복구했습니다.')}}catch(e){toast(e.message)}}
  $('#undo-rebalance').onclick=()=>undo('rebalance');$('#undo-investment').onclick=()=>undo('investment');
  function renderTransactions(){$('#transactions-list').innerHTML=state.transactions.slice().reverse().map(t=>`<div class="trade-card"><b>${safe(t.at)} · ${({investment:'월 투자',monthly_investment:'월 투자',rebalance:'전체 리밸런싱',salary:'월급',saving_transfer:'정기 납입'})[t.type]||t.type}</b><p>투입 ${money(t.contribution)} / 실제 매수 ${money(t.actualInvestment)} / 잔여 현금 ${money(t.cashAfter)}</p><small>총자산 ${money(t.beforeTotal)} → ${money(t.afterTotal)}</small>${(t.trades||[]).map(x=>`<p>${safe(x.name)} ${x.side==='buy'?'+':'−'}${x.quantity} × ${x.price} ${safe(x.currency)} · 수수료 ${money(x.fee)}</p>`).join('')}</div>`).join('')||'<p class="hint">실제 완료한 투자만 기록됩니다.</p>';}

  const EXCEL_HEADERS={
    '투자자산':['ID','종목명','티커','시장','통화','매수평단가','보유수량','현재가','매수환율','리스크','가격기준시각','가격출처','가격유형','해외여부','원화매수평단'],
    '은행자산':['ID','종류','상품명','금액','현재회차','총회차','이율','현재잔액','유동구분','월납입액','납입일','자동반영','출금대상','위험군ID','표시순서'],
    '설정':['항목','값'], '자산기록':['날짜','총자산'], '리스크목표':['리스크','목표비중'], '종목목표':['ID','목표비중']
  };
  function workbookRows(){return {
    '투자자산':state.stocks.map(s=>[s.id,s.name,s.ticker,s.market,s.foreign?'USD':'KRW',s.buy,s.quantity,s.price,s.buyFx,riskLabel(s.risk),s.quoteAsOf||'',s.quoteSource||'',s.quoteKind||'',s.foreign,s.buyKrw]),
    '은행자산':state.savings.map(s=>[s.id,s.type,s.name,s.balance,s.current,s.total,s.rate,s.balance,s.liquidityType,s.monthlyPayment,s.paymentDay,s.autoApply,s.sourceAssetId,s.risk,s.displayOrder]),
    '설정':[['target_asset',state.config.target],['fx',state.config.fx],['risk_levels',state.config.riskGroups.map(g=>g.label).join(',')],['refreshMinutes',state.config.refreshMinutes||0],['fxAsOf',state.config.fxAsOf||''],['fxSource',state.config.fxSource||'수동']],
    '자산기록':state.history.map(h=>[h.date,h.total]),'리스크목표':state.config.risks.map(r=>[riskLabel(r),num(state.riskTargets[r])]),'종목목표':Object.entries(state.allocations)
  }}
  function exportExcel(){if(!globalThis.XLSX){toast('엑셀 모듈을 불러오지 못했습니다. JSON 백업을 사용하세요.');return}
    const wb=XLSX.utils.book_new(),rows=workbookRows();for(const [name,headers]of Object.entries(EXCEL_HEADERS)){const ws=XLSX.utils.aoa_to_sheet([headers,...rows[name]]);ws['!cols']=headers.map(h=>({wch:h==='종목명'||h==='상품명'?28:h==='ID'?38:h.includes('시각')?28:17}));ws['!autofilter']={ref:XLSX.utils.encode_range({s:{r:0,c:0},e:{r:rows[name].length,c:headers.length-1}})};XLSX.utils.book_append_sheet(wb,ws,name)}
    const meta=JSON.stringify(state),chunks=[];for(let i=0;i<meta.length;i+=20000)chunks.push([i/20000,meta.slice(i,i+20000)]);XLSX.utils.book_append_sheet(wb,XLSX.utils.aoa_to_sheet([['순서','백업 JSON (수정 금지)'],...chunks]),'v08백업');XLSX.utils.book_append_sheet(wb,XLSX.utils.aoa_to_sheet([['현금명','금액'],[state.cash.name,state.cash.amount]]),'현금');
    XLSX.writeFile(wb,`MyAssetHub-${today()}.xlsx`);
  }
  function readWorkbook(wb,context=state){
    if(wb.Sheets['v08백업']||wb.Sheets['v07백업']){const backupName=wb.Sheets['v08백업']?'v08백업':'v07백업';const entries=XLSX.utils.sheet_to_json(wb.Sheets[backupName],{header:1}).slice(1);const base=normalize(JSON.parse(entries.map(r=>r[1]).join('')));const without={...wb,Sheets:{...wb.Sheets}};delete without.Sheets[backupName];const core=readWorkbook(without,base);const byLabel=Object.fromEntries(base.config.riskGroups.map(g=>[g.label,g.id]));const coreLabels=Object.fromEntries(core.config.riskGroups.map(g=>[g.id,g.label]));base.stocks=core.stocks.map(x=>({...x,risk:byLabel[coreLabels[x.risk]]}));base.savings=core.savings.map(x=>({...x,risk:base.config.risks.includes(x.risk)?x.risk:base.savings.find(b=>b.id===x.id)?.risk||base.config.cashRiskId}));base.history=core.history;base.allocations=core.allocations;base.riskTargets=Object.fromEntries(Object.entries(core.riskTargets).map(([r,n])=>[byLabel[coreLabels[r]],n]));base.config.target=core.config.target;base.config.fx=core.config.fx;const cash=wb.Sheets['현금']?XLSX.utils.sheet_to_json(wb.Sheets['현금'],{header:1})[1]:null;if(cash)base.cash={...base.cash,name:String(cash[0]),amount:finite(cash[1],'현금')};return normalize(base);}
    if(wb.Sheets.stocks||wb.Sheets.savings){
      const rows=n=>wb.Sheets[n]?XLSX.utils.sheet_to_json(wb.Sheets[n],{defval:''}):[];
      const stocks=rows('stocks').map(s=>{const ticker=String(s['티커']??s.ticker??'').replace(/\.(KS|KQ)$/,'');const existing=context.stocks.find(x=>x.ticker===ticker);return {...s,id:s.id||existing?.id||uid(),price:s['현재가']??s.price,buyFx:s['매수환율']??s.buyFx,market:s['시장']??s.market}});
      const savings=rows('savings').map(s=>({...s,id:s.id||context.savings.find(x=>x.name===s['상품명']&&x.type===s['종류'])?.id||uid(),amount:s['금액']??s['월납입액']??s.amount}));
      const c=rows('config')[0]||{},cfg={...context.config,risks:context.config.riskGroups.map(g=>g.label),...c,target:c['목표금액']??c.target??c.target_asset??context.config.target,fx:c['USD_KRW']??c.fx??context.config.fx,risks:c['리스크분류']?String(c['리스크분류']).split(','):c.risk_levels?String(c.risk_levels).split(','):context.config.riskGroups.map(g=>g.label)};
      return normalize({stocks,savings,config:cfg,history:wb.Sheets.history?rows('history'):context.history,cash:context.cash,transactions:context.transactions,cashflows:context.cashflows,riskTargets:Object.fromEntries(Object.entries(context.riskTargets).map(([r,v])=>[(context.config.riskGroups.find(g=>g.id===r)?.label||r),v])),allocations:context.allocations});
    }
    for(const name of ['투자자산','은행자산','설정'])if(!wb.Sheets[name])throw Error(`${name} 시트가 없습니다. 앱에서 내려받은 엑셀을 사용하세요.`);
    const read=name=>{if(!wb.Sheets[name])return null;const sheet=wb.Sheets[name],range=XLSX.utils.decode_range(sheet['!ref']||'A1');if(range.e.r>20000||range.e.c>50)throw Error('시트 크기가 너무 큽니다.');
      const arr=XLSX.utils.sheet_to_json(sheet,{header:1,defval:'',raw:true});if(EXCEL_HEADERS[name].some((h,i)=>arr[0]?.[i]!==h&&!(name==='은행자산'&&i>=7&&arr[0]?.[i]==null)&&!(name==='투자자산'&&['해외여부','원화매수평단'].includes(h)&&arr[0]?.[i]==null)))throw Error(`${name} 머리글이 변경되었습니다.`);
      for(let r=1;r<=range.e.r;r++)for(let c=0;c<EXCEL_HEADERS[name].length;c++){const cell=sheet[XLSX.utils.encode_cell({r,c})];if(cell?.f)throw Error(`${name} ${r+1}행: 가져오기 영역의 수식은 값으로 붙여넣어 주세요.`)}
      return arr.slice(1).filter(row=>row.some(v=>v!==''&&v!=null));
    };
    const cfg=Object.fromEntries(read('설정'));
    const stocks=read('투자자산').map(r=>{if(!['KRW','USD'].includes(String(r[4]).toUpperCase()))throw Error('투자자산 통화는 KRW 또는 USD입니다.');if(r[13]!==undefined&&r[13]!==''&&bool(r[13])!==(String(r[4]).toUpperCase()==='USD'))throw Error('통화와 해외여부가 일치하지 않습니다.');return {displayOrder:context.stocks.find(x=>x.id===r[0])?.displayOrder,id:r[0],name:r[1],ticker:String(r[2]),market:r[3],foreign:String(r[4]).toUpperCase()==='USD',buy:r[5],quantity:r[6],price:r[7],buyFx:r[8],risk:context.config.riskGroups.find(g=>g.label===r[9])?.id||r[9],quoteAsOf:r[10],quoteSource:r[11],quoteKind:r[12],buyKrw:r[14]===''?undefined:r[14]}});
    const savings=read('은행자산').map(r=>({id:r[0],type:r[1],name:r[2],amount:r[3],current:r[4],total:r[5],rate:r[6],balance:r[7]==null||r[7]===''?Number(r[3])*(['적금','주택청약'].includes(r[1])?Number(r[4]):1):r[7],liquidityType:r[8]||undefined,monthlyPayment:r[9]==null||r[9]===''?(['적금','주택청약'].includes(r[1])?Number(r[3]):0):r[9],paymentDay:r[10]===''?undefined:r[10],autoApply:r[11]===true||String(r[11]).toUpperCase()==='TRUE',sourceAssetId:r[12]||'',risk:r[13]||undefined,displayOrder:r[14]===''?undefined:r[14]}));
    const historyRows=read('자산기록');const history=historyRows===null?context.history:historyRows.map(r=>{let date=r[0];if(typeof date==='number'){const d=XLSX.SSF.parse_date_code(date);date=`${d.y}-${String(d.m).padStart(2,'0')}-${String(d.d).padStart(2,'0')}`}return {date,total:r[1]}});
    return normalize({version:4,stocks,savings,config:{...context.config,...cfg,target:cfg.target_asset??context.config.target},history,cash:context.cash,transactions:context.transactions,cashflows:context.cashflows,riskTargets:Object.fromEntries((read('리스크목표')||Object.entries(context.riskTargets)).map(([r,v])=>[context.config.riskGroups.find(g=>g.label===r)?.id||r,v])),allocations:Object.fromEntries(read('종목목표')||Object.entries(context.allocations))});
  }
  function previewImport(incoming,label){pendingImport=incoming;const incomingIDs=new Set([...incoming.stocks,...incoming.savings].map(s=>s.id)),oldIDs=new Set([...state.stocks,...state.savings].map(s=>s.id));
    $('#import-summary').textContent=`${label}: 투자 ${incoming.stocks.length}개 · 은행 ${incoming.savings.length}개 · 기록 ${incoming.history.length}개. 새 ID ${[...incomingIDs].filter(x=>!oldIDs.has(x)).length}개 / 기존 ID ${[...incomingIDs].filter(x=>oldIDs.has(x)).length}개 / 빠지는 ID ${[...oldIDs].filter(x=>!incomingIDs.has(x)).length}개.`;
    for(const dlg of document.querySelectorAll('dialog[open]'))dlg.close();$('#import-preview').showModal();
  }
  $('#restore-previous').onclick=()=>{try{const raw=localStorage.getItem(KEY+'-recovery');if(!raw)throw Error('아직 복구 사본이 없습니다.');previewImport(normalize(JSON.parse(raw)),'직전 데이터')}catch(e){toast(e.message)}};
  $('#excel-export-btn').onclick=exportExcel;
  $('#excel-import-file').onchange=async e=>{try{const file=e.target.files[0];if(!file)return;if(file.size>10_000_000)throw Error('10MB 이하의 엑셀을 사용하세요.');const wb=XLSX.read(await file.arrayBuffer(),{type:'array'});previewImport(readWorkbook(wb),'엑셀')}catch(err){alert('가져오기 실패: '+err.message)}finally{e.target.value=''}};
  $('#import-file').onchange=async e=>{try{const file=e.target.files[0];if(!file)return;if(file.size>5_000_000)throw Error('5MB 이하의 JSON을 사용하세요.');const raw=JSON.parse(await file.text());if(!Object.hasOwn(raw,'stocks')||!Object.hasOwn(raw,'savings'))throw Error('자산 백업 파일이 아닙니다.');previewImport(normalize({...raw,history:raw.history??state.history,cash:raw.cash??state.cash,transactions:raw.transactions??state.transactions,cashflows:raw.cashflows??state.cashflows}),'JSON')}catch(err){alert('복원 실패: '+err.message)}finally{e.target.value=''}};
  $('#apply-import').onclick=()=>{if(!pendingImport)return;const previous=state,wasBlocked=storageBlocked;try{const raw=localStorage.getItem(KEY);if(raw)localStorage.setItem(KEY+'-recovery',raw);state=pendingImport;storageBlocked=false;if(!persist({record:false,cloud:false}))throw Error('저장 공간이 부족합니다.');pendingImport=null;$('#import-preview').close();startRefreshTimer();toast('백업 데이터를 적용했습니다.')}catch(e){state=previous;storageBlocked=wasBlocked;render();alert('적용 실패: '+e.message)}};
  $('#raw-backup').onclick=()=>{const raw=localStorage.getItem(KEY)||localStorage.getItem(LEGACY_KEY);if(!raw){toast('저장 원본이 없습니다.');return}const url=URL.createObjectURL(new Blob([raw],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='my-asset-hub-recovery-raw.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
  let installPrompt=null;
  window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();installPrompt=e;$('#install-app').hidden=false});
  $('#install-app').onclick=async()=>{if(!installPrompt)return;await installPrompt.prompt();await installPrompt.userChoice;installPrompt=null;$('#install-app').hidden=true};
  $('#install-guide').onclick=()=>alert('Android: Chrome의 메뉴 → 앱 설치 또는 홈 화면에 추가.\niPhone: Safari의 공유 → 홈 화면에 추가 → 웹 앱으로 열기.\nHTTPS로 배포된 주소에서 설치하세요. 설치 전·후 저장소가 다를 수 있으므로 JSON 백업 후 필요하면 복원하세요.');
  $('#update-app').hidden=true;

  if('serviceWorker' in navigator)window.addEventListener('load',()=>navigator.serviceWorker.register('./service-worker.js').catch(()=>{}));
  window.addEventListener('resize',()=>{if(tab==='dashboard')renderHistory()});window.addEventListener('online',()=>{renderMarketStatus();refreshMarket(false)});window.addEventListener('offline',renderMarketStatus);
  window.addEventListener('storage',e=>{if(e.key===KEY&&e.newValue){try{state=normalize(JSON.parse(e.newValue));render()}catch{toast('다른 탭의 데이터를 확인하세요.')}}});
  // Comma formatting preserves the caret by restoring its digit index.
  document.addEventListener('input',e=>{const el=e.target;if(!el.matches('[data-money]'))return;const left=el.value.slice(0,el.selectionStart).replace(/\D/g,'').length;el.value=formatMoney(el.value);let pos=0,digits=0;while(pos<el.value.length&&digits<left){if(/\d/.test(el.value[pos]))digits++;pos++}el.setSelectionRange(pos,pos)});
  $('#monthly-tab').onclick=()=>{ $('#monthly-view').hidden=false;$('#full-view').hidden=true;$('#monthly-tab').classList.add('active');$('#full-tab').classList.remove('active')};
  $('#full-tab').onclick=()=>{ $('#monthly-view').hidden=true;$('#full-view').hidden=false;$('#full-tab').classList.add('active');$('#monthly-tab').classList.remove('active');if(Portfolio.validateTargets(state).step1){state=Portfolio.distribute(state,'value',true);renderRebalance(calc())}};
  $('#monthly-amount').oninput=()=>{activePlan=null;$('#monthly-plan').textContent='금액이 변경되었습니다. 계획을 다시 계산하세요.'};
  $('#monthly-calculate').onclick=()=>{try{activePlan=Portfolio.plan(state,{mode:'investment',contribution:num($('#monthly-amount').value),fromCash:true,method:'deficit',excluded:[...investmentExcluded]});renderPlan(activePlan,'#monthly-plan')}catch(e){activePlan=null;$('#monthly-plan').textContent=e.message}};
  $('#setup-now').onclick=()=>openSettings();$('#setup-later').onclick=()=>{sessionStorage.setItem('asset-hub-setup-later','yes');$('#setup-card').classList.add('hidden')};
  if(!state.stocks.length&&!state.savings.length&&!state.config.salary.autoApply&&!sessionStorage.getItem('asset-hub-setup-later'))$('#setup-card').classList.remove('hidden');
  let pendingDrag=null;
  function moveAsset(id,group,beforeId){
    const all=[...state.stocks,...state.savings,state.cash],asset=all.find(x=>x.id===id);
    if(!asset||!state.config.risks.includes(group)||beforeId===id)return;
    const source=id==='cash'?state.config.cashRiskId:asset.risk,revision=state.revision;
    const commit=()=>{
      if(state.revision!==revision){toast('확인 중 자산이 변경되었습니다. 다시 이동하세요.');return}
      const n=structuredClone(state),assets=[...n.stocks,...n.savings,n.cash],moved=assets.find(x=>x.id===id);
      if(id==='cash')n.config.cashRiskId=group;else moved.risk=group;
      const risk=x=>x.id==='cash'?n.config.cashRiskId:x.risk;
      const ordered=assets.filter(x=>risk(x)===group&&x.id!==id).sort((a,b)=>(a.displayOrder??0)-(b.displayOrder??0));
      const at=ordered.findIndex(x=>x.id===beforeId);ordered.splice(at<0?ordered.length:at,0,moved);ordered.forEach((x,i)=>x.displayOrder=i);
      if(source!==group){
        assets.filter(x=>risk(x)===source).sort((a,b)=>(a.displayOrder??0)-(b.displayOrder??0)).forEach((x,i)=>x.displayOrder=i);
        for(const x of assets)if([source,group].includes(risk(x)))delete n.allocations[x.id];
        commitState(Portfolio.distribute(n,'value',true),{record:false});
      }else commitState(n,{record:false});
    };
    if(source!==group){pendingDrag=commit;$('#risk-drag-message').textContent=`${asset.name}을(를) ‘${riskLabel(source)}’ → ‘${riskLabel(group)}’으로 이동하시겠습니까?`;$('#risk-drag-confirm').showModal()}else commit();
  }
  $('#risk-drag-cancel').onclick=()=>{pendingDrag=null;$('#risk-drag-confirm').close()};$('#risk-drag-apply').onclick=()=>{const action=pendingDrag;pendingDrag=null;$('#risk-drag-confirm').close();action?.()};
  let dragging=null;
  $('#assets').addEventListener('pointerdown',e=>{const h=e.target.closest('[data-drag-id]');if(!h)return;dragging={id:h.dataset.dragId,pointer:e.pointerId,handle:h,x:e.clientX,y:e.clientY};try{h.setPointerCapture?.(e.pointerId)}catch{}});
  $('#assets').addEventListener('pointermove',e=>{if(!dragging||dragging.pointer!==e.pointerId)return;const target=document.elementFromPoint(e.clientX,e.clientY)?.closest('.asset-group');document.querySelectorAll('.asset-group').forEach(g=>g.classList.toggle('drag-over',g===target))});
  $('#assets').addEventListener('pointerup',e=>{if(!dragging||dragging.pointer!==e.pointerId)return;const id=dragging.id;dragging=null;const target=document.elementFromPoint(e.clientX,e.clientY)?.closest('.asset-group');document.querySelectorAll('.asset-group').forEach(g=>g.classList.remove('drag-over'));if(target){const row=document.elementFromPoint(e.clientX,e.clientY)?.closest('.sortable-asset');moveAsset(id,target.dataset.group,row?.dataset.assetId)}});
  $('#assets').addEventListener('pointercancel',()=>{dragging=null;document.querySelectorAll('.asset-group').forEach(g=>g.classList.remove('drag-over'))});
  $('#recurring-close').onclick=()=>$('#recurring-summary').close();
  $('#recurring-undo').onclick=()=>{undo('auto');$('#recurring-summary').close()};
  if(!storageBlocked){const applied=Cashflow.apply(state);if(applied.pending.length)toast('정기 자금 반영 확인 필요: '+applied.pending.join(' / '));if(applied.changes.length){const prior=structuredClone(state);if(commitState(applied.state,{backupKey:KEY+'-before-auto'})){ $('#recurring-details').innerHTML=applied.changes.map(x=>`<p>${x.type==='salary'?'월급':'정기 납입'} +${money(x.amount)}</p>`).join('');$('#recurring-net').textContent='총자산 순증가 '+money(applied.net);$('#recurring-summary').showModal()}else state=prior}}
  // Testable existing calculations. No personal data leaves the device through this interface.
  window.AssetHub={version:APP_VERSION,storageKey:KEY,normalize,calc,workbookRows,readWorkbook,applyEditorMarketSelection,getState:()=>structuredClone(state)};
  $('#monthly-amount').value=formatMoney(state.config.monthlyInvestment);if(storageBlocked)render();else persist();startRefreshTimer();checkBuildStatus();if(navigator.onLine)setTimeout(()=>refreshMarket(false),800);
})();

