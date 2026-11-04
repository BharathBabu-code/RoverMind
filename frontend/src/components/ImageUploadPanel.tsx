import React, { useRef, useState } from 'react';
import { UploadCloud, Image as ImageIcon, Sparkles, AlertCircle, RefreshCw, X } from 'lucide-react';
import { ImageMetadata } from '../types/api';
import { uploadRoverImage, loadSampleRoverImage } from '../services/api';

interface ImageUploadPanelProps {
  isOpen: boolean;
  onClose: () => void;
  onImageSelected: (metadata: ImageMetadata) => void;
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
  const [dragActive, setDragActive] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const file = files[0];

    setErrorMsg(null);
    setIsLoading(true);

    try {
      const response = await uploadRoverImage(file);
      onImageSelected(response.metadata);
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to process optical frame.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLoadSample = async () => {
    setErrorMsg(null);
    setIsLoading(true);
    try {
      const response = await loadSampleRoverImage();
      onImageSelected(response.metadata);
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load sample image.');
    } finally {
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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
      <div className="hud-panel max-w-xl w-full border-mars-700 shadow-2xl">
        {/* Header */}
        <div className="hud-panel-header">
          <div className="flex items-center gap-2">
            <ImageIcon className="w-4 h-4 text-mars-rust" />
            <h3 className="font-display font-bold text-sm tracking-wide text-white uppercase">
              Ingest Rover Optical Payload
            </h3>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          {errorMsg && (
            <div className="p-3 rounded bg-red-950/60 border border-red-500/40 text-red-200 text-xs font-mono flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0 text-red-400" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Drag & Drop Area */}
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
            className={`border-2 border-dashed rounded-lg p-8 flex flex-col items-center justify-center text-center cursor-pointer transition-all ${
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

            <div className="w-14 h-14 rounded-full bg-mars-850 flex items-center justify-center text-mars-rust mb-3 border border-mars-750 shadow-inner">
              {isLoading ? (
                <RefreshCw className="w-7 h-7 animate-spin text-mars-glow" />
              ) : (
                <UploadCloud className="w-7 h-7" />
              )}
            </div>

            <p className="font-display font-semibold text-sm text-slate-100">
              {isLoading ? 'Verifying & Ingesting Frame...' : 'Click to Browse or Drag Image Here'}
            </p>
            <p className="text-xs text-slate-400 mt-1 font-mono">
              Accepts PNG or JPEG • Max 20MB • Max 8192×8192 px
            </p>
            <p className="text-[11px] text-slate-500 mt-2 font-mono">
              Two-pass Pillow header verification ensures payload integrity
            </p>
          </div>

          {/* Alternative Quick Action: Load Authentic Sample */}
          <div className="pt-2 flex items-center justify-between border-t border-mars-800">
            <span className="text-xs font-mono text-slate-400">
              Don't have a rover image file ready?
            </span>
            <button
              onClick={handleLoadSample}
              disabled={isLoading}
              className="btn-secondary text-xs flex items-center gap-1.5"
            >
              <Sparkles className="w-3.5 h-3.5 text-mars-amber" />
              Load Sample (1648×1200)
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
