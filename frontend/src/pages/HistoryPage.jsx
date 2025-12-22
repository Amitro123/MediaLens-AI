import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api'
import { Clock, ChevronRight, Search, FileText, Calendar, Zap } from 'lucide-react'
import SessionDetails from '../components/SessionDetails'

export default function HistoryPage() {
    const { sessionId } = useParams()
    const [history, setHistory] = useState([])
    const [loading, setLoading] = useState(true)
    const [searchQuery, setSearchQuery] = useState('')
    const [selectedSession, setSelectedSession] = useState(null)
    const [detailsLoading, setDetailsLoading] = useState(false)
    const navigate = useNavigate()

    useEffect(() => {
        const fetchHistory = async () => {
            try {
                const data = await api.getHistory()
                setHistory(data.sessions || [])
            } catch (err) {
                console.error("Failed to fetch history:", err)
            } finally {
                setLoading(false)
            }
        }
        fetchHistory()
    }, [])

    useEffect(() => {
        if (sessionId) {
            const fetchDetails = async () => {
                setDetailsLoading(true)
                try {
                    const data = await api.getSession(sessionId)
                    setSelectedSession(data)
                } catch (err) {
                    console.error("Failed to fetch session details:", err)
                    setSelectedSession(null)
                } finally {
                    setDetailsLoading(false)
                }
            }
            fetchDetails()
        } else {
            setSelectedSession(null)
        }
    }, [sessionId])

    const sortedHistory = [...history].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))

    const filteredHistory = sortedHistory.filter(session => {
        const title = session.title || 'Untitled Session';
        const modeName = session.mode_name || 'General Documentation';
        return title.toLowerCase().includes(searchQuery.toLowerCase()) ||
            modeName.toLowerCase().includes(searchQuery.toLowerCase());
    })

    const formatDate = (isoString) => {
        const date = new Date(isoString)
        return date.toLocaleDateString(undefined, {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        })
    }

    if (loading && history.length === 0) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
            </div>
        )
    }

    return (
        <div className="max-w-[1600px] mx-auto px-6 py-8 h-[calc(100vh-64px)] flex flex-col">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8 shrink-0">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-2 flex items-center gap-3">
                        <Clock className="w-8 h-8 text-indigo-400" />
                        Session History
                    </h1>
                    <p className="text-slate-400">View and manage your past AI-generated documentation.</p>
                </div>

                <div className="flex items-center gap-3">
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                        <input
                            type="text"
                            placeholder="Search sessions..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-4 py-2 text-sm text-slate-200 focus:ring-2 focus:ring-indigo-500 outline-none w-64 transition-all"
                        />
                    </div>
                </div>
            </div>

            <div className="flex gap-6 overflow-hidden flex-1">
                {/* Master List */}
                <div className={`flex-none w-full md:w-96 flex flex-col overflow-hidden ${sessionId ? 'hidden md:flex' : 'flex'}`}>
                    <div className="overflow-y-auto pr-2 space-y-3 pb-8">
                        {filteredHistory.length > 0 ? (
                            filteredHistory.map((session) => (
                                <button
                                    key={session.id}
                                    onClick={() => navigate(`/history/${session.id}`)}
                                    className={`w-full group rounded-xl p-4 flex items-start justify-between transition-all duration-200 border text-left ${sessionId === session.id
                                            ? 'bg-indigo-500/10 border-indigo-500/50 shadow-lg shadow-indigo-500/5'
                                            : 'bg-slate-800/40 border-slate-700/50 hover:bg-slate-800/60'
                                        }`}
                                >
                                    <div className="flex items-start gap-4">
                                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${sessionId === session.id ? 'bg-indigo-600' : 'bg-slate-700'
                                            }`}>
                                            {session.mode === 'bug_report' ? '🐛' : session.mode === 'feature_spec' ? '✨' : '📄'}
                                        </div>
                                        <div className="overflow-hidden">
                                            <h3 className={`font-bold truncate mb-1 ${sessionId === session.id ? 'text-indigo-300' : 'text-slate-100'
                                                }`}>
                                                {session.title}
                                            </h3>
                                            <div className="flex flex-col gap-1 text-[10px] text-slate-500 uppercase tracking-wider font-bold">
                                                <span>{formatDate(session.timestamp)}</span>
                                                <span className="text-slate-600">{session.mode_name}</span>
                                            </div>
                                        </div>
                                    </div>
                                    <ChevronRight className={`w-4 h-4 mt-1 transition-transform ${sessionId === session.id ? 'text-indigo-400 translate-x-1' : 'text-slate-600'
                                        }`} />
                                </button>
                            ))
                        ) : (
                            <div className="text-center py-12 text-slate-500">
                                No sessions found.
                            </div>
                        )}
                    </div>
                </div>

                {/* Vertical Divider */}
                <div className="hidden md:block w-px bg-slate-800/50 h-full shrink-0" />

                {/* Detail View */}
                <div className="flex-1 overflow-y-auto">
                    {detailsLoading ? (
                        <div className="flex flex-col items-center justify-center h-full text-slate-500">
                            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-indigo-500 mb-4"></div>
                            <p>Loading session details...</p>
                        </div>
                    ) : selectedSession ? (
                        <div className="pr-4">
                            <SessionDetails session={selectedSession} onBack={() => navigate('/history')} />
                        </div>
                    ) : (
                        <div className="flex flex-col items-center justify-center h-full text-center p-12 bg-slate-800/20 rounded-3xl border-2 border-dashed border-slate-700/50">
                            <div className="w-20 h-20 bg-slate-800 rounded-full flex items-center justify-center mb-6 text-3xl opacity-50">
                                👈
                            </div>
                            <h3 className="text-xl font-bold text-slate-300 mb-2">Select a session</h3>
                            <p className="text-slate-500 max-w-sm">
                                Choose a session from the list on the left to view documentation, key frames, and video.
                            </p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
