import axios from 'axios';

// En local
//const API_URL = 'https://localhost:8000/api';

// Pour la production (Iwaju Tech)
const API_URL = 'https://propection.iwajutech.com/api';

const api = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export default api;