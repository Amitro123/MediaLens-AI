import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api'
import DocViewer from '../components/DocViewer'
import { ChevronLeft } from 'lucide-react'

export default function DocPage() {
    const { taskId } = useParams()
    const navigate = useNavigate()
    const [content, setContent] = useState('')
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        const fetchDoc = async () => {
            try {
                const data = await api.getResult(taskId)
                setContent(data.documentation)
            } catch (err) {
                console.error("Failed to fetch doc:", err)
                setError(err.message)
            } finally {
                setLoading(false)
            }
        }
        fetchDoc()
    }, [taskId])

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
            </div>
        )
    }

    if (error) {
        return (
            <div className="max-w-4xl mx-auto px-6 py-12 text-center">
                <div className="text-4xl mb-4">⚠️</div>
                <h2 className="text-xl font-bold text-white mb-2">Failed to load document</h2>
                <p className="text-slate-400 mb-6">{error}</p>
                <button
                    onClick={() => navigate('/history')}
                    className="px-6 py-2 bg-slate-800 text-slate-200 rounded-lg hover:bg-slate-700 transition-colors"
                >
                    Back to History
                </button>
            </div>
        )
    }

    return (
        <div className="max-w-5xl mx-auto px-6 py-8">
            <button
                onClick={() => navigate('/history')}
                className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors mb-6 text-sm font-medium"
            >
                <ChevronLeft className="w-4 h-4" />
                Back to History
            </button>

            <DocViewer content={content} taskId={taskId} isDevMode={false} />
        </div>
    )
}
