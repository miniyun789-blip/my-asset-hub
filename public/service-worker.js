// My Asset Hub recovery service worker.
// This intentionally removes legacy offline caches and unregisters itself.
// PWA installation is provided by manifest.webmanifest while offline caching is disabled.
self.addEventListener('install',event=>{
  self.skipWaiting();
});
self.addEventListener('activate',event=>{
  event.waitUntil((async()=>{
    try{
      const keys=await caches.keys();
      await Promise.all(keys.filter(k=>k.startsWith('my-asset-hub-')).map(k=>caches.delete(k)));
    }catch{}
    try{await self.registration.unregister();}catch{}
    try{
      const clientsList=await self.clients.matchAll({type:'window',includeUncontrolled:true});
      for(const client of clientsList){
        try{client.postMessage({type:'MY_ASSET_HUB_SW_REMOVED'});}catch{}
      }
    }catch{}
  })());
});
// Deliberately no fetch handler: navigation and assets always use the network.
