function Header({ onRefresh }) {
    const exportJSON = async () => {
        try {
            const response = await fetch('/api/prospects/export/json');
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `prospects_${new Date().toISOString().slice(0,10)}.json`;
            a.click();
        } catch (error) {
            console.error('Erreur export JSON:', error);
            alert('Erreur lors de l\'export JSON');
        }
    };

    const exportCSV = async () => {
        try {
            const response = await fetch('/api/prospects/export/csv');
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `prospects_${new Date().toISOString().slice(0,10)}.csv`;
            a.click();
        } catch (error) {
            console.error('Erreur export CSV:', error);
            alert('Erreur lors de l\'export CSV');
        }
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