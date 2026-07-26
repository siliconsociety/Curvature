/* curvature.js — the sole script (C-300): working navigation, enhanced. */
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
    const active = document.activeElement;
    const focusId = active?.id && roots.some((root) => {
      const target = root.id && document.getElementById(root.id);
      return target?.contains(active);
    }) ? active.id : "";
    for (const root of roots) {
      const target = root.id && document.getElementById(root.id);
      if (target) target.replaceWith(root);
    }
    if (soft) return startLive();
    const auto = roots.map((root) => root.querySelector("[autofocus]")).find(Boolean);
    if (auto) auto.focus();
    else if (focusId) document.getElementById(focusId)?.focus({ preventScroll: true });
    if (push) history.pushState({ curvature: true }, "", url);
    startLive();
  };

  // Live (C-502): streams belong to their declaring roots.
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

  const setPending = (owner, active) => {
    if (!owner) return;
    const [form, submitter] = owner;
    form.toggleAttribute("data-curvature-pending", active);
    form.setAttribute("aria-busy", active ? "true" : "false");
    submitter?.toggleAttribute("data-curvature-pending", active);
  };

  const boostedFetch = async (url, options, push, owner) => {
    if (navigation) {
      navigation.controller.abort();
      setPending(navigation.owner, false);
    }
    const current = { controller: new AbortController(), owner };
    navigation = current;
    setPending(owner, true);
    try {
      const response = await fetch(url, {
        ...options,
        headers: HEADER,
        credentials: "same-origin",
        redirect: "follow",
        signal: current.controller.signal,
      });
      const type = response.headers.get("content-type") || "";
      if (!response.ok || !type.includes("text/html")) return fallback(response.url || url);
      swap(await response.text(), response.url, push);
    } catch (error) {
      if (error.name === "AbortError") return;
      return fallback(url);
    } finally {
      if (navigation === current) {
        setPending(owner, false);
        navigation = undefined;
      }
    }
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
    const submitter = event.submitter;
    const effective = (attribute, name) => (
      submitter?.hasAttribute(attribute) ? submitter[`form${name}`] : form[name.toLowerCase()]
    );
    const url = new URL(effective("formaction", "Action"), location.href);
    if (!sameOrigin(url)) return;
    const method = (effective("formmethod", "Method") || "get").toUpperCase();
    const target = effective("formtarget", "Target");
    if (target && target !== "_self") return;
    // Mutations stay native: enhancement never risks replaying a write.
    if (method !== "GET") return;
    event.preventDefault();
    url.search = new URLSearchParams(new FormData(form, submitter || undefined)).toString();
    boostedFetch(url, { method: "GET" }, true, [form, submitter]);
  });

  addEventListener("popstate", () => {
    boostedFetch(new URL(location.href), { method: "GET" }, false);
  });

  startLive();
})();
