import { useRef, useEffect } from "react";
import { cn, parseTimestamp } from "@/lib/utils";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Play } from "lucide-react";

interface Scene {
    scene_number: number;
    timestamp: string;
    dialogue?: {
        hebrew?: string;
        english?: string;
    };
}

interface TranscriptionSegment {
    start: number;
    end: number;
    text: string;
}

interface TranscriptionPanelProps {
    scenes: Scene[];
    transcriptSegments?: TranscriptionSegment[];
    currentTime: number;
    onSeek: (time: number) => void;
}


export const TranscriptionPanel = ({ scenes, transcriptSegments, currentTime, onSeek }: TranscriptionPanelProps) => {
    const activeRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to active segment
    useEffect(() => {
        if (activeRef.current) {
            activeRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }, [currentTime]);

    // Format helper
    const formatTime = (seconds: number) => {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    // Determine what to show: Raw segments OR Scene dialogue
    const hasRawSegments = transcriptSegments && transcriptSegments.length > 0;

    return (
        <ScrollArea className="h-[400px] pr-4">
            <div className="space-y-2">
                {hasRawSegments ? (
                    // Render Raw Segments
                    transcriptSegments!.map((seg, idx) => {
                        const isActive = currentTime >= seg.start && currentTime < seg.end;
                        return (
                            <div
                                key={idx}
                                ref={isActive ? activeRef : null}
                                className={cn(
                                    "group p-3 rounded-lg border text-left transition-all cursor-pointer relative overflow-hidden",
                                    isActive
                                        ? "bg-primary/5 border-primary shadow-sm"
                                        : "bg-card border-border hover:bg-muted/50"
                                )}
                                onClick={() => onSeek(seg.start)}
                            >
                                <div className="flex gap-3">
                                    <div className={cn(
                                        "flex-shrink-0 w-12 text-xs font-mono py-1 rounded text-center h-fit",
                                        isActive ? "text-primary font-bold bg-primary/10" : "text-muted-foreground bg-muted"
                                    )}>
                                        {formatTime(seg.start)}
                                    </div>
                                    <div className="flex-1">
                                        <p className={cn(
                                            "text-sm leading-relaxed",
                                            isActive ? "text-foreground font-medium" : "text-muted-foreground"
                                        )} dir="auto">
                                            {seg.text}
                                        </p>
                                    </div>
                                    <div className="opacity-0 group-hover:opacity-100 absolute right-2 top-1/2 -translate-y-1/2 transition-opacity">
                                        <div className="bg-primary text-primary-foreground rounded-full p-1.5 shadow-md">
                                            <Play className="w-3 h-3 fill-current" />
                                        </div>
                                    </div>
                                </div>
                            </div>
                        );
                    })
                ) : (
                    // Render Scenes (Fallback)
                    scenes.map((scene, idx) => {
                        const sceneTime = parseTimestamp(scene.timestamp);
                        const nextSceneTime = idx < scenes.length - 1 ? parseTimestamp(scenes[idx + 1].timestamp) : sceneTime + 30;
                        const isActive = currentTime >= sceneTime && currentTime < nextSceneTime;

                        return (
                            <div
                                key={idx}
                                ref={isActive ? activeRef : null}
                                className={cn(
                                    "group p-3 rounded-lg border text-left transition-all cursor-pointer relative overflow-hidden",
                                    isActive
                                        ? "bg-primary/5 border-primary shadow-sm"
                                        : "bg-card border-border hover:bg-muted/50"
                                )}
                                onClick={() => onSeek(sceneTime)}
                            >
                                <div className="flex gap-3">
                                    <div className={cn(
                                        "flex-shrink-0 w-12 text-xs font-mono py-1 rounded text-center h-fit",
                                        isActive ? "text-primary font-bold bg-primary/10" : "text-muted-foreground bg-muted"
                                    )}>
                                        {scene.timestamp}
                                    </div>

                                    <div className="flex-1 space-y-1">
                                        {scene.dialogue?.hebrew ? (
                                            <p className={cn(
                                                "text-sm leading-relaxed",
                                                isActive ? "text-foreground font-medium" : "text-muted-foreground"
                                            )} dir="rtl">
                                                {scene.dialogue.hebrew}
                                            </p>
                                        ) : (
                                            <p className="text-xs text-muted-foreground italic">
                                                (No dialogue detected)
                                            </p>
                                        )}

                                        {scene.dialogue?.english && (
                                            <p className="text-xs text-muted-foreground">
                                                {scene.dialogue.english}
                                            </p>
                                        )}
                                    </div>

                                    <div className="opacity-0 group-hover:opacity-100 absolute right-2 top-1/2 -translate-y-1/2 transition-opacity">
                                        <div className="bg-primary text-primary-foreground rounded-full p-1.5 shadow-md">
                                            <Play className="w-3 h-3 fill-current" />
                                        </div>
                                    </div>
                                </div>
                            </div>
                        );
                    })
                )}
            </div>
        </ScrollArea>
    );
};
