/* Shared state-to-pose contract. Head tracking remains independent of body pose. */
(function (root) {
  'use strict';
  function selectPose({scene = 'idle', hover = false, drag = false, visible = true, hasTarget = false} = {}) {
    if (!visible) return 'hidden';
    if (scene !== 'idle') return scene;
    if (drag) return 'drag';
    if (hover) return 'hover';
    if (hasTarget) return 'standReach';
    return 'idleSit';
  }
  const api = {selectPose};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.TraePosePolicy = api;
})(typeof window === 'undefined' ? globalThis : window);
