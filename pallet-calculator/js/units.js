/** Unit conversion helpers */
export const MM_PER_INCH = 25.4;
export const KG_PER_LB = 0.45359237;

export function mmToInch(mm){return mm / MM_PER_INCH;}
export function inchToMm(inch){return inch * MM_PER_INCH;}
export function kgToLb(kg){return kg / KG_PER_LB;}
export function lbToKg(lb){return lb * KG_PER_LB;}

export function format(value, unit){return Number(value.toFixed(2));}
