/* curvature.js — the boost layer. The only script (C-300).
 *
 * It intercepts working links and working forms inside a [data-boost]
 * scope, refetches with the Curvature-Boost header, and swaps the returned
 * subtrees by id. Every path out of here on trouble is the same: real
 * navigation to a real URL. The app never needs this file; it only
 * enjoys it.
 */
(() => {
  "use strict";

  const HEADER = { "Curvature-Boost": "1" };

  const sameOrigin = (url) => url.origin === location.origin;

  const fallback = (url) => location.assign(url);

  const swap = (markup, url, push) => {
    const template = document.createElement("template");
    template.innerHTML = markup;
    const roots = [...template.content.children];
    if (roots.length === 0) return fallback(url);
    for (const root of roots) {
      if (!root.id || !document.getElementById(root.id)) return fallback(url);
    }
    for (const root of roots) {
      document.getElementById(root.id).replaceWith(root);
    }
    for (const root of roots) {
      const auto = root.querySelector("[autofocus]");
      if (auto) { auto.focus(); break; }
    }
    if (push) history.pushState({ curvature: true }, "", url);
  };

  const boostedFetch = async (url, options, push) => {
    let response;
    try {
      response = await fetch(url, {
        ...options,
        headers: HEADER,
        credentials: "same-origin",
        redirect: "follow",
      });
    } catch {
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
    event.preventDefault();
    if (method === "GET") {
      url.search = new URLSearchParams(new FormData(form)).toString();
      boostedFetch(url, { method: "GET" }, true);
    } else {
      boostedFetch(url, { method: "POST", body: new FormData(form) }, true);
    }
  });

  addEventListener("popstate", () => {
    boostedFetch(new URL(location.href), { method: "GET" }, false);
  });
})();
