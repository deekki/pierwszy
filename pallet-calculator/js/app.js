import {state,applyPreset,subscribe} from './state.js';
import {PRESETS} from './presets.js';
import {calculate} from './solver.js';
import {render} from './renderer.js';
import {exportJSON,exportSVG} from './export.js';
import {LANGS,applyLang} from './i18n.js';
import {mmToInch,inchToMm,kgToLb,lbToKg} from './units.js';

function init(){
  const presetSel=document.getElementById('pallet-preset');
  Object.entries(PRESETS).forEach(([id,p])=>{
    const opt=document.createElement('option');opt.value=id;opt.textContent=p.label;presetSel.appendChild(opt);
  });
  presetSel.value=state.pallet.preset;
  presetSel.addEventListener('change',()=>{
    applyPreset(presetSel.value);
    document.getElementById('custom-pallet').style.display=presetSel.value==='CUSTOM'?'block':'none';
  });
  document.getElementById('calc-btn').addEventListener('click',()=>{updateState();calculate();updateSummary();render();});
  document.getElementById('clear-btn').addEventListener('click',()=>{state.layers=[];render();updateSummary();});
  document.getElementById("export-json").addEventListener("click",exportJSON);
  document.getElementById("export-svg").addEventListener("click",exportSVG);

  const langSel=document.getElementById('lang-select');
  Object.entries(LANGS).forEach(([id,name])=>{const opt=document.createElement('option');opt.value=id;opt.textContent=name;langSel.appendChild(opt);});
  langSel.value='en';langSel.addEventListener('change',()=>applyLang(langSel.value));applyLang('en');
  document.getElementById('unit-toggle').addEventListener('change',toggleUnits);

  subscribe(()=>{updateInputs();});
  updateInputs();
  updateSummary();
  render();
}

function updateInputs(){const pkg=state.package;document.getElementById('pkg-width').value=pkg.w;document.getElementById('pkg-length').value=pkg.l;document.getElementById('pkg-height').value=pkg.h;document.getElementById('pkg-weight').value=pkg.weight;const pal=state.pallet;document.getElementById('pallet-width').value=pal.w;document.getElementById('pallet-length').value=pal.l;document.getElementById('loading-height').value=pal.loading;document.getElementById('pallet-height').value=pal.h;}

function updateState(){const pkg=state.package;pkg.w=parseFloat(document.getElementById('pkg-width').value);pkg.l=parseFloat(document.getElementById('pkg-length').value);pkg.h=parseFloat(document.getElementById('pkg-height').value);pkg.weight=parseFloat(document.getElementById('pkg-weight').value)||0;const pal=state.pallet;pal.loading=parseFloat(document.getElementById('loading-height').value);pal.h=parseFloat(document.getElementById('pallet-height').value);if(state.pallet.preset==='CUSTOM'){pal.w=parseFloat(document.getElementById('pallet-width').value);pal.l=parseFloat(document.getElementById('pallet-length').value);}}

function updateSummary(){const layer=state.layers[0];if(!layer){document.getElementById('summary').textContent='';return;} const itemsPerLayer=layer.items.length;const layers=state.layers.length;const total=itemsPerLayer*layers;const totalWeight=total*state.package.weight;const totalHeight=state.pallet.h+layers*state.package.h;document.getElementById('summary').textContent=`Items/layer: ${itemsPerLayer}, Total items: ${total}, Total weight: ${totalWeight.toFixed(2)}, Total height: ${totalHeight}`;}

function toggleUnits(e){const toInch=e.target.checked;const pkg=state.package;const pal=state.pallet; if(toInch && state.units.length==='mm'){pkg.w=mmToInch(pkg.w);pkg.l=mmToInch(pkg.l);pkg.h=mmToInch(pkg.h);pal.w=mmToInch(pal.w);pal.l=mmToInch(pal.l);pal.h=mmToInch(pal.h);pal.loading=mmToInch(pal.loading);state.units.length='in'; document.getElementById('unit-label').textContent='in/lbs'; pkg.weight=kgToLb(pkg.weight); state.units.weight='lb';}
  else if(!toInch && state.units.length==='in'){pkg.w=inchToMm(pkg.w);pkg.l=inchToMm(pkg.l);pkg.h=inchToMm(pkg.h);pal.w=inchToMm(pal.w);pal.l=inchToMm(pal.l);pal.h=inchToMm(pal.h);pal.loading=inchToMm(pal.loading);state.units.length='mm'; document.getElementById('unit-label').textContent='mm/kg'; pkg.weight=lbToKg(pkg.weight); state.units.weight='kg';}
  updateInputs();render();}

window.addEventListener('DOMContentLoaded',init);

