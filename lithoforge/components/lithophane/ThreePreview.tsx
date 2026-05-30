'use client';

import React, { useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import type { Triangle } from '@/types';
import { useLithoStore } from '@/lib/store';

interface PreviewMeshProps {
  triangles: Triangle[];
  mode: 'solid' | 'backlit';
}

function LithoMesh({ triangles, mode }: PreviewMeshProps) {
  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry();
    const positions = new Float32Array(triangles.length * 9);
    const normals = new Float32Array(triangles.length * 9);

    triangles.forEach((t, i) => {
      const base = i * 9;
      positions[base + 0] = t.a.x; positions[base + 1] = t.a.z; positions[base + 2] = -t.a.y;
      positions[base + 3] = t.b.x; positions[base + 4] = t.b.z; positions[base + 5] = -t.b.y;
      positions[base + 6] = t.c.x; positions[base + 7] = t.c.z; positions[base + 8] = -t.c.y;
      normals[base + 0] = t.normal.x; normals[base + 1] = t.normal.z; normals[base + 2] = -t.normal.y;
      normals[base + 3] = t.normal.x; normals[base + 4] = t.normal.z; normals[base + 5] = -t.normal.y;
      normals[base + 6] = t.normal.x; normals[base + 7] = t.normal.z; normals[base + 8] = -t.normal.y;
    });

    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geo.setAttribute('normal', new THREE.BufferAttribute(normals, 3));
    return geo;
  }, [triangles]);

  const material = useMemo(() => {
    if (mode === 'backlit') {
      return new THREE.MeshPhysicalMaterial({
        color: new THREE.Color(0xfff5e0),
        transparent: true,
        opacity: 0.85,
        roughness: 0.1,
        metalness: 0,
        transmission: 0.6,
        thickness: 3,
        side: THREE.DoubleSide,
      });
    }
    return new THREE.MeshStandardMaterial({
      color: new THREE.Color(0xf5f5f0),
      roughness: 0.4,
      metalness: 0.0,
      side: THREE.DoubleSide,
    });
  }, [mode]);

  return <mesh geometry={geometry} material={material} />;
}

function BacklitLight() {
  return (
    <>
      {/* Warm amber backlight from behind/below */}
      <pointLight position={[50, -30, -5]} intensity={8} color={new THREE.Color(0xffb347)} />
      <pointLight position={[50, 130, -5]} intensity={8} color={new THREE.Color(0xffb347)} />
      <ambientLight intensity={0.2} color={new THREE.Color(0xfff0d0)} />
    </>
  );
}

function SolidLight() {
  return (
    <>
      <ambientLight intensity={0.6} />
      <directionalLight position={[100, 200, 100]} intensity={1.2} castShadow />
      <directionalLight position={[-50, 100, -50]} intensity={0.4} />
    </>
  );
}

interface ThreePreviewProps {
  triangles: Triangle[] | null;
}

export function ThreePreview({ triangles }: ThreePreviewProps) {
  const { previewMode, setPreviewMode } = useLithoStore();

  return (
    <div className="relative w-full h-full min-h-[300px] rounded-lg overflow-hidden bg-zinc-900">
      <Canvas
        camera={{ position: [50, 80, 150], fov: 45 }}
        shadows
        gl={{ antialias: true }}
      >
        {previewMode === 'backlit' ? <BacklitLight /> : <SolidLight />}
        <OrbitControls makeDefault enableDamping dampingFactor={0.08} />

        {triangles && triangles.length > 0 ? (
          <LithoMesh triangles={triangles} mode={previewMode} />
        ) : (
          <EmptyState />
        )}

        {previewMode === 'solid' && (
          <gridHelper args={[200, 20, '#555', '#888']} position={[50, 0, -50]} />
        )}
      </Canvas>

      {/* Mode toggle overlay */}
      <div className="absolute top-2 right-2 flex gap-1">
        <button
          onClick={() => setPreviewMode('solid')}
          className={`px-2 py-1 text-xs rounded ${previewMode === 'solid' ? 'bg-white text-black' : 'bg-white/20 text-white'}`}
        >
          Solid
        </button>
        <button
          onClick={() => setPreviewMode('backlit')}
          className={`px-2 py-1 text-xs rounded ${previewMode === 'backlit' ? 'bg-amber-400 text-black' : 'bg-white/20 text-white'}`}
        >
          Backlit
        </button>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <mesh position={[50, 0, -50]}>
      <boxGeometry args={[100, 1, 100]} />
      <meshStandardMaterial color="#333" roughness={0.8} />
    </mesh>
  );
}
