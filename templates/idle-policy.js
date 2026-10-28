/* Pure idle timer; integrate with the current native adapter, not a standalone pet. */
(function (root) {
  'use strict';
  function createIdlePolicy(start = 0) {
    let last = start, pointer = null, wasEligible = true;
    return {
      interact(now) { last = now; },
      pointer(x, y, now) {
        const valid = Number.isFinite(x) && Number.isFinite(y);
        const changed = valid && (!pointer || pointer[0] !== x || pointer[1] !== y);
        pointer = valid ? [x, y] : null;
        if (changed) last = now;
      },
      select(now, { scene = 'idle', hover = false, drag = false, visible = true } = {}) {
        const eligible = scene === 'idle' && !hover && !drag && visible;
        if (!eligible || !wasEligible) last = now;
        wasEligible = eligible;
        if (!eligible) return scene === 'idle' && drag ? 'drag' : scene;
        return now - last >= 2000 ? 'idleSit' : 'idle';
      }
    };
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = { createIdlePolicy };
  else root.TraeIdlePolicy = { createIdlePolicy };
})(typeof window === 'undefined' ? globalThis : window);
