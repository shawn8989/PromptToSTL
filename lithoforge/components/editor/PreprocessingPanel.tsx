'use client';

import React, { useEffect, useCallback } from 'react';
import { useLithoStore } from '@/lib/store';
import { applyPreprocessing } from '@/lib/lithophane';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { RotateCcw } from 'lucide-react';

export function PreprocessingPanel() {
  const { currentProject, setPreprocessing, updateProcessedImage } = useLithoStore();
  const { images, preprocessing } = currentProject;

  const reprocessImages = useCallback(async () => {
    for (const img of images) {
      const image = new Image();
      await new Promise<void>((res) => { image.onload = () => res(); image.src = img.dataUrl; });
      const canvas = document.createElement('canvas');
      canvas.width = img.width;
      canvas.height = img.height;
      const ctx = canvas.getContext('2d')!;
      ctx.drawImage(image, 0, 0);
      const imgData = ctx.getImageData(0, 0, img.width, img.height);
      applyPreprocessing(imgData.data, preprocessing);
      ctx.putImageData(imgData, 0, 0);
      updateProcessedImage(img.id, canvas.toDataURL('image/jpeg', 0.92));
    }
  }, [images, preprocessing, updateProcessedImage]);

  // Re-process whenever preprocessing settings change
  useEffect(() => {
    if (images.length > 0) {
      reprocessImages();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [preprocessing]);

  const reset = () => {
    setPreprocessing({ brightness: 0, contrast: 10, gamma: 1.0, invert: true });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium">Image Processing</p>
        <Button variant="ghost" size="sm" onClick={reset} className="h-7 px-2">
          <RotateCcw className="h-3 w-3 mr-1" /> Reset
        </Button>
      </div>

      <SliderField
        label="Brightness"
        value={preprocessing.brightness}
        min={-100}
        max={100}
        step={1}
        onChange={(v) => setPreprocessing({ brightness: v })}
        displayValue={`${preprocessing.brightness > 0 ? '+' : ''}${preprocessing.brightness}`}
      />

      <SliderField
        label="Contrast"
        value={preprocessing.contrast}
        min={-100}
        max={100}
        step={1}
        onChange={(v) => setPreprocessing({ contrast: v })}
        displayValue={`${preprocessing.contrast > 0 ? '+' : ''}${preprocessing.contrast}`}
      />

      <SliderField
        label="Gamma"
        value={preprocessing.gamma}
        min={0.1}
        max={3.0}
        step={0.05}
        onChange={(v) => setPreprocessing({ gamma: v })}
        displayValue={preprocessing.gamma.toFixed(2)}
      />

      <div className="flex items-center justify-between">
        <Label htmlFor="invert-toggle" className="text-sm">
          Invert
          <span className="text-xs text-muted-foreground ml-1">(recommended for lithophanes)</span>
        </Label>
        <Switch
          id="invert-toggle"
          checked={preprocessing.invert}
          onCheckedChange={(v) => setPreprocessing({ invert: v })}
        />
      </div>
    </div>
  );
}

function SliderField({
  label,
  value,
  min,
  max,
  step,
  onChange,
  displayValue,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
  displayValue: string;
}) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between">
        <Label className="text-xs">{label}</Label>
        <span className="text-xs tabular-nums text-muted-foreground">{displayValue}</span>
      </div>
      <Slider
        value={[value]}
        min={min}
        max={max}
        step={step}
        onValueChange={([v]) => onChange(v)}
        className="h-4"
      />
    </div>
  );
}
