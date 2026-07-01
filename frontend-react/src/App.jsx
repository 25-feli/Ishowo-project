import { useState, useEffect } from 'react';
import api from './api/api';
import './App.css';

// Composants
import Header from './components/Header';
import Stats from './components/Stats';
import Actions from './components/Actions';
import Filters from './components/Filters';
import ProspectsTable from './components/ProspectsTable';

function App() {
    const [prospects, setProspects] = useState([]);
    const [stats, setStats] = useState({});
    const [loading, setLoading] = useState(true);
    const [filteredProspects, setFilteredProspects] = useState([]);

    // Charger les données au démarrage
    useEffect(() => {
        loadData();
        const interval = setInterval(loadData, 30000);
        return () => clearInterval(interval);
    }, []);

    const loadData = async () => {
        try {
            setLoading(true);
            const [prospectsRes, statsRes] = await Promise.all([
                api.get('/prospects?limit=500'),
                api.get('/stats')
            ]);
            setProspects(prospectsRes.data.prospects || []);
            setFilteredProspects(prospectsRes.data.prospects || []);
            setStats(statsRes.data);
        } catch (error) {
            console.error('Erreur chargement:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleCollect = async (source, limit) => {
        try {
            const response = await api.post(`/collect?source=${source}&limit=${limit}&max_pages=10`);
            loadData();
            return response.data;
        } catch (error) {
            console.error('Erreur collecte:', error);
            throw error;
        }
    };

    const handleFullProcessing = async () => {
        try {
            const response = await api.post('/process-full');
            // Rafraîchir après quelques secondes
            setTimeout(loadData, 3000);
            return response.data;
        } catch (error) {
            console.error('Erreur processing:', error);
            throw error;
        }
    };

    const handleFilter = (filters) => {
        let filtered = [...prospects];
        if (filters.minScore) {
            filtered = filtered.filter(p => (p.analysis?.score || 0) >= filters.minScore);
        }
        if (filters.type) {
            filtered = filtered.filter(p => (p.analysis?.business_type || '').toLowerCase() === filters.type);
        }
        if (filters.verified === 'true') {
            filtered = filtered.filter(p => p.phone_verification?.valid === true);
        } else if (filters.verified === 'false') {
            filtered = filtered.filter(p => p.phone_verification?.valid === false);
        }
        if (filters.stock === 'true') {
            filtered = filtered.filter(p => p.analysis?.stock_management_need === true);
        } else if (filters.stock === 'false') {
            filtered = filtered.filter(p => p.analysis?.stock_management_need === false);
        }
        setFilteredProspects(filtered);
    };

    return (
        <div className="app">
            <Header onRefresh={loadData} />
            <Actions 
                onCollect={handleCollect} 
                onFullProcessing={handleFullProcessing} 
            />
            <Stats stats={stats} prospects={prospects} />
            <Filters onFilter={handleFilter} />
            <ProspectsTable 
                prospects={filteredProspects} 
                loading={loading} 
            />
        </div>
    );
}

export default App;