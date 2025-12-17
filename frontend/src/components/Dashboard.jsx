import { useState, useRef } from 'react'
import UploadForm from './UploadForm'

// Mock meetings data
const UPCOMING_MEETINGS = [
    {
        id: 'mtg_1',
        title: 'Daily Standup',
        time: '10:00 AM',
        attendees: ['Alice', 'Bob', 'Charlie'],
        type: 'standup',
        mode: 'general_doc',
        keywords: ['status', 'blockers']
    },
    {
        id: 'mtg_2',
        title: 'Design Review - Auth Flow',
        time: '11:00 AM',
        attendees: ['Sarah', 'Mike'],
        type: 'review',
        mode: 'feature_kickoff',
        keywords: ['authentication', 'ui/ux', 'security']
    },
    {
        id: 'mtg_3',
        title: 'Bug Bash: Payment Gateway',
        time: '02:00 PM',
        attendees: ['QA Team'],
        type: 'bug',
        mode: 'bug_report',
        keywords: ['stripe', 'errors', '500']
    }
]

const getMeetingIcon = (type) => {
    switch (type) {
        case 'standup': return '⚡'
        case 'review': return '🎨'
        case 'bug': return '🐛'
        default: return '📅'
    }
}

export default function Dashboard() {
    const [selectedMeeting, setSelectedMeeting] = useState(null)
    const [isDevMode, setIsDevMode] = useState(false)

    // Transform meeting to session object for UploadForm
    const sessionContext = selectedMeeting ? {
        id: selectedMeeting.id,
        title: selectedMeeting.title,
        context_keywords: selectedMeeting.keywords,
        suggested_mode: selectedMeeting.mode
    } : null

    return (
        <div className="min-h-screen bg-slate-900 text-slate-100 font-sans">
            {/* Main Content Grid */}
            <main className="max-w-7xl mx-auto px-6 py-8">
                <div className="grid grid-cols-12 gap-8 min-h-[600px]">

                    {/* Left Panel: Sidebar */}
                    <aside className="col-span-4 space-y-6">
                        <div className="bg-slate-800/40 rounded-2xl p-1 border border-slate-700/50 overflow-hidden backdrop-blur-sm">
                            <div className="px-5 py-4 border-b border-slate-700/50 flex justify-between items-center">
                                <h2 className="font-semibold text-slate-200">Upcoming Sessions</h2>
                                <span className="text-xs bg-slate-700 text-slate-300 px-2 py-1 rounded-full">Today</span>
                            </div>
                            <div className="p-3 space-y-2">
                                {UPCOMING_MEETINGS.map((meeting) => (
                                    <button
                                        key={meeting.id}
                                        onClick={() => setSelectedMeeting(meeting)}
                                        className={`w-full text-left p-4 rounded-xl transition-all duration-300 group ${selectedMeeting?.id === meeting.id
                                            ? 'bg-gradient-to-r from-indigo-600 to-violet-600 shadow-lg shadow-indigo-900/50 scale-[1.02] border-transparent'
                                            : 'bg-slate-800/50 hover:bg-slate-700/80 border border-slate-700/30'
                                            }`}
                                    >
                                        <div className="flex items-center gap-4">
                                            <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-xl transition-colors ${selectedMeeting?.id === meeting.id ? 'bg-white/20' : 'bg-slate-700 group-hover:bg-slate-600'
                                                }`}>
                                                {getMeetingIcon(meeting.type)}
                                            </div>
                                            <div className="flex-1">
                                                <h3 className={`font-semibold text-sm ${selectedMeeting?.id === meeting.id ? 'text-white' : 'text-slate-200'
                                                    }`}>
                                                    {meeting.title}
                                                </h3>
                                                <div className={`flex items-center gap-2 mt-1 text-xs ${selectedMeeting?.id === meeting.id ? 'text-indigo-100' : 'text-slate-400'
                                                    }`}>
                                                    <span>{meeting.time}</span>
                                                    <span>•</span>
                                                    <span>{meeting.attendees.length} attendees</span>
                                                </div>
                                            </div>
                                        </div>
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Quick Stats Card */}
                        <div className="grid grid-cols-2 gap-4">
                            <div className="bg-slate-800/40 p-5 rounded-2xl border border-slate-700/50">
                                <p className="text-3xl font-bold text-slate-100">3</p>
                                <p className="text-xs text-slate-400 mt-1 uppercase tracking-wide">Sessions</p>
                            </div>
                            <div className="bg-slate-800/40 p-5 rounded-2xl border border-slate-700/50">
                                <p className="text-3xl font-bold text-emerald-400">0</p>
                                <p className="text-xs text-slate-400 mt-1 uppercase tracking-wide">Processed</p>
                            </div>
                        </div>
                    </aside>

                    {/* Right Panel: Context & Upload */}
                    <section className="col-span-8">
                        <div className="h-full bg-slate-800/40 rounded-3xl border border-slate-700/50 backdrop-blur-md overflow-hidden flex flex-col relative">
                            {/* Decorative gradient blob */}
                            <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-600/10 blur-[100px] pointer-events-none" />

                            <div className="p-8 border-b border-slate-700/50 flex-none relative z-10">
                                <div className="flex items-start justify-between">
                                    <div>
                                        <h2 className="text-2xl font-bold text-white mb-2">
                                            {selectedMeeting ? selectedMeeting.title : 'Active Session Context'}
                                        </h2>
                                        <p className="text-slate-400 max-w-lg">
                                            {selectedMeeting
                                                ? `Context activated. Uploaded videos will be processed as ${selectedMeeting.type.replace('_', ' ')}.`
                                                : 'Select a meeting from the sidebar to automatically configure the AI context.'}
                                        </p>
                                    </div>
                                    {selectedMeeting && (
                                        <div className="flex flex-col items-end gap-2">
                                            <span className="px-3 py-1 bg-indigo-500/20 text-indigo-300 rounded-full text-xs font-medium border border-indigo-500/30">
                                                Mode: {selectedMeeting.mode}
                                            </span>
                                            <button
                                                onClick={() => setSelectedMeeting(null)}
                                                className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
                                            >
                                                Clear Context
                                            </button>
                                        </div>
                                    )}
                                </div>
                            </div>

                            <div className="flex-1 p-8 relative z-10">
                                {selectedMeeting ? (
                                    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
                                        <UploadForm session={sessionContext} isDevMode={isDevMode} />
                                    </div>
                                ) : (
                                    <div className="h-full flex flex-col items-center justify-center text-slate-500 border-2 border-dashed border-slate-700/50 rounded-2xl bg-slate-800/20">
                                        <div className="w-16 h-16 rounded-full bg-slate-700/50 flex items-center justify-center mb-4 text-3xl">
                                            👈
                                        </div>
                                        <h3 className="text-lg font-medium text-slate-300">No Context Selected</h3>
                                        <p className="text-sm max-w-sm text-center mt-2">
                                            Choose a meeting from the sidebar to start a documentation session.
                                        </p>
                                    </div>
                                )}
                            </div>
                        </div>
                    </section>
                </div>
            </main>
        </div>
    )
}
