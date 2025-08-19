/** Layout utilities */
import {state,pushHistory} from './state.js';

export function snap(v,grid){return Math.round(v/grid)*grid;}

export function intersects(a,b){
  return !(a.x+a.w<=b.x || b.x+b.w<=a.x || a.y+a.l<=b.y || b.y+b.l<=a.y);
}

export function withinPallet(item){const p=state.pallet;return item.x>=0&&item.y>=0&&item.x+item.w<=p.w&&item.y+item.l<=p.l;}

export function moveItem(layerIndex,id,dx,dy){const item=state.layers[layerIndex].items.find(it=>it.id===id);if(!item||item.locked)return;item.x=snap(item.x+dx,1);item.y=snap(item.y+dy,1);if(!withinPallet(item))return false; if(collides(layerIndex,item))return false;pushHistory();return true;}
export function rotateItem(layerIndex,id){const item=state.layers[layerIndex].items.find(it=>it.id===id);if(!item||item.locked)return; [item.w,item.l]=[item.l,item.w];item.rot=(item.rot+90)%180;if(!withinPallet(item) || collides(layerIndex,item)) {[item.w,item.l]=[item.l,item.w];item.rot=(item.rot+90)%180;return false;} pushHistory();return true;}
export function collides(layerIndex,target){return state.layers[layerIndex].items.some(it=>it!==target && intersects(it,target));}
export function removeItem(layerIndex,id){const arr=state.layers[layerIndex].items;const i=arr.findIndex(it=>it.id===id);if(i>=0){arr.splice(i,1);pushHistory();}}
export function addItem(layerIndex,item){state.layers[layerIndex].items.push(item);pushHistory();}
