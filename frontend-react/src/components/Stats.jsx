function Stats({ stats, prospects }) {
    const joignables = prospects?.filter(p => p.phone_verification?.valid === true).length || 0;
    const nonJoignables = prospects?.filter(p => p.phone_verification?.valid === false).length || 0;

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
            <div className="stat-box">
                <div className="number orange">{stats.high_score || 0}</div>
                <div className="label">⭐ Score {'>'} 7</div>
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