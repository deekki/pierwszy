import { PalletProject, LayerType } from './models';

export function loadProject(data: string): PalletProject {
  const obj = JSON.parse(data);
  if (!obj.guiSettings || obj.guiSettings.PPB_VERSION_NO !== '3.1.1') {
    throw new Error('Unsupported PPB version');
  }

  function assertNumber(v: any, name: string) {
    if (typeof v !== 'number' || Number.isNaN(v)) {
      throw new Error(`Invalid number for ${name}`);
    }
  }

  const dims = obj.dimensions;
  assertNumber(dims.length, 'dimensions.length');
  assertNumber(dims.width, 'dimensions.width');
  assertNumber(dims.maxLoadHeight, 'dimensions.maxLoadHeight');

  const prod = obj.productDimensions;
  assertNumber(prod.length, 'productDimensions.length');
  assertNumber(prod.width, 'productDimensions.width');
  assertNumber(prod.height, 'productDimensions.height');
  assertNumber(prod.weight, 'productDimensions.weight');

  if (!Array.isArray(obj.layerTypes) || !Array.isArray(obj.layers)) {
    throw new Error('Invalid layer definitions');
  }

  const layerNames = new Set<string>(obj.layerTypes.map((lt: LayerType) => lt.name));
  for (const name of obj.layers) {
    if (!layerNames.has(name)) {
      throw new Error(`Layer reference ${name} not found`);
    }
  }

  return obj as PalletProject;
}

export function saveProject(project: PalletProject): string {
  if (project.guiSettings.PPB_VERSION_NO !== '3.1.1') {
    project.guiSettings.PPB_VERSION_NO = '3.1.1';
  }
  return JSON.stringify(project, null, 2);
}
