// Run with Playwright plus a locally installed Chromium executable.
const fs=require('fs'),assert=require('assert'),http=require('http'),path=require('path'),os=require('os');
const artifactDir=path.resolve(__dirname,'../test-artifacts');fs.mkdirSync(artifactDir,{recursive:true});
const {chromium}=require('playwright');
(async()=>{
 const chromiumBinary=process.env.CHROMIUM_EXECUTABLE||chromium.executablePath();
 const root=path.resolve(__dirname,'../public');const server=http.createServer((req,res)=>{const file=path.join(root,req.url==='/'?'index.html':req.url);res.setHeader('Content-Type',file.endsWith('.js')?'application/javascript':'text/html');res.end(fs.readFileSync(file))});await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const browser=await chromium.launch({executablePath:chromiumBinary,headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--disable-gpu','--no-zygote','--single-process','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-software-rasterizer']});
 const page=await browser.newPage({viewport:{width:1280,height:950},serviceWorkers:'block'});let errors=[],failQuotes=false;page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
 await page.route('**/api/**',async route=>{let data={ok:true};const path=new URL(route.request().url()).pathname;
  if(path==='/api/search')data={results:[{name:'Apple Inc.',ticker:'AAPL',market:'NASDAQ',currency:'USD'}],total:1};
  if(path==='/api/fx')data=failQuotes?{error:'test failure'}:{rate:1400,source:'TEST fixture',asOf:'2026-09-24T00:00:00Z'};
  if(path==='/api/quote')data=failQuotes?{error:'test failure'}:{price:150,currency:'USD',source:'TEST fixture',asOf:'2026-09-24T00:00:00Z',kind:'test'};
  await route.fulfill({status:failQuotes&&path==='/api/fx'?502:200,contentType:'application/json',body:JSON.stringify(data)});
 });
 const url=`http://127.0.0.1:${server.address().port}`;await page.goto(url);await page.waitForFunction(()=>window.AssetHub);assert.equal(await page.locator('#hero-total').innerText(),'0원');await page.waitForTimeout(1000);
 // Search → choose → add foreign stock.
 await page.getByRole('button',{name:'자산 관리',exact:true}).click();await page.locator('#add-stock').click();await page.locator('#open-market-search').click();await page.locator('#market-query').fill('AAPL');await page.locator('[data-market-pick="0"]').click();
 for(const [key,value]of Object.entries({buy:'100',quantity:'10',price:'120',buyFx:'1300'}))await page.locator(`#editor [name=${key}]`).fill(value);
 await page.locator('#editor-form button[type=submit]').click();assert.equal(await page.locator('#stock-total').innerText(),'1,680,000원');assert.equal(await page.locator('#profit-total').innerText(),'+380,000원');
 // Additional purchase weighted cost and FX, then edit back.
 await page.locator('#add-stock').click();for(const [k,v]of Object.entries({name:'Apple',ticker:'AAPL',buy:'200',quantity:'5',buyFx:'1500'}))await page.locator(`#editor [name=${k}]`).fill(v);await page.locator('#editor [name=foreign]').selectOption('true');await page.locator('#editor-form button[type=submit]').click();
 let merged=await page.evaluate(()=>AssetHub.getState().stocks[0]);assert.equal(merged.quantity,15);assert(Math.abs(merged.buy-133.33333333333334)<1e-8);assert.equal(merged.buyFx,1400);assert.equal(await page.evaluate(()=>AssetHub.getState().stocks.length),1);
 await page.locator('[data-edit=stock]').click();for(const [k,v]of Object.entries({buy:'100',quantity:'10',buyFx:'1300'}))await page.locator(`#editor [name=${k}]`).fill(v);await page.locator('#editor-form button[type=submit]').click();
 // Deposit principal must not multiply installment count.
 await page.locator('#add-bank').click();await page.locator('#editor [name=type]').selectOption('예금');await page.locator('#editor [name=name]').fill('예금 테스트');await page.locator('#editor [name=amount]').fill('1000000');await page.locator('#editor [name=current]').fill('5');await page.locator('#editor-form button[type=submit]').click();assert.equal(await page.locator('#bank-total').innerText(),'1,000,000원');
 await page.reload();await page.waitForFunction(()=>window.AssetHub);assert.equal(await page.locator('#hero-total').innerText(),'2,680,000원');
 await page.locator('#refresh-market').click();await page.waitForFunction(()=>document.querySelector('#refresh-market').disabled===false);assert.equal(await page.locator('#hero-total').innerText(),'3,100,000원');
 failQuotes=true;await page.locator('#refresh-market').click();await page.waitForFunction(()=>!document.querySelector('#refresh-market').disabled);assert.equal(await page.locator('#hero-total').innerText(),'3,100,000원');assert(await page.evaluate(()=>AssetHub.getState().stocks[0].quoteError));
 // Rebalancing target validation and currency conversion.
 await page.getByRole('button',{name:'리밸런싱',exact:true}).click();assert((await page.locator('#allocation-list').innerText()).includes('목표 비중 확인 필요'));
 await page.locator('[data-risk="초고위험"]').fill('50');await page.locator('[data-risk="초고위험"]').press('Tab');await page.locator('[data-risk="안전"]').fill('50');await page.locator('[data-risk="안전"]').press('Tab');await page.locator('#distribute').click();assert((await page.locator('#allocation-list').innerText()).includes('약 2.619주/개'));
 // Excel round-trip, numeric Korean code, legacy FALSE, invalid data reject.
 const result=await page.evaluate(()=>{
  const wb=XLSX.utils.book_new(),headers={'투자자산':['ID','종목명','티커','시장','통화','매수평단가','보유수량','현재가','매수환율','리스크','가격기준시각','가격출처','가격유형','해외여부'],'은행자산':['ID','종류','상품명','금액','현재회차','총회차','이율'],'설정':['항목','값'],'자산기록':['날짜','총자산'],'리스크목표':['리스크','목표비중'],'종목목표':['ID','목표비중']};
  for(const [name,rows]of Object.entries(AssetHub.workbookRows()))XLSX.utils.book_append_sheet(wb,XLSX.utils.aoa_to_sheet([headers[name],...rows]),name);
  const round=AssetHub.readWorkbook(XLSX.read(XLSX.write(wb,{type:'array',bookType:'xlsx'}),{type:'array'}));const old=AssetHub.getState();
  const legacy=AssetHub.normalize({stocks:[{'종목명':'삼성전자','티커':5930,'매수평단가':100,'보유수량':1,'해외여부':'false','리스크':'위험'}],savings:[]});
  let rejected=false;try{AssetHub.normalize({...old,stocks:[{...old.stocks[0],buy:'bad'}]})}catch{rejected=true}
  return {same:round.stocks[0].quantity===old.stocks[0].quantity&&round.stocks[0].price===old.stocks[0].price&&round.config.fx===old.config.fx&&round.history.length===old.history.length,ticker:legacy.stocks[0].ticker,foreign:legacy.stocks[0].foreign,rejected};
 });assert.deepEqual(result,{same:true,ticker:'005930',foreign:false,rejected:true});
 // Actual Excel download and import preview must work.
 await page.locator('#backup-btn').click();const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#excel-export-btn').click()]);const downloadPath=path.join(os.tmpdir(),'asset-ui-roundtrip.xlsx');await download.saveAs(downloadPath);await page.locator('#excel-import-file').setInputFiles(downloadPath);await page.locator('#apply-import').click();assert.equal(await page.locator('#hero-total').innerText(),'3,100,000원');
 // JSON actual download/import/recovery snapshot.
 await page.locator('#backup-btn').click();const [jsonDownload]=await Promise.all([page.waitForEvent('download'),page.locator('#export-btn').click()]);await jsonDownload.saveAs(path.join(os.tmpdir(),'pwa-roundtrip.json'));await page.locator('#import-file').setInputFiles(path.join(os.tmpdir(),'pwa-roundtrip.json'));await page.locator('#apply-import').click();assert.equal(await page.locator('#hero-total').innerText(),'3,100,000원');assert(await page.evaluate(()=>!!localStorage.getItem('my-asset-hub-html-v1-recovery')));
 // Mobile overflow, keyboard/dialog and overview screenshot.
 await page.getByRole('button',{name:'대시보드',exact:true}).click();await page.screenshot({path:path.join(artifactDir,'app-desktop.png'),fullPage:true});
 await page.setViewportSize({width:390,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:path.join(artifactDir,'app-mobile.png'),fullPage:true});
 // Deleting the last asset records zero rather than leaving yesterday's value.
 await page.getByRole('button',{name:'자산 관리',exact:true}).click();await page.locator('[data-delete=stock]').click();await page.locator('[data-delete=bank]').click();assert.equal(await page.locator('#hero-total').innerText(),'0원');assert.equal(await page.evaluate(()=>AssetHub.getState().history.at(-1).total),0);
 assert.deepEqual(errors,[]);console.log('PASS: UI CRUD, search selection, FX/P&L, quote failure retention, rebalance FX, Excel roundtrip, migration, validation, persistence, zero history, mobile layout.');
 await browser.close();await new Promise(r=>server.close(r));
})().catch(e=>{console.error(e);process.exit(1)});
