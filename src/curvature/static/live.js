/* live.js (C-300): lifecycle for server-declared EventSource streams. */
export const createLive = (swap) => {
  const streams = new Map();
  const endedOwners = new WeakSet();

  const stop = (stream, source, terminal) => {
    const active = streams.get(stream);
    if (!active || active.source !== source) {
      return;
    }
    source.close();
    streams.delete(stream);
    if (!terminal) {
      return;
    }
    for (const owner of document.querySelectorAll("[data-live]")) {
      if (owner.dataset.live === stream) {
        endedOwners.add(owner);
      }
    }
  };

  return () => {
    const owners = new Map();
    for (const owner of document.querySelectorAll("[data-live]")) {
      const stream = owner.dataset.live;
      if (!stream || endedOwners.has(owner) || owners.has(stream)) {
        continue;
      }
      owners.set(stream, owner);
    }

    for (const [stream, active] of streams) {
      const owner = owners.get(stream);
      if (owner) {
        active.owner = owner;
      } else {
        stop(stream, active.source, false);
      }
    }

    for (const [stream, owner] of owners) {
      if (streams.has(stream)) {
        continue;
      }
      const source = new EventSource(stream);
      streams.set(stream, { owner, source });
      source.onmessage = (event) => swap(event.data);
      source.addEventListener(
        "curvature-end",
        () => stop(stream, source, true),
      );
    }
  };
};
