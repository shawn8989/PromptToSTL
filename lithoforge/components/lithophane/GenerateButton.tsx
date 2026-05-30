'use client';

import React, { useState } from 'react';
import { useLithoStore } from '@/lib/store';
import { imageDataToHeightmap, generateLithoMesh } from '@/lib/lithophane';
import { downloadSTL } from '@/lib/stl';
import { getImageData } from '@/lib/imageUtils';
import type { Triangle } from '@/types';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Download, Layers } from 'lucide-react';

interface GenerateButtonProps {
  onMeshReady: (triangles: Triangle[]) => void;
}

export function GenerateButton({ onMeshReady }: GenerateButtonProps) {
  const { currentProject, setGenerating, isGenerating, generationProgress } = useLithoStore();
  const { images, lithophane, activeShapeId, customText } = currentProject;
  const [lastMesh, setLastMesh] = useState<Triangle[] | null>(null);

  const image = images[0]; // use first image for now

  const handleGenerate = async () => {
    if (!image) return;
    setGenerating(true, 5);

    try {
      const { plateWidth, plateHeight, borderWidth, resolution } = lithophane;

      // Resolution: pixels per mm
      const hmW = Math.round((plateWidth - borderWidth * 2) * resolution);
      const hmH = Math.round((plateHeight - borderWidth * 2) * resolution);

      setGenerating(true, 15);

      // Get preprocessed image pixel data
      const imgData = await getImageData(image.processedDataUrl, hmW, hmH);

      setGenerating(true, 30);

      // Build heightmap
      const heightmap = imageDataToHeightmap(
        imgData.data,
        imgData.width,
        imgData.height,
        hmW,
        hmH
      );

      setGenerating(true, 60);

      // Generate triangulated mesh
      const triangles = generateLithoMesh({
        shapeId: activeShapeId,
        customText: activeShapeId === 'text_custom' ? customText : undefined,
        heightmap,
        settings: lithophane,
      });

      setGenerating(true, 90);

      setLastMesh(triangles);
      onMeshReady(triangles);

      setGenerating(false, 100);
    } catch (err) {
      console.error('Generation failed:', err);
      setGenerating(false, 0);
    }
  };

  const handleExport = () => {
    if (!lastMesh) return;
    const projectName = currentProject.name.replace(/\s+/g, '_').toLowerCase();
    const shapeName = activeShapeId.replace('text_', '');
    downloadSTL(lastMesh, `lithoforge_${projectName}_${shapeName}`);
  };

  const canGenerate = images.length > 0;

  return (
    <div className="space-y-2">
      <Button
        onClick={handleGenerate}
        disabled={!canGenerate || isGenerating}
        className="w-full"
        size="lg"
      >
        <Layers className="h-4 w-4 mr-2" />
        {isGenerating ? 'Generating…' : 'Generate Lithophane'}
      </Button>

      {isGenerating && (
        <Progress value={generationProgress} className="h-1.5" />
      )}

      {!canGenerate && (
        <p className="text-xs text-muted-foreground text-center">
          Upload an image first to generate
        </p>
      )}

      {lastMesh && !isGenerating && (
        <Button
          onClick={handleExport}
          variant="outline"
          className="w-full"
          size="sm"
        >
          <Download className="h-4 w-4 mr-2" />
          Export STL ({lastMesh.length.toLocaleString()} triangles)
        </Button>
      )}
    </div>
  );
}
