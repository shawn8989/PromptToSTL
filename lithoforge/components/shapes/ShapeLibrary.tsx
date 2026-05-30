'use client';

import React from 'react';
import { useLithoStore } from '@/lib/store';
import { getGeometricShapes, getTextShapes } from '@/lib/shapes';
import type { ShapeId } from '@/types';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';

export function ShapeLibrary() {
  const { currentProject, setActiveShape, setCustomText } = useLithoStore();
  const { activeShapeId, customText } = currentProject;
  const geometricShapes = getGeometricShapes();
  const textShapes = getTextShapes();

  return (
    <div className="space-y-3">
      <div>
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
          Geometric
        </p>
        <div className="grid grid-cols-3 gap-1.5">
          {geometricShapes.map((shape) => (
            <ShapeButton
              key={shape.id}
              id={shape.id}
              label={shape.label}
              active={activeShapeId === shape.id}
              onClick={() => setActiveShape(shape.id as ShapeId)}
            />
          ))}
        </div>
      </div>

      <div>
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
          Text Frames
        </p>
        <div className="grid grid-cols-3 gap-1.5">
          {textShapes.filter((s) => s.id !== 'text_custom').map((shape) => (
            <ShapeButton
              key={shape.id}
              id={shape.id}
              label={shape.label}
              active={activeShapeId === shape.id}
              onClick={() => setActiveShape(shape.id as ShapeId)}
            />
          ))}
        </div>
      </div>

      <div>
        <ShapeButton
          id="text_custom"
          label="Custom Text"
          active={activeShapeId === 'text_custom'}
          onClick={() => setActiveShape('text_custom')}
          fullWidth
        />
        {activeShapeId === 'text_custom' && (
          <div className="mt-2 space-y-1">
            <Label htmlFor="custom-text" className="text-xs">
              Your text (uppercase recommended)
            </Label>
            <Input
              id="custom-text"
              value={customText}
              onChange={(e) => setCustomText(e.target.value.toUpperCase())}
              placeholder="e.g. GRACE"
              maxLength={12}
              className="h-8 text-sm font-bold tracking-widest"
            />
          </div>
        )}
      </div>
    </div>
  );
}

function ShapeButton({
  label,
  active,
  onClick,
  fullWidth = false,
}: {
  id?: string;
  label: string;
  active: boolean;
  onClick: () => void;
  fullWidth?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'px-2 py-2 rounded-md text-xs font-medium border transition-all',
        fullWidth ? 'w-full col-span-3' : '',
        active
          ? 'bg-primary text-primary-foreground border-primary shadow-sm'
          : 'bg-background border-border hover:border-primary/50 hover:bg-muted'
      )}
    >
      {label}
    </button>
  );
}
