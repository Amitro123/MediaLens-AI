import { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Copy, Clock, Play, ArrowLeft } from 'lucide-react';
import { toast } from 'sonner';
import { parseDocumentation } from '@/utils/jsonParser';

import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';

interface TranscriptSegment {
    start: number;
    end: number;
    text: string;
}

interface Scene {
    scene_number: number;
    timestamp: string;
    location: string;
    characters?: string[];
    dialogue?: {
        hebrew: string;
        english: string;
    };
    visual_description: string;
    mood_tone?: string;
    keywords?: string[];
}

interface ResultResponse {
    task_id: string;
    documentation: string | Scene[];
    stt_provider: string;
    transcript: string;
    transcript_segments: TranscriptSegment[];
    duration?: number;
    frames_count?: number;
}

export function ResultsView() {
    const { sessionId } = useParams<{ sessionId: string }>();
    const navigate = useNavigate();
    const videoRef = useRef<HTMLVideoElement>(null);

    const [scenes, setScenes] = useState<Scene[]>([]);
    const [transcriptSegments, setTranscriptSegments] = useState<TranscriptSegment[]>([]);
    const [documentation, setDocumentation] = useState<string>('');
    const [duration, setDuration] = useState(0);
    const [currentTime, setCurrentTime] = useState(0);
    const [framesCount, setFramesCount] = useState<number | null>(null);
    const [loading, setLoading] = useState(true);

    // Hardcoded 25 frames as per requirement/backend default
    const FRAMES_COUNT = 25;

    useEffect(() => {
        if (sessionId) {
            fetchResults();
        }
    }, [sessionId]);

    async function fetchResults() {
        try {
            console.log('🔍 Fetching results for:', sessionId);

            const response = await axios.get<ResultResponse>(`/api/v1/result/${sessionId}`);
            const data = response.data;

            console.log('📦 Raw response:', data);

            // Parse documentation
            let parsedScenes: Scene[] = [];
            if (data.documentation) {
                if (typeof data.documentation === 'string') {
                    // Use new robust parser
                    const parsed = parseDocumentation<Scene[]>(data.documentation);
                    if (parsed) {
                        parsedScenes = parsed;

                        if (!Array.isArray(parsedScenes)) {
                            throw new Error('Failed to parse scene documentation: Not an array');
                        }

                        console.log(`✅ Loaded ${parsedScenes.length} scenes`);
                        setScenes(parsedScenes);
                        setDocumentation(JSON.stringify(parsedScenes, null, 2));
                    } else {
                        // It might be a string that isn't JSON or failed parsing
                        setDocumentation(data.documentation);
                    }
                } else if (Array.isArray(data.documentation)) {
                    // Already parsed by backend (if backend changed to return dict)
                    parsedScenes = data.documentation as Scene[];
                    setScenes(parsedScenes);
                    setDocumentation(JSON.stringify(parsedScenes, null, 2));
                }
            }

            // Load transcript segments
            if (data.transcript_segments) {
                setTranscriptSegments(data.transcript_segments);
            }

            // Fetch Video Duration if not in result
            if (data.duration) {
                setDuration(data.duration);
            } else {
                // Attempt to get duration from video metadata when it loads
            }

            if (data.frames_count) {
                setFramesCount(data.frames_count);
            }

            setLoading(false);

        } catch (err: any) {
            console.error('❌ Error:', err);
            toast.error('Failed to load results: ' + (err.message || 'Unknown error'));
            setLoading(false);
        }
    }

    function seekTo(timeInSeconds: number) {
        if (videoRef.current) {
            videoRef.current.currentTime = timeInSeconds;
            videoRef.current.play();
        }
    }

    function formatTime(seconds: number): string {
        if (!seconds) return '0:00';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    function copyToClipboard(text: string, label: string) {
        navigator.clipboard.writeText(text);
        toast.success(`${label} copied!`);
    }

    const handleLoadedMetadata = (e: React.SyntheticEvent<HTMLVideoElement>) => {
        setDuration(e.currentTarget.duration);
    };

    if (loading) {
        return (
            <div className="flex h-screen w-full items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
            </div>
        );
    }

    return (
        <div className="container mx-auto p-6 max-w-[1400px]">
            {/* Back Button */}
            <div className="mb-6">
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => navigate('/')}
                    className="gap-2"
                >
                    <ArrowLeft className="w-4 h-4" />
                    Back to Dashboard
                </Button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-6">
                {/* LEFT COLUMN */}
                <div className="space-y-6">
                    {/* Video Player */}
                    <Card className="overflow-hidden bg-black/5 border-none shadow-md">
                        <CardContent className="p-0">
                            <video
                                ref={videoRef}
                                src={`/api/v1/sessions/${sessionId}/video`}
                                controls
                                className="w-full max-h-[500px] rounded-lg bg-black"
                                onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
                                onLoadedMetadata={handleLoadedMetadata}
                            />
                        </CardContent>
                    </Card>

                    {/* Transcript Timeline */}
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between py-4">
                            <CardTitle className="text-lg flex items-center gap-2">
                                <Clock className="w-5 h-5" />
                                Transcript Timeline
                            </CardTitle>
                            <Badge variant="secondary">
                                {transcriptSegments?.length || 0} segments
                            </Badge>
                        </CardHeader>
                        <CardContent>
                            <ScrollArea className="h-[400px] pr-4">
                                {transcriptSegments?.length > 0 ? (
                                    <div className="space-y-2">
                                        {transcriptSegments.map((segment, idx) => {
                                            const isActive = currentTime >= segment.start && currentTime < segment.end;

                                            return (
                                                <div
                                                    key={idx}
                                                    onClick={() => seekTo(segment.start)}
                                                    className={`
                            p-3 rounded-md border-l-4 cursor-pointer transition-all duration-200
                            ${isActive
                                                            ? 'bg-primary/10 border-primary shadow-sm'
                                                            : 'bg-muted/30 border-transparent hover:bg-muted'
                                                        }
                          `}
                                                >
                                                    <div className="flex flex-row-reverse items-start gap-4">
                                                        {/* Time Badge (Left/Right depending on RTL intent, put it on left for consistency with design) */}
                                                        <div className="min-w-[50px] flex-shrink-0">
                                                            <Badge
                                                                variant={isActive ? "default" : "outline"}
                                                                className="text-xs w-full justify-center"
                                                            >
                                                                {formatTime(segment.start)}
                                                            </Badge>
                                                        </div>

                                                        {/* Text (RTL) */}
                                                        <p
                                                            className={`
                                flex-1 text-sm text-right dir-rtl font-sans
                                ${isActive ? 'font-medium text-foreground' : 'text-muted-foreground'}
                                `}
                                                            dir="rtl"
                                                        >
                                                            {segment.text}
                                                        </p>
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                ) : (
                                    <div className="text-center py-10 text-muted-foreground">
                                        No transcript available
                                    </div>
                                )}
                            </ScrollArea>
                        </CardContent>
                    </Card>

                    {/* Generated Documentation */}
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between py-4">
                            <CardTitle className="text-lg flex items-center gap-2">
                                <Copy className="w-5 h-5" />
                                Generated Documentation
                            </CardTitle>
                            <Button
                                size="sm"
                                variant="outline"
                                onClick={() => copyToClipboard(documentation, 'Documentation')}
                                className="gap-2"
                            >
                                <Copy className="w-4 h-4" />
                                Copy All
                            </Button>
                        </CardHeader>
                        <CardContent>
                            <ScrollArea className="h-[600px] pr-4">
                                {scenes.length > 0 ? (
                                    <div className="space-y-4">
                                        {scenes.map((scene, idx) => (
                                            <div
                                                key={idx}
                                                className="p-4 bg-card rounded-lg border border-border/50 shadow-sm border-l-4 border-l-primary"
                                            >
                                                <div className="flex flex-wrap gap-2 mb-3">
                                                    <Badge variant="default">Scene {scene.scene_number}</Badge>
                                                    <Badge variant="outline" className="font-mono">{scene.timestamp}</Badge>
                                                    {scene.mood_tone && (
                                                        <Badge variant="secondary" className="bg-purple-100 text-purple-700 hover:bg-purple-200 border-purple-200">
                                                            {scene.mood_tone}
                                                        </Badge>
                                                    )}
                                                </div>

                                                <div className="flex items-center gap-2 mb-2">
                                                    <span className="text-lg">📍</span>
                                                    <span className="font-semibold">{scene.location}</span>
                                                </div>

                                                <p className="text-sm text-muted-foreground mb-4 leading-relaxed">
                                                    {scene.visual_description}
                                                </p>

                                                {scene.dialogue?.hebrew && (
                                                    <div className="bg-blue-50/50 p-3 rounded-md mb-3 border border-blue-100 dark:bg-blue-900/20 dark:border-blue-800">
                                                        <p className="text-sm font-medium text-right mb-1" dir="rtl">
                                                            "{scene.dialogue.hebrew}"
                                                        </p>
                                                        {scene.dialogue.english && (
                                                            <p className="text-xs text-muted-foreground mt-1 italic">
                                                                "{scene.dialogue.english}"
                                                            </p>
                                                        )}
                                                    </div>
                                                )}

                                                {scene.characters && scene.characters.length > 0 && (
                                                    <div className="flex flex-wrap gap-2 items-center">
                                                        <span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Characters:</span>
                                                        {scene.characters.map((char, i) => (
                                                            <Badge key={i} variant="outline" className="text-xs">
                                                                {char}
                                                            </Badge>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="p-4 bg-muted/20 rounded-md">
                                        <pre className="text-xs whitespace-pre-wrap font-mono text-muted-foreground">
                                            {documentation || "No documentation available"}
                                        </pre>
                                    </div>
                                )}
                            </ScrollArea>
                        </CardContent>
                    </Card>
                </div>

                {/* RIGHT COLUMN */}
                <div className="space-y-6">
                    {/* Analysis Details */}
                    <Card>
                        <CardHeader className="py-4">
                            <CardTitle className="text-sm uppercase tracking-wider text-muted-foreground">Analysis Details</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="flex justify-between items-center">
                                <span className="text-sm text-muted-foreground">Duration</span>
                                <span className="font-medium font-mono">{formatTime(duration)}</span>
                            </div>
                            <Separator />
                            <div className="flex justify-between items-center">
                                <span className="text-sm text-muted-foreground">Scenes</span>
                                <Badge>{scenes.length}</Badge>
                            </div>
                            <Separator />
                            <div className="flex justify-between items-center">
                                <span className="text-sm text-muted-foreground">Transcript</span>
                                <Badge variant="outline">{transcriptSegments?.length || 0} segments</Badge>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Key Moments */}
                    <Card className="flex flex-col flex-1 min-h-[400px]">
                        <CardHeader className="py-4">
                            <CardTitle className="text-sm flex items-center gap-2">
                                <Clock className="w-4 h-4" />
                                Key Moments (Click to Jump)
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="flex-1">
                            <ScrollArea className="h-[600px] pr-2">
                                <div className="grid grid-cols-2 gap-3">
                                    {Array.from({ length: framesCount || FRAMES_COUNT }, (_, i) => {
                                        // Estimated time based on standard 25 frame extraction? 
                                        // Or is it 25 frames TOTAL spread across video?
                                        // Typically 'extract_frames' in backend usually does fixed count or fixed interval.
                                        // Assuming fixed count of 25 frames spread evenly.
                                        const frameTime = duration ? (duration / FRAMES_COUNT) * i : i * 5;
                                        const scene = scenes[i] || scenes[scenes.length - 1]; // Fallback to last scene? Or just null?

                                        return (
                                            <div
                                                key={i}
                                                className="group relative cursor-pointer overflow-hidden rounded-md border border-border hover:ring-2 hover:ring-primary transition-all"
                                                onClick={() => seekTo(frameTime)}
                                            >
                                                <div className="aspect-video bg-muted relative">
                                                    <img
                                                        src={`/api/v1/sessions/${sessionId}/frames/${i}.jpg`}
                                                        alt={`Frame ${i}`}
                                                        className="object-cover w-full h-full transition-transform duration-500 group-hover:scale-110"
                                                        loading="lazy"
                                                        onError={(e) => {
                                                            (e.target as HTMLImageElement).src = 'https://placehold.co/600x400?text=No+Preview';
                                                        }}
                                                    />
                                                    <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors" />
                                                </div>

                                                {/* Timestamp Overlay */}
                                                <div className="absolute bottom-1 left-1">
                                                    <Badge variant="secondary" className="bg-black/70 text-white hover:bg-black/90 text-[10px] h-5 px-1.5 border-none">
                                                        {formatTime(frameTime)}
                                                    </Badge>
                                                </div>

                                                {/* Copy JSON Button */}
                                                {scenes[i] && (
                                                    <Button
                                                        size="icon"
                                                        variant="ghost"
                                                        className="absolute top-1 right-1 w-6 h-6 bg-black/50 text-white hover:bg-black/80 hover:text-white opacity-0 group-hover:opacity-100 transition-opacity"
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            copyToClipboard(
                                                                JSON.stringify(scenes[i], null, 2),
                                                                `Scene ${scenes[i].scene_number}`
                                                            );
                                                        }}
                                                    >
                                                        <Copy className="w-3 h-3" />
                                                    </Button>
                                                )}
                                            </div>
                                        );
                                    })}
                                </div>
                            </ScrollArea>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
}

export default ResultsView;
