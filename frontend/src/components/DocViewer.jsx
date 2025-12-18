import { useState, useRef } from 'react'
import { api } from '../api'
import { ThumbsUp, ThumbsDown, MessageSquare, Check, Zap, Server, Database, Activity, Download, Copy, FileText, CheckSquare, Video, ChevronDown, ChevronUp, Play } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

// Utility: Extract timestamp from frame filename
// Handles two patterns:
// 1. New format (dual-stream): frame_0003_t15.5s.jpg -> 15.5 seconds (exact timestamp)
// 2. Legacy format: frame_0012.jpg -> 12 * 5 = 60 seconds (assumes 5-second interval)
function extractTimestampFromFilename(src) {
    if (!src) return null;

    // Pattern 1: Explicit timestamp - frame_XXXX_t15.5s.jpg
    const timestampMatch = src.match(/_t(\d+\.?\d*)s\.(jpg|png|jpeg)/i);
    if (timestampMatch) return parseFloat(timestampMatch[1]);

    // Pattern 2: Frame index only - frame_0012.jpg
    // Legacy videos use 5-second intervals, so frame 12 = 60 seconds
    const frameMatch = src.match(/frame_(\d+)\.(jpg|png|jpeg)/i);
    if (frameMatch) {
        const frameIndex = parseInt(frameMatch[1], 10);
        const FRAME_INTERVAL_SECONDS = 5; // Default interval for legacy frames
        return frameIndex * FRAME_INTERVAL_SECONDS;
    }

    return null;
}

// Utility: Format seconds as MM:SS
function formatTimestamp(seconds) {
    if (seconds === null || isNaN(seconds)) return '';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

export default function DocViewer({ content, taskId, isDevMode }) {
    const [rating, setRating] = useState(null)
    const [comment, setComment] = useState('')
    const [showCommentInput, setShowCommentInput] = useState(false)
    const [submitted, setSubmitted] = useState(false)
    const [feedbackLoading, setFeedbackLoading] = useState(false)
    const [showExportMenu, setShowExportMenu] = useState(false)
    const [exportStatus, setExportStatus] = useState(null)
    const [isVideoExpanded, setIsVideoExpanded] = useState(false)

    const videoRef = useRef(null)
    const pendingSeekRef = useRef(null) // Store pending seek timestamp

    // Seek video to timestamp and play
    const seekToTimestamp = (seconds) => {
        if (seconds === null) return;

        setIsVideoExpanded(true)

        const video = videoRef.current;
        if (!video) {
            // Video not mounted yet, store for later
            pendingSeekRef.current = seconds;
            return;
        }

        // Check if video metadata is loaded
        if (video.readyState >= 1) {
            // Metadata loaded, can seek immediately
            video.currentTime = seconds;
            video.play().catch(() => {
                // Autoplay may be blocked
            });
        } else {
            // Wait for metadata to load
            pendingSeekRef.current = seconds;
            video.addEventListener('loadedmetadata', () => {
                if (pendingSeekRef.current !== null) {
                    video.currentTime = pendingSeekRef.current;
                    video.play().catch(() => { });
                    pendingSeekRef.current = null;
                }
            }, { once: true });
        }
    }

    const handleRate = async (value) => {
        setRating(value)
        if (value === 5) {
            submitFeedback(5)
        } else {
            setShowCommentInput(true)
        }
    }

    const submitFeedback = async (score) => {
        if (!taskId) return

        setFeedbackLoading(true)
        try {
            await api.sendFeedback(taskId, {
                rating: score,
                comment: comment
            })
            setSubmitted(true)
        } catch (err) {
            console.error("Failed to submit feedback:", err)
        } finally {
            setFeedbackLoading(false)
        }
    }

    const handleExport = async (target) => {
        setShowExportMenu(false)
        setExportStatus(`Exporting to ${target}...`)

        if (target === 'clipboard') {
            try {
                await navigator.clipboard.writeText(content)
                setExportStatus('✓ Copied to clipboard!')
                setTimeout(() => setExportStatus(null), 3000)
            } catch (err) {
                setExportStatus('✗ Failed to copy')
                setTimeout(() => setExportStatus(null), 3000)
            }
            return
        }

        try {
            await api.exportSession(taskId, target)
            const targetName = target === 'notion' ? 'Notion' : 'Jira'
            setExportStatus(`✓ Exported to ${targetName}!`)
            setTimeout(() => setExportStatus(null), 3000)
        } catch (err) {
            console.error('Export failed:', err)
            setExportStatus('✗ Export failed')
            setTimeout(() => setExportStatus(null), 3000)
        }
    }

    const telemetry = {
        processingTime: "14.2s",
        cost: "$0.004",
        steps: [
            { name: "Audio Extract", time: "0.8s" },
            { name: "Groq STT", time: "2.1s" },
            { name: "RAG Context", time: "0.5s" },
            { name: "Gemini Pro", time: "10.8s" }
        ],
        contexts: [
            "technical_spec_v2.md",
            "api_routes.py",
            "schema_migration.sql"
        ]
    }

    // Video source URL
    const videoSrc = taskId ? `/uploads/${taskId}/video.mp4` : null

    return (
        <div className="space-y-6">
            {/* Collapsible Video Player */}
            {videoSrc && (
                <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl overflow-hidden">
                    <button
                        onClick={() => setIsVideoExpanded(!isVideoExpanded)}
                        className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-800/50 transition-colors"
                    >
                        <div className="flex items-center gap-2 text-slate-300">
                            <Video className="w-4 h-4 text-indigo-400" />
                            <span className="font-medium text-sm">Source Video</span>
                            <span className="text-xs text-slate-500">Click images to seek</span>
                        </div>
                        {isVideoExpanded ? (
                            <ChevronUp className="w-4 h-4 text-slate-500" />
                        ) : (
                            <ChevronDown className="w-4 h-4 text-slate-500" />
                        )}
                    </button>
                    {isVideoExpanded && (
                        <div className="p-4 pt-0">
                            <video
                                ref={videoRef}
                                src={videoSrc}
                                controls
                                className="w-full max-h-64 rounded-lg bg-black"
                                preload="metadata"
                                onLoadedMetadata={() => {
                                    // Process pending seek when video is ready
                                    if (pendingSeekRef.current !== null && videoRef.current) {
                                        videoRef.current.currentTime = pendingSeekRef.current;
                                        videoRef.current.play().catch(() => { });
                                        pendingSeekRef.current = null;
                                    }
                                }}
                            />
                        </div>
                    )}
                </div>
            )}

            {/* Action Bar */}
            <div className="flex justify-between items-center bg-slate-800/50 p-3 rounded-lg border border-slate-700/50">
                <div className="bg-emerald-900/30 text-emerald-400 text-xs px-3 py-1 rounded-full font-medium flex items-center gap-1 border border-emerald-500/30">
                    <Zap className="w-3 h-3 fill-current" />
                    Saved you ~30 mins
                </div>

                <div className="relative">
                    <button
                        onClick={() => setShowExportMenu(!showExportMenu)}
                        className="flex items-center gap-2 px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium shadow-sm hover:shadow-indigo-500/20"
                    >
                        <Download className="w-4 h-4" />
                        Export
                    </button>
                    {showExportMenu && (
                        <div className="absolute right-0 mt-2 w-48 bg-slate-800 rounded-lg shadow-xl border border-slate-700 py-1 z-10 text-slate-200">
                            <button
                                onClick={() => handleExport('clipboard')}
                                className="w-full px-4 py-2 text-left text-sm hover:bg-slate-700 flex items-center gap-2"
                            >
                                <Copy className="w-4 h-4 text-slate-400" />
                                Copy to Clipboard
                            </button>
                            <button
                                onClick={() => handleExport('notion')}
                                className="w-full px-4 py-2 text-left text-sm hover:bg-slate-700 flex items-center gap-2"
                            >
                                <FileText className="w-4 h-4 text-slate-400" />
                                Send to Notion
                            </button>
                            <button
                                onClick={() => handleExport('jira')}
                                className="w-full px-4 py-2 text-left text-sm hover:bg-slate-700 flex items-center gap-2"
                            >
                                <CheckSquare className="w-4 h-4 text-slate-400" />
                                Create Jira Ticket
                            </button>
                        </div>
                    )}
                </div>
            </div>

            {exportStatus && (
                <div className="text-sm text-center text-slate-300 bg-slate-800/80 px-3 py-1 rounded border border-slate-700">
                    {exportStatus}
                </div>
            )}

            {/* Generated Content with Clickable Images */}
            <div className="prose prose-sm prose-invert max-w-none bg-slate-900/50 p-6 rounded-xl border border-slate-700/50 shadow-inner overflow-x-auto">
                <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                        img: ({ node, src, alt, ...props }) => {
                            const timestamp = extractTimestampFromFilename(src);
                            const hasTimestamp = timestamp !== null;

                            return (
                                <div
                                    className={`relative inline-block my-4 ${hasTimestamp ? 'cursor-pointer group' : ''}`}
                                    onClick={() => hasTimestamp && seekToTimestamp(timestamp)}
                                >
                                    <img
                                        {...props}
                                        src={src}
                                        alt={alt || "Documentation Image"}
                                        className={`rounded-lg shadow-lg border border-slate-700/50 max-w-full transition-all ${hasTimestamp ? 'group-hover:border-indigo-500/50 group-hover:shadow-indigo-500/20' : ''}`}
                                    />
                                    {hasTimestamp && (
                                        <>
                                            {/* Timestamp Badge */}
                                            <span className="absolute top-2 left-2 bg-black/70 text-white text-xs px-2 py-1 rounded-full flex items-center gap-1 backdrop-blur-sm">
                                                <Play className="w-3 h-3 fill-current" />
                                                {formatTimestamp(timestamp)}
                                            </span>
                                            {/* Hover Overlay */}
                                            <div className="absolute inset-0 bg-indigo-500/0 group-hover:bg-indigo-500/10 rounded-lg transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100">
                                                <span className="bg-indigo-600 text-white text-xs px-3 py-1.5 rounded-full font-medium shadow-lg">
                                                    Click to seek
                                                </span>
                                            </div>
                                        </>
                                    )}
                                </div>
                            );
                        },
                        code: ({ node, inline, className, children, ...props }) => {
                            const match = /language-(\w+)/.exec(className || '')
                            return !inline ? (
                                <pre className="bg-slate-950/50 p-4 rounded-lg overflow-x-auto border border-slate-800/50 my-4">
                                    <code className={className} {...props}>
                                        {children}
                                    </code>
                                </pre>
                            ) : (
                                <code className="bg-slate-800 px-1.5 py-0.5 rounded text-indigo-300 font-mono text-xs" {...props}>
                                    {children}
                                </code>
                            )
                        }
                    }}
                >
                    {content}
                </ReactMarkdown>
            </div>


            {/* DevStats Panel */}
            {isDevMode && (
                <div className="bg-slate-900/80 backdrop-blur text-slate-300 rounded-xl p-5 font-mono text-xs shadow-xl border border-slate-700/80">
                    <div className="flex items-center gap-2 mb-4 text-indigo-400 font-bold border-b border-slate-700/50 pb-2">
                        <Activity className="w-4 h-4" />
                        SYSTEM TELEMETRY
                        <span className="text-xs text-slate-500 font-normal">(Mock Data)</span>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                        <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700/30">
                            <div className="text-slate-500 mb-1">Total Time</div>
                            <div className="text-lg font-bold text-white">{telemetry.processingTime}</div>
                        </div>
                        <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700/30">
                            <div className="text-slate-500 mb-1">Est. Cost</div>
                            <div className="text-lg font-bold text-emerald-400">{telemetry.cost}</div>
                        </div>
                        <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700/30 col-span-2">
                            <div className="text-slate-500 mb-1">Model Config</div>
                            <div className="text-white">Gemini 1.5 Pro (temperature=0.2)</div>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <div className="text-slate-500 mb-2 flex items-center gap-2">
                                <Server className="w-3 h-3" />
                                Pipeline Latency
                            </div>
                            <div className="space-y-1">
                                {telemetry.steps.map((step, idx) => (
                                    <div key={idx} className="flex items-center justify-between bg-slate-800/30 px-3 py-1.5 rounded border border-slate-700/30">
                                        <span>{step.name}</span>
                                        <span className="text-indigo-300">{step.time}</span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div>
                            <div className="text-slate-500 mb-2 flex items-center gap-2">
                                <Database className="w-3 h-3" />
                                RAG Sources
                            </div>
                            <div className="flex flex-wrap gap-2">
                                {telemetry.contexts.map((ctx, idx) => (
                                    <span key={idx} className="bg-indigo-900/30 text-indigo-300 px-2 py-1 rounded text-[10px] border border-indigo-500/20">
                                        {ctx}
                                    </span>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Feedback UI */}
            <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-5">
                <div className="flex items-center justify-between">
                    <span className="font-medium text-slate-300">How would you rate this documentation?</span>

                    {!submitted ? (
                        <div className="flex gap-2">
                            <button
                                onClick={() => handleRate(5)}
                                className={`p-2 rounded-full hover:bg-emerald-500/20 transition-all ${rating === 5 ? 'bg-emerald-500/20 text-emerald-400 ring-1 ring-emerald-500/50' : 'text-slate-500 hover:text-emerald-400'}`}
                            >
                                <ThumbsUp className="w-5 h-5" />
                            </button>
                            <button
                                onClick={() => handleRate(1)}
                                className={`p-2 rounded-full hover:bg-red-500/20 transition-all ${rating === 1 ? 'bg-red-500/20 text-red-400 ring-1 ring-red-500/50' : 'text-slate-500 hover:text-red-400'}`}
                            >
                                <ThumbsDown className="w-5 h-5" />
                            </button>
                        </div>
                    ) : (
                        <div className="flex items-center gap-2 text-emerald-400 font-medium animate-in fade-in">
                            <Check className="w-4 h-4" />
                            Thanks for your feedback!
                        </div>
                    )}
                </div>

                {showCommentInput && !submitted && (
                    <div className="mt-4 animate-in fade-in slide-in-from-top-2">
                        <textarea
                            value={comment}
                            onChange={(e) => setComment(e.target.value)}
                            placeholder="How can we improve this? (Optional)"
                            className="w-full text-sm p-3 bg-slate-900/50 border border-slate-700 rounded-lg text-slate-200 placeholder-slate-500 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
                            rows={3}
                        />
                        <div className="mt-2 flex justify-end">
                            <button
                                onClick={() => submitFeedback(rating)}
                                disabled={feedbackLoading}
                                className="bg-indigo-600 text-white text-sm px-4 py-2 rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors shadow-lg shadow-indigo-500/20"
                            >
                                {feedbackLoading ? "Sending..." : "Submit Feedback"}
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
