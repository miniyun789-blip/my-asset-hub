/* Local only: deterministic recurring cash flow, with monthly transaction IDs. */
(function(root){
'use strict';
const kstDate=at=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(at));
function apply(state,at=Date.now()){
 const n=structuredClone(state),date=kstDate(at),month=date.slice(0,7),day=Number(date.slice(8));
 const changes=[],pending=[];let net=0;
 const amount=x=>Number(x)||0;
 const find=id=>id==='cash'?n.cash:n.savings.find(x=>x.id===id);
 const balance=x=>x?.id==='cash'?x.amount:x?.balance;
 const set=(x,value)=>{if(x.id==='cash')x.amount=value;else x.balance=value};
 const salary=n.config.salary||{};
 if(salary.autoApply&&amount(salary.amount)>0&&day>=Number(salary.day||1)){
  const id=`salary:${month}`;
  if(!n.recurringApplied[id]){
   const target=find(salary.targetId);
   if(!target||target.liquidityType==='fixed')pending.push('월급: 반영할 유동 자산을 지정하세요.');
   else{set(target,balance(target)+amount(salary.amount));n.recurringApplied[id]=date;const tx={id,type:'salary',at:new Date(at).toISOString(),amount:amount(salary.amount),targetId:target.id};n.transactions.push(tx);n.cashflows.push(tx);changes.push(tx);net+=tx.amount}
  }
 }
 for(const asset of n.savings){if(!asset.autoApply||!(amount(asset.monthlyPayment)>0)||day<Number(asset.paymentDay||1))continue;
  const id=`saving:${asset.id}:${month}`;if(n.recurringApplied[id])continue;
  const source=find(asset.sourceAssetId),payment=amount(asset.monthlyPayment);
  if(!source||source.id===asset.id||source.liquidityType==='fixed'){pending.push(asset.name+': 유효한 출금 대상을 지정하세요.');continue}
  if(balance(source)<payment){pending.push(asset.name+': 출금 대상의 잔액이 부족합니다.');continue}
  set(source,balance(source)-payment);asset.balance+=payment;n.recurringApplied[id]=date;
  const tx={id,type:'saving_transfer',at:new Date(at).toISOString(),amount:payment,sourceId:source.id,targetId:asset.id};n.transactions.push(tx);n.cashflows.push(tx);changes.push(tx);
 }
 return {state:n,changes,pending,net,month};
}
root.Cashflow={kstDate,apply};
})(globalThis);
