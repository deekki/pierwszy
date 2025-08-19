/** SVG rendering and interactions */
import {state} from './state.js';
import {moveItem,rotateItem,removeItem,collides} from './layout.js';

const svg=document.getElementById('canvas');
let currentLayer=0;

export function render(){
  svg.innerHTML='';
  const p=state.pallet;
  svg.setAttribute('viewBox',`0 0 ${p.w} ${p.l}`);
  const palletRect=document.createElementNS('http://www.w3.org/2000/svg','rect');
  palletRect.setAttribute('width',p.w);palletRect.setAttribute('height',p.l);palletRect.setAttribute('fill','#ddd');
  palletRect.setAttribute('stroke','#999');
  svg.appendChild(palletRect);
  if(!state.layers[currentLayer]) return;
  state.layers[currentLayer].items.forEach(item=>{
    const r=document.createElementNS('http://www.w3.org/2000/svg','rect');
    r.classList.add('box');
    r.setAttribute('x',item.x);r.setAttribute('y',item.y);r.setAttribute('width',item.w);r.setAttribute('height',item.l);
    r.addEventListener('mousedown',evt=>startDrag(evt,item));
    r.addEventListener('dblclick',()=>{rotateItem(currentLayer,item.id);render();});
    r.addEventListener('contextmenu',evt=>{evt.preventDefault();removeItem(currentLayer,item.id);render();});
    svg.appendChild(r);
  });
}

let drag=null;
function startDrag(evt,item){drag={item,startX:evt.clientX,startY:evt.clientY};}
svg.addEventListener('mousemove',evt=>{
  if(!drag)return;const dx=evt.clientX-drag.startX;const dy=evt.clientY-drag.startY;drag.startX=evt.clientX;drag.startY=evt.clientY;
  if(moveItem(currentLayer,drag.item.id,dx,dy)) render();
});
svg.addEventListener('mouseup',()=>{drag=null;});
svg.addEventListener('mouseleave',()=>{drag=null;});

export function setLayer(i){currentLayer=i;render();}
