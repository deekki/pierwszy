export interface Dimensions {
  length: number;
  width: number;
  maxLoadHeight: number;
  height?: number;
}

export interface ProductDimensions {
  length: number;
  width: number;
  height: number;
  weight: number;
}

export interface PatternItem {
  x: number;
  y: number;
  r: number;
  g?: number;
  f?: number;
}

export interface LayerType {
  name: string;
  class: 'layer' | 'separator';
  height?: number;
  pattern?: PatternItem[];
  altPattern?: PatternItem[];
  approach?: string;
  altApproach?: string;
}

export interface GuiSettings {
  PPB_VERSION_NO: string;
  altLayout?: string;
}

export interface PalletProject {
  name: string;
  description?: string;
  dimensions: Dimensions;
  productDimensions: ProductDimensions;
  maxGrip: number;
  maxGripAuto?: number;
  labelOrientation?: string;
  guiSettings: GuiSettings;
  layerTypes: LayerType[];
  layers: string[];
}
