import { motion } from "framer-motion";
import { Loader2, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface ProgressBarProps {
    progress: number;
    stage: string;
    isComplete?: boolean;
}

const STAGE_LABELS: Record<string, string> = {
    "": "Starting...",
    "Analyzing video duration...": "📹 Analyzing video...",
    "Creating optimized proxy...": "⚡ Optimizing...",
    "Analyzing content relevance...": "🔍 Analyzing content...",
    "Extracting key frames...": "🎬 Extracting frames...",
    "Generating documentation with Gemini...": "🤖 Generating docs...",
    "Generating documentation...": "🤖 Generating docs...",
    "Storing artifacts...": "💾 Saving...",
    "Complete!": "✅ Complete!",
};

export const ProgressBar = ({ progress, stage, isComplete = false }: ProgressBarProps) => {
    const displayStage = STAGE_LABELS[stage] || stage || "Processing...";
    const clampedProgress = Math.min(100, Math.max(0, progress));

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full max-w-md mx-auto"
        >
            {/* Stage Label */}
            <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                    {isComplete ? (
                        <CheckCircle2 className="w-5 h-5 text-green-500" />
                    ) : (
                        <Loader2 className="w-5 h-5 text-primary animate-spin" />
                    )}
                    <span className={cn(
                        "text-sm font-medium",
                        isComplete ? "text-green-500" : "text-muted-foreground"
                    )}>
                        {displayStage}
                    </span>
                </div>
                <span className={cn(
                    "text-sm font-bold",
                    isComplete ? "text-green-500" : "text-primary"
                )}>
                    {clampedProgress}%
                </span>
            </div>

            {/* Progress Bar Track */}
            <div
                className="w-full h-3 bg-secondary rounded-full overflow-hidden border border-border"
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={clampedProgress}
                aria-label={isComplete ? "Processing complete" : `Processing: ${clampedProgress}% complete`}
            >
                <motion.div
                    className={cn(
                        "h-full rounded-full",
                        isComplete
                            ? "bg-gradient-to-r from-green-500 to-emerald-400"
                            : "bg-gradient-to-r from-primary to-purple-500"
                    )}
                    initial={{ width: 0 }}
                    animate={{ width: `${clampedProgress}%` }}
                    transition={{
                        duration: 0.5,
                        ease: "easeOut"
                    }}
                />
            </div>

            {/* Stage Dots */}
            <div className="flex justify-between mt-2 px-1">
                {[10, 30, 50, 70, 100].map((milestone) => (
                    <div
                        key={milestone}
                        className={cn(
                            "w-2 h-2 rounded-full transition-colors duration-300",
                            clampedProgress >= milestone
                                ? isComplete ? "bg-green-500" : "bg-primary"
                                : "bg-muted"
                        )}
                    />
                ))}
            </div>
        </motion.div>
    );
};
