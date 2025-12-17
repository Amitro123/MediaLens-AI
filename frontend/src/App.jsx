import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Dashboard from './components/Dashboard'
import HistoryPage from './pages/HistoryPage'
import DocPage from './pages/DocPage'
import Navbar from './components/Navbar'

function App() {
    return (
        <Router>
            <div className="min-h-screen bg-slate-900 text-slate-100 selection:bg-indigo-500/30">
                <Navbar />
                <main>
                    <Routes>
                        <Route path="/" element={<Dashboard />} />
                        <Route path="/history" element={<HistoryPage />} />
                        <Route path="/doc/:taskId" element={<DocPage />} />
                    </Routes>
                </main>
            </div>
        </Router>
    )
}

export default App
