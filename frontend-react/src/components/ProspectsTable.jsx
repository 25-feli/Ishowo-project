function ProspectsTable({ prospects, loading }) {
    if (loading) {
        return (
            <div className="table-container">
                <div className="loading">Chargement des prospects...</div>
            </div>
        );
    }

    if (!prospects || prospects.length === 0) {
        return (
            <div className="table-container">
                <div className="loading">Aucun prospect trouvé</div>
            </div>
        );
    }

    const typeMap = {
        'commerce': 'badge-commerce',
        'pharmacy': 'badge-pharmacy',
        'construction': 'badge-construction',
        'transport': 'badge-transport',
        'service': 'badge-service'
    };

    return (
        <div className="table-container">
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 15 }}>
                <h2>📋 Liste des prospects</h2>
                <span style={{ background: '#667eea', color: 'white', padding: '4px 12px', borderRadius: 20 }}>
                    {prospects.length} résultats
                </span>
            </div>
            <div style={{ overflowX: 'auto', maxHeight: 600, overflowY: 'auto' }}>
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Nom</th>
                            <th>Téléphone</th>
                            <th>Secteur</th>
                            <th>Type</th>
                            <th>Score</th>
                            <th>📦 Stock</th>
                            <th>📞 Joignable</th>
                            <th>Justification</th>
                        </tr>
                    </thead>
                    <tbody>
                        {prospects.slice(0, 100).map(p => {
                            const type = p.analysis?.business_type || 'unknown';
                            const typeClass = typeMap[type] || '';
                            const typeLabel = type.toUpperCase() || '❓';
                            const stockNeed = p.analysis?.stock_management_need;
                            const verified = p.phone_verification?.valid;
                            const score = p.analysis?.score || 0;

                            return (
                                <tr key={p.id}>
                                    <td>{p.id}</td>
                                    <td><strong>{p.name || 'N/A'}</strong></td>
                                    <td>{p.phone || 'N/A'}</td>
                                    <td>{p.sector || 'N/A'}</td>
                                    <td>
                                        <span className={`badge ${typeClass}`}>
                                            {typeLabel}
                                        </span>
                                    </td>
                                    <td><strong>{score}</strong></td>
                                    <td>
                                        <span className={`badge ${stockNeed ? 'badge-success' : 'badge-danger'}`}>
                                            {stockNeed ? '📦 Oui' : '📦 Non'}
                                        </span>
                                    </td>
                                    <td>
                                        <span className={`badge ${verified === true ? 'badge-success' : verified === false ? 'badge-danger' : 'badge-warning'}`}>
                                            {verified === true ? '✅' : verified === false ? '❌' : '⏳'}
                                        </span>
                                    </td>
                                    <td><small>{p.analysis?.justification?.substring(0, 60) || 'N/A'}</small></td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

export default ProspectsTable;