import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { UploadZone } from "./UploadZone";
import { DocModeSelector, type DocMode } from "./DocModeSelector";
import { ProcessingProgress, type ProcessingStep } from "./ProcessingProgress";
import { SessionHistory } from "./SessionHistory";
import { SessionDetails } from "./SessionDetails";
import { CalendarDashboard } from "./CalendarDashboard";
import { ExportOptions } from "./ExportOptions";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, type Session } from "@/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// Map UI modes to backend mode strings
const modeMap: Record<DocMode, string> = {
  bug: "bug_report",
  feature: "feature_kickoff",
  technical: "general_doc",
  hr: "hr_interview",
  finance: "finance_review",
};

export const Dashboard = () => {
  const [selectedMode, setSelectedMode] = useState<DocMode>("technical");
  const [projectName, setProjectName] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStep, setProcessingStep] = useState<ProcessingStep>("upload");
  const [progress, setProgress] = useState(0);
  const [stage, setStage] = useState("");  // Backend stage label
  const [showResults, setShowResults] = useState(false);
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [generatedDoc, setGeneratedDoc] = useState<string>("");
  const [selectedSession, setSelectedSession] = useState<Session | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Poll for status when processing (with timeout and retry limits)
  useEffect(() => {
    if (!currentTaskId || !isProcessing) return;

    const MAX_RETRIES = 5;
    const MAX_DURATION_MS = 5 * 60 * 1000; // 5 minutes
    let retryCount = 0;
    const startTime = Date.now();

    const pollStatus = async () => {
      // Check timeout
      if (Date.now() - startTime > MAX_DURATION_MS) {
        setError("Processing timed out. Please try again.");
        setIsProcessing(false);
        return;
      }

      try {
        const response = await api.getStatus(currentTaskId);
        const { status, progress: serverProgress, stage: serverStage } = response.data;

        // Reset retry count on success
        retryCount = 0;

        setProgress(serverProgress);
        if (serverStage) setStage(serverStage);

        // Map status to step
        if (serverProgress < 20) setProcessingStep("upload");
        else if (serverProgress < 40) setProcessingStep("transcribe");
        else if (serverProgress < 70) setProcessingStep("analyze");
        else if (serverProgress < 100) setProcessingStep("generate");
        else setProcessingStep("complete");

        // Check if complete
        if (status === "completed" || serverProgress >= 100) {
          const resultResponse = await api.getResult(currentTaskId);
          setGeneratedDoc(resultResponse.data.documentation);
          setIsProcessing(false);
          setShowResults(true);
          setProcessingStep("complete");
          return; // Stop polling
        }

        if (status === "failed") {
          setError("Processing failed. Please try again.");
          setIsProcessing(false);
          return;
        }
      } catch (err: any) {
        console.error("Status poll error:", err);
        retryCount++;
        if (retryCount >= MAX_RETRIES) {
          setError("Unable to reach server. Please check your connection and try again.");
          setIsProcessing(false);
          return;
        }
      }
    };

    const interval = setInterval(pollStatus, 2000);
    return () => clearInterval(interval);
  }, [currentTaskId, isProcessing]);

  // Check for active session on mount
  useEffect(() => {
    const checkActiveSession = async () => {
      try {
        const response = await api.getActiveSession();
        if (response.data) {
          const { session_id, progress: sessionProgress, stage: sessionStage } = response.data;
          setCurrentTaskId(session_id);
          setIsProcessing(true);
          setProgress(sessionProgress);
          if (sessionStage) setStage(sessionStage);

          // Derive processing step from progress to avoid UI flash
          if (sessionProgress < 20) setProcessingStep("upload");
          else if (sessionProgress < 40) setProcessingStep("transcribe");
          else if (sessionProgress < 70) setProcessingStep("analyze");
          else if (sessionProgress < 100) setProcessingStep("generate");
          else setProcessingStep("complete");
        }
      } catch (err) {
        // No active session, that's fine
      }
    };

    checkActiveSession();
  }, []);

  const handleFileSelect = async (file: File) => {
    setIsProcessing(true);
    setShowResults(false);
    setProgress(0);
    setProcessingStep("upload");
    setError(null);

    try {
      const backendMode = modeMap[selectedMode];
      const response = await api.manualUpload(file, backendMode, projectName || undefined);

      const { task_id, status, result } = response.data;
      setCurrentTaskId(task_id);

      // If already completed (short video), show result immediately
      if (status === "completed" && result) {
        setGeneratedDoc(result);
        setIsProcessing(false);
        setShowResults(true);
        setProcessingStep("complete");
        setProgress(100);
      }
    } catch (err: any) {
      console.error("Upload error:", err);
      setError(err.response?.data?.detail || err.message || "Upload failed");
      setIsProcessing(false);
    }
  };

  const handleSessionSelect = (session: Session) => {
    setSelectedSession(session);
    // Reset the upload/results view when viewing a session from history
    setShowResults(false);
    setGeneratedDoc("");
  };

  const handleCloseSession = () => {
    setSelectedSession(null);
  };

  return (
    <section id="dashboard" className="py-24 px-4">
      <div className="max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-12"
        >
          <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
            Start <span className="text-gradient">Documenting</span>
          </h2>
          <p className="text-muted-foreground max-w-xl mx-auto">
            Upload a video and let AI create professional documentation in minutes
          </p>
        </motion.div>

        {/* Show SessionDetails if a session is selected, otherwise show upload UI */}
        {selectedSession ? (
          <SessionDetails session={selectedSession} onClose={handleCloseSession} />
        ) : (
          <div className="space-y-8">
            {/* Calendar Dashboard - Upcoming Meetings */}
            <CalendarDashboard />

            {/* Doc Mode Selector */}
            <DocModeSelector selected={selectedMode} onSelect={setSelectedMode} />

            {/* Project Name Input */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="max-w-md"
            >
              <Label htmlFor="project" className="text-foreground mb-2 block">
                Project Name (Optional)
              </Label>
              <Input
                id="project"
                placeholder="e.g., Auth System Refactor"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                className="bg-card border-border focus:border-primary"
              />
            </motion.div>

            {/* Error Display */}
            {error && (
              <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-4 text-destructive">
                {error}
              </div>
            )}

            {/* Upload Zone or Processing Progress */}
            {isProcessing ? (
              <ProcessingProgress currentStep={processingStep} progress={progress} stage={stage} />
            ) : (
              <UploadZone onFileSelect={handleFileSelect} />
            )}

            {/* Results Section */}
            {showResults && generatedDoc && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-8"
              >
                {/* Documentation Preview */}
                <div className="glass rounded-2xl p-6 md:p-8">
                  <h3 className="text-lg font-semibold text-foreground mb-4">Generated Documentation</h3>
                  <div className="prose prose-invert max-w-none bg-secondary/50 rounded-lg p-6 overflow-auto max-h-[600px]">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {generatedDoc}
                    </ReactMarkdown>
                  </div>
                </div>

                {/* Export Options */}
                <ExportOptions sessionId={currentTaskId || undefined} documentation={generatedDoc} />
              </motion.div>
            )}

            {/* Session History - connected to API */}
            <SessionHistory onSelectSession={handleSessionSelect} />
          </div>
        )}
      </div>
    </section>
  );
};
