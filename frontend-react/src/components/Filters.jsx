import { useState } from 'react';

function Filters({ onFilter }) {
    const [filters, setFilters] = useState({
        minScore: '',
        type: '',
        verified: '',
        stock: ''
    });

    const handleChange = (key, value) => {
        const newFilters = { ...filters, [key]: value };
        setFilters(newFilters);
        onFilter(newFilters);
    };

    const resetFilters = () => {
        const empty = { minScore: '', type: '', verified: '', stock: '' };
        setFilters(empty);
        onFilter(empty);
    };

    return (
        <div className="filters">
            <select 
                value={filters.minScore} 
                onChange={(e) => handleChange('minScore', e.target.value)}
            >
                <option value="">Tous les scores</option>
                <option value="7">⭐ ≥ 7</option>
                <option value="5">📊 ≥ 5</option>
                <option value="3">📉 ≥ 3</option>
            </select>

            <select 
                value={filters.type} 
                onChange={(e) => handleChange('type', e.target.value)}
            >
                <option value="">Tous les types</option>
                <option value="commerce">🛒 Commerce</option>
                <option value="pharmacy">💊 Pharmacie</option>
                <option value="construction">🏗️ Construction</option>
                <option value="transport">🚚 Transport</option>
                <option value="service">💼 Service</option>
            </select>

            <select 
                value={filters.verified} 
                onChange={(e) => handleChange('verified', e.target.value)}
            >
                <option value="">Tous</option>
                <option value="true">✅ Joignables</option>
                <option value="false">❌ Non joignables</option>
            </select>

            <select 
                value={filters.stock} 
                onChange={(e) => handleChange('stock', e.target.value)}
            >
                <option value="">Tous</option>
                <option value="true">📦 Besoin stock</option>
                <option value="false">📦 Pas besoin</option>
            </select>

            <button onClick={resetFilters}>↺ Réinitialiser</button>
        </div>
    );
}

export default Filters;