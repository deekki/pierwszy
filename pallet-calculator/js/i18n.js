/** Simple i18n */
export const LANGS={'en':'English','pl':'Polski'};
export const strings={
  en:{packageData:'Package data',palletData:'Pallet data',width:'Width',length:'Length',height:'Height',weight:'Weight',preset:'Preset',loadingHeight:'Loading height',palletHeight:'Pallet height',calculate:'Calculate',clear:'Clear'},
  pl:{packageData:'Dane paczki',palletData:'Dane palety',width:'Szerokość',length:'Długość',height:'Wysokość',weight:'Waga',preset:'Preset',loadingHeight:'Maks. wysokość',palletHeight:'Wysokość palety',calculate:'Oblicz',clear:'Wyczyść'}
};

export function applyLang(lang){document.querySelectorAll('[data-i18n]').forEach(el=>{const key=el.getAttribute('data-i18n');el.textContent=strings[lang][key];});}
