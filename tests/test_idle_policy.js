const {selectPose} = require('../templates/default-pose-policy.js');
const assert = require('node:assert/strict');
assert.equal(selectPose(), 'idleSit');
assert.equal(selectPose({hasTarget:true}), 'standReach');
for(const scene of ['busy','superbusy','waiting','voice','completed'])
  assert.equal(selectPose({scene,hasTarget:true}),scene);
assert.equal(selectPose({drag:true,hasTarget:true}),'drag');
assert.equal(selectPose({hover:true,hasTarget:true}),'hover');
assert.equal(selectPose({visible:false}),'hidden');
console.log('10 pose routing assertions PASS');
