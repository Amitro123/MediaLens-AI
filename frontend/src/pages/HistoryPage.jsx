import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { Clock, ChevronRight, Search, Filter, FileText, Calendar, Zap } from 'lucide-react'

export default function HistoryPage() {
    const [history, setHistory] = useState([])
    const [loading, setLoading] = useState(true)
    const [searchQuery, setSearchQuery] = useState('')
    const navigate = useNavigate()

    useEffect(() => {
        const fetchHistory = async () => {
            try {
                const data = await api.getHistory()
                console.log("History data received:", data)
                setHistory(data.sessions || [])
            } catch (err) {
                console.error("Failed to fetch history:", err)
            } finally {
                console.log("History loading completed")
                setLoading(false)
            }
        }
        fetchHistory()
    }, [])

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
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        })
    }

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
            </div>
        )
    }

    return (
        <div className="max-w-7xl mx-auto px-6 py-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
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

            {filteredHistory.length > 0 ? (
                <div className="grid grid-cols-1 gap-4">
                    {filteredHistory.map((session) => (
                        <button
                            key={session.id}
                            onClick={() => navigate(`/doc/${session.id}`)}
                            className="group bg-slate-800/40 hover:bg-slate-800/60 border border-slate-700/50 rounded-2xl p-5 flex items-center justify-between transition-all duration-300 hover:scale-[1.01] hover:shadow-xl hover:shadow-indigo-500/5 backdrop-blur-sm text-left"
                        >
                            <div className="flex items-center gap-5">
                                <div className="w-12 h-12 rounded-xl bg-slate-700 flex items-center justify-center group-hover:bg-indigo-600/20 transition-colors">
                                    {session.mode === 'bug_report' ? '🐛' : session.mode === 'feature_spec' ? '✨' : '📄'}
                                </div>
                                <div>
                                    <h3 className="font-bold text-slate-100 group-hover:text-indigo-300 transition-colors mb-1">
                                        {session.title}
                                    </h3>
                                    <div className="flex items-center gap-4 text-xs text-slate-500">
                                        <span className="flex items-center gap-1.5">
                                            <Calendar className="w-3.5 h-3.5" />
                                            {formatDate(session.timestamp)}
                                        </span>
                                        <span className="px-2 py-0.5 rounded-full bg-slate-700/50 border border-slate-700 text-slate-400">
                                            {session.mode_name}
                                        </span>
                                        {session.status === 'completed' && (
                                            <span className="flex items-center gap-1 text-emerald-500 font-medium">
                                                <Zap className="w-3 h-3 fill-current" />
                                                Verified
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </div>
                            <ChevronRight className="w-5 h-5 text-slate-600 group-hover:text-indigo-400 group-hover:translate-x-1 transition-all" />
                        </button>
                    ))}
                </div>
            ) : (
                <div className="bg-slate-800/20 border-2 border-dashed border-slate-700/50 rounded-3xl p-12 text-center">
                    <div className="w-20 h-20 bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-6 text-3xl opacity-50">
                        📁
                    </div>
                    <h3 className="text-xl font-bold text-slate-300 mb-2">No history found</h3>
                    <p className="text-slate-500 max-w-sm mx-auto">
                        Your generated documentation will appear here once you complete your first session.
                    </p>
                    <button
                        onClick={() => navigate('/')}
                        className="mt-6 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-medium transition-all shadow-lg shadow-indigo-500/20"
                    >
                        Start New Session
                    </button>
                </div>
            )}
        </div>
    )
}
