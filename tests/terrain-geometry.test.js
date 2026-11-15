import test from 'node:test';
import assert from 'node:assert/strict';
import {localBasis,sitePosition,skyDirection} from '../src/terrain-geometry.js';
const ref={longitude:-137.5,latitude:-89.46,elevationM:1944,radiusM:1737400};
const point={...ref};
const near=(a,b,tol=1e-8)=>a.forEach((v,i)=>assert.ok(Math.abs(v-b[i])<tol,`${a} differs from ${b}`));
test('site observer height maps to the true vertical without exaggeration',()=>{
  near(sitePosition(point,ref),[0,0,0]);near(sitePosition(point,ref,2),[0,2,0]);
});
test('north east and below-horizon directions use the same local frame as geometry',()=>{
  near(skyDirection(0,0,point,ref),[0,0,-1]);near(skyDirection(90,0,point,ref),[1,0,0]);
  near(skyDirection(0,-90,point,ref),[0,-1,0]);
});
test('directions stay unit length and preserve angles away from the mesh reference',()=>{
  const remote={longitude:50,latitude:-87,elevationM:1800};
  const a=skyDirection(0,0,remote,ref),b=skyDirection(90,0,remote,ref);
  assert.ok(Math.abs(Math.hypot(...a)-1)<1e-12);assert.ok(Math.abs(a.reduce((s,v,i)=>s+v*b[i],0))<1e-12);
});
test('curved-Moon mesh positions retain spherical sag',()=>{
  const equator={longitude:0,latitude:0,elevationM:0,radiusM:1737400};
  const delta=.1*Math.PI/180;
  const p=sitePosition({longitude:.1,latitude:0,elevationM:0},equator);
  near(p,[equator.radiusM*Math.sin(delta),equator.radiusM*(Math.cos(delta)-1),0],1e-7);
  assert.ok(p[1]<0);
});
test('polar bases remain orthonormal and wrap longitude',()=>{
  const b=localBasis(179,-90);
  for(let i=0;i<3;i++)for(let j=0;j<3;j++)assert.ok(Math.abs(b[i].reduce((s,v,k)=>s+v*b[j][k],0)-(i===j?1:0))<1e-12);
  near(skyDirection(13,4,{longitude:-180,latitude:-89},ref),skyDirection(13,4,{longitude:180,latitude:-89},ref));
});
