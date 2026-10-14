// Offline cache for the takeoff card. Bump VERSION on each update.
const VERSION='sen3-v10-dd20261001';const FILES=['./','index.html','manifest.webmanifest','icon-180.png','icon-512.png','runways.json','tab-data.pdf'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(VERSION).then(c=>c.addAll(FILES.map(f=>new Request(f,{cache:'reload'})))).then(()=>self.skipWaiting()));});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==VERSION).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',e=>{const u=new URL(e.request.url);if(u.origin!==location.origin)return; // weather goes straight to the network
  if(e.request.method!=='GET')return;
  // no-cache: always check GitHub for a newer copy instead of the browser's 10-minute HTTP cache
  e.respondWith(fetch(u.href,{cache:'no-cache'}).then(r=>{const c=r.clone();caches.open(VERSION).then(x=>x.put(e.request,c));return r;}).catch(()=>caches.match(e.request,{ignoreSearch:true}).then(r=>r||caches.match('index.html'))));});
