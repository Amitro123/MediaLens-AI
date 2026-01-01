import axios from 'axios';

// API base URL - uses proxy in dev mode (vite.config.ts handles /api -> localhost:8000)
const http = axios.create({
    baseURL: '',
    headers: { 'Content-Type': 'application/json' }
});

// Types matching backend responses
export interface KeyFrame {
    timestamp_sec: number;
    thumbnail_url: string;
    label?: string;
    json_data?: Record<string, unknown>;  // Raw JSON for Copy feature
}

export interface Segment {
    start_sec: number;
    end_sec: number;
    text: string;
}

export interface Session {
    id: string;
    title: string;
    status: string;
    mode?: string;
    topic?: string;
    created_at?: string;
    doc_markdown?: string;
    result?: string;
    video_url?: string;
    key_frames?: KeyFrame[];
    segments?: Segment[];
}

export interface Mode {
    mode: string;
    name: string;
    description: string;
    icon?: string;
    department?: string;
}

export interface UploadResponse {
    task_id: string;
    status: string;
    result?: string;
}

export interface StatusResponse {
    status: string;
    progress: number;
    stage?: string;  // Current processing stage label
}

export interface ActiveSession {
    session_id: string;
    status: string;
    title: string;
    mode?: string;
    progress: number;
}

// API Client - connected to real backend
export const api = {
    // ============ SESSIONS / HISTORY ============
    // List all past sessions (for History view)
    listSessions: () => http.get<Session[]>('/api/sessions'),

    // Get single session details (with key_frames, doc_markdown, segments)
    getSession: (sessionId: string) => http.get<Session>(`/api/sessions/${sessionId}`),

    // Get draft sessions from calendar
    getDraftMeetings: () => http.get<Session[]>('/api/v1/sessions/drafts'),

    // Prep session for upload
    prepSession: (sessionId: string) =>
        http.post<{ status: string; id: string }>(`/api/v1/sessions/${sessionId}/prep`),

    // ============ UPLOADS ============
    // Upload to existing session (calendar-based)
    uploadToSession: (sessionId: string, file: File, mode?: string) => {
        const formData = new FormData();
        formData.append('file', file);
        if (mode) formData.append('mode', mode);
        return http.post<UploadResponse>(`/api/v1/upload/${sessionId}`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });
    },

    // Manual upload (creates new session)
    manualUpload: (file: File, mode: string, projectName?: string) => {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('mode', mode);
        if (projectName) formData.append('project_name', projectName);
        return http.post<UploadResponse>('/api/v1/upload', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });
    },

    // ============ STATUS & RESULTS ============
    getStatus: (taskId: string) => http.get<StatusResponse>(`/api/v1/status/${taskId}`),
    getResult: (taskId: string) => http.get<{ task_id: string; documentation: string }>(`/api/v1/result/${taskId}`),
    getActiveSession: () => http.get<ActiveSession | null>('/api/v1/active-session'),

    // ============ MODES ============
    getModes: () => http.get<{ modes: Mode[] }>('/api/v1/modes'),

    // ============ DRIVE / MCP ============
    getDriveFiles: () => http.get<{ files: any[] }>('/api/v1/integrations/drive/files'),
    importFromDrive: (fileUri: string, fileName: string, mode: string) =>
        http.post<UploadResponse>('/api/v1/import/drive', { file_uri: fileUri, file_name: fileName, mode }),

    // ============ ACTIONS ============
    sendFeedback: (sessionId: string, rating: number, comment?: string) =>
        http.post(`/api/v1/sessions/${sessionId}/feedback`, { rating, comment }),

    exportSession: (sessionId: string, target: 'jira' | 'notion' | 'clipboard') =>
        http.post(`/api/v1/sessions/${sessionId}/export`, { target }),

    cancelSession: (sessionId: string) =>
        http.post(`/api/v1/sessions/${sessionId}/cancel`),
};

export default api;
