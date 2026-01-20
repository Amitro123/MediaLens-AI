import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { PlayCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface Scene {
    scene_number: number;
    timestamp: string;
    location: string;
    visual_description: string;
    dialogue?: {
        hebrew?: string;
        english?: string;
    };
    keywords: string[];
}

interface SceneCardProps {
    scene: Scene;
    thumbnailUrl: string;
    onJumpTo: (timestamp: string) => void;
}

export const SceneCard = ({ scene, thumbnailUrl, onJumpTo }: SceneCardProps) => {
    return (
        <Card
            className="overflow-hidden cursor-pointer hover:shadow-lg hover:border-primary/50 transition-all group"
            onClick={() => onJumpTo(scene.timestamp)}
        >
            <CardContent className="p-0 flex flex-col md:flex-row gap-4">
                {/* Thumbnail Section */}
                <div className="relative w-full md:w-48 h-32 flex-shrink-0 bg-muted">
                    <img
                        src={thumbnailUrl}
                        alt={`Scene ${scene.scene_number}`}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                            // Fallback to a valid placeholder
                            (e.target as HTMLImageElement).src = 'https://placehold.co/600x400?text=No+Preview';
                            (e.target as HTMLImageElement).classList.add('opacity-50');
                        }}
                    />
                    <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 bg-black/30 transition-opacity">
                        <PlayCircle className="w-10 h-10 text-white drop-shadow-lg" />
                    </div>
                    <Badge className="absolute top-2 left-2 bg-black/70 hover:bg-black/80 text-white border-0">
                        {scene.timestamp}
                    </Badge>
                </div>

                {/* Content Section */}
                <div className="flex-1 p-4 md:pl-0 flex flex-col gap-2">
                    <div className="flex items-center gap-2">
                        <Badge variant="outline" className="text-xs font-semibold px-2 py-0 h-5">
                            Scene {scene.scene_number}
                        </Badge>
                        <h4 className="font-semibold text-sm text-foreground line-clamp-1">
                            {scene.location}
                        </h4>
                    </div>

                    <p className="text-sm text-muted-foreground line-clamp-2 leading-relaxed">
                        {scene.visual_description}
                    </p>

                    {scene.dialogue?.hebrew && (
                        <div className="mt-auto bg-muted/40 p-2 rounded text-xs text-right border-r-2 border-primary/20 italic text-foreground/80">
                            "{scene.dialogue.hebrew}"
                        </div>
                    )}

                    <div className="flex flex-wrap gap-1 mt-2">
                        {/* Fix: keywords might be undefined or null from loose LLM JSON */}
                        {(scene.keywords || []).slice(0, 3).map((keyword, i) => (
                            <span key={i} className="text-[10px] uppercase tracking-wider text-muted-foreground bg-secondary px-1.5 py-0.5 rounded">
                                {keyword}
                            </span>
                        ))}
                    </div>
                </div>
            </CardContent>
        </Card>
    );
};
