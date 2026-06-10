import API from '../config';

export const uploadLog = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API}/logs/upload`, { method: 'POST', body: formData });
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Upload failed');
    }
    return res.json();
};

export const fetchHealth = async () => {
    const res = await fetch(`${API}/health`);
    if (!res.ok) throw new Error('Health check failed');
    return res.json();
};

export const fetchFiles = async () => {
    const res = await fetch(`${API}/logs/files`);
    if (!res.ok) throw new Error('Failed to fetch files');
    return res.json();
};
