import axios from 'axios';

const http = axios.create({
    baseURL: 'http://localhost:8000',
    timeout: 300000, // 5 minutes for video upload
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
    timestamp?: string;  // Added for history display
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
    stage?: string;  // Current processing stage label
}

// API Client - connected to real backend
export const api = {
    // ============ UPLOADS ============
    // Manual upload (creates new session)
    manualUpload: (file: File, mode: string, projectName?: string, sttProvider: string = "auto", onProgress?: (percent: number) => void) => {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('mode', mode);
        formData.append('stt_provider', sttProvider);
        if (projectName) formData.append('project_name', projectName);
        return http.post<UploadResponse>('/api/v1/upload', formData, {
            headers: {
                'Content-Type': undefined,
            },
            onUploadProgress: (progressEvent) => {
                if (onProgress && progressEvent.total) {
                    const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                    onProgress(percentCompleted);
                }
            }
        });
    },

    // ============ STATUS & RESULTS ============
    getStatus: (taskId: string) => http.get<StatusResponse>(`/api/v1/status/${taskId}`),
    getResult: (taskId: string) => http.get<{
        task_id: string;
        documentation: string;
        stt_provider?: string;
        transcript?: string;
        transcript_segments?: any[];
    }>(`/api/v1/result/${taskId}`),
    getSession: (sessionId: string) => http.get<Session>(`/api/v1/sessions/${sessionId}`),
    getSessions: () => http.get<{ sessions: Session[] }>('/api/v1/history'),

    // ============ MODES ============
    getModes: () => http.get<{ modes: Mode[] }>('/api/v1/modes'),

    // ============ ACTIONS ============
    sendFeedback: (sessionId: string, rating: number, comment?: string) =>
        http.post(`/api/v1/sessions/${sessionId}/feedback`, { rating, comment }),

    exportSession: (sessionId: string, target: 'jira' | 'notion' | 'clipboard') =>
        http.post(`/api/v1/sessions/${sessionId}/export`, { target }),

    cancelSession: (sessionId: string) =>
        http.post(`/api/v1/sessions/${sessionId}/cancel`),
};

export default api;
