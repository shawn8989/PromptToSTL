'use client';

import React, { useCallback, useRef, useState } from 'react';
import { useLithoStore } from '@/lib/store';
import { resizeImage, readFileAsDataUrl } from '@/lib/imageUtils';
import { applyPreprocessing } from '@/lib/lithophane';
import { Upload, X, ImageIcon } from 'lucide-react';
import type { UploadedImage, PreprocessingSettings } from '@/types';

function generateId() {
  return Math.random().toString(36).slice(2, 10);
}

async function processAndStore(
  file: File,
  addImage: (image: UploadedImage) => void,
  preprocessing: PreprocessingSettings
) {
  const raw = await readFileAsDataUrl(file);
  const { dataUrl, width, height } = await resizeImage(raw, 1024);

  // Apply preprocessing to get the processed version
  const img = new Image();
  await new Promise<void>((res) => { img.onload = () => res(); img.src = dataUrl; });
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d')!;
  ctx.drawImage(img, 0, 0);
  const imgData = ctx.getImageData(0, 0, width, height);
  applyPreprocessing(imgData.data, preprocessing);
  ctx.putImageData(imgData, 0, 0);
  const processedDataUrl = canvas.toDataURL('image/jpeg', 0.92);

  addImage({
    id: generateId(),
    name: file.name,
    dataUrl,
    processedDataUrl,
    width,
    height,
  });
}

export function PhotoUpload() {
  const { currentProject, addImage, removeImage } = useLithoStore();
  const { images, preprocessing } = currentProject;
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(
    async (files: FileList | null) => {
      if (!files) return;
      const accepted = ['image/jpeg', 'image/png', 'image/heic', 'image/heif'];
      for (const file of Array.from(files)) {
        if (!accepted.includes(file.type) && !file.name.match(/\.(heic|heif)$/i)) continue;
        await processAndStore(file, addImage, preprocessing);
      }
    },
    [addImage, preprocessing]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      handleFiles(e.dataTransfer.files);
    },
    [handleFiles]
  );

  return (
    <div className="space-y-3">
      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={`
          border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors
          ${isDragging ? 'border-primary bg-primary/5' : 'border-muted-foreground/30 hover:border-primary/50'}
        `}
      >
        <Upload className="mx-auto h-8 w-8 text-muted-foreground mb-2" />
        <p className="text-sm text-muted-foreground">
          Drop a photo here or <span className="text-primary">click to browse</span>
        </p>
        <p className="text-xs text-muted-foreground/70 mt-1">JPG, PNG, HEIC — max 1024px</p>
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/heic,image/heif,.heic,.heif"
          multiple
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      {images.length > 0 && (
        <div className="grid grid-cols-2 gap-2">
          {images.map((img) => (
            <div key={img.id} className="relative group rounded-md overflow-hidden border border-border">
              {/* Show processed (grayscale+inverted) preview */}
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={img.processedDataUrl}
                alt={img.name}
                className="w-full h-24 object-cover"
              />
              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors" />
              <button
                onClick={(e) => { e.stopPropagation(); removeImage(img.id); }}
                className="absolute top-1 right-1 p-0.5 rounded-full bg-destructive text-destructive-foreground opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <X className="h-3 w-3" />
              </button>
              <div className="absolute bottom-0 left-0 right-0 px-1 py-0.5 bg-black/60 text-xs text-white truncate">
                {img.name}
              </div>
            </div>
          ))}
        </div>
      )}

      {images.length === 0 && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <ImageIcon className="h-3 w-3" />
          No image loaded — upload one to generate a lithophane
        </div>
      )}
    </div>
  );
}
