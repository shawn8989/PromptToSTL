import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type {
  Project,
  PreprocessingSettings,
  LithophaneSettings,
  UploadedImage,
  ShapeId,
} from '@/types';

function generateId(): string {
  return Math.random().toString(36).slice(2, 10);
}

const DEFAULT_PREPROCESSING: PreprocessingSettings = {
  brightness: 0,
  contrast: 10,
  gamma: 1.0,
  invert: true, // lithophanes need inversion by default
};

const DEFAULT_LITHOPHANE: LithophaneSettings = {
  minThickness: 0.8,
  maxThickness: 3.0,
  plateWidth: 100,
  plateHeight: 100,
  borderWidth: 3,
  resolution: 2,
};

function createNewProject(name = 'Untitled Lithophane'): Project {
  return {
    id: generateId(),
    name,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    images: [],
    preprocessing: { ...DEFAULT_PREPROCESSING },
    lithophane: { ...DEFAULT_LITHOPHANE },
    shapes: [],
    customText: '',
    activeShapeId: 'heart',
  };
}

interface LithoForgeState {
  currentProject: Project;
  savedProjects: Project[];
  isGenerating: boolean;
  generationProgress: number;
  previewMode: 'solid' | 'backlit';

  // Project actions
  newProject: (name?: string) => void;
  saveProject: () => void;
  loadProject: (id: string) => void;
  deleteProject: (id: string) => void;
  setProjectName: (name: string) => void;

  // Image actions
  addImage: (image: UploadedImage) => void;
  removeImage: (id: string) => void;
  updateProcessedImage: (id: string, dataUrl: string) => void;

  // Settings actions
  setPreprocessing: (settings: Partial<PreprocessingSettings>) => void;
  setLithophane: (settings: Partial<LithophaneSettings>) => void;
  setActiveShape: (id: ShapeId) => void;
  setCustomText: (text: string) => void;

  // Generation state
  setGenerating: (v: boolean, progress?: number) => void;
  setPreviewMode: (mode: 'solid' | 'backlit') => void;
}

export const useLithoStore = create<LithoForgeState>()(
  persist(
    (set, get) => ({
      currentProject: createNewProject(),
      savedProjects: [],
      isGenerating: false,
      generationProgress: 0,
      previewMode: 'solid',

      newProject: (name) => {
        set({ currentProject: createNewProject(name) });
      },

      saveProject: () => {
        const { currentProject, savedProjects } = get();
        const updated = {
          ...currentProject,
          updatedAt: new Date().toISOString(),
        };
        const existing = savedProjects.findIndex((p) => p.id === updated.id);
        const next =
          existing >= 0
            ? savedProjects.map((p, i) => (i === existing ? updated : p))
            : [...savedProjects, updated];
        set({ savedProjects: next, currentProject: updated });
      },

      loadProject: (id) => {
        const project = get().savedProjects.find((p) => p.id === id);
        if (project) set({ currentProject: { ...project } });
      },

      deleteProject: (id) => {
        set((s) => ({
          savedProjects: s.savedProjects.filter((p) => p.id !== id),
        }));
      },

      setProjectName: (name) => {
        set((s) => ({
          currentProject: { ...s.currentProject, name },
        }));
      },

      addImage: (image) => {
        set((s) => ({
          currentProject: {
            ...s.currentProject,
            images: [...s.currentProject.images, image],
          },
        }));
      },

      removeImage: (id) => {
        set((s) => ({
          currentProject: {
            ...s.currentProject,
            images: s.currentProject.images.filter((img) => img.id !== id),
          },
        }));
      },

      updateProcessedImage: (id, dataUrl) => {
        set((s) => ({
          currentProject: {
            ...s.currentProject,
            images: s.currentProject.images.map((img) =>
              img.id === id ? { ...img, processedDataUrl: dataUrl } : img
            ),
          },
        }));
      },

      setPreprocessing: (settings) => {
        set((s) => ({
          currentProject: {
            ...s.currentProject,
            preprocessing: { ...s.currentProject.preprocessing, ...settings },
          },
        }));
      },

      setLithophane: (settings) => {
        set((s) => ({
          currentProject: {
            ...s.currentProject,
            lithophane: { ...s.currentProject.lithophane, ...settings },
          },
        }));
      },

      setActiveShape: (id) => {
        set((s) => ({
          currentProject: { ...s.currentProject, activeShapeId: id },
        }));
      },

      setCustomText: (text) => {
        set((s) => ({
          currentProject: { ...s.currentProject, customText: text },
        }));
      },

      setGenerating: (v, progress = 0) => {
        set({ isGenerating: v, generationProgress: progress });
      },

      setPreviewMode: (mode) => {
        set({ previewMode: mode });
      },
    }),
    {
      name: 'lithoforge-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        savedProjects: state.savedProjects,
        currentProject: state.currentProject,
      }),
    }
  )
);
