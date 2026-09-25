const VERSION='0.6.0-r3';
const PREFIX='my-asset-hub-';
const CACHE=PREFIX+'v'+VERSION;
const CORE=['./index.html','./js/app.js','./config.js','./vendor/xlsx.full.min.js','./manifest.webmanifest','./icons/icon-192.png','./icons/icon-512.png'];

self.addEventListener('install',event=>{
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE).then(async cache=>{
      for(const path of CORE){
        try{await cache.add(new Request(new URL(path,self.registration.scope),{cache:'reload'}));}catch{}
      }
    })
  );
});

self.addEventListener('activate',event=>{
  event.waitUntil(
    caches.keys()
      .then(keys=>Promise.all(keys.filter(k=>k.startsWith(PREFIX)&&k!==CACHE).map(k=>caches.delete(k))))
      .then(()=>self.clients.claim())
  );
});

self.addEventListener('fetch',event=>{
  const request=event.request;
  const url=new URL(request.url);
  if(request.method!=='GET'||url.origin!==self.location.origin||url.pathname.startsWith('/api/'))return;

  if(request.mode==='navigate'){
    event.respondWith((async()=>{
      try{
        const network=await fetch(request,{cache:'no-store'});
        if(network&&network.ok){
          const cache=await caches.open(CACHE);
          cache.put(new URL('./index.html',self.registration.scope),network.clone()).catch(()=>{});
          return network;
        }
      }catch{}
      const cache=await caches.open(CACHE);
      const cached=await cache.match(new URL('./index.html',self.registration.scope));
      if(cached)return cached;
      return new Response('My Asset Hub를 불러오지 못했습니다. 네트워크 연결 후 다시 시도하세요.',{
        status:503,
        headers:{'content-type':'text/plain; charset=utf-8'}
      });
    })());
    return;
  }

  const coreUrls=new Set(CORE.map(p=>new URL(p,self.registration.scope).href));
  if(coreUrls.has(url.href)){
    event.respondWith((async()=>{
      try{
        const network=await fetch(request,{cache:'no-store'});
        if(network&&network.ok){
          const cache=await caches.open(CACHE);
          cache.put(request,network.clone()).catch(()=>{});
          return network;
        }
      }catch{}
      const cache=await caches.open(CACHE);
      return (await cache.match(request))||Response.error();
    })());
  }
});
