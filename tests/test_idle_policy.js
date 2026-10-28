const assert = require('node:assert/strict');
const {createIdlePolicy} = require('../templates/idle-policy.js');
let checks = 0;
function eq(a, b) { assert.equal(a, b); checks++; }
let p = createIdlePolicy(0);
eq(p.select(1999), 'idle'); eq(p.select(2000), 'idleSit'); eq(p.select(9000), 'idleSit');
p.pointer(20, 10, 9001); eq(p.select(9001), 'idle');
p.pointer(20, 10, 10000); eq(p.select(11001), 'idleSit');
p.pointer(null, null, 11002); eq(p.select(11002), 'idleSit');
eq(p.select(12000, {hover:true}), 'idle'); eq(p.select(17000, {hover:true}), 'idle');
eq(p.select(17001), 'idle'); eq(p.select(19001), 'idleSit');
eq(p.select(20000, {drag:true}), 'drag'); eq(p.select(20001), 'idle');
for (const scene of ['busy', 'superbusy', 'voice', 'waiting', 'completed']) {
  eq(p.select(30000, {scene}), scene); eq(p.select(30001), 'idle'); eq(p.select(32001), 'idleSit');
}
eq(p.select(40000, {visible:false}), 'idle'); eq(p.select(90000), 'idle');
eq(p.select(91999), 'idle'); eq(p.select(92000), 'idleSit');
p.interact(92001); eq(p.select(92001), 'idle'); eq(p.select(94001), 'idleSit');
console.log(JSON.stringify({passed:checks, scope:'pure idle policy, not live TRAE integration'}));
