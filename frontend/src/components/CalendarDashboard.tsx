import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Calendar, Clock, Zap, CheckCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { api } from "@/api";

interface DraftSession {
    id: string;
    title: string;
    time: string;
    status: string;
    context_keywords?: string[];
}

interface CalendarDashboardProps {
    onSelectSession?: (sessionId: string) => void;
}

const formatTime = (isoString: string) => {
    try {
        const date = new Date(isoString);
        return date.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
    } catch {
        return isoString;
    }
};

export const CalendarDashboard = ({ onSelectSession }: CalendarDashboardProps) => {
    const [drafts, setDrafts] = useState<DraftSession[]>([]);
    const [loading, setLoading] = useState(true);
    const [preppingId, setPreppingId] = useState<string | null>(null);

    useEffect(() => {
        const loadDrafts = async () => {
            try {
                const response = await api.getDraftMeetings();
                // Map backend response to DraftSession format
                const data = (response.data || []) as any[];
                setDrafts(data.map(d => ({
                    id: d.id,
                    title: d.title,
                    time: d.time || d.created_at || "",
                    status: d.status,
                    context_keywords: d.context_keywords
                })));
            } catch (err) {
                console.error("Failed to load draft sessions:", err);
            } finally {
                setLoading(false);
            }
        };
        loadDrafts();
    }, []);

    const handlePrep = async (sessionId: string) => {
        setPreppingId(sessionId);
        try {
            await api.prepSession(sessionId);
            // Optimistic update
            setDrafts(prev =>
                prev.map(d =>
                    d.id === sessionId ? { ...d, status: "ready_for_upload" } : d
                )
            );
        } catch (err) {
            console.error("Failed to prep session:", err);
        } finally {
            setPreppingId(null);
        }
    };

    const handleSelectReady = (sessionId: string) => {
        if (onSelectSession) {
            onSelectSession(sessionId);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-6">
                <Loader2 className="w-5 h-5 animate-spin text-primary mr-2" />
                <span className="text-muted-foreground">Loading meetings...</span>
            </div>
        );
    }

    if (drafts.length === 0) {
        return null; // Don't show section if no meetings
    }

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass rounded-xl p-4 mb-6"
        >
            <div className="flex items-center gap-2 mb-4">
                <Calendar className="w-5 h-5 text-primary" />
                <h3 className="font-semibold text-foreground">Upcoming Meetings</h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {drafts.map((session, idx) => {
                    const isReady = session.status === "ready_for_upload";
                    const isPrepping = preppingId === session.id;

                    return (
                        <motion.div
                            key={session.id}
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            transition={{ delay: idx * 0.05 }}
                            className={cn(
                                "p-4 rounded-lg border transition-all",
                                isReady
                                    ? "border-green-500/50 bg-green-500/10"
                                    : "border-border bg-card hover:border-primary/30"
                            )}
                        >
                            <div className="flex items-start justify-between mb-2">
                                <h4 className="font-medium text-foreground text-sm truncate flex-1">
                                    {session.title}
                                </h4>
                                <Badge
                                    variant={isReady ? "default" : "secondary"}
                                    className={cn(
                                        "ml-2 shrink-0",
                                        isReady && "bg-green-500/20 text-green-400"
                                    )}
                                >
                                    {isReady ? "Ready" : "Scheduled"}
                                </Badge>
                            </div>

                            <div className="flex items-center text-xs text-muted-foreground mb-3">
                                <Clock className="w-3 h-3 mr-1" />
                                {formatTime(session.time)}
                            </div>

                            {session.context_keywords && session.context_keywords.length > 0 && (
                                <div className="flex flex-wrap gap-1 mb-3">
                                    {session.context_keywords.slice(0, 3).map((kw, i) => (
                                        <span
                                            key={i}
                                            className="text-xs px-1.5 py-0.5 bg-secondary rounded text-muted-foreground"
                                        >
                                            {kw}
                                        </span>
                                    ))}
                                </div>
                            )}

                            {isReady ? (
                                <Button
                                    size="sm"
                                    className="w-full"
                                    onClick={() => handleSelectReady(session.id)}
                                >
                                    <CheckCircle className="w-3 h-3 mr-1" />
                                    Upload Video
                                </Button>
                            ) : (
                                <Button
                                    size="sm"
                                    variant="outline"
                                    className="w-full"
                                    onClick={() => handlePrep(session.id)}
                                    disabled={isPrepping}
                                >
                                    {isPrepping ? (
                                        <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                                    ) : (
                                        <Zap className="w-3 h-3 mr-1" />
                                    )}
                                    Prep Context
                                </Button>
                            )}
                        </motion.div>
                    );
                })}
            </div>
        </motion.div>
    );
};
