// Curved-Moon coordinates shared by the mesh, site markers and sky guides.
const rad = Math.PI / 180;
export function localBasis(longitude, latitude) {
  const l = longitude * rad, p = latitude * rad;
  return [[-Math.sin(l), Math.cos(l), 0],
    [-Math.sin(p)*Math.cos(l), -Math.sin(p)*Math.sin(l), Math.cos(p)],
    [Math.cos(p)*Math.cos(l), Math.cos(p)*Math.sin(l), Math.sin(p)]];
}
const dot = (a,b) => a.reduce((sum,v,i) => sum+v*b[i],0);
const sceneVector = (world,reference) => {
  const [east,north,up] = localBasis(reference.longitude,reference.latitude);
  return [dot(world,east),dot(world,up),-dot(world,north)];
};
export function sitePosition(point,reference,height=0) {
  const up = localBasis(point.longitude,point.latitude)[2];
  const origin = localBasis(reference.longitude,reference.latitude)[2];
  const world = up.map((v,i) => v*(reference.radiusM+point.elevationM+height)-origin[i]*(reference.radiusM+reference.elevationM));
  return sceneVector(world,reference);
}
export function skyDirection(azimuth,elevation,point,reference) {
  const [east,north,up] = localBasis(point.longitude,point.latitude);
  const az=azimuth*rad, el=elevation*rad;
  const world=up.map((v,i) => east[i]*Math.sin(az)*Math.cos(el)+north[i]*Math.cos(az)*Math.cos(el)+v*Math.sin(el));
  return sceneVector(world,reference);
}
