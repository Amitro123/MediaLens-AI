import { motion } from "framer-motion";
import {
  Film,
  Scissors,
  UserSearch,
  Type,
  Check
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

export type DocMode = "scene_detection" | "clip_generator" | "character_tracker" | "subtitle_extractor";

interface DocModeOption {
  id: DocMode;
  label: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  department: "Media" | "Social" | "Ops";
  badgeVariant: "media" | "social" | "ops"; // Assuming Badge variant allows string or we need to add these variants to Badge component. If strictly typed, might need "default" or "secondary" fallback.
}

const docModes: DocModeOption[] = [
  {
    id: "scene_detection",
    label: "Scene Detection",
    description: "Catalog every scene with timestamps",
    icon: Film,
    department: "Media",
    badgeVariant: "media",
  },
  {
    id: "clip_generator",
    label: "Viral Clip Gen",
    description: "Find shareable moments for social",
    icon: Scissors,
    department: "Social",
    badgeVariant: "social",
  },
  {
    id: "character_tracker",
    label: "Character Tracker",
    description: "Track appearances and actions",
    icon: UserSearch,
    department: "Media",
    badgeVariant: "media",
  },
  {
    id: "subtitle_extractor",
    label: "Subtitle Extractor",
    description: "Generate SRT subtitles",
    icon: Type,
    department: "Ops",
    badgeVariant: "ops",
  },
];

interface DocModeSelectorProps {
  selected: DocMode;
  onSelect: (mode: DocMode) => void;
}

export const DocModeSelector = ({ selected, onSelect }: DocModeSelectorProps) => {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-foreground">Analysis Mode</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {docModes.map((mode, index) => (
          <motion.button
            key={mode.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: index * 0.05 }}
            onClick={() => onSelect(mode.id)}
            className={cn(
              "relative p-4 rounded-xl border text-left transition-all duration-200",
              selected === mode.id
                ? "border-primary bg-primary/5 shadow-glow"
                : "border-border bg-card hover:border-primary/30 hover:bg-card/80"
            )}
          >
            {selected === mode.id && (
              <motion.div
                layoutId="selected-mode"
                className="absolute top-3 right-3 w-5 h-5 rounded-full bg-primary flex items-center justify-center"
                transition={{ type: "spring", stiffness: 500, damping: 30 }}
              >
                <Check className="w-3 h-3 text-primary-foreground" />
              </motion.div>
            )}

            <div className="flex items-start gap-3">
              <div className={cn(
                "w-10 h-10 rounded-lg flex items-center justify-center shrink-0",
                selected === mode.id
                  ? "bg-primary/20"
                  : "bg-secondary"
              )}>
                <mode.icon className={cn(
                  "w-5 h-5",
                  selected === mode.id ? "text-primary" : "text-muted-foreground"
                )} />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className={cn(
                    "font-medium",
                    selected === mode.id ? "text-foreground" : "text-foreground/80"
                  )}>
                    {mode.label}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground line-clamp-1">
                  {mode.description}
                </p>
                {/* Badge might complain if variant is not standard, using 'secondary' as fallback if needed or ignoring error if variants are custom extended */}
                <Badge variant={"secondary"} className="mt-2 text-[10px]">
                  {mode.department}
                </Badge>
              </div>
            </div>
          </motion.button>
        ))}
      </div>
    </div>
  );
};
