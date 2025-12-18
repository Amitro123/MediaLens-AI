import { useState, useEffect, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { api } from '../api'
import { Upload, FileVideo, Loader2, CheckCircle, XCircle } from 'lucide-react'
import DocViewer from './DocViewer'

const PROCESSING_STEPS = [
    "Uploading video...",
    "Analyzing audio tracks...",
    "Filtering relevant segments...",
    "Extracting key frames...",
    "Generating documentation..."
]

export default function UploadForm({ session = null, isDevMode = false }) {
    const [modes, setModes] = useState([])
    const [selectedMode, setSelectedMode] = useState('general_doc')
    const [projectName, setProjectName] = useState('')
    const [language, setLanguage] = useState('en')
    const [videoFile, setVideoFile] = useState(null)
    const [driveUrl, setDriveUrl] = useState('')
    const [uploadMode, setUploadMode] = useState('file')
    const [uploading, setUploading] = useState(false)
    const [progress, setProgress] = useState(0)
    const [result, setResult] = useState(null)
    const [error, setError] = useState(null)
    const [statusMessage, setStatusMessage] = useState("")

    useEffect(() => {
        if (session) {
            setProjectName(session.title)
            if (session.suggested_mode) {
                setSelectedMode(session.suggested_mode)
            }

            // Recovery logic: if the session passed from parent is already active
            const activeStatuses = ['processing', 'downloading_from_drive', 'uploading'];
            if (activeStatuses.includes(session.status)) {
                console.log("Attaching to active session:", session.id);
                setUploading(true);
                setStatusMessage("Re-attaching to session...");
                pollActiveSession(session.id);
            }
        }
    }, [session])

    useEffect(() => {
        fetchModes()
    }, [])

    const fetchModes = async () => {
        try {
            const data = await api.getModes()
            setModes(data.modes || [])
        } catch (err) {
            console.error('Failed to fetch modes:', err)
            setModes([
                { mode: 'general_doc', name: 'Technical Documentation', description: 'General documentation', department: 'R&D' },
                { mode: 'bug_report', name: 'Bug Report', description: 'Bug analysis', department: 'R&D' },
                { mode: 'feature_spec', name: 'Feature Spec', description: 'Feature requirements', department: 'R&D' },
                { mode: 'hr_interview', name: 'Candidate Review', description: 'Interview summary', department: 'HR' }
            ])
        }
    }

    const onDrop = useCallback((acceptedFiles) => {
        if (acceptedFiles.length > 0) {
            setVideoFile(acceptedFiles[0])
            setError(null)
            setResult(null)
        }
    }, [])

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            'video/*': ['.mp4', '.mov', '.avi', '.webm']
        },
        maxFiles: 1,
        multiple: false
    })

    const handleSubmit = async (e) => {
        e.preventDefault()

        const hasInput = uploadMode === 'drive' ? driveUrl.trim() : videoFile
        if (!hasInput) {
            setError(uploadMode === 'drive' ? 'Please enter a Drive URL' : 'Please select a video file')
            return
        }

        setUploading(true)
        setProgress(0)
        setError(null)
        setResult(null)
        setStatusMessage(PROCESSING_STEPS[0])

        try {
            let stepIndex = 0
            const progressInterval = setInterval(() => {
                setProgress(prev => {
                    const next = Math.min(prev + 5, 90)
                    if (next > 20 && stepIndex === 0) { stepIndex = 1; setStatusMessage(PROCESSING_STEPS[1]) }
                    else if (next > 40 && stepIndex === 1) { stepIndex = 2; setStatusMessage(PROCESSING_STEPS[2]) }
                    else if (next > 60 && stepIndex === 2) { stepIndex = 3; setStatusMessage(PROCESSING_STEPS[3]) }
                    else if (next > 80 && stepIndex === 3) { stepIndex = 4; setStatusMessage(PROCESSING_STEPS[4]) }
                    return next
                })
            }, 600)

            let data;

            if (uploadMode === 'drive') {
                if (!session) {
                    throw new Error("Drive import currently requires an active session context.")
                }
                data = await api.uploadFromDrive({
                    url: driveUrl,
                    session_id: session.id
                })
            } else {
                const formData = new FormData()
                formData.append('file', videoFile)

                if (session) {
                    formData.append('mode', selectedMode)
                    data = await api.uploadToSession(session.id, formData)
                } else {
                    formData.append('project_name', projectName || 'Untitled Project')
                    formData.append('language', language)
                    formData.append('mode', selectedMode)
                    data = await api.manualUpload(formData)
                }
            }

            clearInterval(progressInterval)
            setProgress(100)
            setResult(data)

        } catch (err) {
            console.error(err)
            setError(err.response?.data?.detail || err.message || 'Upload failed. Please try again.')
        } finally {
            setUploading(false)
        }
    }

    const pollActiveSession = async (taskId) => {
        // Polling interval
        const interval = setInterval(async () => {
            try {
                const statusData = await api.getStatus(taskId);
                console.log("Polling status:", statusData);

                if (statusData.status === 'completed') {
                    clearInterval(interval);
                    setStatusMessage("Finalizing...");
                    const resultData = await api.getResult(taskId);
                    setResult({ result: resultData.documentation, task_id: taskId });
                    setUploading(false);
                    setProgress(100);
                } else if (statusData.status === 'failed') {
                    clearInterval(interval);
                    setError(statusData.error || 'The background job failed.');
                    setUploading(false);
                } else {
                    // Update progress incrementally
                    setProgress(prev => Math.min(prev + 2, 95));
                    if (statusData.status === 'downloading_from_drive') {
                        setStatusMessage("Downloading from Drive...");
                    } else {
                        setStatusMessage("Processing video pipeline...");
                    }
                }
            } catch (err) {
                console.error("Polling error:", err);
            }
        }, 3000);

        // Cleanup on unmount
        return () => clearInterval(interval);
    }

    const resetForm = () => {
        setVideoFile(null)
        setDriveUrl('')
        setUploadMode('file')
        setProjectName('')
        setResult(null)
        setError(null)
        setProgress(0)
    }

    // Input classes for Dark Theme
    const inputClasses = "w-full px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-100 placeholder-slate-400 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
    const labelClasses = "block text-sm font-medium text-slate-300 mb-2"

    return (
        <div className="space-y-6">
            {/* Tab Navigation */}
            <div className="flex bg-slate-700/30 p-1 rounded-lg">
                <button
                    type="button"
                    onClick={() => { setUploadMode('file'); setError(null); }}
                    className={`flex-1 px-4 py-2 text-sm font-medium rounded-md transition-all ${uploadMode === 'file'
                        ? 'bg-indigo-600 text-white shadow-lg'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/50'
                        }`}
                >
                    Upload Video
                </button>
                <button
                    type="button"
                    onClick={() => { setUploadMode('drive'); setError(null); }}
                    className={`flex-1 px-4 py-2 text-sm font-medium rounded-md transition-all ${uploadMode === 'drive'
                        ? 'bg-indigo-600 text-white shadow-lg'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/50'
                        }`}
                >
                    Import from Drive
                </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">

                {/* Documentation Mode */}
                <div>
                    <label className={labelClasses}>Documentation Mode</label>
                    <div className="relative">
                        <select
                            value={selectedMode}
                            onChange={(e) => setSelectedMode(e.target.value)}
                            className={inputClasses + " appearance-none"}
                            disabled={uploading}
                        >
                            {/* Group modes by department */}
                            {['R&D', 'HR', 'Finance'].map(dept => {
                                const deptModes = modes.filter(m => m.department === dept)
                                if (deptModes.length === 0) return null

                                return (
                                    <optgroup key={dept} label={`${dept} Department`} className="bg-slate-800 text-slate-300">
                                        {deptModes.map((mode) => (
                                            <option key={mode.mode} value={mode.mode}>
                                                {mode.name}
                                            </option>
                                        ))}
                                    </optgroup>
                                )
                            })}
                            {/* Fallback if no department found */}
                            {modes.filter(m => !m.department).map(mode => (
                                <option key={mode.mode} value={mode.mode}>{mode.name}</option>
                            ))}
                        </select>
                        <div className="absolute inset-y-0 right-0 flex items-center px-4 pointer-events-none text-slate-400">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" /></svg>
                        </div>
                    </div>
                </div>

                {/* Project Name & Language Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label className={labelClasses}>Project Name (Optional)</label>
                        <input
                            type="text"
                            value={projectName}
                            onChange={(e) => setProjectName(e.target.value)}
                            placeholder="My Awesome Project"
                            className={inputClasses}
                            disabled={uploading}
                        />
                    </div>

                    <div>
                        <label className={labelClasses}>Language</label>
                        <div className="relative">
                            <select
                                value={language}
                                onChange={(e) => setLanguage(e.target.value)}
                                className={inputClasses + " appearance-none"}
                                disabled={uploading}
                            >
                                <option value="en">English</option>
                                <option value="he">Hebrew</option>
                            </select>
                            <div className="absolute inset-y-0 right-0 flex items-center px-4 pointer-events-none text-slate-400">
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" /></svg>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Upload Area */}
                <div className="bg-slate-800/50 rounded-xl p-1 border border-slate-700/50">
                    {uploadMode === 'drive' ? (
                        <div className="p-4">
                            <label className={labelClasses}>Google Drive Link</label>
                            <input
                                type="text"
                                value={driveUrl}
                                placeholder="https://drive.google.com/file/d/..."
                                onChange={(e) => setDriveUrl(e.target.value)}
                                className={inputClasses}
                                disabled={uploading}
                            />
                            <p className="mt-2 text-xs text-slate-500">
                                Paste a public link or ensure the file is shared with the service account.
                            </p>
                        </div>
                    ) : (
                        <div className="p-1">
                            <div
                                {...getRootProps()}
                                className={`border-2 border-dashed rounded-lg p-10 text-center cursor-pointer transition-all duration-300 ${isDragActive
                                    ? 'border-indigo-500 bg-indigo-500/10'
                                    : 'border-slate-600/50 hover:border-indigo-500/50 hover:bg-slate-700/30'
                                    } ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}
                            >
                                <input {...getInputProps()} disabled={uploading} />
                                {videoFile ? (
                                    <div className="flex flex-col items-center justify-center gap-3 text-emerald-400 animate-in fade-in zoom-in duration-300">
                                        <div className="w-12 h-12 rounded-full bg-emerald-500/20 flex items-center justify-center">
                                            <FileVideo className="w-6 h-6" />
                                        </div>
                                        <div>
                                            <p className="font-medium text-lg">{videoFile.name}</p>
                                            <span className="text-sm text-slate-500">
                                                ({(videoFile.size / 1024 / 1024).toFixed(2)} MB)
                                            </span>
                                        </div>
                                        <button
                                            type="button"
                                            onClick={(e) => { e.stopPropagation(); setVideoFile(null); }}
                                            className="text-xs text-slate-400 hover:text-white underline mt-2"
                                        >
                                            Change File
                                        </button>
                                    </div>
                                ) : (
                                    <div className="space-y-4">
                                        <div className="w-16 h-16 rounded-full bg-slate-700/50 flex items-center justify-center mx-auto text-slate-400 group-hover:text-indigo-400 transition-colors">
                                            <Upload className="w-8 h-8" />
                                        </div>
                                        <div>
                                            <p className="text-slate-300 font-medium text-lg">
                                                {isDragActive ? 'Drop it like it\'s hot!' : 'Click or Drag Video Here'}
                                            </p>
                                            <p className="text-sm text-slate-500 mt-1">
                                                MP4, MOV, AVI, WEBM (Max 15 min)
                                            </p>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>

                {/* Submit Button */}
                <button
                    type="submit"
                    disabled={!(uploadMode === 'drive' ? driveUrl.trim() : videoFile) || uploading}
                    className="w-full bg-gradient-to-r from-indigo-600 to-violet-600 text-white py-4 px-6 rounded-xl font-bold hover:shadow-lg hover:shadow-indigo-500/25 disabled:opacity-50 disabled:cursor-not-allowed transition-all active:scale-[0.98] flex items-center justify-center gap-3"
                >
                    {uploading ? (
                        <>
                            <Loader2 className="w-5 h-5 animate-spin" />
                            <span>{statusMessage || "Processing..."}</span>
                        </>
                    ) : (
                        <>
                            {uploadMode === 'drive' ? (
                                <><Upload className="w-5 h-5" /> Import & Analyze</>
                            ) : (
                                <><Upload className="w-5 h-5" /> Generate Documentation</>
                            )}
                        </>
                    )}
                </button>
            </form>

            {/* Progress Bar */}
            {uploading && (
                <div className="space-y-2 animate-in fade-in slide-in-from-bottom-2">
                    <div className="flex justify-between text-xs text-slate-400 uppercase tracking-wide font-medium">
                        <span>{statusMessage}</span>
                        <span>{progress}%</span>
                    </div>
                    <div className="w-full bg-slate-700 rounded-full h-2 overflow-hidden">
                        <div
                            className="bg-indigo-500 h-2 rounded-full transition-all duration-300 relative overflow-hidden"
                            style={{ width: `${progress}%` }}
                        >
                            <div className="absolute inset-0 bg-white/20 animate-[shimmer_2s_infinite] w-full" style={{ backgroundImage: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.5), transparent)' }}></div>
                        </div>
                    </div>
                </div>
            )}

            {/* Error Message */}
            {error && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-start gap-4 animate-in shake">
                    <XCircle className="w-6 h-6 text-red-500 flex-shrink-0 mt-0.5" />
                    <div>
                        <h4 className="font-bold text-red-400">Upload Failed</h4>
                        <p className="text-sm text-red-300/80 mt-1">{error}</p>
                    </div>
                </div>
            )}

            {/* Success Result */}
            {result && (
                <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4">
                    <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-6 flex items-start gap-4">
                        <CheckCircle className="w-6 h-6 text-emerald-500 flex-shrink-0 mt-0.5" />
                        <div className="flex-1">
                            <h4 className="font-bold text-emerald-400 text-lg">Documentation Generated!</h4>
                            <p className="text-sm text-emerald-300/80 mt-1">
                                Task ID: {result.task_id}
                            </p>
                        </div>
                        <button
                            onClick={resetForm}
                            className="text-sm text-emerald-400 hover:text-emerald-300 font-medium underline"
                        >
                            Upload Another
                        </button>
                    </div>

                    <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden shadow-2xl">
                        <div className="px-6 py-4 border-b border-slate-700 flex justify-between items-center bg-slate-900/50">
                            <h3 className="font-semibold text-slate-200">Generated Documentation</h3>
                            {isDevMode && (
                                <span className="text-[10px] bg-indigo-500/20 text-indigo-300 px-2 py-1 rounded font-mono border border-indigo-500/30">
                                    DEV PREVIEW
                                </span>
                            )}
                        </div>
                        <div className="p-0">
                            <DocViewer
                                content={result.result}
                                taskId={result.task_id}
                                isDevMode={isDevMode}
                            />
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
