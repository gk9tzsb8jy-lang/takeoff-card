// Offline cache for the N600NJ card. Bump VERSION on each update.
const VERSION='n600nj-v14-dd20261029';const FILES=['./','index.html','manifest.webmanifest','icon-180.png','icon-512.png','tab-data.pdf','runways.json'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(VERSION).then(c=>c.addAll(FILES.map(f=>new Request(f,{cache:'reload'})))).then(()=>self.skipWaiting()));});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k.startsWith('n600nj-')&&k!==VERSION).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',e=>{const u=new URL(e.request.url);if(u.origin!==location.origin)return; // weather goes straight to the network
  if(e.request.method!=='GET')return;
  e.respondWith(fetch(u.href,{cache:'no-cache'}).then(r=>{const c=r.clone();caches.open(VERSION).then(x=>x.put(e.request,c));return r;}).catch(()=>caches.match(e.request,{ignoreSearch:true}).then(r=>r||caches.match('index.html'))));});
