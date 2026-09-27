/* Pure portfolio, migration and execution logic. No network or storage side effects. */
(function(root){
'use strict';
const copy=x=>structuredClone(x),EPS=.010000001,labels=['초고위험 (코인&텐베거)','위험 (ETF&빅테크)','중립 (금&채권)','안전 (현금)'];
function number(x,label,min=0){const n=Number(x);if(x==null||x===''||!Number.isFinite(n)||n<min)throw Error(label+' 값을 확인하세요.');return n}
const cryptoAsset=s=>s.ticker.startsWith('KRW-');
const id=()=>globalThis.crypto?.randomUUID?.()||'id-'+Date.now()+'-'+Math.random().toString(36).slice(2);
function migrate(raw,legacy){
 if(Number(raw?.version)>3)throw Error('더 새로운 데이터 버전입니다. 앱 업데이트 후 가져오세요.');
 const s=legacy(raw),old=Number(raw.version||0)<3,cfg=Array.isArray(raw.config)?raw.config[0]||{}:raw.config||{};
 let groups=old?s.config.risks.map((label,i)=>({id:'risk_'+(i+1),label,description:''})):copy(cfg.riskGroups);
 if(!Array.isArray(groups)||!groups.length)throw Error('리스크 분류가 비어 있습니다.');
 groups=groups.map(g=>({id:String(g.id),label:String(g.label).trim(),description:String(g.description||'')}));
 if(groups.some(g=>!/^risk_[\w-]+$/.test(g.id)||!g.label)||new Set(groups.map(g=>g.id)).size!==groups.length||new Set(groups.map(g=>g.label)).size!==groups.length)throw Error('리스크 ID/이름을 확인하세요.');
 const ids=groups.map(g=>g.id),lookup=r=>old?(groups.find(g=>g.label===r)?.id||ids[0]):r;
 const cashRiskId=old?(groups.find(g=>g.label==='안전')?.id||ids.at(-1)):cfg.cashRiskId;
 if(!ids.includes(cashRiskId))throw Error('현금 리스크 분류를 확인하세요.');
 s.stocks=s.stocks.map((x,i)=>{const original=raw.stocks[i];const risk=lookup(original.risk??original['리스크']??(old?groups[0].label:ids[0]));if(!ids.includes(risk))throw Error('자산 리스크 연결이 없습니다.');const buyKrw=number(original.buyKrw??(x.buy*(x.foreign?(x.buyFx||s.config.fx):1)),'원화 매수평단');return {...x,risk,buyKrw,costMigration:original.costMigration||(old&&x.foreign&&!x.buyFx?'이전 환율 없음: 이전 저장 환율로 환산':'')};});
 s.savings=s.savings.map((x,i)=>{const risk=old?cashRiskId:(raw.savings[i].risk||cashRiskId);if(!ids.includes(risk))throw Error('은행 리스크 연결이 없습니다.');return {...x,risk}});
 s.config={...s.config,riskGroups:groups,risks:ids,cashRiskId,monthlyInvestment:number(cfg.monthlyInvestment??2000000,'월 투자금'),minCashMode:cfg.minCashMode==='percent'?'percent':'amount',minCash:number(cfg.minCash??0,'최소 현금')};
 if(s.config.minCashMode==='percent'&&s.config.minCash>100)throw Error('최소 현금 비율은 100 이하입니다.');
 s.cash={id:'cash',name:String(raw.cash?.name||'현금/예수금'),amount:number(raw.cash?.amount??0,'현금')};
 s.riskTargets=Object.fromEntries(Object.entries(s.riskTargets).map(([k,v])=>[lookup(k),v]));
 if(Object.keys(s.riskTargets).some(k=>!ids.includes(k)))throw Error('목표 리스크 연결을 확인하세요.');
 for(const k of ['transactions','cashflows']){if(raw[k]!=null&&!Array.isArray(raw[k]))throw Error(k+' 목록 오류');s[k]=copy(raw[k]||[])}
 s.version=3;s.revision=number(raw.revision??0,'저장 버전');s.migration={...(raw.migration||{}),...(old?{from:Number(raw.version||0),at:new Date().toISOString()}:{} )};
 return s;
}
function calc(s){const stocks=s.stocks.map(x=>{const price=x.price==null?(x.foreign?x.buyKrw/s.config.fx:x.buyKrw):x.price;return {...x,value:price*x.quantity*(x.foreign?s.config.fx:1),cost:x.buyKrw*x.quantity,quote:price,estimated:x.price==null}}),banks=s.savings.map(x=>({...x,value:x.amount*(['適金','적금','주택청약'].includes(x.type)?x.current:1),fixed:['적금','주택청약'].includes(x.type)}));const stockTotal=stocks.reduce((a,x)=>a+x.value,0),bankTotal=banks.reduce((a,x)=>a+x.value,0),cashTotal=s.cash.amount,cost=stocks.reduce((a,x)=>a+x.cost,0)+bankTotal+cashTotal;return {stocks,banks,stockTotal,bankTotal,cashTotal,cost,total:stockTotal+bankTotal+cashTotal};}
function items(s){const c=calc(s);return [...c.stocks.map(x=>({...x,kind:'stock'})),...c.banks.map(x=>({...x,kind:'bank'})),{id:'cash',name:s.cash.name,risk:s.config.cashRiskId,value:s.cash.amount,kind:'cash'}]}
function validateTargets(s){const all=items(s),sum=s.config.risks.reduce((a,r)=>a+(Number(s.riskTargets[r])||0),0);const step1=Math.abs(sum-100)<=EPS,groups=s.config.risks.map(r=>{const target=Number(s.riskTargets[r])||0,part=all.filter(x=>x.risk===r),sum=part.reduce((a,x)=>a+(Number(s.allocations[x.id])||0),0);return {id:r,target,sum,valid:Math.abs(target-sum)<=EPS}});return {sum,step1,step2:step1&&groups.every(g=>g.valid),groups};}
function distribute(s,method='equal',onlyMissing=false){const n=copy(s),all=items(n);for(const r of n.config.risks){const part=all.filter(x=>x.risk===r),target=Number(n.riskTargets[r])||0;if(onlyMissing&&part.every(x=>Object.hasOwn(n.allocations,x.id)))continue;const total=part.reduce((a,x)=>a+x.value,0);part.forEach(x=>n.allocations[x.id]=target*(method==='value'&&total?x.value/total:1/part.length));}return n;}
function renameRisks(s,groups,cashRiskId,moves={}){const n=copy(s),ids=new Set(groups.map(g=>g.id));if(!ids.has(cashRiskId))throw Error('현금 리스크를 선택하세요.');for(const old of n.config.risks){if(ids.has(old))continue;const dest=moves[old];if(!ids.has(dest))throw Error('삭제할 리스크의 이동 대상을 선택하세요.');for(const x of [...n.stocks,...n.savings])if(x.risk===old)x.risk=dest;n.riskTargets[dest]=(n.riskTargets[dest]||0)+(n.riskTargets[old]||0);delete n.riskTargets[old];}n.config.riskGroups=copy(groups);n.config.risks=[...ids];n.config.cashRiskId=cashRiskId;return n;}
function fingerprint(s){return JSON.stringify(s)}
function plan(s,opt={}){
 const valid=validateTargets(s);if(!valid.step2)throw Error('STEP 1·2 목표 합계를 먼저 맞추세요.');
 const mode=opt.mode==='investment'?'investment':'rebalance',contribution=mode==='investment'?number(opt.contribution,'투자가능금액'):0,method=opt.method==='regular'?'regular':'deficit';
 const c=calc(s),total=c.total+contribution,excluded=new Set(opt.excluded||[]);if(total<=0)throw Error('자산 또는 투자금을 입력하세요.');
 const minCash=s.config.minCashMode==='percent'?total*s.config.minCash/100:s.config.minCash;
 const spendable=mode==='investment'?Math.max(0,contribution-Math.max(0,minCash-c.cashTotal)):Math.max(0,c.stockTotal+c.cashTotal-minCash);
 const rows=c.stocks.map(x=>{if(!(x.price>0)||x.quoteError)throw Error(x.name+': 정상 시세를 갱신하세요.');if(!cryptoAsset(x)&&!Number.isInteger(x.quantity))throw Error(x.name+': 기존 소수점 주식은 정수 거래 계획에서 제외할 수 없습니다. 수량 확인 후 진행하세요.');const unit=x.price*(x.foreign?s.config.fx:1);return {...x,unit,targetPct:Number(s.allocations[x.id])||0,wanted:total*(Number(s.allocations[x.id])||0)/100,crypto:cryptoAsset(x),excluded:excluded.has(x.id),qty:x.quantity}});
 // Existing bank balances are never assumed to be instantly available brokerage cash.
 const warnings=[];if(c.banks.length)warnings.push('은행자산은 그대로 유지하며 현금/예수금만 매수 재원으로 사용합니다.');
 const lockedGroups=s.config.risks.filter(r=>c.banks.filter(x=>x.risk===r).reduce((a,x)=>a+x.value,0)>total*(s.riskTargets[r]||0)/100+.01);
 if(lockedGroups.length)warnings.push('현재 고정자산 때문에 이 목표비중은 완전히 달성할 수 없습니다.');
 if(minCash>c.cashTotal+contribution+(mode==='rebalance'?c.stockTotal:0))warnings.push('가용자산이 최소 현금보다 적어 완전 달성이 불가능합니다.');
 if(mode==='investment'){
  const weights=rows.map(x=>x.excluded?0:method==='regular'?x.targetPct:Math.max(0,x.wanted-x.value)),sum=weights.reduce((a,x)=>a+x,0);
  const desiredCash=method==='regular'?contribution*(s.allocations.cash||0)/100:Math.max(0,total*(s.allocations.cash||0)/100-c.cashTotal);
  const budget=Math.min(spendable,Math.max(0,contribution-desiredCash),method==='regular'?contribution*sum/100:Infinity);
  rows.forEach((x,i)=>{x.desiredBuy=sum?budget*weights[i]/sum:0;if(method==='deficit')x.desiredBuy=Math.min(x.desiredBuy,Math.max(0,x.wanted-x.value));x.desired=x.quantity+x.desiredBuy/x.unit;x.qty=x.excluded?x.quantity:x.crypto?Math.floor(x.desired*1e8)/1e8:Math.round(x.desired)});
 }else rows.forEach(x=>{x.desired=x.wanted/x.unit;x.qty=x.crypto?Math.floor(x.desired*1e8)/1e8:Math.round(x.desired)});
 const available=mode==='investment'?spendable:c.stockTotal+c.cashTotal-minCash;
 const spend=()=>rows.reduce((a,x)=>a+(mode==='investment'?x.qty-x.quantity:x.qty)*x.unit,0);
 // Proportional contraction first bounds work even with very large portfolios; integer corrections follow.
 let used=spend(),cap=Math.max(0,available);if(used>cap+.001&&used>0){const factor=cap/used;for(const x of rows){const base=mode==='investment'?x.quantity:0,add=Math.max(0,x.qty-base)*factor;x.qty=base+(x.crypto?Math.floor(add*1e8)/1e8:Math.floor(add));}}
 // Greedy one-lot improvement minimizes squared per-asset KRW target error locally, not a global integer optimum.
 for(let k=0;k<10000;k++){const remaining=cap-spend();let best=null,gain=-1;for(const x of rows){if(x.excluded&&mode==='investment')continue;const target=mode==='investment'?x.desired:x.wanted/x.unit;const step=x.crypto?Math.min(Math.max(0,target-x.qty),Math.max(0,remaining/x.unit)):1;if(step<=0||step*x.unit>remaining+.000001)continue;const improvement=(target-x.qty)**2-(target-x.qty-step)**2;if(improvement>=-1e-9&&target>x.qty&&improvement*x.unit*x.unit>gain+.000001){gain=improvement*x.unit*x.unit;best={x,step}}}if(!best)break;best.x.qty+=best.step;if(best.x.crypto)best.x.qty=Math.floor(best.x.qty*1e8+1e-5)/1e8;}
 const trades=rows.map(x=>{const delta=Number((x.qty-x.quantity).toFixed(8));return {id:x.id,name:x.name,ticker:x.ticker,foreign:x.foreign,crypto:x.crypto,risk:x.risk,current:x.quantity,target:x.qty,delta,price:x.price,unit:x.unit,amount:Math.abs(delta)*x.unit,currentPct:x.value/total*100,targetPct:x.targetPct,afterPct:x.qty*x.unit/total*100}});
 const net=trades.reduce((a,x)=>a+x.delta*x.unit,0),cashAfter=c.cashTotal+contribution-net;if(cashAfter<-.01)throw Error('예산을 초과한 계획입니다.');
 const afterGroups=s.config.risks.map(r=>({id:r,before:items(s).filter(x=>x.risk===r).reduce((a,x)=>a+x.value,0)/Math.max(c.total,1)*100,after:(trades.filter(x=>x.risk===r).reduce((a,x)=>a+x.target*x.unit,0)+c.banks.filter(x=>x.risk===r).reduce((a,x)=>a+x.value,0)+(r===s.config.cashRiskId?cashAfter:0))/total*100,target:Number(s.riskTargets[r])||0}));
 return {id:id(),mode,method,contribution,minCash,fx:s.config.fx,at:new Date().toISOString(),fingerprint:fingerprint(s),beforeTotal:c.total,total,cashBefore:c.cashTotal,cashAfter:Math.max(0,cashAfter),trades,afterGroups,warnings,excluded:[...excluded]};
}
function execute(s,p,fills){
 if(p.fingerprint!==fingerprint(s))throw Error('계획 이후 자산/시세가 변경되었습니다. 다시 계산하세요.');
 if(s.transactions.some(t=>t.id===p.id))throw Error('이미 반영된 계획입니다.');
 const n=copy(s),seen=new Set(),actual=[];let cash=s.cash.amount+p.contribution;
 for(const f of fills){if(seen.has(f.id))throw Error('중복 체결 항목');seen.add(f.id);const t=p.trades.find(x=>x.id===f.id);if(!t||!t.delta)throw Error('계획에 없는 거래');const quantity=number(f.quantity,'실제 수량'),price=number(f.price,'실제 가격',.00000001),fee=number(f.fee??0,'수수료');if(quantity>Math.abs(t.delta)+1e-8)throw Error('실제 수량은 추천수량 이하여야 합니다.');if(!t.crypto&&!Number.isInteger(quantity))throw Error('주식/ETF는 정수 수량입니다.');if(t.crypto&&Math.abs(quantity*1e8-Math.round(quantity*1e8))>.0001)throw Error('코인은 소수점 8자리까지 입력하세요.');if(quantity===0){if(fee)throw Error('미체결 거래의 수수료를 확인하세요.');continue}const side=t.delta<0?'sell':'buy',amount=quantity*price*(t.foreign?p.fx:1);actual.push({...t,quantity,price,fee,amount,side});}
 for(const t of actual.filter(x=>x.side==='sell')){const x=n.stocks.find(x=>x.id===t.id);if(t.quantity>x.quantity+1e-8)throw Error('보유 수량을 초과한 매도');x.quantity=Number((x.quantity-t.quantity).toFixed(8));cash+=t.amount-t.fee;}
 let bought=0;for(const t of actual.filter(x=>x.side==='buy')){const x=n.stocks.find(x=>x.id===t.id),cost=t.amount+t.fee;if(p.mode==='investment'&&bought+cost>p.contribution+1e-6)throw Error('신규 투자금 범위를 초과했습니다.');if(cost>cash+1e-6)throw Error('실제 체결 금액이 가용 현금을 초과합니다.');x.buyKrw=(x.buyKrw*x.quantity+cost)/(x.quantity+t.quantity);x.quantity=Number((x.quantity+t.quantity).toFixed(8));cash-=cost;bought+=cost;}
 if(cash<-.000001)throw Error('수수료를 포함한 현금이 부족합니다.');
 if(actual.some(x=>x.side==='buy')&&cash<p.minCash-.01)throw Error('최소 현금 유지 조건을 충족하지 못합니다.');
 n.cash.amount=Math.max(0,cash);const after=calc(n).total;const event={id:p.id,type:p.mode,method:p.method,at:new Date().toISOString(),contribution:p.contribution,actualInvestment:bought,beforeTotal:p.beforeTotal,afterTotal:after,cashAfter:n.cash.amount,trades:actual.map(x=>({id:x.id,name:x.name,ticker:x.ticker,side:x.side,quantity:x.quantity,price:x.price,currency:x.foreign?'USD':'KRW',fx:x.foreign?p.fx:1,fee:x.fee,amount:x.amount}))};n.transactions.push(event);if(p.contribution)n.cashflows.push({id:p.id,at:event.at,amount:p.contribution,type:'contribution'});return n;
}
root.Portfolio={labels,migrate,calc,items,validateTargets,distribute,renameRisks,plan,execute,fingerprint};
})(globalThis);
