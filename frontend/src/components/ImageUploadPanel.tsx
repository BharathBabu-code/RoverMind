import React, { useRef, useState, useEffect } from 'react';
import {
  UploadCloud,
  Sparkles,
  AlertCircle,
  RefreshCw,
  X,
  Layers,
  Camera
} from 'lucide-react';
import { ImageMetadata, GalleryItem } from '../types/api';
import { uploadRoverImage, fetchGalleryItems, loadGalleryImage } from '../services/api';

interface ImageUploadPanelProps {
  isOpen: boolean;
  onClose: () => void;
  onImageSelected: (metadata: ImageMetadata) => Promise<void> | void;
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
}

export const ImageUploadPanel: React.FC<ImageUploadPanelProps> = ({
  isOpen,
  onClose,
  onImageSelected,
  isLoading,
  setIsLoading,
}) => {
  const [activeTab, setActiveTab] = useState<'gallery' | 'upload'>('gallery');
  const [galleryItems, setGalleryItems] = useState<GalleryItem[]>([]);
  const [isGalleryLoading, setIsGalleryLoading] = useState(false);
  const [selectedGalleryId, setSelectedGalleryId] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Fetch pre-loaded Mars gallery items when modal opens
  useEffect(() => {
    if (isOpen) {
      setErrorMsg(null);
      setIsGalleryLoading(true);
      fetchGalleryItems()
        .then((items) => {
          setGalleryItems(items);
          if (items.length > 0 && !selectedGalleryId) {
            setSelectedGalleryId(items[0].id);
          }
        })
        .catch((err) => {
          console.warn('Failed to load gallery items:', err);
        })
        .finally(() => setIsGalleryLoading(false));
    }
  }, [isOpen]);

  if (!isOpen) return null;

  // Handle custom file upload from device
  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const file = files[0];

    setErrorMsg(null);
    setIsLoading(true);

    try {
      const response = await uploadRoverImage(file);
      onClose();
      await onImageSelected(response.metadata);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to process optical frame.');
      setIsLoading(false);
    }
  };

  // Handle loading a selected gallery image
  const handleSelectGalleryItem = async (galleryId: string) => {
    setErrorMsg(null);
    setSelectedGalleryId(galleryId);
    setIsLoading(true);
    try {
      const response = await loadGalleryImage(galleryId);
      onClose();
      await onImageSelected(response.metadata);
    } catch (err: any) {
      setErrorMsg(err.message || `Failed to load gallery frame '${galleryId}'.`);
      setIsLoading(false);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFiles(e.dataTransfer.files);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md">
      <div className="hud-panel max-w-3xl w-full border-mars-700 shadow-2xl flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="hud-panel-header flex items-center justify-between border-b border-mars-800 p-4">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded bg-mars-900 border border-mars-750 flex items-center justify-center text-mars-rust">
              <Camera className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-display font-bold text-sm tracking-wide text-white uppercase">
                Ingest Mars Surface Imagery
              </h3>
              <p className="font-mono text-[10px] text-slate-400">
                Select an authentic pre-downloaded rover frame or upload custom imagery from your device
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors p-1"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Selection */}
        <div className="px-6 pt-4 pb-2 flex gap-3 border-b border-mars-850 bg-mars-950/60">
          <button
            onClick={() => setActiveTab('gallery')}
            className={`flex items-center gap-2 px-4 py-2 rounded-t font-mono text-xs uppercase tracking-wider transition-all border-b-2 ${
              activeTab === 'gallery'
                ? 'border-mars-rust text-white bg-mars-900/80 font-bold'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-mars-900/40'
            }`}
          >
            <Layers className="w-3.5 h-3.5 text-mars-amber" />
            <span>Mars Rover Gallery ({galleryItems.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('upload')}
            className={`flex items-center gap-2 px-4 py-2 rounded-t font-mono text-xs uppercase tracking-wider transition-all border-b-2 ${
              activeTab === 'upload'
                ? 'border-mars-rust text-white bg-mars-900/80 font-bold'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-mars-900/40'
            }`}
          >
            <UploadCloud className="w-3.5 h-3.5 text-mars-rust" />
            <span>Upload From Device</span>
          </button>
        </div>

        {/* Content Area */}
        <div className="p-6 overflow-y-auto space-y-4 flex-1">
          {errorMsg && (
            <div className="p-3 rounded bg-red-950/60 border border-red-500/40 text-red-200 text-xs font-mono flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0 text-red-400" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* TAB 1: PRE-DOWNLOADED GALLERY */}
          {activeTab === 'gallery' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs font-mono text-slate-400 pb-1">
                <span>Authentic Mars surface frames captured by NASA Perseverance Navcam/Hazcam:</span>
                {isGalleryLoading && (
                  <span className="flex items-center gap-1 text-mars-copper">
                    <RefreshCw className="w-3 h-3 animate-spin" /> Fetching gallery...
                  </span>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {galleryItems.map((item) => {
                  const isSelected = selectedGalleryId === item.id;
                  return (
                    <div
                      key={item.id}
                      onClick={() => handleSelectGalleryItem(item.id)}
                      className={`group relative rounded-lg border p-3.5 cursor-pointer transition-all flex flex-col justify-between ${
                        isSelected
                          ? 'border-mars-rust bg-mars-900/90 shadow-[0_0_20px_rgba(234,88,12,0.25)]'
                          : 'border-mars-800 bg-mars-950/60 hover:border-mars-700 hover:bg-mars-900/40'
                      }`}
                    >
                      <div className="space-y-2">
                        {/* Thumbnail Viewport */}
                        <div className="relative w-full h-36 rounded overflow-hidden bg-black/60 border border-mars-850">
                          <img
                            src={item.preview_url}
                            alt={item.title}
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                            loading="lazy"
                          />
                          <div className="absolute top-2 left-2 px-2 py-0.5 rounded bg-black/75 backdrop-blur-sm border border-mars-800 text-[10px] font-mono text-mars-copper">
                            Sol {item.sol} • {item.camera.split(' ')[0]}
                          </div>
                          <div className="absolute bottom-2 right-2 px-2 py-0.5 rounded bg-black/75 backdrop-blur-sm border border-mars-800 text-[10px] font-mono text-slate-300">
                            {item.width}×{item.height} px
                          </div>
                        </div>

                        {/* Title & Metadata */}
                        <div>
                          <div className="flex items-center justify-between">
                            <h4 className="font-display font-bold text-xs uppercase tracking-wide text-white group-hover:text-mars-copper transition-colors">
                              {item.title}
                            </h4>
                          </div>
                          <span className="text-[10px] font-mono text-mars-amber block mt-0.5">
                            {item.site} ({item.rover})
                          </span>
                        </div>

                        <p className="text-[11px] text-slate-400 font-mono line-clamp-2 leading-relaxed">
                          {item.description}
                        </p>
                      </div>

                      {/* Action Button */}
                      <div className="mt-3 pt-2 border-t border-mars-850 flex items-center justify-between">
                        <span className="text-[10px] font-mono text-slate-500">
                          {(item.file_size_bytes / (1024 * 1024)).toFixed(1)} MB PNG
                        </span>
                        <button
                          type="button"
                          disabled={isLoading}
                          className="btn-primary text-[11px] px-3 py-1 flex items-center gap-1.5"
                        >
                          {isLoading && isSelected ? (
                            <RefreshCw className="w-3 h-3 animate-spin text-white" />
                          ) : (
                            <Sparkles className="w-3 h-3 text-mars-amber" />
                          )}
                          <span>Select & Ingest</span>
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* TAB 2: DEVICE UPLOAD DROPZONE */}
          {activeTab === 'upload' && (
            <div className="space-y-4">
              <div
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => inputRef.current?.click()}
                className={`border-2 border-dashed rounded-lg p-10 flex flex-col items-center justify-center text-center cursor-pointer transition-all ${
                  dragActive
                    ? 'border-mars-rust bg-mars-rust/10 scale-[0.99]'
                    : 'border-mars-750 bg-mars-950/80 hover:border-mars-rust/70 hover:bg-mars-900'
                }`}
              >
                <input
                  ref={inputRef}
                  type="file"
                  accept="image/png,image/jpeg"
                  className="hidden"
                  onChange={(e) => handleFiles(e.target.files)}
                />

                <div className="w-16 h-16 rounded-full bg-mars-850 flex items-center justify-center text-mars-rust mb-3 border border-mars-750 shadow-inner">
                  {isLoading ? (
                    <RefreshCw className="w-8 h-8 animate-spin text-mars-glow" />
                  ) : (
                    <UploadCloud className="w-8 h-8" />
                  )}
                </div>

                <p className="font-display font-semibold text-sm text-slate-100">
                  {isLoading ? 'Verifying & Ingesting Frame...' : 'Click to Browse or Drag Image Here'}
                </p>
                <p className="text-xs text-slate-400 mt-1 font-mono">
                  Accepts PNG or JPEG • Max 20MB • Max 8192×8192 px
                </p>
                <p className="text-[11px] text-slate-500 mt-2 font-mono">
                  Two-pass Pillow header verification ensures payload safety against decompression bombs
                </p>
              </div>

              {/* Quick switch to gallery */}
              <div className="p-3 rounded bg-mars-900/60 border border-mars-800 flex items-center justify-between text-xs font-mono">
                <span className="text-slate-400">Want to test with pre-downloaded Mars rover photos?</span>
                <button
                  type="button"
                  onClick={() => setActiveTab('gallery')}
                  className="text-mars-copper hover:text-white flex items-center gap-1 font-semibold"
                >
                  <span>Open Mars Gallery ({galleryItems.length} frames)</span>
                  <Layers className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
