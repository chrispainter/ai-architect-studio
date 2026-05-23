import axios from 'axios';

// In dev mode, Vite proxy handles /api and /ws routes (see vite.config.js)
// In production (Docker), nginx handles proxying
const API_URL = import.meta.env.VITE_API_URL || '';

export const api = axios.create({
    baseURL: API_URL,
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

/**
 * Download a crew run's markdown export and trigger a browser save.
 * Pulls the file as a blob (so the JWT bearer token comes along via the
 * configured axios interceptors), reads the server-suggested filename from
 * the Content-Disposition header, and clicks a hidden <a> to save it.
 */
export async function downloadRunExport(runId) {
    const res = await api.get(`/api/v1/runs/${runId}/export`, { responseType: 'blob' });
    const disposition = res.headers['content-disposition'] || '';
    const match = disposition.match(/filename="?([^"]+)"?/i);
    const filename = match ? match[1] : `run-${runId}.md`;
    const url = window.URL.createObjectURL(res.data);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
}

// Redirect to login on 401
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            if (window.location.pathname !== '/login') {
                window.location.href = '/login';
            }
        }
        return Promise.reject(error);
    }
);
