import { useState, useRef, useEffect } from "react";
import { formatDuration, parseTimestamp } from "@/lib/utils";
import { VideoTimeline } from "./VideoTimeline";
import { SceneCard } from "./SceneCard";
import { TranscriptionPanel } from "./TranscriptionPanel";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Loader2 } from "lucide-react";
import { api } from "@/api";

interface ResultsViewProps {
    sessionId: string;
}

interface Scene {
    scene_number: number;
    timestamp: string;
    location: string;
    visual_description: string;
    dialogue?: { hebrew?: string; english?: string };
    keywords: string[];
}

interface ProcessedData {
    scenes: Scene[];
    metadata: {
        duration: number;
        project_name?: string;
        mode?: string;
        stt_provider?: string;
    };
    transcriptSegments?: any[]; // Raw segments from STT
}

// Local mock while fetching
const MOCK_DURATION = 120; // Default if unknown

export const ResultsView = ({ sessionId }: ResultsViewProps) => {
    const [data, setData] = useState<ProcessedData | null>(null);
    const [loading, setLoading] = useState(true);
    const [currentTime, setCurrentTime] = useState(0);
    const videoRef = useRef<HTMLVideoElement>(null);

    // Fetch results
    useEffect(() => {
        const fetchData = async () => {
            try {
                console.log('🔍 Fetching results for:', sessionId);

                // 1. Get raw result string
                const resultRes = await api.getResult(sessionId);
                const responseData = resultRes.data;

                console.log('📦 Raw response:', responseData);
                console.log('📄 Documentation type:', typeof responseData.documentation);

                // 2. Parse JSON. 
                let jsonData: Scene[] = [];
                const docContent = responseData.documentation;

                if (typeof docContent === 'string') {
                    console.log('🔧 Parsing documentation string...');
                    try {
                        // Try direct parse first
                        jsonData = JSON.parse(docContent);
                    } catch {
                        // Try extracting from markdown block
                        console.log('⚠️ Direct parse failed, trying markdown extraction...');
                        const jsonMatch = docContent.match(/```json\s*([\s\S]*?)\s*```/);
                        if (jsonMatch) {
                            jsonData = JSON.parse(jsonMatch[1]);
                        } else {
                            console.error("❌ Could not parse JSON from documentation");
                            jsonData = [];
                        }
                    }
                } else if (Array.isArray(docContent)) {
                    console.log('✅ Documentation already parsed (Array)');
                    jsonData = docContent;
                } else if (typeof docContent === 'object') {
                    console.log('✅ Documentation already parsed (Object - might be wrapped?)');
                    // Fallback/Warning: This shouldn't typically happen with strict Scene[] type
                    jsonData = (docContent as any).scenes || [];
                }

                console.log('✅ Parsed scenes:', jsonData);
                console.log('📊 Scene count:', jsonData.length);

                // 3. Get Session Details for consistent metadata
                let sessionRes;
                try {
                    const res = await api.getSession(sessionId);
                    sessionRes = res.data;
                } catch {
                    sessionRes = {};
                }

                // Determine STT Provider (API result > Session > Default)
                const provider = responseData.stt_provider || (sessionRes as any).stt_provider || "unknown";

                setData({
                    scenes: Array.isArray(jsonData) ? jsonData : [],
                    metadata: {
                        duration: sessionRes.duration || 0, // Prefer session duration if available
                        mode: sessionRes.mode || "scene_detection",
                        project_name: sessionRes.title,
                        stt_provider: provider
                    },
                    transcriptSegments: responseData.transcript_segments
                });

            } catch (err) {
                console.error("❌ Error fetching results:", err);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [sessionId]);

    const handleSeek = (time: number) => {
        if (videoRef.current) {
            videoRef.current.currentTime = time;
            videoRef.current.play();
        }
    };

    const handleLoadedMetadata = () => {
        if (videoRef.current && data) {
            setData(prev => prev ? ({
                ...prev,
                metadata: {
                    ...prev.metadata,
                    duration: videoRef.current!.duration
                }
            }) : null);
        }
    };

    if (loading) {
        return (
            <div className="flex h-[400px] items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
        );
    }

    if (!data) return <div>Failed to load results.</div>;

    const providerLabel = data.metadata.stt_provider === "groq" ? "⚡ Groq"
        : data.metadata.stt_provider === "google" ? "🎯 Google"
            : data.metadata.stt_provider;

    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-in fade-in duration-500">
            {/* Left Column: Video & Timeline & Scenes */}
            <div className="lg:col-span-2 space-y-6">

                {/* Video Player */}
                <div className="relative bg-black rounded-xl overflow-hidden shadow-2xl ring-1 ring-white/10 aspect-video group">
                    <video
                        ref={videoRef}
                        src={`http://localhost:8000/api/v1/sessions/${sessionId}/video`}
                        className="w-full h-full"
                        controls
                        onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
                        onLoadedMetadata={handleLoadedMetadata}
                    />
                </div>

                {/* Timeline */}
                <VideoTimeline
                    scenes={data.scenes}
                    duration={data.metadata.duration || MOCK_DURATION}
                    currentTime={currentTime}
                    onSeek={handleSeek}
                />

                {/* Scenes List */}
                <div className="space-y-4">
                    <h3 className="text-xl font-semibold tracking-tight">Detected Scenes ({data.scenes.length})</h3>
                    <div className="grid grid-cols-1 gap-4">
                        {data.scenes.map((scene, idx) => (
                            <SceneCard
                                key={idx}
                                scene={scene}
                                thumbnailUrl={`http://localhost:8000/api/v1/sessions/${sessionId}/frames/${idx}.jpg`}
                                onJumpTo={() => handleSeek(parseTimestamp(scene.timestamp))}
                            />
                        ))}
                    </div>
                </div>
            </div>

            {/* Right Column: Metadata & Transcript */}
            <div className="space-y-6">
                {/* Info Card */}
                <Card>
                    <CardHeader>
                        <CardTitle>Analysis Details</CardTitle>
                        <CardDescription>Session metadata</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex justify-between items-center border-b pb-2">
                            <span className="text-muted-foreground text-sm">Duration</span>
                            <span className="font-mono">{Math.floor(data.metadata.duration / 60)}m {Math.floor(data.metadata.duration % 60)}s</span>
                        </div>
                        <div className="flex justify-between items-center border-b pb-2">
                            <span className="text-muted-foreground text-sm">Scenes</span>
                            <span className="font-mono">{data.scenes.length}</span>
                        </div>
                        <div className="flex justify-between items-center">
                            <span className="text-muted-foreground text-sm">Provider</span>
                            <Badge variant={data.metadata.stt_provider === "groq" ? "default" : "secondary"}>
                                {providerLabel}
                            </Badge>
                        </div>
                    </CardContent>
                </Card>

                {/* Transcript Panel */}
                <Card className="flex flex-col max-h-[600px]">
                    <CardHeader className="pb-3">
                        <CardTitle className="text-base flex items-center gap-2">
                            <span>Live Transcript</span>
                            <Badge className="ml-auto bg-red-500 hover:bg-red-600 animate-pulse">REC</Badge>
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="flex-1 overflow-hidden p-0">
                        <TranscriptionPanel
                            scenes={data.scenes}
                            transcriptSegments={data.transcriptSegments}
                            currentTime={currentTime}
                            onSeek={handleSeek}
                        />
                    </CardContent>
                </Card>
            </div>
        </div>
    );
};
