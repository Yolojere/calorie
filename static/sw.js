const CACHE_NAME = 'trackyou-v1.2';

// TIER 1: Critical resources - precache these (loaded immediately on install)
const criticalResources = [
  '/',
  '/static/js/translationswo.js',
  '/static/js/translationshistory.js',
  '/static/js/translations.js',
  '/static/css/styles.css',
  '/static/images/trackyoulogo.png',
  '/static/images/favicon-192x192.png',
  '/static/images/favicon-512x512.png'
];

// TIER 2: Page-specific resources - runtime cache these (loaded when visited)
const pageSpecificResources = [
  '/login',
  '/workout',
  '/history',
  '/activity',
  '/custom_food',
  '/profile',
  '/register'
];

// =============== INSTALL ===============
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('Caching critical resources');
        return cache.addAll(criticalResources);
      })
      .catch((error) => {
        console.error('Failed to cache critical resources:', error);
      })
  );
  self.skipWaiting();
});

// =============== ACTIVATE ===============
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// =============== FETCH ===============
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip cross-origin requests
  if (url.origin !== location.origin && !isCDNResource(url)) return;

  // Skip non-GET requests
  if (request.method !== 'GET') return;

  // Skip API calls
  if (
    url.pathname.includes('/api/') || 
    url.pathname.includes('/save_') || 
    url.pathname.includes('/delete_') ||
    url.pathname.includes('/search_')
  ) return;

  // ✅ Skip favicon and app icon requests completely
  if (
    url.pathname.includes('favicon') ||
    url.pathname.includes('icon-') ||
    url.pathname.includes('apple-touch-icon')
  ) {
    return; // Let browser handle them natively
  }

  // Handle Range requests (for media)
  if (request.headers.has('range')) {
    event.respondWith(handleRangeRequest(request));
    return;
  }

  // Network First for HTML pages
  if (request.headers.get('accept')?.includes('text/html')) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response && response.ok && response.status === 200) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        })
        .catch(() => caches.match(request).then((res) => res || caches.match('/offline.html')))
    );
    return;
  }

  // Cache First for JavaScript
  if (url.pathname.endsWith('.js') && url.origin === location.origin) {
    event.respondWith(
      caches.match(request)
        .then((cachedResponse) => {
          if (cachedResponse) {
            // Update cache in background
            fetch(request).then((response) => {
              if (response && response.ok && response.status === 200) {
                caches.open(CACHE_NAME).then((cache) => cache.put(request, response));
              }
            }).catch(() => {});
            return cachedResponse;
          }
          return fetch(request).then((response) => {
            if (response && response.ok && response.status === 200) {
              const clone = response.clone();
              caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
            }
            return response;
          });
        })
    );
    return;
  }

  // Cache First for CSS and images
  if (
    url.pathname.endsWith('.css') ||
    request.destination === 'image' ||
    url.pathname.includes('/static/images/')
  ) {
    event.respondWith(
      caches.match(request).then((cachedResponse) => {
        if (cachedResponse) return cachedResponse;
        return fetch(request).then((response) => {
          if (response && response.ok && response.status === 200) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        });
      })
    );
    return;
  }

  // CDN resources (cache first)
  if (isCDNResource(url)) {
    event.respondWith(
      caches.match(request).then((cachedResponse) => {
        if (cachedResponse) return cachedResponse;
        return fetch(request).then((response) => {
          if (response && response.ok && response.status === 200) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        });
      })
    );
    return;
  }

  // Default: Network first, fallback to cache
  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response && response.ok && response.status === 200) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
        }
        return response;
      })
      .catch(() => caches.match(request))
  );
});

// =============== RANGE HANDLER ===============
function handleRangeRequest(request) {
  return caches.match(request.url)
    .then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse.arrayBuffer().then((arrayBuffer) => {
          const bytes = /^bytes\=(\d+)\-(\d+)?$/g.exec(request.headers.get('range'));
          if (bytes) {
            const start = Number(bytes[1]);
            const end = Number(bytes[2]) || arrayBuffer.byteLength - 1;
            return new Response(arrayBuffer.slice(start, end + 1), {
              status: 206,
              statusText: 'Partial Content',
              headers: [
                ['Content-Range', `bytes ${start}-${end}/${arrayBuffer.byteLength}`],
                ['Content-Type', cachedResponse.headers.get('Content-Type')]
              ]
            });
          }
          return new Response(arrayBuffer);
        });
      }

      // No cached version → fetch full file
      const newRequest = new Request(request.url, { headers: new Headers(request.headers) });
      return fetch(newRequest, { cache: 'no-store' })
        .then((response) => {
          if (response && response.ok && response.status === 200) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request.url, clone));
          }
          return response;
        });
    })
    .catch(() => fetch(request));
}

// =============== HELPER ===============
function isCDNResource(url) {
  const cdnDomains = [
    'cdn.jsdelivr.net',
    'cdnjs.cloudflare.com',
    'fonts.googleapis.com',
    'fonts.gstatic.com'
  ];
  return cdnDomains.some(domain => url.hostname.includes(domain));
}
