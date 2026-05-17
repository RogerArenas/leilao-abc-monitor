const CACHE = 'leilao-v1';
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(['/', '/index.html'])));
});
self.addEventListener('fetch', e => {
  if (e.request.url.includes('dados.json')) return;
  e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
});
