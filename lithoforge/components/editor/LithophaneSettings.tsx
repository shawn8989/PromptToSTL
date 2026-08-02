'use client';

import React from 'react';
import { useLithoStore } from '@/lib/store';
import { Slider } from '@/components/ui/slider';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';

export function LithophaneSettings() {
  const { currentProject, setLithophane } = useLithoStore();
  const s = currentProject.lithophane;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <Label className="text-xs">Plate Width (mm)</Label>
          <Input
            type="number"
            value={s.plateWidth}
            min={20}
            max={300}
            onChange={(e) => setLithophane({ plateWidth: Number(e.target.value) })}
            className="h-8 text-sm"
          />
        </div>
        <div className="space-y-1">
          <Label className="text-xs">Plate Height (mm)</Label>
          <Input
            type="number"
            value={s.plateHeight}
            min={20}
            max={300}
            onChange={(e) => setLithophane({ plateHeight: Number(e.target.value) })}
            className="h-8 text-sm"
          />
        </div>
      </div>

      <SliderField
        label={`Min thickness: ${s.minThickness.toFixed(1)} mm`}
        value={s.minThickness}
        min={0.4}
        max={1.5}
        step={0.1}
        onChange={(v) => setLithophane({ minThickness: v })}
      />

      <SliderField
        label={`Max thickness: ${s.maxThickness.toFixed(1)} mm`}
        value={s.maxThickness}
        min={1.5}
        max={5.0}
        step={0.1}
        onChange={(v) => setLithophane({ maxThickness: v })}
      />

      <SliderField
        label={`Border width: ${s.borderWidth.toFixed(1)} mm`}
        value={s.borderWidth}
        min={0}
        max={10}
        step={0.5}
        onChange={(v) => setLithophane({ borderWidth: v })}
      />
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
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
}) {
  return (
    <div className="space-y-1">
      <Label className="text-xs">{label}</Label>
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
