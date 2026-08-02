'use client';

import React, { useState } from 'react';
import dynamic from 'next/dynamic';
import { PhotoUpload } from '@/components/editor/PhotoUpload';
import { PreprocessingPanel } from '@/components/editor/PreprocessingPanel';
import { ShapeLibrary } from '@/components/shapes/ShapeLibrary';
import { LithophaneSettings } from '@/components/editor/LithophaneSettings';
import { GenerateButton } from '@/components/lithophane/GenerateButton';
import { useLithoStore } from '@/lib/store';
import { Separator } from '@/components/ui/separator';
import { Input } from '@/components/ui/input';
import type { Triangle } from '@/types';
import { Save } from 'lucide-react';
import { Button } from '@/components/ui/button';

// Three.js must be loaded client-side only
const ThreePreview = dynamic(
  () => import('@/components/lithophane/ThreePreview').then((m) => m.ThreePreview),
  { ssr: false, loading: () => <div className="w-full h-full min-h-[300px] rounded-lg bg-zinc-900 animate-pulse" /> }
);

export default function HomePage() {
  const { currentProject, setProjectName, saveProject } = useLithoStore();
  const [mesh, setMesh] = useState<Triangle[] | null>(null);

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      {/* Left sidebar */}
      <aside className="w-72 flex-shrink-0 border-r border-border overflow-y-auto bg-card">
        <div className="p-4 space-y-5">
          {/* Header */}
          <div>
            <h1 className="text-lg font-bold tracking-tight">LithoForge</h1>
            <p className="text-xs text-muted-foreground">3D Lithophane Generator</p>
          </div>

          {/* Project name */}
          <div className="flex gap-1.5">
            <Input
              value={currentProject.name}
              onChange={(e) => setProjectName(e.target.value)}
              className="h-8 text-sm flex-1"
              placeholder="Project name…"
            />
            <Button variant="outline" size="sm" className="h-8 px-2" onClick={saveProject}>
              <Save className="h-3.5 w-3.5" />
            </Button>
          </div>

          <Separator />

          {/* Photo upload */}
          <section>
            <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
              Photo
            </h2>
            <PhotoUpload />
          </section>

          <Separator />

          {/* Image preprocessing */}
          <section>
            <PreprocessingPanel />
          </section>

          <Separator />

          {/* Shape selection */}
          <section>
            <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
              Shape
            </h2>
            <ShapeLibrary />
          </section>

          <Separator />

          {/* Lithophane settings */}
          <section>
            <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
              Print Settings
            </h2>
            <LithophaneSettings />
          </section>

          <Separator />

          {/* Generate + export */}
          <section>
            <GenerateButton onMeshReady={setMesh} />
          </section>
        </div>
      </aside>

      {/* Main preview area */}
      <main className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 p-4">
          <ThreePreview triangles={mesh} />
        </div>

        {/* Status bar */}
        <div className="border-t border-border px-4 py-2 flex items-center gap-4 text-xs text-muted-foreground">
          <span>
            Shape: <span className="text-foreground font-medium">{currentProject.activeShapeId}</span>
          </span>
          <span>
            Plate: <span className="text-foreground font-medium">
              {currentProject.lithophane.plateWidth}×{currentProject.lithophane.plateHeight}mm
            </span>
          </span>
          {mesh && (
            <span>
              Mesh: <span className="text-foreground font-medium">{mesh.length.toLocaleString()} triangles</span>
            </span>
          )}
          <span className="ml-auto">
            LithoForge v0.1.0
          </span>
        </div>
      </main>
    </div>
  );
}
