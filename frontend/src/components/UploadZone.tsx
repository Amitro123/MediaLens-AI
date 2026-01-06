import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, Video, FileVideo, X, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface UploadZoneProps {
  onFileSelect: (file: File) => void;
  isProcessing?: boolean;
}

export const UploadZone = ({ onFileSelect, isProcessing = false }: UploadZoneProps) => {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const files = Array.from(e.dataTransfer.files);
    const videoFile = files.find(file => file.type.startsWith("video/"));
    
    if (videoFile) {
      setSelectedFile(videoFile);
      onFileSelect(videoFile);
    }
  }, [onFileSelect]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.type.startsWith("video/")) {
      setSelectedFile(file);
      onFileSelect(file);
    }
  }, [onFileSelect]);

  const clearFile = () => {
    setSelectedFile(null);
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className={cn(
        "relative border-2 border-dashed rounded-2xl p-8 md:p-12 transition-all duration-300",
        isDragging
          ? "border-primary bg-primary/5 shadow-glow"
          : "border-border hover:border-primary/50 hover:bg-card/50",
        isProcessing && "pointer-events-none opacity-80"
      )}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Background Glow */}
      <AnimatePresence>
        {isDragging && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 gradient-glow rounded-2xl"
          />
        )}
      </AnimatePresence>

      <div className="relative z-10 flex flex-col items-center text-center">
        <AnimatePresence mode="wait">
          {selectedFile ? (
            <motion.div
              key="file"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="flex flex-col items-center"
            >
              <div className="w-16 h-16 rounded-2xl bg-primary/10 border border-primary/30 flex items-center justify-center mb-4">
                <FileVideo className="w-8 h-8 text-primary" />
              </div>
              <p className="font-medium text-foreground mb-1">{selectedFile.name}</p>
              <p className="text-sm text-muted-foreground mb-4">
                {formatFileSize(selectedFile.size)}
              </p>
              {!isProcessing && (
                <Button variant="ghost" size="sm" onClick={clearFile}>
                  <X className="w-4 h-4 mr-1" />
                  Remove
                </Button>
              )}
            </motion.div>
          ) : (
            <motion.div
              key="upload"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="flex flex-col items-center"
            >
              <div className={cn(
                "w-20 h-20 rounded-2xl bg-secondary border border-border flex items-center justify-center mb-6 transition-all",
                isDragging && "bg-primary/10 border-primary/50 scale-110"
              )}>
                {isDragging ? (
                  <Video className="w-10 h-10 text-primary" />
                ) : (
                  <Upload className="w-10 h-10 text-muted-foreground" />
                )}
              </div>
              <h3 className="text-xl font-semibold text-foreground mb-2">
                {isDragging ? "Drop your video here" : "Upload a video"}
              </h3>
              <p className="text-muted-foreground mb-6">
                Drag and drop or click to browse
              </p>
              <label>
                <input
                  type="file"
                  accept="video/*"
                  className="hidden"
                  onChange={handleFileInput}
                />
                <Button variant="outline" asChild>
                  <span className="cursor-pointer">
                    <Video className="w-4 h-4 mr-2" />
                    Select Video
                  </span>
                </Button>
              </label>
              <p className="text-xs text-muted-foreground mt-4">
                Supports MP4, MOV, WebM, and more
              </p>
            </motion.div>
          )}
        </AnimatePresence>

        {isProcessing && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-6 flex items-center gap-2 text-primary"
          >
            <Loader2 className="w-5 h-5 animate-spin" />
            <span className="font-medium">Processing video...</span>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
};
