# LithoForge

A browser-based 3D lithophane generator. Upload a photo, pick a shape,
and export a print-ready STL in seconds.

## Quick Start

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Requirements

- Node.js 18+
- A modern browser (Chrome/Firefox/Safari — needs `OffscreenCanvas` for
  shape masking)

No server or external APIs required.

## Architecture

```
app/
  page.tsx          <- Main editor (Client Component)
  layout.tsx        <- Root layout + metadata
  pricing/          <- Stripe seam (stub)
  api/              <- Future server routes

components/
  editor/
    PhotoUpload.tsx          <- Drag-drop upload, preview
    PreprocessingPanel.tsx   <- Sliders for brightness/contrast/gamma/invert
    LithophaneSettings.tsx   <- Thickness, plate size, border controls
  shapes/
    ShapeLibrary.tsx         <- Shape picker grid
  lithophane/
    ThreePreview.tsx         <- React Three Fiber 3D viewer
    GenerateButton.tsx       <- Orchestrates generation -> preview -> export

lib/
  shapes.ts         <- SVG path generators for all shapes
  lithophane.ts     <- Heightmap extraction + mesh generation
  stl.ts            <- Binary STL writer
  store.ts          <- Zustand state (persisted to localStorage)
  imageUtils.ts     <- Canvas-based image helpers

types/
  index.ts          <- All shared TypeScript types

docs/
  lithophane-algorithm.md  <- Algorithm writeup
```

## Future Phases

| Phase | Feature | Seam |
|-------|---------|------|
| 2 | Multi-shape composition canvas | `components/editor/Canvas.tsx` |
| 3 | User auth | `lib/auth.ts` (Clerk/Supabase) |
| 4 | Stripe payments | `app/pricing/page.tsx` |
| 5 | Project sharing / gallery | `app/api/projects/` |

## Algorithm

See `docs/lithophane-algorithm.md` for a full writeup.

## Tech Stack

- **Next.js 14** App Router
- **TypeScript** strict mode
- **Tailwind CSS** + shadcn/ui components (manual install)
- **Three.js** + `@react-three/fiber` + `@react-three/drei`
- **Zustand** (persisted state)
- **opentype.js** (text -> SVG paths, used in Phase 2)
