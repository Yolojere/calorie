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
  '/login',
  '/register'
];

// Install event
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

// Activate event
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

// Fetch event with 206 response handling
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip cross-origin requests
  if (url.origin !== location.origin && !isCDNResource(url)) {
    return;
  }

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip API endpoints
  if (url.pathname.includes('/api/') || 
      url.pathname.includes('/save_') || 
      url.pathname.includes('/delete_') ||
      url.pathname.includes('/search_')) {
    return;
  }

  // Handle Range requests (video/audio/large files) differently
  if (request.headers.has('range')) {
    event.respondWith(handleRangeRequest(request));
    return;
  }

  // Network First for HTML pages
  if (request.headers.get('accept')?.includes('text/html')) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          // Only cache successful responses (200-299)
          if (response && response.ok && response.status === 200) {
            const responseClone = response.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(request, responseClone);
            });
          }
          return response;
        })
        .catch(() => {
          return caches.match(request).then((response) => {
            return response || caches.match('/offline.html');
          });
        })
    );
    return;
  }

  // Cache First for JavaScript files
  if (url.pathname.endsWith('.js') && url.origin === location.origin) {
    event.respondWith(
      caches.match(request)
        .then((cachedResponse) => {
          if (cachedResponse) {
            // Update cache in background
            fetch(request).then((response) => {
              if (response && response.ok && response.status === 200) {
                caches.open(CACHE_NAME).then((cache) => {
                  cache.put(request, response);
                });
              }
            }).catch(() => {});
            
            return cachedResponse;
          }

          // Not in cache, fetch from network
          return fetch(request).then((response) => {
            // Only cache 200 responses, not 206
            if (response && response.ok && response.status === 200) {
              const responseClone = response.clone();
              caches.open(CACHE_NAME).then((cache) => {
                cache.put(request, responseClone);
              });
            }
            return response;
          });
        })
    );
    return;
  }

  // Cache First for CSS and images
  if (url.pathname.endsWith('.css') || 
      request.destination === 'image' ||
      url.pathname.includes('/static/images/')) {
    event.respondWith(
      caches.match(request)
        .then((cachedResponse) => {
          if (cachedResponse) {
            return cachedResponse;
          }

          return fetch(request).then((response) => {
            // Only cache complete responses
            if (response && response.ok && response.status === 200) {
              const responseClone = response.clone();
              caches.open(CACHE_NAME).then((cache) => {
                cache.put(request, responseClone);
              });
            }
            return response;
          });
        })
    );
    return;
  }

  // CDN resources
  if (isCDNResource(url)) {
    event.respondWith(
      caches.match(request)
        .then((cachedResponse) => {
          if (cachedResponse) {
            return cachedResponse;
          }

          return fetch(request).then((response) => {
            if (response && response.ok && response.status === 200) {
              const responseClone = response.clone();
              caches.open(CACHE_NAME).then((cache) => {
                cache.put(request, responseClone);
              });
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
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, responseClone);
          });
        }
        return response;
      })
      .catch(() => {
        return caches.match(request);
      })
  );
});

// Handle Range requests (for video/audio files)
function handleRangeRequest(request) {
  return caches.match(request.url)
    .then((cachedResponse) => {
      // If we have a full cached response, serve it
      if (cachedResponse) {
        return cachedResponse.arrayBuffer().then((arrayBuffer) => {
          const bytes = /^bytes\=(\d+)\-(\d+)?$/g.exec(
            request.headers.get('range')
          );
          
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

      // No cached version, fetch from network
      // Create new request WITHOUT range header to get full response
      const newRequest = new Request(request.url, {
        headers: new Headers(request.headers)
      });
      
      // Remove range header to get complete response
      return fetch(newRequest, { cache: "no-store" })
        .then((response) => {
          // Cache the full response for future use
          if (response && response.ok && response.status === 200) {
            const responseClone = response.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(request.url, responseClone);
            });
          }
          return response;
        });
    })
    .catch(() => {
      // If all fails, let browser handle it normally
      return fetch(request);
    });
}

// Helper function
function isCDNResource(url) {
  const cdnDomains = [
    'cdn.jsdelivr.net',
    'cdnjs.cloudflare.com',
    'fonts.googleapis.com',
    'fonts.gstatic.com'
  ];
  return cdnDomains.some(domain => url.hostname.includes(domain));
}