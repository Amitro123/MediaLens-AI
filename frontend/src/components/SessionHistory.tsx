import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  FileText,
  Clock,
  ExternalLink,
  Bug,
  Sparkles,
  BookOpen,
  Users,
  DollarSign,
  Loader2,
  AlertCircle
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { api, type Session } from "@/api";

// Map backend modes to UI modes
type DocMode = "bug" | "feature" | "technical" | "hr" | "finance";

const modeIcons: Record<DocMode, React.ComponentType<{ className?: string }>> = {
  bug: Bug,
  feature: Sparkles,
  technical: BookOpen,
  hr: Users,
  finance: DollarSign,
};

const modeLabels: Record<DocMode, string> = {
  bug: "Bug Report",
  feature: "Feature Spec",
  technical: "Technical Docs",
  hr: "HR Interview",
  finance: "Finance Review",
};

// Map backend mode strings to UI DocMode
const mapBackendMode = (mode?: string): DocMode => {
  if (!mode) return "technical";
  if (mode.includes("bug")) return "bug";
  if (mode.includes("feature")) return "feature";
  if (mode.includes("hr")) return "hr";
  if (mode.includes("finance")) return "finance";
  return "technical";
};

const formatRelativeTime = (dateStr?: string) => {
  if (!dateStr) return "Unknown";

  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
};

interface SessionHistoryProps {
  onSelectSession?: (session: Session) => void;
}

export const SessionHistory = ({ onSelectSession }: SessionHistoryProps) => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load sessions from API
  useEffect(() => {
    const loadSessions = async () => {
      try {
        setLoading(true);
        const response = await api.listSessions();
        setSessions(response.data || []);
        setError(null);
      } catch (err: any) {
        console.error("Failed to load sessions:", err);
        setError(err.message || "Failed to load sessions");
      } finally {
        setLoading(false);
      }
    };

    loadSessions();
  }, []);

  const handleSessionClick = async (session: Session) => {
    if (onSelectSession) {
      try {
        // Load full session details
        const response = await api.getSession(session.id);
        onSelectSession(response.data);
      } catch (err) {
        console.error("Failed to load session details:", err);
        onSelectSession(session);
      }
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-6 h-6 animate-spin text-primary" />
        <span className="ml-2 text-muted-foreground">Loading sessions...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-8 text-destructive">
        <AlertCircle className="w-5 h-5 mr-2" />
        <span>{error}</span>
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
        <p>No sessions yet. Upload a video to get started!</p>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
      className="space-y-4"
    >
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-foreground">Recent Sessions</h3>
        <Button variant="ghost" size="sm">
          View All
          <ExternalLink className="w-3 h-3 ml-1" />
        </Button>
      </div>

      <div className="space-y-3">
        {sessions.slice(0, 10).map((session, index) => {
          const mode = mapBackendMode(session.mode);
          const Icon = modeIcons[mode];

          return (
            <motion.div
              key={session.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1 + index * 0.05 }}
              className="group p-4 rounded-xl border border-border bg-card hover:border-primary/30 hover:bg-card/80 transition-all cursor-pointer"
              onClick={() => handleSessionClick(session)}
            >
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-lg bg-secondary flex items-center justify-center shrink-0 group-hover:bg-primary/10 transition-colors">
                  <Icon className="w-5 h-5 text-muted-foreground group-hover:text-primary transition-colors" />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h4 className="font-medium text-foreground group-hover:text-primary transition-colors truncate">
                        {session.title || `Session ${session.id.slice(0, 8)}`}
                      </h4>
                      <div className="flex items-center gap-3 mt-1">
                        <span className="text-xs text-muted-foreground flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {formatRelativeTime(session.created_at)}
                        </span>
                        <span className={cn(
                          "text-xs px-1.5 py-0.5 rounded",
                          session.status === "completed" && "bg-green-500/20 text-green-400",
                          session.status === "processing" && "bg-yellow-500/20 text-yellow-400",
                          session.status === "failed" && "bg-red-500/20 text-red-400"
                        )}>
                          {session.status}
                        </span>
                      </div>
                    </div>
                    <Badge
                      variant={
                        mode === "hr" ? "hr" :
                          mode === "finance" ? "finance" : "rnd"
                      }
                      className="shrink-0"
                    >
                      {modeLabels[mode]}
                    </Badge>
                  </div>
                </div>

                <Button
                  variant="ghost"
                  size="icon"
                  className="opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
                >
                  <FileText className="w-4 h-4" />
                </Button>
              </div>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
};
