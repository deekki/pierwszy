/** Simple application state with undo/redo */
import {PRESETS} from './presets.js';

const listeners = [];
export const state = {
  units: {length:'mm', weight:'kg'},
  package:{w:300,l:200,h:150,weight:2.5},
  pallet:{preset:'EU_1200x800',w:1200,l:800,h:144,loading:1200},
  layers:[],
  history:{past:[],future:[]}
};

export function subscribe(fn){listeners.push(fn);}
function notify(){listeners.forEach(fn=>fn());}

export function set(key,value){state[key]=value;notify();}
export function pushHistory(){state.history.past.push(JSON.stringify(state.layers));
  if(state.history.past.length>100)state.history.past.shift();
  state.history.future=[];
}
export function undo(){if(!state.history.past.length)return;state.history.future.push(JSON.stringify(state.layers));
  state.layers=JSON.parse(state.history.past.pop());notify();}
export function redo(){if(!state.history.future.length)return;state.history.past.push(JSON.stringify(state.layers));
  state.layers=JSON.parse(state.history.future.pop());notify();}

export function applyPreset(id){const p=PRESETS[id];state.pallet.preset=id;state.pallet.w=p.w;state.pallet.l=p.l;state.pallet.h=p.h;notify();}
