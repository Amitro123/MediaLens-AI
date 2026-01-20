import { useRef, useEffect } from "react";
import { cn, parseTimestamp } from "@/lib/utils";
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "@/components/ui/tooltip";

interface Scene {
    scene_number: number;
    timestamp: string; // "MM:SS"
    location: string;
    visual_description: string;
    dialogue?: {
        hebrew?: string;
        english?: string;
    };
    keywords: string[];
}

interface TimelineProps {
    scenes: Scene[];
    duration: number; // in seconds
    currentTime: number;
    onSeek: (time: number) => void;
}


export const VideoTimeline = ({ scenes, duration, currentTime, onSeek }: TimelineProps) => {
    const progressBarRef = useRef<HTMLDivElement>(null);

    const handleTimelineClick = (e: React.MouseEvent<HTMLDivElement>) => {
        if (!progressBarRef.current) return;
        const rect = progressBarRef.current.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const percent = Math.max(0, Math.min(1, x / rect.width));
        onSeek(percent * duration);
    };

    return (
        <div className="relative h-16 bg-muted/30 rounded-lg p-4 select-none">
            {/* Clickable Progress Bar Area */}
            <div
                ref={progressBarRef}
                className="absolute top-7 left-4 right-4 h-2 bg-secondary rounded-full cursor-pointer group"
                onClick={handleTimelineClick}
            >
                {/* Play Progress */}
                <div
                    className="absolute top-0 left-0 h-full bg-primary/80 rounded-full transition-all duration-100"
                    style={{ width: `${(currentTime / duration) * 100}%` }}
                />

                {/* Hover Highlight (Optional hint) */}
                <div className="absolute inset-0 group-hover:bg-primary/10 rounded-full transition-colors" />
            </div>

            {/* Scene Markers */}
            <div className="absolute top-6 left-4 right-4 h-4 pointer-events-none">
                <TooltipProvider>
                    {scenes.map((scene, idx) => {
                        const time = parseTimestamp(scene.timestamp);
                        const percent = (time / duration) * 100;

                        // Should not exceed 100%
                        if (percent > 100) return null;

                        return (
                            <Tooltip key={idx}>
                                <TooltipTrigger asChild>
                                    <div
                                        className="absolute top-0 w-3 h-3 bg-destructive rounded-full border-2 border-background cursor-pointer hover:scale-150 transition-transform pointer-events-auto"
                                        style={{ left: `calc(${percent}% - 6px)` }}
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            onSeek(time);
                                        }}
                                    />
                                </TooltipTrigger>
                                <TooltipContent>
                                    <div className="text-xs font-bold">Scene {scene.scene_number}</div>
                                    <div className="text-xs text-muted-foreground">{scene.timestamp} - {scene.location}</div>
                                </TooltipContent>
                            </Tooltip>
                        );
                    })}
                </TooltipProvider>
            </div>
        </div>
    );
};
