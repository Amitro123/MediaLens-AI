import { useRef, useState } from 'react'
import { CheckCircle, Circle, Clock, FileText, Download, List, Video, Play, ChevronLeft, Code, Terminal } from 'lucide-react'
import DocViewer from './DocViewer'
import { DEV_MODE_ENABLED } from '../config'

export default function SessionDetails({ session, onBack, devMode = false }) {
    const videoRef = useRef(null)
    const [showDevPanel, setShowDevPanel] = useState(false)

    // Seek Handler
    const handleSeek = (time) => {
        if (videoRef.current) {
            videoRef.current.currentTime = time;
            videoRef.current.play().catch(e => console.warn("Autoplay blocked:", e));
        }
    };

    // Export JSON Handler
    const handleExportJson = () => {
        if (!session) return;
        const blob = new Blob(
            [JSON.stringify(session, null, 2)],
            { type: "application/json" }
        );
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `session-${session.id}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    if (!session) return null;

    const stages = session.pipeline_stages || { stt: 'pending', analysis: 'pending', generation: 'pending' };
    const videoUrl = session.video_url ? `http://localhost:8000${session.video_url}` : null;
    const frames = session.key_frames || session.frames || [];
    const segments = session.segments || [];

    // Determine document content - check both result and doc_markdown
    const docContent = session.result || session.doc_markdown || '';
    const hasDoc = docContent.length > 0;

    // Determine if we are still processing
    const isProcessingDoc = !hasDoc && session.status !== 'completed' && session.status !== 'failed';

    // Format time as mm:ss
    const formatTime = (seconds) => {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-20">
            {/* Header / Meta Info */}
            <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-6 backdrop-blur-sm">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6 border-b border-slate-700/50 pb-6">
                    <div className="flex items-start gap-4">
                        {onBack && (
                            <button
                                onClick={onBack}
                                className="md:hidden p-2 rounded-lg bg-slate-700 text-slate-300 hover:text-white mt-1"
                            >
                                <ChevronLeft className="w-5 h-5" />
                            </button>
                        )}
                        <div>
                            <div className="flex items-center gap-2 mb-2">
                                <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-indigo-500/20 text-indigo-300 border border-indigo-500/20">
                                    {session.mode_name || session.mode}
                                </span>
                                <span className="text-slate-500 text-xs">• {new Date(session.created_at).toLocaleString()}</span>
                            </div>
                            <h1 className="text-2xl font-bold text-white">{session.title}</h1>
                        </div>
                    </div>
                    {/* Status Badge */}
                    <div className="flex gap-2">
                        {session.status === 'completed' || hasDoc ? (
                            <span className="px-3 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-lg text-sm font-medium flex items-center gap-2">
                                <CheckCircle className="w-4 h-4" /> Completed
                            </span>
                        ) : session.status === 'failed' ? (
                            <span className="px-3 py-1 bg-red-500/10 text-red-400 border border-red-500/20 rounded-lg text-sm font-medium flex items-center gap-2">
                                <Circle className="w-4 h-4" /> Failed
                            </span>
                        ) : (
                            <span className="px-3 py-1 bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded-lg text-sm font-medium flex items-center gap-2">
                                <Clock className="w-4 h-4 animate-pulse" /> Processing
                            </span>
                        )}
                    </div>
                </div>

                {/* Pipeline Status & Turn Log */}
                <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                    <div className="flex flex-wrap gap-2">
                        <StatusChip label="1. Fast STT" status={stages.stt} />
                        <StatusChip label="2. Agent Analysis" status={stages.analysis} />
                        <StatusChip label="3. Doc Generated" status={stages.generation} />
                    </div>

                    {session.turn_log_path && (
                        <a
                            href={`http://localhost:8000${session.turn_log_path}`}
                            target="_blank"
                            rel="noreferrer"
                            className="flex items-center gap-2 text-xs font-medium text-slate-400 hover:text-indigo-400 transition-colors px-3 py-1.5 rounded-lg hover:bg-slate-700/50"
                        >
                            <Download className="w-4 h-4" />
                            Download Turn Log (JSONL)
                        </a>
                    )}

                    {/* Export Buttons */}
                    <div className="flex gap-2">
                        <button
                            onClick={handleExportJson}
                            className="flex items-center gap-2 text-xs font-medium text-slate-400 hover:text-indigo-400 transition-colors px-3 py-1.5 rounded-lg hover:bg-slate-700/50 border border-slate-700/50"
                        >
                            <Code className="w-4 h-4" />
                            Export JSON
                        </button>
                        {DEV_MODE_ENABLED && (
                            <button
                                onClick={() => setShowDevPanel(!showDevPanel)}
                                className={`flex items-center gap-2 text-xs font-medium transition-colors px-3 py-1.5 rounded-lg border ${showDevPanel ? 'bg-amber-500/20 text-amber-400 border-amber-500/30' : 'text-slate-400 hover:text-amber-400 hover:bg-slate-700/50 border-slate-700/50'}`}
                            >
                                <Terminal className="w-4 h-4" />
                                {showDevPanel ? 'Dev Mode: ON' : 'Dev Mode'}
                            </button>
                        )}
                    </div>
                </div>
            </div>

            {/* Video Player Section */}
            {videoUrl && (
                <div className="bg-slate-900/80 border border-slate-700/50 rounded-xl overflow-hidden p-4">
                    <div className="flex items-center gap-2 text-slate-300 mb-3">
                        <Video className="w-4 h-4 text-indigo-400" />
                        <span className="font-medium text-sm">Session Recording</span>
                    </div>
                    <video
                        ref={videoRef}
                        src={videoUrl}
                        controls
                        className="w-full max-h-[400px] rounded-lg bg-black shadow-2xl"
                    />
                </div>
            )}

            {/* Frames Gallery */}
            {frames.length > 0 && (
                <div className="space-y-3">
                    <div className="flex items-center justify-between px-1">
                        <h3 className="text-sm font-medium text-slate-400">Key Moments (Click to Seek)</h3>
                        <span className="text-xs text-slate-600">{frames.length} key moments</span>
                    </div>
                    <div className="flex gap-4 overflow-x-auto pb-4 snap-x pr-4 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent">
                        {frames.map((frame, idx) => (
                            <button
                                key={idx}
                                onClick={() => handleSeek(frame.timestamp_sec)}
                                className="group relative flex-none snap-start"
                            >
                                <div className="w-48 aspect-video rounded-xl overflow-hidden border border-slate-700/50 group-hover:border-indigo-500/50 transition-all relative shadow-lg group-hover:shadow-indigo-500/10">
                                    <img
                                        src={`http://localhost:8000${frame.thumbnail_url}`}
                                        alt={`Time ${frame.label}`}
                                        className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity"
                                        loading="lazy"
                                    />
                                    <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/40">
                                        <div className="bg-indigo-600 rounded-full p-2 shadow-xl scale-90 group-hover:scale-100 transition-transform">
                                            <Play className="w-4 h-4 fill-white text-white" />
                                        </div>
                                    </div>
                                    <span className="absolute bottom-2 right-2 bg-black/80 backdrop-blur-sm text-white text-[10px] px-2 py-0.5 rounded-full font-bold border border-white/10">
                                        {frame.label}
                                    </span>
                                </div>
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Timeline / Transcript Section */}
            {segments.length > 0 && (
                <div className="space-y-3">
                    <div className="flex items-center justify-between px-1">
                        <h3 className="text-sm font-medium text-slate-400 flex items-center gap-2">
                            <List className="w-4 h-4" />
                            Timeline / Transcript
                        </h3>
                        <span className="text-xs text-slate-600">{segments.length} segments</span>
                    </div>
                    <div className="bg-slate-800/30 border border-slate-700/50 rounded-xl max-h-64 overflow-y-auto scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent">
                        {segments.map((seg, idx) => (
                            <button
                                key={idx}
                                onClick={() => handleSeek(seg.start_sec)}
                                className="w-full flex items-start gap-3 px-4 py-3 hover:bg-slate-700/30 transition-colors border-b border-slate-700/30 last:border-b-0 text-left"
                            >
                                <span className="text-xs font-mono text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded flex-shrink-0">
                                    {formatTime(seg.start_sec)}
                                </span>
                                <span className="text-sm text-slate-300 leading-relaxed">
                                    {seg.text}
                                </span>
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Document Viewer */}
            <div className="pt-4">
                {hasDoc ? (
                    <div className="space-y-4">
                        <div className="flex items-center gap-2 text-indigo-300 px-1">
                            <FileText className="w-5 h-5" />
                            <h2 className="text-lg font-bold">Generated Technical Document</h2>
                        </div>
                        <div className="bg-slate-800/20 border border-slate-700/30 rounded-2xl overflow-hidden">
                            <DocViewer
                                content={docContent}
                                taskId={session.id}
                                isDevMode={false}
                            />
                        </div>
                    </div>
                ) : isProcessingDoc ? (
                    <div className="bg-slate-800/20 border-2 border-dashed border-slate-700/50 rounded-2xl p-16 text-center text-slate-500">
                        <div className="relative w-16 h-16 mx-auto mb-6">
                            <FileText className="w-16 h-16 opacity-20" />
                            <div className="absolute inset-0 flex items-center justify-center">
                                <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
                            </div>
                        </div>
                        <h3 className="text-xl font-bold text-slate-300 mb-2">Analyzing Session Data...</h3>
                        <p className="max-w-xs mx-auto text-sm">The AI agent is currently generating your technical documentation. This usually takes 30-60 seconds.</p>
                    </div>
                ) : session.status === 'failed' ? (
                    <div className="bg-red-900/20 border border-red-500/30 rounded-2xl p-12 text-center text-red-400">
                        <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
                        <h3 className="text-lg font-medium">Session Failed</h3>
                        <p className="text-sm text-red-300/70">Please check backend logs for details.</p>
                    </div>
                ) : (
                    <div className="bg-slate-800/20 border border-slate-700/50 rounded-2xl p-12 text-center text-slate-500">
                        <FileText className="w-12 h-12 mx-auto mb-4 opacity-30" />
                        <h3 className="text-lg font-medium text-slate-400">Documentation Not Available</h3>
                        <p className="text-sm">This session might have failed during generation or was interrupted.</p>
                    </div>
                )}
            </div>

            {/* Dev Mode Panel */}
            {DEV_MODE_ENABLED && showDevPanel && (
                <div className="bg-slate-900/80 border border-amber-500/30 rounded-xl p-4 space-y-4">
                    <div className="flex items-center gap-2 text-amber-400">
                        <Terminal className="w-5 h-5" />
                        <h3 className="font-bold">Dev Mode – Raw Session JSON</h3>
                    </div>
                    <pre className="bg-black/50 rounded-lg p-4 text-xs text-slate-300 overflow-auto max-h-96 font-mono">
                        {JSON.stringify(session, null, 2)}
                    </pre>
                    {session.metrics && (
                        <div className="border-t border-amber-500/20 pt-4">
                            <h4 className="text-sm font-medium text-amber-300 mb-2">Pipeline Metrics</h4>
                            <ul className="text-xs text-slate-400 space-y-1">
                                {session.metrics.stt_ms && <li>STT duration: {session.metrics.stt_ms} ms</li>}
                                {session.metrics.doc_ms && <li>Doc generation: {session.metrics.doc_ms} ms</li>}
                                {session.metrics.total_ms && <li>Total: {session.metrics.total_ms} ms</li>}
                            </ul>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

// Sub-component for status chips
function StatusChip({ label, status }) {
    let icon = <Circle className="w-4 h-4 text-slate-600" />;
    let textColor = "text-slate-500";
    let borderColor = "border-slate-700/50";
    let bgColor = "bg-slate-800/50";

    if (status === 'completed') {
        icon = <CheckCircle className="w-4 h-4 text-emerald-400" />;
        textColor = "text-slate-200";
        borderColor = "border-emerald-500/30";
        bgColor = "bg-emerald-500/5";
    } else if (status === 'processing') {
        icon = <Clock className="w-4 h-4 text-indigo-400 animate-pulse" />;
        textColor = "text-indigo-200";
        borderColor = "border-indigo-500/50";
        bgColor = "bg-indigo-500/10";
    }

    return (
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full border ${borderColor} ${bgColor} backdrop-blur-sm transition-all`}>
            {icon}
            <span className={`text-[10px] font-bold uppercase tracking-tight ${textColor}`}>{label}</span>
        </div>
    );
}
