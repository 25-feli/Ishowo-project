import axios from 'axios';

// Pour le développement local
//const API_URL = 'http://localhost:8000/api';

// Pour la production (Iwaju Tech)
const API_URL = 'https://ishowo-api.iwajutech.com/api';

const api = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export default api;