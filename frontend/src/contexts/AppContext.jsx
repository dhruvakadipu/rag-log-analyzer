import React, { createContext, useContext, useState, useEffect } from 'react';
import { fetchHealth, fetchFiles } from '../api/endpoints';
import { DEFAULT_AI_MODE } from '../config';

const AppContext = createContext();

export const AppProvider = ({ children }) => {
    const [theme, setTheme] = useState(localStorage.getItem('theme') || 'dark');
    const [aiMode, setAiMode] = useState(DEFAULT_AI_MODE);
    const [ollamaOnline, setOllamaOnline] = useState(null);
    const [files, setFiles] = useState([]);
    const [activeFile, setActiveFile] = useState(null);
    const [chatHistory, setChatHistory] = useState({});
    const [toast, setToast] = useState(null);

    // Sync theme
    useEffect(() => {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
    }, [theme]);

    const toggleTheme = () => setTheme(prev => (prev === 'dark' ? 'light' : 'dark'));

    const showToast = (message, type = 'info') => {
        setToast({ message, type, id: Date.now() });
    };

    const checkHealth = async () => {
        try {
            const data = await fetchHealth();
            setOllamaOnline(data.ollama);
        } catch (err) {
            setOllamaOnline({ online: false });
        }
    };

    const loadFiles = async () => {
        try {
            const data = await fetchFiles();
            setFiles(data.files || []);
        } catch (err) {
            console.error("Failed to load files", err);
        }
    };

    useEffect(() => {
        checkHealth();
        loadFiles();
        const interval = setInterval(checkHealth, 30000);
        return () => clearInterval(interval);
    }, [aiMode]);

    const setMessages = (updater) => {
        if (!activeFile) return;
        setChatHistory(prev => ({
            ...prev,
            [activeFile]: typeof updater === 'function' ? updater(prev[activeFile] || []) : updater,
        }));
    };

    return (
        <AppContext.Provider value={{
            theme, toggleTheme,
            aiMode, setAiMode,
            ollamaOnline, checkHealth,
            files, setFiles,
            activeFile, setActiveFile,
            chatHistory, setMessages,
            toast, setToast, showToast
        }}>
            {children}
        </AppContext.Provider>
    );
};

export const useAppContext = () => useContext(AppContext);
