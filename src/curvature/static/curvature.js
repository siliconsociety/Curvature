/* curvature.js (C-300): stable entrypoint for navigation and fragment swaps. */
(() => {
  "use strict";

  const HEADER = { "Curvature-Boost": "1" };
  const entrypointURL = new URL(document.currentScript.src);
  const liveURL = new URL("live.js", entrypointURL);
  liveURL.search = entrypointURL.search;
  let navigation, liveLoading, liveStart;
  let documentURL = new URL(location.href);

  const sameOrigin = (url) => url.origin === location.origin;
  const fallback = (url) => location.assign(url);
  const scrollToFragment = (url) => {
    if (!url.hash) return;
    // Form decoding is forgiving UTF-8; protect query separators kept literal in fragments.
    const fragment = url.hash.slice(1).replace(/[+&]/g, encodeURIComponent);
    const id = new URLSearchParams(`value=${fragment}`).get("value");
    const target = document.getElementById(id)
      || document.querySelector(`a[name="${CSS.escape(id)}"]`);
    if (target) target.scrollIntoView();
    else if (id.toLowerCase() === "top") scrollTo(0, 0);
  };

  const startLive = () => {
    if (liveStart) return liveStart();
    if (liveLoading) return;
    liveLoading = import(liveURL.href)
      .then((module) => {
        liveStart = module.createLive(
          (markup) => swap(markup, location.href, false, true),
        );
        liveStart();
      })
      // Live is enhancement. Navigation remains usable if its module cannot load.
      .catch(() => undefined);
  };

  const swap = (markup, url, push, soft = false) => {
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

    const autofocus = roots
      .map((root) => root.querySelector("[autofocus]"))
      .find(Boolean);
    if (autofocus) autofocus.focus();
    else if (focusId) document.getElementById(focusId)?.focus({ preventScroll: true });
    if (push) history.pushState({ curvature: true }, "", url);
    documentURL = new URL(url);
    startLive();
    scrollToFragment(documentURL);
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
      const destination = new URL(response.url || url);
      if (!destination.hash) destination.hash = url.hash;
      if (!response.ok || !type.includes("text/html")) return fallback(destination);
      swap(await response.text(), destination, push);
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
    if (
      url.hash
      && url.pathname === location.pathname
      && url.search === location.search
    ) return;
    event.preventDefault();
    boostedFetch(url, { method: "GET" }, true);
  });

  document.addEventListener("submit", (event) => {
    if (event.defaultPrevented) return;
    const form = event.target;
    if (!boostScope(form)) return;
    const submitter = event.submitter;
    const effective = (attribute, name) => (
      submitter?.hasAttribute(attribute)
        ? submitter[`form${name}`]
        : form[name.toLowerCase()]
    );
    const url = new URL(effective("formaction", "Action"), location.href);
    if (!sameOrigin(url)) return;
    const method = (effective("formmethod", "Method") || "get").toUpperCase();
    const target = effective("formtarget", "Target");
    if (target && target !== "_self") return;
    // Mutations stay native: enhancement never risks replaying a write.
    if (method !== "GET") return;
    event.preventDefault();
    url.search = new URLSearchParams(
      new FormData(form, submitter || undefined),
    ).toString();
    boostedFetch(url, { method: "GET" }, true, [form, submitter]);
  });

  addEventListener("popstate", () => {
    const url = new URL(location.href);
    if (
      url.pathname === documentURL.pathname
      && url.search === documentURL.search
    ) return;
    boostedFetch(url, { method: "GET" }, false);
  });

  startLive();
})();
