/** Export utilities */
import {state} from './state.js';

export function exportJSON(){
  const data=JSON.stringify(state);
  download('pallet.json',data,'application/json');
}

export function exportSVG(){
  const svg=document.getElementById('canvas').outerHTML;
  download('layer.svg',svg,'image/svg+xml');
}

function download(name,data,type){
  const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([data],{type}));
  a.download=name;a.click();
}
