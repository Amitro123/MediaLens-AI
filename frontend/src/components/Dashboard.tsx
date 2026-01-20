import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { UploadZone } from "./UploadZone";
import { DocModeSelector, type DocMode } from "./DocModeSelector";
import { ProcessingProgress, type ProcessingStep } from "./ProcessingProgress";
import { ExportOptions } from "./ExportOptions";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, type Session } from "@/api";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ResultsView } from "./results/ResultsView";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// Map UI modes to backend mode strings
const modeMap: Record<DocMode, string> = {
  scene_detection: "scene_detection",
  clip_generator: "clip_generator",
  character_tracker: "character_tracker",
  subtitle_extractor: "subtitle_extractor",
};

export const Dashboard = () => {
  const [selectedMode, setSelectedMode] = useState<DocMode>("scene_detection");
  const [projectName, setProjectName] = useState("");
  const [sttProvider, setSttProvider] = useState("auto");
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStep, setProcessingStep] = useState<ProcessingStep>("upload");
  const [progress, setProgress] = useState(0);
  const [stage, setStage] = useState("");  // Backend stage label
  const [showResults, setShowResults] = useState(false);
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [generatedDoc, setGeneratedDoc] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  // Poll for status when processing (with timeout and retry limits)
  useEffect(() => {
    if (!currentTaskId || !isProcessing) return;

    const MAX_RETRIES = 5;
    const MAX_DURATION_MS = 10 * 60 * 1000; // 10 minutes (increased for long videos)
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


  const handleFileSelect = async (file: File) => {
    setIsProcessing(true);
    setShowResults(false);
    setProgress(0);
    setProcessingStep("upload");
    setError(null);

    try {
      const backendMode = modeMap[selectedMode];

      console.log('STT Provider selected:', sttProvider);

      const response = await api.manualUpload(
        file,
        backendMode,
        projectName || undefined,
        sttProvider,
        (uploadPercent) => {
          // Map upload (0-100) to pipeline progress (0-15)
          const mappedProgress = Math.round((uploadPercent / 100) * 15);
          setProgress(mappedProgress);
        }
      );

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
            Start <span className="text-gradient">Analyzing</span>
          </h2>
          <p className="text-muted-foreground max-w-xl mx-auto">
            Upload a video and let AI extract actionable intelligence in minutes
          </p>
        </motion.div>

        <div className="space-y-8">
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

          {/* STT Provider Selection */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="max-w-md"
          >
            <Label className="text-foreground mb-2 block">Transcription Speed</Label>
            <Select value={sttProvider} onValueChange={setSttProvider}>
              <SelectTrigger className="bg-card border-border">
                <SelectValue placeholder="Select speed" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="auto">Auto (Smart choice)</SelectItem>
                <SelectItem value="groq">Fast (Groq - 4 seconds) ⚡</SelectItem>
                <SelectItem value="google">Accurate (Google - 4 minutes) 🎯</SelectItem>
              </SelectContent>
            </Select>
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
          {showResults && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-8"
            >
              {currentTaskId ? (
                <ResultsView sessionId={currentTaskId} />
              ) : (
                // Fallback if no task ID but generic showing
                <div className="glass rounded-2xl p-6 md:p-8">
                  <p>Results ready.</p>
                </div>
              )}

              {/* Legacy Markdown View (Optional Toggle?) - Removing for now as per "DevLens Style" request */}

              {/* Export Options */}
              <ExportOptions sessionId={currentTaskId || undefined} documentation={generatedDoc} />
            </motion.div>
          )}

        </div>
      </div>
    </section>
  );
};
