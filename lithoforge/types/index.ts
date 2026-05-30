export type ShapeId =
  | 'heart'
  | 'circle'
  | 'square'
  | 'rectangle'
  | 'hexagon'
  | 'oval'
  | 'text_mom'
  | 'text_dad'
  | 'text_love'
  | 'text_family'
  | 'text_baby'
  | 'text_custom';

export interface ShapeDefinition {
  id: ShapeId;
  label: string;
  category: 'geometric' | 'text';
  aspectRatio: number; // width / height
  generatePath: (width: number, height: number) => string;
}

export interface PreprocessingSettings {
  brightness: number;   // -100 to 100
  contrast: number;     // -100 to 100
  gamma: number;        // 0.1 to 3.0
  invert: boolean;
}

export interface LithophaneSettings {
  minThickness: number;  // mm, default 0.8
  maxThickness: number;  // mm, default 3.0
  plateWidth: number;    // mm, default 100
  plateHeight: number;   // mm, default 100
  borderWidth: number;   // mm, default 3
  resolution: number;    // pixels per mm for heightmap, default 2
}

export interface PlacedShape {
  id: string;
  shapeId: ShapeId;
  customText?: string;
  x: number;        // mm from plate center
  y: number;        // mm from plate center
  width: number;    // mm
  height: number;   // mm
  rotation: number; // degrees
  imageId?: string; // which uploaded image fills this shape
}

export interface UploadedImage {
  id: string;
  name: string;
  dataUrl: string;         // original
  processedDataUrl: string; // after preprocessing
  width: number;
  height: number;
}

export interface Project {
  id: string;
  name: string;
  createdAt: string;
  updatedAt: string;
  images: UploadedImage[];
  preprocessing: PreprocessingSettings;
  lithophane: LithophaneSettings;
  shapes: PlacedShape[];
  customText: string;
  activeShapeId: ShapeId;
}

export interface HeightmapData {
  width: number;
  height: number;
  data: Float32Array; // normalized 0-1
}

export interface Vec3 {
  x: number;
  y: number;
  z: number;
}

export interface Triangle {
  a: Vec3;
  b: Vec3;
  c: Vec3;
  normal: Vec3;
}
