function Stats({ stats, prospects }) {
    const joignables = prospects?.filter(p => p.phone_verification?.valid === true).length || 0;
    const nonJoignables = prospects?.filter(p => p.phone_verification?.valid === false).length || 0;
    const API_URL = 'http://localhost:8000/api';
    const exploitable = prospects.filter(p => 
        p.analysis?.score >= 5 && 
        p.phone_verification?.valid === true
    );
    
    // Exporter les exploitables en CSV
    const exportExploitable = () => {
        window.open(`${API_URL}/prospects/export/exploitable/csv`, '_blank');
    };
    return (
        <div className="stats">
            <div className="stat-box">
                <div className="number blue">{stats.total_prospects || 0}</div>
                <div className="label">📋 Total</div>
            </div>
            <div className="stat-box">
                <div className="number green">{stats.analyzed || 0}</div>
                <div className="label">🧠 Analysés</div>
            </div>
            <div className="stat-box">
                <div className="number green">{stats.verified || 0}</div>
                <div className="label">📞 Vérifiés</div>
            </div>
            <div 
                className="stat-box clickable" 
                onClick={exportExploitable}
                style={{ cursor: 'pointer' }}
                title="Cliquez pour exporter les prospects exploitables en CSV"
            >
                <div className="number green">{exploitable.length}</div>
                <div className="label">📊 Prospects exploitables</div>
            </div>
            <div className="stat-box">
                <div className="number purple">{joignables}</div>
                <div className="label">✅ Joignables</div>
            </div>
            <div className="stat-box">
                <div className="number red">{nonJoignables}</div>
                <div className="label">❌ Non joignables</div>
            </div>
        </div>
    );
}

export default Stats;