function Header({ onRefresh }) {
    const API_URL = 'http://localhost:8000/api';

    const exportJSON = () => {
        window.open(`${API_URL}/prospects/export/json`, '_blank');
    };

    const exportCSV = () => {
        window.open(`${API_URL}/prospects/export/csv`, '_blank');
    };

    return (
        <header className="header">
            <div>
                <h1>📊 ISHOWO - Prospect Intelligence</h1>
                <p style={{ opacity: 0.8, fontSize: 14 }}>Système de prospection intelligente</p>
            </div>
            <div className="header-actions">
                <button onClick={onRefresh}>🔄 Actualiser</button>
                <button onClick={exportJSON}>📥 JSON</button>
                <button onClick={exportCSV}>📥 CSV</button>
            </div>
        </header>
    );
}

export default Header;