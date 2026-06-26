const API_URL = 'http://localhost:8000/api';

let allProspects = [];

// ─── COLLECTE ──────────────────────────────────

async function runCollect() {
    const btn = document.getElementById('btnCollect');
    const status = document.getElementById('collectStatus');
    
    const source = document.getElementById('sourceSelect').value;
    const limit = document.getElementById('limitInput').value || 20;
    
    btn.disabled = true;
    showStatus(status, 'processing', '🔄 Collecte en cours...');
    
    try {
        const response = await fetch(`${API_URL}/collect?source=${source}&limit=${limit}&max_pages=10`, {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.status === 'success' || data.new_prospects !== undefined) {
            showStatus(status, 'success', `✅ ${data.new_prospects || 0} nouveaux prospects collectés (${data.duplicates || 0} doublons)`);
            refreshData();
        } else {
            showStatus(status, 'error', `❌ ${data.errors?.join(', ') || 'Erreur inconnue'}`);
        }
    } catch (error) {
        showStatus(status, 'error', `❌ ${error.message}`);
    }
    btn.disabled = false;
}

// FULL PROCESSING 

async function runFullProcessing() {
    const btn = document.getElementById('btnFull');
    const status = document.getElementById('fullStatus');
    
    btn.disabled = true;
    showStatus(status, 'processing', '⚡ Traitement complet en cours... (Analyse IA + Vérification)');
    
    try {
        const response = await fetch(`${API_URL}/process-full`, { method: 'POST' });
        const data = await response.json();
        
        if (data.status === 'processing') {
            showStatus(status, 'success', `✅ Pipeline complet lancé ! ${data.total} prospects en cours de traitement`);
            
            // Rafraîchir toutes les 5 secondes
            let count = 0;
            const interval = setInterval(() => {
                refreshData();
                count++;
                if (count > 12) clearInterval(interval);
            }, 5000);
            
            setTimeout(() => refreshData(), 2000);
        } else {
            showStatus(status, 'info', `ℹ️ ${data.message || 'Aucun prospect à traiter'}`);
        }
    } catch (error) {
        showStatus(status, 'error', `❌ ${error.message}`);
    }
    btn.disabled = false;
}

// CHARGEMENT 

async function refreshData() {
    await loadProspects();
    await loadStats();
}

async function loadProspects() {
    try {
        const response = await fetch(`${API_URL}/prospects?limit=500`);
        if (!response.ok) throw new Error('Erreur API');
        const data = await response.json();
        allProspects = data.prospects || [];
        renderTable(allProspects);
        document.getElementById('resultCount').textContent = `${allProspects.length} résultats`;
    } catch (error) {
        document.getElementById('prospectsBody').innerHTML =
            `<tr><td colspan="9" style="color:red;">❌ Erreur: ${error.message}</td></tr>`;
    }
}

async function loadStats() {
    try {
        const response = await fetch(`${API_URL}/stats`);
        const stats = await response.json();
        
        document.getElementById('statTotal').textContent = stats.total_prospects || 0;
        document.getElementById('statAnalyzed').textContent = stats.analyzed || 0;
        document.getElementById('statVerified').textContent = stats.verified || 0;
        document.getElementById('statHighScore').textContent = stats.high_score || 0;
        
        // Calculer joignables / non joignables
        let joignables = 0, nonJoignables = 0;
        allProspects.forEach(p => {
            if (p.phone_verification?.valid === true) joignables++;
            else if (p.phone_verification?.valid === false) nonJoignables++;
        });
        document.getElementById('statJoignables').textContent = joignables;
        document.getElementById('statNonJoignables').textContent = nonJoignables;
        
    } catch (error) {
        console.error('Erreur stats:', error);
    }
}

// ─── TABLEAU ──────────────────────────────────

function renderTable(prospects) {
    const tbody = document.getElementById('prospectsBody');
    
    if (!prospects || prospects.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:#999;">Aucun prospect trouvé</td></tr>';
        return;
    }

    let html = '';
    prospects.slice(0, 100).forEach(p => {
        // Type badge
        const typeMap = {
            'commerce': 'badge-commerce',
            'pharmacy': 'badge-pharmacy',
            'restaurant': 'badge-restaurant',
            'construction': 'badge-construction',
            'transport': 'badge-transport',
            'service': 'badge-service'
        };
        const typeClass = typeMap[p.analysis?.business_type] || '';
        const typeLabel = p.analysis?.business_type?.toUpperCase() || '❓';
        
        // Stock badge
        const stockNeed = p.analysis?.stock_management_need;
        const stockBadge = stockNeed === true 
            ? '<span class="badge badge-success">📦 Oui</span>'
            : '<span class="badge badge-danger">📦 Non</span>';
        
        // Joignable badge
        const verified = p.phone_verification?.valid;
        let verifBadge = '<span class="badge badge-warning">⏳</span>';
        if (verified === true) verifBadge = '<span class="badge badge-success">✅</span>';
        else if (verified === false) verifBadge = '<span class="badge badge-danger">❌</span>';
        
        const score = p.analysis?.score || 0;
        const justification = p.analysis?.justification || 'N/A';
        
        html += `
            <tr>
                <td>${p.id}</td>
                <td><strong>${p.name || 'N/A'}</strong></td>
                <td>${p.phone || 'N/A'}</td>
                <td>${p.sector || 'N/A'}</td>
                <td><span class="badge ${typeClass}">${typeLabel}</span></td>
                <td><strong>${score}</strong></td>
                <td>${stockBadge}</td>
                <td>${verifBadge}</td>
                <td><small>${justification.substring(0, 60)}${justification.length > 60 ? '...' : ''}</small></td>
            </tr>
        `;
    });
    tbody.innerHTML = html;
}

// ─── EXPORTS ──────────────────────────────────

function exportJSON() {
    window.open(`${API_URL}/prospects/export/json`, '_blank');
}

function exportCSV() {
    window.open(`${API_URL}/prospects/export/csv`, '_blank');
}

// ─── STATUS ──────────────────────────────────

function showStatus(element, type, message) {
    element.className = 'action-status ' + type;
    element.textContent = message;
    element.style.display = 'block';
    
    if (type === 'success' || type === 'error') {
        setTimeout(() => { element.style.display = 'none'; }, 15000);
    }
}

// ─── DÉMARRAGE ───────────────────────────────

document.addEventListener('DOMContentLoaded', refreshData);

// Auto-refresh toutes les 30 secondes
setInterval(refreshData, 30000);