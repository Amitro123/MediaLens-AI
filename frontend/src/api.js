import axios from 'axios'

// Helper to handle API responses and errors
const handleResponse = async (request) => {
    try {
        const response = await request
        return response.data
    } catch (error) {
        throw new Error(error.response?.data?.detail || 'API request failed')
    }
}

export const api = {
    // Sessions (v1 - legacy)
    getDraftMeetings: () => handleResponse(axios.get('/api/v1/sessions/drafts')),
    getSession: (sessionId) => handleResponse(axios.get(`/api/v1/sessions/${sessionId}`)),
    prepSession: (sessionId) => handleResponse(axios.post(`/api/v1/sessions/${sessionId}/prep`)),

    // Sessions (minimal - new History UI)
    // Uses /api/sessions which returns key_frames via storage_service.get_session_details()
    listSessions: () => handleResponse(axios.get('/api/sessions')),
    getSessionDetails: (sessionId) => handleResponse(axios.get(`/api/sessions/${sessionId}`)),

    // Uploads
    uploadToSession: (sessionId, formData) => handleResponse(axios.post(`/api/v1/upload/${sessionId}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    })),
    manualUpload: (formData) => handleResponse(axios.post('/api/v1/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    })),
    uploadFromDrive: (data) => handleResponse(axios.post('/api/v1/upload/drive', data)),
    // MCP Drive Integration
    getDriveFiles: () => handleResponse(axios.get('/api/v1/integrations/drive/files')),
    importFromDrive: (data) => handleResponse(axios.post('/api/v1/import/drive', data)),

    // Modes
    getModes: () => handleResponse(axios.get('/api/v1/modes')),
    // Results
    getHistory: () => handleResponse(axios.get('/api/v1/history')),
    getResult: (taskId) => handleResponse(axios.get(`/api/v1/result/${taskId}`)),
    getStatus: (taskId) => handleResponse(axios.get(`/api/v1/status/${taskId}`)),
    getActiveSession: () => handleResponse(axios.get('/api/v1/active-session')),
    // Feedback
    sendFeedback: (sessionId, feedback) => handleResponse(axios.post(`/api/v1/sessions/${sessionId}/feedback`, feedback)),
    // Export
    exportSession: (sessionId, target) => handleResponse(axios.post(`/api/v1/sessions/${sessionId}/export`, { target })),
}

