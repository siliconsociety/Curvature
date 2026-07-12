/* curvature-offline.js — the replay worker (C-303).
 *
 * A cache, never a database: successful GETs are remembered, and when
 * the network dies you get the last thing you saw. No queues, no
 * shadow state, no decisions — offline writes fail with the browser's
 * own honesty, exactly as the manifesto promised. Registered only when
 * a page declares data-offline-cache; the boost layer does the one
 * line of registering.
 */
const CACHE = "curvature-replay-v1";

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return; // writes are never replayed
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response.ok && response.type === "basic") {
          const copy = response.clone();
          caches.open(CACHE).then((cache) => cache.put(request, copy));
        }
        return response;
      })
      .catch(async () => {
        const remembered = await caches.match(request);
        if (remembered) return remembered;
        return new Response(
          "Offline, and this page was never visited while connected.",
          { status: 503, headers: { "content-type": "text/plain" } },
        );
      }),
  );
});
