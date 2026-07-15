/* curvature.js — the boost layer. The only script (C-300).
 *
 * It intercepts working links and GET forms inside a [data-boost]
 * scope, refetches with the Curvature-Boost header, and swaps the returned
 * subtrees by id. Every path out of here on trouble is the same: real
 * navigation to a real URL. The app never needs this file; it only
 * enjoys it.
 */
(() => {
  "use strict";

  const HEADER = { "Curvature-Boost": "1" };
  let navigation;

  const sameOrigin = (url) => url.origin === location.origin;

  const fallback = (url) => location.assign(url);

  const swap = (markup, url, push, soft) => {
    const template = document.createElement("template");
    template.innerHTML = markup;
    const roots = [...template.content.children];
    if (roots.length === 0) return soft ? undefined : fallback(url);
    if (!soft) {
      for (const root of roots) {
        if (!root.id || !document.getElementById(root.id)) return fallback(url);
      }
    }
    for (const root of roots) {
      const target = root.id && document.getElementById(root.id);
      if (target) target.replaceWith(root);
    }
    if (soft) return startLive();
    for (const root of roots) {
      const auto = root.querySelector("[autofocus]");
      if (auto) { auto.focus(); break; }
    }
    if (push) history.pushState({ curvature: true }, "", url);
    startLive();
  };

  // Live (C-502): each stream belongs to the current root that declares it.
  // Clean terminal events retire that root; a later replacement starts fresh.
  const liveStreams = new Map();
  const endedLive = new WeakSet();

  const stopLive = (stream, source, terminal) => {
    const active = liveStreams.get(stream);
    if (!active || active.source !== source) return;
    source.close();
    liveStreams.delete(stream);
    if (!terminal) return;
    for (const el of document.querySelectorAll("[data-live]")) {
      if (el.dataset.live === stream) endedLive.add(el);
    }
  };

  const startLive = () => {
    const owners = new Map();
    for (const el of document.querySelectorAll("[data-live]")) {
      const stream = el.dataset.live;
      if (!stream || endedLive.has(el) || owners.has(stream)) continue;
      owners.set(stream, el);
    }
    for (const [stream, active] of liveStreams) {
      const owner = owners.get(stream);
      if (owner) active.owner = owner;
      else stopLive(stream, active.source, false);
    }
    for (const [stream, owner] of owners) {
      if (liveStreams.has(stream)) continue;
      const source = new EventSource(stream);
      liveStreams.set(stream, { owner, source });
      source.onmessage = (event) => swap(event.data, location.href, false, true);
      source.addEventListener("curvature-end", () => stopLive(stream, source, true));
    }
  };

  const boostedFetch = async (url, options, push) => {
    if (navigation) navigation.abort();
    navigation = new AbortController();
    let response;
    try {
      response = await fetch(url, {
        ...options,
        headers: HEADER,
        credentials: "same-origin",
        redirect: "follow",
        signal: navigation.signal,
      });
    } catch (error) {
      if (error.name === "AbortError") return;
      return fallback(url);
    }
    const type = response.headers.get("content-type") || "";
    if (!response.ok || !type.includes("text/html")) return fallback(response.url || url);
    swap(await response.text(), response.url, push);
  };

  const boostScope = (node) => node.closest("[data-boost]");

  document.addEventListener("click", (event) => {
    if (event.defaultPrevented || event.button !== 0) return;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const anchor = event.target.closest("a[href]");
    if (!anchor || !boostScope(anchor)) return;
    if (anchor.target && anchor.target !== "_self") return;
    if (anchor.hasAttribute("download")) return;
    const url = new URL(anchor.href, location.href);
    if (!sameOrigin(url)) return;
    event.preventDefault();
    boostedFetch(url, { method: "GET" }, true);
  });

  document.addEventListener("submit", (event) => {
    if (event.defaultPrevented) return;
    const form = event.target;
    if (!boostScope(form)) return;
    const url = new URL(form.action, location.href);
    if (!sameOrigin(url)) return;
    const method = (form.method || "get").toUpperCase();
    // Mutations stay native. A failed enhanced POST cannot be retried without
    // risking a duplicate write, so interception would make the baseline less safe.
    if (method !== "GET") return;
    event.preventDefault();
    url.search = new URLSearchParams(new FormData(form, event.submitter)).toString();
    boostedFetch(url, { method: "GET" }, true);
  });

  addEventListener("popstate", () => {
    boostedFetch(new URL(location.href), { method: "GET" }, false);
  });

  startLive();
})();
