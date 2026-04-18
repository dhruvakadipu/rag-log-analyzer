const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const DEFAULT_AI_MODE = import.meta.env.VITE_DEFAULT_AI_MODE || 'cloud';
export const TOAST_TIMEOUT = parseInt(import.meta.env.VITE_TOAST_TIMEOUT || '4000');

export default API;