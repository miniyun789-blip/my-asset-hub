(async()=>{
const {JSDOM}=require(process.env.JSDOM_PATH||'jsdom'),fs=require('fs'),path=require('path'),assert=require('assert');
const root=path.resolve(__dirname,'../public'),KEY='my-asset-hub-html-v1';
const dom=new JSDOM(fs.readFileSync(root+'/index.html','utf8'),{url:'https://hub.test',runScripts:'outside-only'}),w=dom.window;let messages=[];
w.structuredClone=structuredClone;w.alert=x=>messages.push(x);w.confirm=()=>true;w.setInterval=()=>0;w.setTimeout=()=>0;w.HTMLDialogElement.prototype.showModal=function(){this.open=true};w.HTMLDialogElement.prototype.close=function(){this.open=false};w.fetch=async()=>({ok:true,json:async()=>({rate:1400,price:150,currency:'USD',source:'fixture',asOf:'2026-09-25T00:00:00Z'})});
w.eval(fs.readFileSync(root+'/vendor/xlsx.full.min.js','utf8'));w.eval(fs.readFileSync(root+'/js/app.js','utf8'));
const $=s=>w.document.querySelector(s),click=s=>$(s).click(),set=(s,v)=>$(s).value=String(v),submit=s=>$(s).dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));
const json=v=>JSON.parse(JSON.stringify(v));let count=0;function check(name,fn){fn();count++;console.log('PASS',name)}
function stock(values){click('#add-stock');for(const [k,v]of Object.entries(values))set(`#editor [name=${k}]`,v);submit('#editor-form')}
function bank(type,amount,current,total=12){click('#add-bank');for(const[k,v]of Object.entries({type,name:type,amount,current,total,rate:3}))set(`#editor [name=${k}]`,v);submit('#editor-form')}
stock({name:'Apple',ticker:'AAPL',buy:100,quantity:10,price:120,buyFx:1300,foreign:'true'});
check('USD evaluation, buy FX, total, profit',()=>{const c=w.AssetHub.calc();assert.equal(c.total,1620000);assert.equal(c.cost,1300000);assert.equal($('#profit-total').textContent,'+320,000원')});
stock({name:'Apple again',ticker:'AAPL',buy:200,quantity:5,buyFx:1500,foreign:'true'});
check('additional buy weighted average and FX',()=>{const s=w.AssetHub.getState().stocks;assert.equal(s.length,1);assert.equal(s[0].quantity,15);assert.equal(s[0].buy,2000/15);assert.equal(s[0].buyFx,1400);assert.equal(s[0].price,120)});
click('[data-edit=stock]');set('#editor [name=quantity]',10);set('#editor [name=buy]',100);set('#editor [name=buyFx]',1300);submit('#editor-form');
check('stock edit',()=>assert.equal(w.AssetHub.calc().stocks[0].cost,1300000));
for(const [type,a,c]of [['예금',1000000,5],['파킹통장',200000,3],['적금',100000,3],['주택청약',50000,4]])bank(type,a,c);
check('all four bank types: deposits not multiplied',()=>assert.equal(w.AssetHub.calc().bankTotal,1700000));
check('invalid installment count rejected',()=>{const s=w.AssetHub.getState();assert.throws(()=>w.AssetHub.normalize({...s,savings:[{...s.savings[2],current:13}]}))});
check('legacy missing history, numeric ticker, FALSE, amount aliases',()=>{const s=w.AssetHub.normalize({stocks:[{'종목명':'삼성전자','티커':5930,'매수평단가':100,'보유수량':1,'해외여부':'false'}],savings:[{'상품명':'예금','종류':'예금','금액':100,'현재회차':5,'총회차':1}]});assert.equal(s.stocks[0].ticker,'005930');assert.equal(s.stocks[0].foreign,false);assert.equal(s.savings[0].amount,100);assert.equal(s.history.length,0)});
check('invalid and duplicate data rejected',()=>{const s=w.AssetHub.getState();assert.throws(()=>w.AssetHub.normalize({...s,stocks:[{...s.stocks[0],buy:'bad'}]}));assert.throws(()=>w.AssetHub.normalize({...s,stocks:[s.stocks[0],s.stocks[0]]}));assert.throws(()=>w.AssetHub.normalize({...s,history:[{date:'2026-02-30',total:1}]}))});
check('rebalance invalid targets blocked and fixed amounts',()=>{assert($('#allocation-list').textContent.includes('목표 비중 확인 필요'));assert($('#rebalance-basis').textContent.includes('500,000원'))});
// Remove all but deposit so group targets have exact, independently known result.
for(const s of w.AssetHub.getState().savings.slice(1))click(`[data-delete=bank][data-id="${s.id}"]`);
for(const [risk,v]of [['초고위험',50],['안전',50]]){set(`[data-risk="${risk}"]`,v);$(`[data-risk="${risk}"]`).dispatchEvent(new w.Event('change',{bubbles:true}))}click('#distribute');
check('rebalance USD unit conversion',()=>{assert($('#allocation-list').textContent.includes('약 1.914주/개'));assert(!$('#allocation-list').textContent.includes('목표 비중 확인 필요'))});
let exported;w.XLSX.writeFile=wb=>{exported=wb};click('#excel-export-btn');
check('Excel six sheets, requested schema and actual binary roundtrip',()=>{assert.equal(exported.SheetNames.length,6);assert(w.XLSX.utils.sheet_to_json(exported.Sheets['투자자산'],{header:1})[0].includes('해외여부'));const bytes=w.XLSX.write(exported,{type:'array',bookType:'xlsx'});const result=w.AssetHub.readWorkbook(w.XLSX.read(bytes,{type:'array'}));const old=w.AssetHub.getState();for(const key of ['stocks','savings','history','allocations'])assert.deepEqual(json(result[key]),json(old[key]));for(const r of old.config.risks)assert.equal(result.riskTargets[r]||0,old.riskTargets[r]||0);assert.equal(result.config.fx,old.config.fx)});
check('legacy v0.5 Excel without history preserves history',()=>{const wb=w.XLSX.utils.book_new();for(const[name,rows]of Object.entries({stocks:[{'종목명':'삼성전자','티커':5930,'매수평단가':100,'보유수량':1,'해외여부':'FALSE'}],savings:[],config:[]}))w.XLSX.utils.book_append_sheet(wb,w.XLSX.utils.json_to_sheet(rows),name);const s=w.AssetHub.readWorkbook(wb);assert.equal(s.stocks[0].foreign,false);assert.equal(s.history.length,w.AssetHub.getState().history.length)});
check('JSON roundtrip and local persistence',()=>{assert.deepEqual(json(w.AssetHub.normalize(JSON.parse(w.localStorage.getItem(KEY)))),json(w.AssetHub.getState()))});
await $('#refresh-market').onclick();
check('UI automatic quote/FX integration with fixture',()=>{assert.equal(w.AssetHub.calc().total,3100000);assert.equal(w.AssetHub.getState().config.fx,1400)});
w.fetch=async()=>({ok:false,json:async()=>({error:'provider unavailable'})});await $('#refresh-market').onclick();
check('failed quote/FX retain prior values with error status',()=>{assert.equal(w.AssetHub.calc().total,3100000);assert(w.AssetHub.getState().stocks[0].quoteError);assert(w.AssetHub.getState().config.fxError)});
for(const s of w.AssetHub.getState().stocks)click(`[data-delete=stock][data-id="${s.id}"]`);for(const s of w.AssetHub.getState().savings)click(`[data-delete=bank][data-id="${s.id}"]`);
check('delete final asset records zero',()=>{assert.equal(w.AssetHub.calc().total,0);assert.equal(w.AssetHub.getState().history.at(-1).total,0)});
// Fresh application instance verifies corrupt raw data is not overwritten.
const broken=new JSDOM(fs.readFileSync(root+'/index.html','utf8'),{url:'https://hub.test',runScripts:'outside-only'}),v=broken.window;v.alert=()=>{};v.setTimeout=()=>0;v.setInterval=()=>0;v.structuredClone=structuredClone;v.localStorage.setItem(KEY,'{broken');v.eval(fs.readFileSync(root+'/js/app.js','utf8'));
check('corrupt raw storage is protected',()=>assert.equal(v.localStorage.getItem(KEY),'{broken'));
check('unexpected alerts',()=>assert.deepEqual(messages,[]));console.log(`${count} DOM/data tests PASS (not a real browser or installation test)`);dom.window.close();broken.window.close();

})().catch(e=>{console.error(e);process.exit(1)});
