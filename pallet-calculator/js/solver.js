/** Simple grid solver */
import {state,pushHistory} from './state.js';

export function calculate(){
  const {package:pkg,pallet}=state;
  if(pkg.w<=0||pkg.l<=0) return [];
  const orientations=[{w:pkg.w,l:pkg.l,rot:0},{w:pkg.l,l:pkg.w,rot:90}];
  let best={count:0,orient:null};
  orientations.forEach(o=>{
    const cols=Math.floor(pallet.w/o.w);
    const rows=Math.floor(pallet.l/o.l);
    const count=cols*rows;
    if(count>best.count)best={count,orient:o};
  });
  if(!best.orient)return [];
  const cols=Math.floor(pallet.w/best.orient.w);
  const rows=Math.floor(pallet.l/best.orient.l);
  const items=[];
  for(let y=0;y<rows;y++){
    for(let x=0;x<cols;x++){
      items.push({x:x*best.orient.w,y:y*best.orient.l,w:best.orient.w,l:best.orient.l,rot:best.orient.rot,id:Date.now()+items.length});
    }
  }
  const layers=Math.floor((pallet.loading - pallet.h) / pkg.h);
  state.layers=[{items}];
  state.layers.length=layers;
  for(let i=1;i<layers;i++) state.layers[i]={items:JSON.parse(JSON.stringify(items))};
  pushHistory();
  return items;
}
