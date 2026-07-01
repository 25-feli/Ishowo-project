// src/components/Actions.jsx
import { useState } from 'react';

function Actions({ onCollect, onFullProcessing }) {
    const [source, setSource] = useState('africa');
    const [limit, setLimit] = useState(20);
    const [status, setStatus] = useState('');
    const [statusType, setStatusType] = useState('');

    const showStatus = (type, message) => {
        setStatusType(type);
        setStatus(message);
        setTimeout(() => {
            setStatus('');
            setStatusType('');
        }, 10000);
    };

    const handleCollect = async () => {
        try {
            showStatus('processing', '🔄 Collecte en cours...');
            const result = await onCollect(source, limit);
            showStatus('success', `✅ ${result.new_prospects || 0} nouveaux prospects collectés !`);
        } catch (error) {
            showStatus('error', `❌ Erreur: ${error.message}`);
        }
    };

    const handleFull = async () => {
        try {
            showStatus('processing', '⚡ Pipeline complet en cours...');
            const result = await onFullProcessing();
            showStatus('success', `✅ Pipeline complet lancé ! ${result.total || 0} prospects en cours`);
        } catch (error) {
            showStatus('error', `❌ Erreur: ${error.message}`);
        }
    };

    return (
        <div className="actions-panel">
            <div className="actions-grid">
                <div className="action-card">
                    <h3>📥 Collecter des prospects</h3>
                    <div className="action-form">
                        <select value={source} onChange={(e) => setSource(e.target.value)}>
                            <option value="africa">🌍 Go Africa Online</option>
                            <option value="showroom">🏢 Showroom Africa</option>
                            <option value="all">🔀 Toutes les sources</option>
                        </select>
                        <input 
                            type="number" 
                            value={limit} 
                            onChange={(e) => setLimit(parseInt(e.target.value) || 20)}
                            min="1"
                            max="500"
                            style={{ width: 80 }}
                        />
                        <button className="btn-primary" onClick={handleCollect}>
                            🚀 Lancer
                        </button>
                    </div>
                </div>

                <div className="action-card">
                    <h3>⚡ Full Processing</h3>
                    <p style={{ color: '#777', fontSize: 14, marginBottom: 10 }}>
                        Analyse IA + Vérification téléphonique
                    </p>
                    <button className="btn-danger" onClick={handleFull}>
                        🚀 Lancer le traitement
                    </button>
                </div>
            </div>
            {status && (
                <div className={`status-message ${statusType}`}>
                    {status}
                </div>
            )}
        </div>
    );
}

export default Actions;