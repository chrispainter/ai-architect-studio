import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'https://ai-architect-backend-7dan.onrender.com';

export const api = axios.create({
    baseURL: API_URL,
});
