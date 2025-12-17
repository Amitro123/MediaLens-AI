import { Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, History, Rocket } from 'lucide-react'

export default function Navbar() {
    const location = useLocation()

    return (
        <header className="border-b border-slate-700/50 bg-slate-900/50 backdrop-blur-md sticky top-0 z-50">
            <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
                <div className="flex items-center gap-8">
                    <Link to="/" className="flex items-center gap-3 group">
                        <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform">
                            <span className="text-xl">🚀</span>
                        </div>
                        <div>
                            <h1 className="text-xl font-bold tracking-tight text-white">DevLens</h1>
                            <p className="text-[10px] text-slate-400 font-medium tracking-wide uppercase">Mission Control</p>
                        </div>
                    </Link>

                    <nav className="flex items-center gap-1">
                        <Link
                            to="/"
                            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${location.pathname === '/'
                                    ? 'bg-gradient-to-r from-indigo-600 to-violet-600 text-white shadow-md shadow-indigo-900/40'
                                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                                }`}
                        >
                            <LayoutDashboard className="w-4 h-4" />
                            Dashboard
                        </Link>
                        <Link
                            to="/history"
                            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${location.pathname === '/history'
                                    ? 'bg-gradient-to-r from-indigo-600 to-violet-600 text-white shadow-md shadow-indigo-900/40'
                                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                                }`}
                        >
                            <History className="w-4 h-4" />
                            History
                        </Link>
                    </nav>
                </div>
            </div>
        </header>
    )
}
