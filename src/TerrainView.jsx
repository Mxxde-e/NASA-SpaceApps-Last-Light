import React,{useEffect,useRef,useState} from 'react';
import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {sitePosition,skyDirection} from './terrain-geometry.js';

export default function TerrainView({point,candidates,scenario,index,request,onSelect,onMaps}) {
  const host=useRef(null), stage=useRef(null), labels=useRef({});
  const [mesh,setMesh]=useState(null),[error,setError]=useState(''),[view,setView]=useState('orbit');
  const points=[{id:'O',point},...candidates].filter(s=>s.point);
  const current=scenario?.point||point;
  const sample=scenario?.samples[Math.min(index,scenario.samples.length-1)];
  useEffect(()=>{
    if(!scenario&&(view==='sun'||view==='earth'))setView('orbit');
  },[scenario,view]);
  useEffect(()=>{
    const abort=new AbortController();
    fetch('/api/terrain-mesh',{signal:abort.signal}).then(async r=>{const d=await r.json();if(!r.ok)throw new Error(d.detail||'Terrain mesh unavailable.');return d;}).then(setMesh).catch(e=>{if(e.name!=='AbortError')setError(e.message);});
    return()=>abort.abort();
  },[]);
  useEffect(()=>{
    if(!mesh||!host.current)return;
    const element=host.current;
    let renderer,controls,observer,disposed=false;
    const scene=new THREE.Scene();scene.background=new THREE.Color('#08131e');
    const camera=new THREE.PerspectiveCamera(52,1,.1,40000);
    const vector=v=>new THREE.Vector3(...v);
    const disposeGroup=group=>{
      group.traverse(o=>{o.geometry?.dispose();if(o.material){for(const m of (Array.isArray(o.material)?o.material:[o.material]))m.dispose();}});
      group.clear();
    };
    try {
      renderer=new THREE.WebGLRenderer({antialias:true,alpha:false});
      renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,1.75));
      renderer.domElement.setAttribute('role','img');
      renderer.domElement.setAttribute('aria-label','Interactive NASA elevation terrain. Use the view buttons or NASA maps for keyboard access.');
      element.prepend(renderer.domElement);
      controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=false;
      controls.minDistance=100;controls.maxDistance=13000;controls.maxPolarAngle=Math.PI*.49;
      const geometry=new THREE.BufferGeometry();
      const position=new Float32Array(mesh.verticesENU.length);
      for(let i=0;i<position.length;i+=3){position[i]=mesh.verticesENU[i];position[i+1]=mesh.verticesENU[i+2];position[i+2]=-mesh.verticesENU[i+1];}
      geometry.setAttribute('position',new THREE.BufferAttribute(position,3));geometry.setIndex(mesh.indices);geometry.computeVertexNormals();
      scene.add(new THREE.Mesh(geometry,new THREE.MeshLambertMaterial({color:'#a4aaa9',side:THREE.DoubleSide})));
      scene.add(new THREE.AmbientLight('#91a7bf',1));
      const light=new THREE.DirectionalLight('#ffe2ae',2);scene.add(light);scene.add(light.target);
      const markers=new THREE.Group(),sky=new THREE.Group();scene.add(markers,sky);
      let projected=[],lastContext=null;
      const draw=()=>{
        if(disposed)return;
        renderer.render(scene,camera);
        const width=element.clientWidth,height=element.clientHeight;
        for(const label of Object.values(labels.current))if(label)label.hidden=true;
        for(const {id,position} of projected){
          const label=labels.current[id];if(!label)continue;
          const p=position.clone().project(camera);
          const forward=position.clone().sub(camera.position).dot(camera.getWorldDirection(new THREE.Vector3()))>0;
          label.hidden=!forward||p.z>1||p.z< -1||Math.abs(p.x)>.94||Math.abs(p.y)>.91;
          label.style.left=`${(p.x+1)*width/2}px`;label.style.top=`${(1-p.y)*height/2}px`;
        }
      };
      controls.addEventListener('change',draw);
      const onLost=event=>{event.preventDefault();setError('The 3D graphics context was interrupted. Switch to NASA maps to continue.');};
      renderer.domElement.addEventListener('webglcontextlost',onLost);
      observer=new ResizeObserver(()=>{const w=element.clientWidth,h=element.clientHeight;renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();draw();});observer.observe(element);
      function update(context){
        lastContext=context;
        const {points,current,sample,scenario,view,request}=context;
        if(!current)return;
        const height=request?.observerHeightM||2;
        const eye=vector(sitePosition(current,mesh.reference,height));
        disposeGroup(markers);disposeGroup(sky);projected=[];
        for(const item of points){
          const pos=vector(sitePosition(item.point,mesh.reference,18));
          const marker=new THREE.Mesh(new THREE.SphereGeometry(20,12,8),new THREE.MeshBasicMaterial({color:item.id===(scenario?.id||'O')?'#f2c477':'#86d5c7'}));
          marker.position.copy(pos);markers.add(marker);projected.push({id:item.id,position:pos.clone().add(new THREE.Vector3(0,65,0))});
        }
        // Sky directions use an angular guide sphere, not invented nearby terrain.
        if(scenario){
          const h=scenario.horizon;
          for(const [key,color] of [['low','#486f70'],['high','#486f70'],['nominal','#eb9cbd']]){
            const vertices=h.azimuth.map((az,i)=>vector(skyDirection(az,h[key][i],current,mesh.reference)).multiplyScalar(10000).add(eye));
            if(vertices.length)vertices.push(vertices[0].clone());
            sky.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(vertices),new THREE.LineBasicMaterial({color,transparent:true,opacity:key==='nominal'?1:.5,depthTest:false})));
          }
          for(const [body,color] of [['sun','#f6c469'],['earth','#7ed9d0']]){
            const direction=vector(skyDirection(sample[body+'Az'],sample[body+'El'],current,mesh.reference));
            const pos=direction.clone().multiplyScalar(10000).add(eye);
            const radius=10000*Math.tan((sample[body+'AngularRadiusDeg']||.25)*Math.PI/180);
            const bodyMesh=new THREE.Mesh(new THREE.SphereGeometry(radius,20,12),new THREE.MeshBasicMaterial({color,depthTest:false}));
            bodyMesh.position.copy(pos);bodyMesh.renderOrder=2;sky.add(bodyMesh);projected.push({id:body,position:pos});
          }
          light.position.copy(eye).add(vector(skyDirection(sample.sunAz,sample.sunEl,current,mesh.reference)).multiplyScalar(10000));light.target.position.copy(eye);
        }else{light.position.set(-4000,6000,3000);light.target.position.set(0,0,0);}
        controls.enabled=view==='orbit';
        if(view!=='orbit'){
          camera.up.copy(vector(skyDirection(0,90,current,mesh.reference)));
          camera.position.copy(eye);
          const dir=sample&&view!=='north'?skyDirection(sample[view+'Az'],sample[view+'El'],current,mesh.reference):skyDirection(0,0,current,mesh.reference);
          camera.lookAt(eye.clone().add(vector(dir).multiplyScalar(1000)));
        }else if(context.reset){
          camera.up.set(0,1,0);controls.target.copy(eye);camera.position.copy(eye).add(new THREE.Vector3(3300,2900,3900));controls.update();
        }
        draw();
      }
      stage.current={update,reset:()=>{if(lastContext)update({...lastContext,view:'orbit',reset:true});}};
      stage.current.update({points,current,sample,scenario,view,request,reset:true});
      return()=>{disposed=true;stage.current=null;observer.disconnect();controls.dispose();renderer.domElement.removeEventListener('webglcontextlost',onLost);disposeGroup(scene);renderer.dispose();renderer.domElement.remove();};
    }catch(e){setError('3D terrain could not start on this device. NASA maps and the numerical horizon remain available.');observer?.disconnect();controls?.dispose();disposeGroup(scene);renderer?.dispose();renderer?.domElement.remove();}
  },[mesh]);
  const previous=useRef({point:null,view:null});
  useEffect(()=>{
    const reset=view==='orbit'&&(previous.current.view!=='orbit'||previous.current.point!==current);
    stage.current?.update({points,current,sample,scenario,view,request,reset});previous.current={point:current,view};
  },[mesh,point,candidates,scenario,index,request,view]);
  return <div className="terrain-stage">
    <div className="terrain-view-tools" role="group" aria-label="3D camera view">
      <button aria-pressed={view==='orbit'} onClick={()=>{setView('orbit');stage.current?.reset();}}>Orbit terrain</button>
      <button disabled={!scenario} aria-pressed={view==='sun'} onClick={()=>setView('sun')}>Look toward Sun</button>
      <button disabled={!scenario} aria-pressed={view==='earth'} onClick={()=>setView('earth')}>Look toward Earth</button>
      <button aria-pressed={view==='north'} onClick={()=>setView('north')}>Look north</button>
    </div>
    <div className="terrain-canvas" ref={host}>
      {!mesh&&!error&&<p className="terrain-loading" role="status">Loading verified NASA elevation mesh…</p>}
      {points.map(item=><button ref={el=>{labels.current[item.id]=el;}} hidden key={item.id} className="terrain-site-label" aria-label={`Focus ${item.id==='O'?'original point':item.id} in terrain view`} onClick={()=>onSelect(item.id)}>{item.id}</button>)}
      {['sun','earth'].map(body=><span key={body} hidden ref={el=>{labels.current[body]=el;}} className={`terrain-sky-label ${body}`}>{body.toUpperCase()} · {sample?.[body+'State']}</span>)}
      <div className="terrain-corner">CONNECTING RIDGE<br/><span>TRUE VERTICAL SCALE · 5 KM STUDY</span></div>
      <div className="terrain-instructions">{view==='orbit'?'Drag to orbit · scroll or pinch to zoom':'Surface observer · fixed direction'}</div>
    </div>
    {error&&<div className="terrain-fallback" role="status"><p>{error}</p><button onClick={onMaps}>Open NASA maps →</button></div>}
    <p className="terrain-disclosure">5 m elevation source · {mesh?.displaySpacingM||50} m display spacing · no vertical exaggeration. Shading is illustrative. {scenario?'Pink: computed angular horizon; muted curves: sensitivity. Sky guides use a schematic radius, with directions from the selected surface observer. The horizon uses terrain out to 300 km beyond this mesh.':'Run a study to add the computed horizon and date-specific Sun/Earth directions.'} Analysis uses full-resolution source data, independently of this view.</p>
  </div>;
}
