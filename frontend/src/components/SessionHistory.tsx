import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Clock, FileVideo, CheckCircle2, XCircle, Loader2, Eye } from "lucide-react";
import { api, type Session } from "@/api";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";

export const SessionHistory = () => {
    const [sessions, setSessions] = useState<Session[]>([]);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        loadSessions();
    }, []);

    const loadSessions = async () => {
        try {
            const response = await api.getSessions();
            // Filter to only completed sessions and sort by timestamp (newest first)
            const completedSessions = response.data.sessions
                .filter((s: Session) => s.status === "completed")
                .sort((a: Session, b: Session) =>
                    new Date(b.timestamp || b.created_at || 0).getTime() - new Date(a.timestamp || a.created_at || 0).getTime()
                );
            setSessions(completedSessions);
        } catch (error) {
            console.error("Failed to load sessions:", error);
        } finally {
            setLoading(false);
        }
    };

    const formatDate = (timestamp: string) => {
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        return date.toLocaleDateString();
    };

    const getModeLabel = (mode: string) => {
        const labels: Record<string, string> = {
            scene_detection: "Scene Detection",
            clip_generator: "Viral Clips",
            character_tracker: "Character Tracking",
            subtitle_extractor: "Subtitles",
            general_doc: "General Doc",
        };
        return labels[mode] || mode;
    };

    const getModeColor = (mode: string) => {
        const colors: Record<string, string> = {
            scene_detection: "bg-blue-500/10 text-blue-500 border-blue-500/20",
            clip_generator: "bg-purple-500/10 text-purple-500 border-purple-500/20",
            character_tracker: "bg-green-500/10 text-green-500 border-green-500/20",
            subtitle_extractor: "bg-orange-500/10 text-orange-500 border-orange-500/20",
            general_doc: "bg-gray-500/10 text-gray-500 border-gray-500/20",
        };
        return colors[mode] || colors.general_doc;
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
        );
    }

    if (sessions.length === 0) {
        return (
            <div className="text-center py-12 text-muted-foreground">
                <FileVideo className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>No previous sessions yet</p>
                <p className="text-sm mt-2">Upload a video to get started</p>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <div className="flex items-center gap-2 mb-4">
                <Clock className="w-5 h-5 text-primary" />
                <h3 className="text-lg font-semibold">Recent Sessions</h3>
                <Badge variant="secondary" className="ml-auto">
                    {sessions.length}
                </Badge>
            </div>

            <ScrollArea className="h-[500px] pr-4">
                <div className="space-y-3">
                    {sessions.map((session, idx) => (
                        <motion.div
                            key={session.id}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: idx * 0.05 }}
                            className={cn(
                                "group relative p-4 rounded-lg border bg-card hover:bg-accent/50 transition-all cursor-pointer",
                                "hover:border-primary/50 hover:shadow-md"
                            )}
                            onClick={() => navigate(`/results/${session.id}`)}
                        >
                            <div className="flex items-start gap-3">
                                <div className="flex-shrink-0 mt-1">
                                    <FileVideo className="w-5 h-5 text-primary" />
                                </div>

                                <div className="flex-1 min-w-0">
                                    <div className="flex items-start justify-between gap-2 mb-2">
                                        <h4 className="font-medium text-foreground truncate">
                                            {session.title || "Untitled Project"}
                                        </h4>
                                        <span className="text-xs text-muted-foreground whitespace-nowrap">
                                            {formatDate(session.timestamp || session.created_at || new Date().toISOString())}
                                        </span>
                                    </div>

                                    <div className="flex items-center gap-2 flex-wrap">
                                        {session.mode && (
                                            <Badge variant="outline" className={cn("text-xs", getModeColor(session.mode))}>
                                                {getModeLabel(session.mode)}
                                            </Badge>
                                        )}
                                        <Badge variant="outline" className="text-xs bg-green-500/10 text-green-500 border-green-500/20">
                                            <CheckCircle2 className="w-3 h-3 mr-1" />
                                            Completed
                                        </Badge>
                                    </div>
                                </div>

                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="opacity-0 group-hover:opacity-100 transition-opacity"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        navigate(`/results/${session.id}`);
                                    }}
                                >
                                    <Eye className="w-4 h-4 mr-1" />
                                    View
                                </Button>
                            </div>
                        </motion.div>
                    ))}
                </div>
            </ScrollArea>
        </div>
    );
};
