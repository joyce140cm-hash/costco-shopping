var CACHE='costco-v1';
var ASSETS=[
  '/costco-shopping/',
  '/costco-shopping/index.html',
  '/costco-shopping/manifest.json',
  '/costco-shopping/icon-192.png',
  '/costco-shopping/icon-512.png'
];

self.addEventListener('install',function(e){
  e.waitUntil(
    caches.open(CACHE).then(function(c){return c.addAll(ASSETS);})
  );
  self.skipWaiting();
});

self.addEventListener('activate',function(e){
  e.waitUntil(
    caches.keys().then(function(keys){
      return Promise.all(keys.filter(function(k){return k!==CACHE;}).map(function(k){return caches.delete(k);}));
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch',function(e){
  var url=e.request.url;
  // deals.json 永遠從網路抓（要取得最新特價）
  if(url.indexOf('deals.json')!==-1){
    e.respondWith(
      fetch(e.request).catch(function(){return caches.match(e.request);})
    );
    return;
  }
  // 其他資源：先找快取，沒有再去網路
  e.respondWith(
    caches.match(e.request).then(function(r){
      return r||fetch(e.request).then(function(res){
        if(res&&res.status===200){
          var clone=res.clone();
          caches.open(CACHE).then(function(c){c.put(e.request,clone);});
        }
        return res;
      });
    })
  );
});
