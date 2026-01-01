import { motion } from "framer-motion";
import {
  Mic,
  Brain,
  FileText,
  Check,
  Loader2,
  Video
} from "lucide-react";
import { cn } from "@/lib/utils";

export type ProcessingStep = "upload" | "transcribe" | "analyze" | "generate" | "complete";

interface StepConfig {
  id: ProcessingStep;
  label: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
}

const steps: StepConfig[] = [
  {
    id: "upload",
    label: "Uploading",
    description: "Processing video file",
    icon: Video,
  },
  {
    id: "transcribe",
    label: "Transcribing",
    description: "Extracting audio with Whisper",
    icon: Mic,
  },
  {
    id: "analyze",
    label: "Analyzing",
    description: "AI identifying key moments",
    icon: Brain,
  },
  {
    id: "generate",
    label: "Generating",
    description: "Creating documentation",
    icon: FileText,
  },
  {
    id: "complete",
    label: "Complete",
    description: "Documentation ready",
    icon: Check,
  },
];

interface ProcessingProgressProps {
  currentStep: ProcessingStep;
  progress?: number;
  stage?: string;  // Backend stage label (e.g., "Extracting key frames...")
}

export const ProcessingProgress = ({ currentStep, progress = 0, stage = "" }: ProcessingProgressProps) => {
  const currentIndex = steps.findIndex(s => s.id === currentStep);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass rounded-2xl p-6 md:p-8"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-foreground">Processing Video</h3>
        <span className="text-lg font-bold text-primary">{Math.round(progress)}%</span>
      </div>

      {/* Backend Stage Label */}
      {stage && (
        <div className="mb-4 text-sm text-muted-foreground flex items-center gap-2">
          <Loader2 className="w-4 h-4 animate-spin text-primary" />
          <span>{stage}</span>
        </div>
      )}

      {/* Progress Bar */}
      <div className="h-3 bg-secondary rounded-full mb-8 overflow-hidden border border-border">
        <motion.div
          className="h-full bg-gradient-to-r from-primary to-purple-500 rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        />
      </div>

      {/* Steps */}
      <div className="relative">
        {/* Connection Line */}
        <div className="absolute top-5 left-5 right-5 h-0.5 bg-border hidden md:block" />

        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {steps.map((step, index) => {
            const isActive = index === currentIndex;
            const isComplete = index < currentIndex;
            const isPending = index > currentIndex;

            return (
              <motion.div
                key={step.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className="flex flex-col items-center text-center relative"
              >
                {/* Icon Circle */}
                <div
                  className={cn(
                    "w-10 h-10 rounded-full flex items-center justify-center mb-3 transition-all duration-300 relative z-10",
                    isComplete && "bg-primary text-primary-foreground",
                    isActive && "bg-primary/20 border-2 border-primary text-primary animate-glow-pulse",
                    isPending && "bg-secondary text-muted-foreground"
                  )}
                >
                  {isComplete ? (
                    <Check className="w-5 h-5" />
                  ) : isActive ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <step.icon className="w-5 h-5" />
                  )}
                </div>

                <span
                  className={cn(
                    "text-sm font-medium mb-1 transition-colors",
                    isActive && "text-primary",
                    isComplete && "text-foreground",
                    isPending && "text-muted-foreground"
                  )}
                >
                  {step.label}
                </span>
                <span className="text-xs text-muted-foreground hidden md:block">
                  {step.description}
                </span>
              </motion.div>
            );
          })}
        </div>
      </div>
    </motion.div>
  );
};
