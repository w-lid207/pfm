// ═══════════════════════════════════════════════════════════
// CollecteOpt — app.js v3.0
// Enhanced: point modal (name/capacity/fill), zone polygons, OSRM
// ═══════════════════════════════════════════════════════════

// ── State ────────────────────────────────────────────────
const state = {
    mode: 'depot', // 'depot' | 'point' | 'landfill'
    depot: null,
    landfill: { lat: 30.38, lng: -9.55 }, // Default landfill near Agadir
    points: [],
    zones: [],
    camions: [],
    results: null,
    osrmRoutes: [],
};

let map, simInterval, simTrucks = [];
const routeLayers = L.layerGroup();
const markerLayers = L.layerGroup();
const zoneLayers = L.layerGroup();
const simLayers = L.layerGroup();

// Truck route colors
const COLORS = ['#2563EB', '#DC2626', '#16A34A', '#EA580C', '#7C3AED', '#0891B2', '#DB2777', '#65A30D'];

// Fuel configuration
const FUEL_STATIONS = [
    // Agadir
    { lat: 30.4320, lng: -9.5850, nom: 'Station Afriquia – Agadir Centre' },
    { lat: 30.4050, lng: -9.5720, nom: 'Station Shell – Agadir Hay Mohammadi' },
    { lat: 30.4480, lng: -9.6100, nom: 'Station Total – Agadir Route Essaouira' },
    { lat: 30.3900, lng: -9.5400, nom: 'Station Winxo – Agadir Zone Industrielle' },
    // Casablanca
    { lat: 33.5898, lng: -7.6038, nom: 'Station Shell – Casa Centre' },
    { lat: 33.5532, lng: -7.6409, nom: 'Station Afriquia – Casa Maarif' },
    { lat: 33.5851, lng: -7.5627, nom: 'Station Total – Casa Roches Noires' },
    // Rabat
    { lat: 34.0208, lng: -6.8416, nom: 'Station Winxo – Rabat Agdal' },
    // Marrakech
    { lat: 31.6294, lng: -8.0062, nom: 'Station Afriquia – Marrakech Guéliz' }, // Guéliz
    // Fès
    { lat: 34.0331, lng: -5.0002, nom: 'Station Shell – Fès Ville Nouvelle' },
    // Tanger
    { lat: 35.7594, lng: -5.8339, nom: 'Station Total – Tanger Centre' },
];
const FUEL_CAPACITY = 200;
const FUEL_CONSUMPTION_KM = 15.0; // Exaggerated for simulation purposes (normal is 0.35)
const FUEL_THRESHOLD_PCT = 0.15;

function findNearestStation(lat, lng) {
    let best = null, bestDist = Infinity;
    FUEL_STATIONS.forEach(fs => {
        const d = haversineMeters(lat, lng, fs.lat, fs.lng);
        if (d < bestDist) { bestDist = d; best = fs; }
    });
    return best;
}

async function buildDetourPath(fromLat, fromLng, toLat, toLng, stepM = 20) {
    try {
        const route = await fetchFullOSRMRoute([[fromLat, fromLng], [toLat, toLng]]);
        if (route && route.length > 1) {
            return interpolateRoute(route, stepM);
        }
    } catch (e) {
        console.warn('Detour OSRM failed, falling back to straight line', e);
    }
    // Fallback if OSRM fails completely
    const d = haversineMeters(fromLat, fromLng, toLat, toLng);
    const n = Math.max(2, Math.ceil(d / stepM));
    const pts = [];
    for (let i = 0; i <= n; i++) {
        const frac = i / n;
        pts.push([fromLat + (toLat - fromLat) * frac, fromLng + (toLng - fromLng) * frac]);
    }
    return pts;
}

// ── Init ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    map = L.map('map', { zoomControl: true }).setView([30.4278, -9.5981], 13);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap',
        maxZoom: 19,
    }).addTo(map);

    routeLayers.addTo(map);
    markerLayers.addTo(map);
    zoneLayers.addTo(map);
    simLayers.addTo(map);

    map.on('click', onMapClick);

    // ── Keyboard shortcut ──
    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') closeModal();
    });
});

// ══════════════════════════════════════════════════════════
// MAP INTERACTIONS
// ══════════════════════════════════════════════════════════

function onMapClick(e) {
    const { lat, lng } = e.latlng;

    if (state.mode === 'depot') {
        state.depot = { lat, lng };
        redrawMarkers();
        setMode('point');
        showToast('Dépôt placé. Mode: Points de collecte.', 'success');
    } else if (state.mode === 'point') {
        // Show modal instead of adding directly
        document.getElementById('modalPointLat').value = lat;
        document.getElementById('modalPointLng').value = lng;
        document.getElementById('modalPointName').value = `Point ${state.points.length + 1}`;
        document.getElementById('modalPointBennes').value = 2;
        generateRandomWaste();
        document.getElementById('addPointModal').style.display = 'flex';
        setTimeout(() => document.getElementById('modalPointName').focus(), 100);
    } else if (state.mode === 'landfill') {
        state.landfill = { lat, lng };
        redrawMarkers();
        showToast('Décharge placée sur la carte.', 'success');
        setMode('point');
    }
}

function closeModal() {
    document.getElementById('addPointModal').style.display = 'none';
}

function generateRandomWaste() {
    const bennes = parseInt(document.getElementById('modalPointBennes').value) || 2;
    // Total 150-600kg rules -> approx 100-250kg per bin
    const minVol = bennes * 100;
    const maxVol = bennes * 250;
    const randVol = Math.floor(Math.random() * (maxVol - minVol + 1)) + minVol;
    document.getElementById('modalPointVolume').value = randVol;
}

function confirmAddPoint() {
    const lat = parseFloat(document.getElementById('modalPointLat').value);
    const lng = parseFloat(document.getElementById('modalPointLng').value);
    const name = document.getElementById('modalPointName').value || `Point ${state.points.length + 1}`;
    const bennes = parseInt(document.getElementById('modalPointBennes').value) || 2;
    const volume = parseInt(document.getElementById('modalPointVolume').value) || 350;

    const capacity = Math.max(volume, bennes * 300);
    const fill = Math.min(100, Math.round((volume / capacity) * 100));

    // Generate individual bin details
    const bennes_detail = [];
    let remainingVol = volume;
    for (let i = 0; i < bennes; i++) {
        // Distribute volume somewhat randomly but sum equals total
        let bVol = (i === bennes - 1) ? remainingVol : Math.floor((Math.random() * 0.4 + 0.6) * (volume / bennes));
        if (bVol < 0) bVol = 0;
        remainingVol -= bVol;

        bennes_detail.push({
            id: i + 1,
            volume: bVol,
            type: Math.random() > 0.8 ? 'Dangereux' : 'Normal', // 20% chance for dangerous waste
            capacity: Math.round(capacity / bennes)
        });
    }

    state.points.push({ lat, lng, name, capacity, fill, volume, nombre_bennes: bennes, selected: true, bennes_detail });
    closeModal();
    redrawMarkers();
    updatePointsList();
    if (typeof updateMiniDash === 'function') updateMiniDash();
    showToast(`${name} ajouté (${volume} kg, ${bennes} bennes)`, 'success');
}

// ── Import JSON ─────────────────────────────────────────
function importJSON(event) {
    const file = event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = function (e) {
        try {
            const data = JSON.parse(e.target.result);
            if (data.depot) {
                state.depot = data.depot;
                document.getElementById('depotInfo').innerHTML = `<span class="tag tag-green">✓ ${state.depot.lat.toFixed(4)}, ${state.depot.lng.toFixed(4)}</span>`;
            }
            if (data.points && Array.isArray(data.points)) {
                data.points.forEach(p => {
                    const bennes = p.nombre_bennes || Math.ceil((p.volume || 150) / 150);
                    const volume = p.volume || (bennes * 200);
                    const capacity = p.capacite || bennes * 300;

                    const bennes_detail = [];
                    let remainingVol = volume;
                    for (let i = 0; i < bennes; i++) {
                        let bVol = (i === bennes - 1) ? remainingVol : Math.floor((Math.random() * 0.4 + 0.6) * (volume / bennes));
                        if (bVol < 0) bVol = 0;
                        remainingVol -= bVol;
                        bennes_detail.push({
                            id: i + 1,
                            volume: bVol,
                            type: Math.random() > 0.8 ? 'Dangereux' : 'Normal',
                            capacity: Math.round(capacity / bennes)
                        });
                    }

                    state.points.push({
                        lat: p.lat,
                        lng: p.lng,
                        name: p.nom || `Point ${state.points.length + 1}`,
                        capacity: capacity,
                        fill: p.fill || 100,
                        volume: volume,
                        nombre_bennes: bennes,
                        selected: true,
                        bennes_detail: bennes_detail
                    });
                });
            }
            if (data.camions && Array.isArray(data.camions)) {
                state.camions = data.camions;
            }
            redrawMarkers();
            updatePointsList();
            updateCamionsList();
            if (typeof updateMiniDash === 'function') updateMiniDash();
            if (state.points.length > 0) {
                map.setView([state.points[0].lat, state.points[0].lng], 13);
            }
            showToast('Données JSON importées !', 'success');
        } catch (err) {
            showToast('Erreur lors de la lecture du JSON.', 'error');
        }
    };
    reader.readAsText(file);
    event.target.value = ""; // reset
}

// ── Modes ────────────────────────────────────────────────
function setMode(m) {
    state.mode = m;
    document.querySelectorAll('.mode-btn').forEach(b => {
        b.classList.toggle('active', b.getAttribute('data-mode') === m);
    });
}

// ── Point fill → color ──────────────────────────────────
function getPointColor(fill) {
    if (fill >= 80) return '#DC2626'; // red = full
    if (fill >= 50) return '#EA580C'; // orange
    return '#16A34A';                 // green
}

// ── Redraw all markers ──────────────────────────────────
function redrawMarkers() {
    markerLayers.clearLayers();

    // Depot
    if (state.depot) {
        L.marker([state.depot.lat, state.depot.lng], {
            icon: L.divIcon({
                className: '',
                html: `<div style="background:#2563EB;color:white;padding:5px 8px;border-radius:8px;font-size:11px;font-weight:700;box-shadow:0 2px 8px rgba(37,99,235,.4)">🏭 Dépôt</div>`,
                iconAnchor: [28, 18],
            }),
            zIndexOffset: 900,
        }).addTo(markerLayers);

        const info = document.getElementById('depotInfo');
        if (info) info.innerHTML = `<span class="tag tag-green">✓ ${state.depot.lat.toFixed(4)}, ${state.depot.lng.toFixed(4)}</span>`;
    }

    // Landfill
    if (state.landfill) {
        L.marker([state.landfill.lat, state.landfill.lng], {
            icon: L.divIcon({
                className: '',
                html: `<div style="background:#7C3AED;color:white;padding:5px 10px;border-radius:8px;font-size:11px;font-weight:700;box-shadow:0 2px 8px rgba(124,58,237,.4)">🏗️ Décharge</div>`,
                iconAnchor: [36, 18],
            }),
            zIndexOffset: 850,
        }).addTo(markerLayers);

        const lfInfo = document.getElementById('landfillInfo');
        if (lfInfo) lfInfo.innerHTML = `<span class="tag tag-green">✓ ${state.landfill.lat.toFixed(4)}, ${state.landfill.lng.toFixed(4)}</span>`;
    }

    // Points
    state.points.forEach((p, i) => {
        if (p.selected === false) return; // Skip unselected points

        const color = getPointColor(p.fill);
        const isFull = p.fill >= 80;
        const numBennes = p.nombre_bennes || 1;

        for (let b = 0; b < numBennes; b++) {
            // Visually offset multiple bins side-by-side in pixels, without changing exact map coordinates
            const xOffset = (b - (numBennes - 1) / 2) * 28; // 28px spacing

            // Get bin details if available, else fallback
            const bInfo = (p.bennes_detail && p.bennes_detail[b]) ? p.bennes_detail[b] : {
                id: b + 1, volume: Math.round(p.volume / numBennes), capacity: Math.round(p.capacity / numBennes), type: 'Normal'
            };
            const bFill = Math.min(100, Math.round((bInfo.volume / bInfo.capacity) * 100));
            const color = getPointColor(bFill);
            const isFull = bFill >= 80;

            const marker = L.marker([p.lat, p.lng], {
                icon: L.divIcon({
                    className: '',
                    html: `<div style="
                        background:${color};color:white;
                        border-radius:50%;width:26px;height:26px;
                        display:flex;align-items:center;justify-content:center;
                        font-size:11px;font-weight:700;
                        box-shadow:0 2px 6px ${color}66;
                        border:2px solid white;
                        position: relative;
                        ${isFull ? 'animation:pulse 1.5s infinite' : ''}
                    ">
                        ${i + 1}<span style="font-size:8.5px;margin-left:0.5px;opacity:0.9;font-weight:600">-${b + 1}</span>
                        <div style="position:absolute;top:-4px;right:-4px;background:#2563EB;color:white;border-radius:50%;width:12px;height:12px;font-size:8px;display:flex;align-items:center;justify-content:center;border:1px solid white;box-shadow:0 1px 3px rgba(0,0,0,0.3);">✓</div>
                    </div>`,
                    iconAnchor: [13 - xOffset, 13],
                    popupAnchor: [xOffset, -13],
                }),
                zIndexOffset: 500 + b,
            }).addTo(markerLayers);

            marker.bindPopup(`
                <div style="font-family:Inter,sans-serif;min-width:180px">
                    <div style="font-weight:700;font-size:14px;margin-bottom:2px;border-bottom:1px solid #eee;padding-bottom:4px">Point ${i + 1} : Benne ${b + 1}</div>
                    <div style="display:flex;justify-content:space-between;margin-top:6px;font-size:12px;">
                        <span style="color:#555">Quantité:</span>
                        <b>${bInfo.volume} kg</b>
                    </div>
                    <div style="display:flex;justify-content:space-between;margin-top:4px;font-size:12px;">
                        <span style="color:#555">Type de déchet:</span>
                        <b style="color:${bInfo.type === 'Dangereux' ? '#DC2626' : '#16A34A'}">${bInfo.type}</b>
                    </div>
                    <div style="display:flex;justify-content:space-between;margin-top:4px;margin-bottom:6px;font-size:12px;">
                        <span style="color:#555">Remplissage:</span>
                        <b style="color:${color}">${bFill}%</b>
                    </div>
                    <div style="background:#eee;border-radius:4px;height:8px;overflow:hidden">
                        <div style="background:${color};height:100%;width:${bFill}%;border-radius:4px"></div>
                    </div>
                </div>
            `);
        }
    });

    document.getElementById('pointCount').textContent = state.points.reduce((sum, p) => sum + (p.selected !== false ? (p.nombre_bennes || 1) : 0), 0);
}

// ── Update points list in sidebar ───────────────────────
function updatePointsList() {
    const el = document.getElementById('pointsList');
    if (!el) return;

    if (state.points.length === 0) {
        el.innerHTML = '<div style="font-size:11px;color:var(--text-muted);padding:6px">Aucun point ajouté</div>';
        return;
    }

    el.innerHTML = state.points.map((p, i) => {
        const color = getPointColor(p.fill);
        const fillTag = p.fill >= 80 ? 'tag-red' : p.fill >= 50 ? 'tag-orange' : 'tag-green';
        return `
            <div class="item-card">
                <div class="dot" style="background:${color}"></div>
                <div class="info">
                    <div class="name">${p.name}</div>
                    <div class="detail">${p.volume}kg · ${p.nombre_bennes || Math.ceil((p.capacity || 1) / 300)} bennes</div>
                </div>
                <input type="checkbox" ${p.selected !== false ? 'checked' : ''} onchange="togglePointSelection(${i})" style="margin: 0 8px; cursor: pointer;">
                <button class="remove-btn" onclick="removePoint(${i})">×</button>
            </div>`;
    }).join('');
}

function togglePointSelection(i) {
    state.points[i].selected = !state.points[i].selected;
    redrawMarkers();
}

function removePoint(i) {
    state.points.splice(i, 1);
    redrawMarkers();
    updatePointsList();
    if (typeof updateMiniDash === 'function') updateMiniDash();
}

// ══════════════════════════════════════════════════════════
// ZONES (polygons)
// ══════════════════════════════════════════════════════════

function addZone() {
    const name = document.getElementById('zoneNameInput')?.value.trim();
    const pointsStr = document.getElementById('zonePointsInput')?.value.trim();
    const color = document.getElementById('zoneColorInput')?.value.trim() || COLORS[state.zones.length % COLORS.length];

    if (!name) { showToast('Entrez un nom de zone', 'warning'); return; }

    const indices = pointsStr.split(',').map(s => parseInt(s.trim()) - 1).filter(n => !isNaN(n) && n >= 0 && n < state.points.length);

    if (indices.length < 1) { showToast('Une zone nécessite au moins 1 point', 'warning'); return; }

    const alreadyAssigned = [];
    indices.forEach(i => {
        const pId = i + 1;
        state.zones.forEach(z => {
            if (z.points.includes(pId) && !alreadyAssigned.includes(pId)) {
                alreadyAssigned.push(pId);
            }
        });
    });

    if (alreadyAssigned.length > 0) {
        showToast(`Points déjà assignés à une autre zone : ${alreadyAssigned.join(', ')}`, 'warning');
        return;
    }

    const points = indices.map(i => state.points[i]);
    state.zones.push({ nom: name, points: indices.map(i => i + 1), color, coords: points.map(p => [p.lat, p.lng]) });

    redrawZones();
    updateZonesList();

    document.getElementById('zoneNameInput').value = '';
    document.getElementById('zonePointsInput').value = '';
    document.getElementById('zoneColorInput').value = '';
    showToast(`Zone "${name}" ajoutée`, 'success');
}

function redrawZones() {
    zoneLayers.clearLayers();
    state.zones.forEach(z => {
        L.polygon(z.coords, {
            color: z.color,
            fillColor: z.color,
            fillOpacity: 0.12,
            weight: 2,
            dashArray: '6 4',
        }).addTo(zoneLayers).bindPopup(`<b>${z.nom}</b><br>${z.coords.length} points`);
    });
}

function updateZonesList() {
    const el = document.getElementById('zonesList');
    if (!el) return;

    if (state.zones.length === 0) {
        el.innerHTML = '<div style="font-size:11px;color:var(--text-muted);padding:6px">Aucune zone</div>';
        return;
    }

    el.innerHTML = state.zones.map((z, i) =>
        `<div class="item-card">
            <div class="dot" style="background:${z.color}"></div>
            <div class="info">
                <div class="name">${z.nom}</div>
                <div class="detail">${z.coords.length} points</div>
            </div>
            <button class="remove-btn" onclick="removeZone(${i})">×</button>
         </div>`
    ).join('');
}

function removeZone(i) {
    state.zones.splice(i, 1);
    redrawZones();
    updateZonesList();
}

// ══════════════════════════════════════════════════════════
// CAMIONS
// ══════════════════════════════════════════════════════════

function addCamion() {
    const cap = parseInt(document.getElementById('camionCapInput')?.value) || 5000;
    const cost = parseInt(document.getElementById('camionCostInput')?.value) || 200;
    const pause = parseInt(document.getElementById('camionPauseInput')?.value) || 45;
    const unload = parseInt(document.getElementById('camionUnloadInput')?.value) || 30;

    state.camions.push({
        capacite: cap, cout_fixe: cost,
        pause_obligatoire: pause, temps_de_dechargement: unload
    });
    updateCamionsList();
    if (typeof updateMiniDash === 'function') updateMiniDash();
}

function updateCamionsList() {
    const el = document.getElementById('camionsList');
    if (!el) return;
    el.innerHTML = state.camions.map((c, i) =>
        `<div class="item-card">
            <div class="dot" style="background:${COLORS[i % COLORS.length]}"></div>
            <div class="info">
                <div class="name">Camion ${i + 1}</div>
                <div class="detail">${c.capacite} kg · ${c.cout_fixe} MAD/km</div>

            </div>
            <button class="remove-btn" onclick="removeCamion(${i})">×</button>
         </div>`
    ).join('');
}

function removeCamion(i) {
    state.camions.splice(i, 1);
    updateCamionsList();
    if (typeof updateMiniDash === 'function') updateMiniDash();
}

// ══════════════════════════════════════════════════════════
// UTILITIES
// ══════════════════════════════════════════════════════════

function showToast(msg, type = 'info') {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = msg;
    container.appendChild(toast);
    setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 300); }, 3500);
}

async function searchCity() {
    const q = document.getElementById('citySearch')?.value;
    if (!q) return;
    try {
        const resp = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(q)}`);
        const data = await resp.json();
        if (data.length > 0) {
            map.setView([parseFloat(data[0].lat), parseFloat(data[0].lon)], 13);
        } else {
            showToast('Ville introuvable', 'warning');
        }
    } catch (e) { showToast('Erreur recherche', 'error'); }
}

function resetAll() {
    state.depot = null;
    state.landfill = { lat: 30.38, lng: -9.55 };
    state.points = [];
    state.zones = [];
    state.camions = [];
    state.results = null;
    state.osrmRoutes = [];
    routeLayers.clearLayers();
    markerLayers.clearLayers();
    zoneLayers.clearLayers();
    simLayers.clearLayers();

    document.getElementById('depotInfo').innerHTML = '<span class="tag tag-orange">⊘ Non placé</span>';
    const lfInfo = document.getElementById('landfillInfo');
    if (lfInfo) lfInfo.innerHTML = '<span class="tag tag-green">✓ Par défaut</span>';
    document.getElementById('pointCount').textContent = '0';
    updatePointsList();
    updateZonesList();
    updateCamionsList();

    const rp = document.getElementById('resultsPanel');
    if (rp) rp.classList.remove('visible');

    setMode('depot');
    showToast('Tout a été réinitialisé', 'info');
}

// ══════════════════════════════════════════════════════════
// OSRM ROUTING (direct browser calls — fast, no backend proxy)
// ══════════════════════════════════════════════════════════

async function fetchFullOSRMRoute(waypoints) {
    if (!waypoints || waypoints.length < 2) return waypoints || [];
    const OSRM_BASE = 'https://router.project-osrm.org';
    const CHUNK_SIZE = 50;
    const fullRoute = [];

    for (let i = 0; i < waypoints.length - 1; i += CHUNK_SIZE - 1) {
        const chunk = waypoints.slice(i, i + CHUNK_SIZE);
        let success = false;
        try {
            const coordsStr = chunk.map(c => `${c[1].toFixed(6)},${c[0].toFixed(6)}`).join(';');
            const url = `${OSRM_BASE}/route/v1/driving/${coordsStr}?overview=full&geometries=geojson`;
            const resp = await fetch(url, { signal: AbortSignal.timeout(10000) });
            if (resp.status === 200) {
                const data = await resp.json();
                if (data.code === 'Ok' && data.routes && data.routes.length > 0) {
                    const segment = data.routes[0].geometry.coordinates.map(([lon, lat]) => [lat, lon]);
                    if (fullRoute.length > 0) segment.shift();
                    fullRoute.push(...segment);
                    success = true;
                }
            }
        } catch (e) {
            console.warn('OSRM chunk failed:', e);
        }

        if (!success) {
            console.warn('Fallback to straight lines for chunk');
            const segment = [...chunk];
            if (fullRoute.length > 0) segment.shift();
            fullRoute.push(...segment);
        }
    }
    return fullRoute.length > 0 ? fullRoute : waypoints;
}

function interpolateRoute(coords, stepMeters = 20) {
    if (!coords || coords.length < 2) return coords || [];
    const result = [coords[0]];
    for (let i = 0; i < coords.length - 1; i++) {
        const [lat1, lng1] = coords[i];
        const [lat2, lng2] = coords[i + 1];
        const d = haversineMeters(lat1, lng1, lat2, lng2);
        if (d <= stepMeters) { result.push(coords[i + 1]); continue; }
        const n = Math.ceil(d / stepMeters);
        for (let s = 1; s <= n; s++) {
            const t = s / n;
            result.push([lat1 + (lat2 - lat1) * t, lng1 + (lng2 - lng1) * t]);
        }
    }
    return result;
}

function haversineMeters(lat1, lng1, lat2, lng2) {
    const R = 6371000;
    const dLat = (lat2 - lat1) * Math.PI / 180, dLng = (lng2 - lng1) * Math.PI / 180;
    const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLng / 2) ** 2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// ══════════════════════════════════════════════════════════
// OPTIMISATION
// ══════════════════════════════════════════════════════════

async function runOptimization() {
    if (!state.depot) { showToast('Placez d\'abord le dépôt sur la carte', 'warning'); return; }
    if (state.points.length < 1) { showToast('Ajoutez au moins 1 point de collecte', 'warning'); return; }
    if (state.camions.length === 0) { showToast('Ajoutez au moins un camion', 'warning'); return; }

    const btn = document.getElementById('optimizeBtn');
    if (btn) { btn.disabled = true; btn.innerHTML = '<div class="spinner"></div> Optimisation...'; }

    const multiObj = document.getElementById('toggleMultiObj')?.checked ?? true;
    const simulation = document.getElementById('toggleSimulation')?.checked ?? false;

    const payload = {
        depot: state.depot,
        points: state.points.filter(p => p.selected !== false).map(p => ({ lat: p.lat, lng: p.lng, volume: p.volume })),
        zones: state.zones.map(z => ({ nom: z.nom, points: z.points })),
        camions: state.camions.map(c => ({ capacite: c.capacite, cout_fixe: c.cout_fixe })),
        parametres: { multi_objectif: multiObj, simulation: simulation, landfill: state.landfill },
    };

    try {
        const resp = await fetch('/api/solve', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const data = await resp.json();
        if (!data.success) { showToast(`Erreur: ${data.error}`, 'error'); return; }

        state.results = data;
        state.osrmRoutes = []; // Clear previous OSRM routes
        const routes = data.vrp?.routes || [];

        // INSTANT: show results with straight-line routes
        drawRoutes(data);
        showResults(data);
        showToast('✅ Optimisation terminée !', 'success');
        if (btn) { btn.disabled = false; btn.innerHTML = '🚀 Lancer l\'Optimisation'; }

        // BACKGROUND: upgrade to real OSRM road routes (non-blocking)
        fetchOSRMRoutesInBackground(routes, data);

    } catch (e) {
        showToast(`Erreur: ${e.message}`, 'error');
        if (btn) { btn.disabled = false; btn.innerHTML = '🚀 Lancer l\'Optimisation'; }
    }
}

async function fetchOSRMRoutesInBackground(routes, data) {
    try {
        const osrmResults = [];
        for (let i = 0; i < routes.length; i++) {
            const wp = routes[i].coordinates || [];
            if (wp.length >= 2) {
                osrmResults.push(await fetchFullOSRMRoute(wp));
                if (i < routes.length - 1) await new Promise(r => setTimeout(r, 300));
            } else {
                osrmResults.push(wp);
            }
        }
        state.osrmRoutes = osrmResults;
        routes.forEach((route, i) => { route.osrm_coordinates = osrmResults[i]; });
        drawRoutes(data);
        showToast('🗺️ Routes routières mises à jour', 'success');
    } catch (e) {
        console.warn('Background OSRM fetch failed:', e);
    }
}

// ── Draw routes on map ──────────────────────────────────
function drawRoutes(data) {
    routeLayers.clearLayers();
    const routes = data.vrp?.routes || [];

    routes.forEach((route, i) => {
        const color = COLORS[i % COLORS.length];
        const coords = route.osrm_coordinates || route.coordinates || [];

        if (coords.length >= 2) {
            L.polyline(coords, {
                color,
                weight: 4,
                opacity: 0.8,
                lineJoin: 'round',
            }).addTo(routeLayers);
        }

        // Point markers along route
        (route.visits || []).forEach(v => {
            if (v.lat && v.lng) {
                L.circleMarker([v.lat, v.lng], {
                    radius: 5, color: '#fff', fillColor: color,
                    fillOpacity: 1, weight: 2,
                }).addTo(routeLayers);
            }
        });
    });
}

// ── Display results panel ───────────────────────────────
function showResults(data) {
    const panel = document.getElementById('resultsPanel');
    if (panel) panel.classList.add('visible');

    const vrp = data.vrp || {};
    const eval_ = data.evaluation || {};
    const metrics = eval_.metrics || {};
    const score = eval_.scores?.global ?? eval_.score_global ?? '--';

    setText('scoreGlobal', typeof score === 'number' ? `${score.toFixed(1)}%` : score);
    setText('metricDistance', `${metrics.total_distance_km ?? vrp.total_distance_km ?? 0} km`);
    setText('metricCO2', `${metrics.co2_total_kg?.toFixed(1) ?? '--'} kg`);
    setText('metricCost', `${metrics.cout_total_mad?.toFixed(0) ?? vrp.total_cost_mad?.toFixed(0) ?? '--'} MAD`);
    setText('metricTrucks', metrics.num_trucks_used ?? vrp.routes?.length ?? 0);
    setText('metricUtil', `${metrics.utilisation_moyenne_pct?.toFixed(0) ?? '--'}%`);
    setText('metricDuration', `${metrics.duree_estimee_min ? (metrics.duree_estimee_min / 60).toFixed(1) : '--'} h`);
    setText('metricPending', vrp.points_pending?.length ?? 0);
}

function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

// ══════════════════════════════════════════════════════════
// SIMULATION
// ══════════════════════════════════════════════════════════

let simSpeed = 40;
let isSimPaused = false;
let simStepCount = 0;
let simAlerts = [];
let simLandfillVisits = 0;
let simLandfillTotal = 0;
let STEPS_PER_TICK = 2;

function startAdvancedSimulation() {
    if (typeof switchTab === 'function') switchTab('sim');
    startSimulation();
}

function pauseAdvancedSimulation() {
    isSimPaused = true;
    showToast('Simulation en pause', 'info');
}

function stopAdvancedSimulation() {
    stopSimulation();
    showToast('Simulation arrêtée', 'info');
}

function changeSimSpeed() {
    const selector = document.getElementById('speedSelect');
    if (selector) {
        simSpeed = parseInt(selector.value);
        if (simInterval && !isSimPaused) {
            clearInterval(simInterval);
            simInterval = setInterval(simLoopTick, simSpeed);
        }
    }
}

function addAdvAlert(type, title, detail) {
    const icon = type === 'danger' ? '🔴' : type === 'warning' ? '⏰' : type === 'success' ? '✅' : 'ℹ️';
    const time = new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    simAlerts.unshift({ type, title, detail, time, icon });
    renderAdvAlerts();
}

function renderAdvAlerts() {
    const container = document.getElementById('advAlertsList');
    const badge = document.getElementById('advAlertBadge');
    if (!container) return;

    if (badge) badge.textContent = simAlerts.length;

    if (simAlerts.length === 0) {
        container.innerHTML = '<div style="font-size:11px;color:var(--text-muted);padding:6px">Aucune alerte</div>';
        return;
    }
    container.innerHTML = simAlerts.slice(0, 30).map(a => `
        <div style="padding:10px 12px; border-radius:4px; border-left:3px solid ${a.type === 'danger' ? 'var(--accent-red)' : a.type === 'warning' ? 'var(--accent-orange)' : 'var(--accent-green)'}; background:var(--bg-primary); margin-bottom:6px;">
            <div style="font-size:12px; font-weight:600; margin-bottom:2px;">${a.icon} ${a.title}</div>
            <div style="font-size:10px; color:var(--text-muted);">${a.detail} · ${a.time}</div>
        </div>
    `).join('');
}

function startSimulation() {
    if (!state.results) { showToast('Lancez l\'optimisation d\'abord', 'warning'); return; }

    // Check if OSRM routes are retrieved
    if (state.osrmRoutes.length === 0 && (state.results.vrp?.routes?.length || 0) > 0) {
        showToast('⏳ Veuillez patienter, chargement des routes sur le réseau routier en cours...', 'warning');
        return;
    }

    if (isSimPaused && simInterval) {
        isSimPaused = false;
        showToast('▶ Reprise de la simulation', 'info');
        return;
    }

    stopSimulation();
    simLayers.clearLayers();

    simStepCount = 0;
    simAlerts = [];
    simLandfillVisits = 0;
    simLandfillTotal = 0;
    isSimPaused = false;
    renderAdvAlerts();

    if (document.getElementById('advLandfillVisits')) {
        document.getElementById('advLandfillVisits').textContent = '0';
        document.getElementById('advLandfillTotal').textContent = '0';
        document.getElementById('advSimStep').textContent = '0';
        document.getElementById('advSimDone').textContent = '0';
        document.getElementById('advSimCollected').textContent = '0';
    }

    const routes = state.results.vrp?.routes || [];
    const depot = state.depot || { lat: 30.4278, lng: -9.5981 };
    const landfill = state.landfill || { lat: 30.38, lng: -9.55 };

    if (document.getElementById('advSimTotal')) {
        document.getElementById('advSimTotal').textContent = routes.length;
    }

    // Draw fuel stations
    FUEL_STATIONS.forEach(fs => {
        L.marker([fs.lat, fs.lng], {
            icon: L.divIcon({
                className: '',
                html: `<div style="background:#F59E0B;color:white;border-radius:50%;width:20px;height:20px;display:flex;align-items:center;justify-content:center;font-size:10px;box-shadow:0 1px 4px rgba(0,0,0,.3)">⛽</div>`,
                iconAnchor: [10, 10],
            }),
            zIndexOffset: 800,
        }).addTo(simLayers).bindPopup(`<b>${fs.nom}</b>`);
    });

    addAdvAlert('info', 'Simulation démarrée', `${routes.length} camions déployés`);

    // ── Build simulation trucks ───────────────────────────
    const trucks = routes.map((route, idx) => {
        const color = COLORS[idx % COLORS.length];
        const rawCoords = route.osrm_coordinates || route.coordinates || [];
        const smoothCoords = interpolateRoute(rawCoords, 20);

        // Capacity tracking from VRP visits
        const visits = route.visits || [];
        const capacity = route.camion_capacite || 5000;

        // Build waypoint triggers: at which step index does the truck arrive at each visit?
        // IMPORTANT: search only AFTER previous trigger's step to handle repeated visits
        const visitTriggers = [];
        let searchFrom = 0;
        visits.forEach(v => {
            let bestIdx = searchFrom, bestDist = Infinity;
            for (let s = searchFrom; s < smoothCoords.length; s++) {
                const d = haversineMeters(smoothCoords[s][0], smoothCoords[s][1], v.lat, v.lng);
                if (d < bestDist) { bestDist = d; bestIdx = s; }
                // Once we start moving away from the target, stop searching
                if (d > bestDist * 3 && bestDist < 200) break;
            }
            visitTriggers.push({
                stepIdx: bestIdx,
                volume: v.quantite_collectee || 0,
                name: v.nom || `Point ${v.point_id}`,
                lat: v.lat, lng: v.lng,
                isLandfill: v.is_landfill_trip || false,
            });
            // Next visit must be at or after this one
            searchFrom = bestIdx + 1;
        });

        // Tiny stagger: 3 ticks (150ms) per truck — barely noticeable but prevents z-fighting
        const startDelay = idx * 3;

        const marker = L.marker([depot.lat, depot.lng], {
            icon: L.divIcon({
                className: '',
                html: `<div style="background:${color};color:white;border-radius:50%;width:36px;height:36px;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;box-shadow:0 2px 10px rgba(0,0,0,.45);border:2.5px solid white;letter-spacing:-0.5px">🚛${idx + 1}</div>`,
                iconAnchor: [18, 18],
            }),
            zIndexOffset: 1000 + idx,
        }).addTo(simLayers);

        marker.bindPopup(`<b>Camion ${idx + 1}</b><br>Chargement: 0%`);

        // Distinct colored trail
        const trail = L.polyline([], { color, weight: 3, opacity: 0.6, dashArray: '4 6' }).addTo(simLayers);

        return {
            marker, trail, color, idx,
            // Route segments: start with the main route
            segments: [{ coords: smoothCoords, visitTriggers }],
            segIdx: 0,          // current segment index
            step: -startDelay,  // step within current segment
            done: false,
            // Capacity state
            capacity,
            loaded: 0,
            nextTrigger: 0,     // index into current segment's visitTriggers
            tripsToLandfill: 0,
            totalDumped: 0,
            phase: 'collecting', // 'collecting' | 'to_landfill' | 'from_landfill'
            pendingDetour: null, // future segments to insert
            // ── Fuel properties ──
            // ── Fuel properties ──
            fuelCapacity: FUEL_CAPACITY,
            currentFuel: FUEL_CAPACITY,
            fuelConsumption: FUEL_CONSUMPTION_KM,
            fuelThreshold: FUEL_CAPACITY * FUEL_THRESHOLD_PCT,
            isRefueling: false,
            refuelPhase: null,
            refuelCount: 0,
            fuelAlertFired: false,
            // ── Shift properties ──
            shiftStart: (() => { const d = new Date(); return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`; })(),
            shiftEnd: (() => { const d = new Date(); d.setHours(d.getHours() + 8); return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`; })(),
            pauseRequired: 45, // mins
            continuousDriving: 0, // mins
            onBreak: false,
            breakTimeLeft: 0, // ticks
            currentTime: (() => { const d = new Date(); return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`; })(),
            startedAlertSent: false,
            finishedAlertSent: false,
        };
    });

    // Store trucks globally for sidebar updates
    simTrucks = trucks;

    // Show simulation panel in sidebar (for backward compat if needed)
    const simPanel = document.getElementById('simCamionsPanel');
    if (simPanel) simPanel.style.display = 'block';

    updateAdvTruckCards();

    // ── Main animation loop ──────────────────────────────
    simInterval = setInterval(simLoopTick, simSpeed);
    showToast('▶ Simulation démarrée — camions en route', 'info');
}

function simLoopTick() {
    if (isSimPaused || !simTrucks) return;

    simStepCount++;
    if (document.getElementById('advSimStep')) {
        document.getElementById('advSimStep').textContent = simStepCount;
    }

    let doneCount = 0;
    let totalCollectedNow = 0;

    const landfill = state.landfill || { lat: 30.38, lng: -9.55 };

    simTrucks.forEach(t => {
        if (t.done) {
            if (!t.finishedAlertSent) {
                t.finishedAlertSent = true;
                const d = new Date(); const tStr = String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
                addAdvAlert('success', `Fin de tournée — Camion ${t.idx + 1}`, `Le camion est retourné au dépôt à ${tStr}`);
            }
            doneCount++;
            return;
        }
        if (t.paused) return; // waiting for OSRM route fetch

        // Current segment
        let seg = t.segments[t.segIdx];
        if (!seg || !seg.coords || seg.coords.length === 0) {
            t.done = true; doneCount++; return;
        }

        // Advance step
        for (let tick = 0; tick < STEPS_PER_TICK; tick++) {
            t.step++;
            if (t.step < 0) continue; // tiny stagger wait

            if (t.step === 0 && t.segIdx === 0 && !t.startedAlertSent) {
                t.startedAlertSent = true;
                const d = new Date(); const tStr = String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
                addAdvAlert('info', `Départ — Camion ${t.idx + 1}`, `Le camion est sorti à ${tStr}`);
            }

            // ── Pre-emptive fuel detour injection ──
            if (!t.isRefueling && !t.done && t.segIdx < t.segments.length && t.step >= 0 && t.step < seg.coords.length - 1) {
                if (t.currentFuel <= t.fuelThreshold && !t.fuelAlertFired) {
                    const [curLat, curLng] = seg.coords[t.step];
                    const station = findNearestStation(curLat, curLng);
                    if (station) {
                        t.fuelAlertFired = true;
                        t.isRefueling = true;
                        t.refuelPhase = 'starting_detour'; // the very first interrupted segment
                        t.refuelStation = station;

                        // Pause truck while fetching detour
                        t.paused = true;

                        Promise.all([
                            buildDetourPath(curLat, curLng, station.lat, station.lng),
                            buildDetourPath(station.lat, station.lng, curLat, curLng)
                        ]).then(([toStationPath, fromStationPath]) => {
                            const remainingCoords = seg.coords.slice(t.step);
                            const remainingTriggers = seg.visitTriggers.slice(t.nextTrigger).map(vt => ({ ...vt, stepIdx: vt.stepIdx - t.step }));

                            seg.coords = seg.coords.slice(0, t.step + 1);
                            seg.visitTriggers = seg.visitTriggers.slice(0, t.nextTrigger);

                            t.segments.splice(t.segIdx + 1, 0,
                                { coords: toStationPath, visitTriggers: [] },
                                { coords: fromStationPath, visitTriggers: [] },
                                { coords: remainingCoords, visitTriggers: remainingTriggers }
                            );

                            addAdvAlert('warning', `Carburant insuffisant – Direction station`, `Camion ${t.idx + 1} via ${station.nom}`);
                            t.step = seg.coords.length; // Force end of segment
                            t.paused = false; // Resume truck
                        }).catch(e => {
                            console.error("Failed to build detour", e);
                            t.paused = false;
                        });

                        break; // Stop inner tick loop immediately while waiting
                    }
                }
            }

            if (t.step >= seg.coords.length) {
                // Segment finished — move to next segment

                if (t.isRefueling) {
                    if (t.refuelPhase === 'starting_detour') {
                        // The original route segment was interrupted.
                        // The NEXT segment simulation will be the drive to the station.
                        t.refuelPhase = 'to_station';
                    } else if (t.refuelPhase === 'to_station') {
                        // Truck has arrived at the station. Refill fuel now!
                        t.currentFuel = t.fuelCapacity;
                        t.refuelCount++;
                        t.refuelPhase = 'to_route';
                        addAdvAlert('success', `Plein effectué – Reprise de la tournée`, `Camion ${t.idx + 1} a refait le plein à ${t.refuelStation.nom}`);
                    } else if (t.refuelPhase === 'to_route') {
                        // Truck is back on the main route.
                        t.isRefueling = false;
                        t.refuelPhase = null;
                        t.fuelAlertFired = false;
                    }
                }

                t.segIdx++;
                t.step = 0;
                t.nextTrigger = 0;

                if (t.segIdx >= t.segments.length) {
                    t.done = true;
                    if (!t.finishedAlertSent) {
                        t.finishedAlertSent = true;
                        const d = new Date(); const tStr = String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
                        addAdvAlert('success', `Fin de tournée — Camion ${t.idx + 1}`, `Le camion est retourné au dépôt à ${tStr}`);
                    }
                    doneCount++;
                    t.marker.setPopupContent(
                        `<b>Camion ${t.idx + 1}</b><br>✅ Retour au dépôt (Terminé)<br>` +
                        `Vidanges: ${t.tripsToLandfill}`
                    );
                    break;
                }
                // Re-fetch new segment
                seg = t.segments[t.segIdx];
                continue;
            }

            // Move marker
            const [lat, lng] = seg.coords[t.step];
            t.marker.setLatLng([lat, lng]);
            t.trail.addLatLng([lat, lng]);

            // Fuel consumption deduction & Time advance
            if (t.step > 0) {
                const [pLat, pLng] = seg.coords[t.step - 1];
                const distM = haversineMeters(pLat, pLng, lat, lng);
                t.currentFuel -= (distM / 1000) * t.fuelConsumption;
                if (t.currentFuel < 0) t.currentFuel = 0;

                // Advance clock: 1 tick = ~10 seconds of sim time
                let [hh, mm] = t.currentTime.split(':').map(Number);
                const simSecondsPerTick = 10;
                let totalMin = hh * 60 + mm + (simSecondsPerTick / 60);

                t.currentTime = `${String(Math.floor(totalMin / 60) % 24).padStart(2, '0')}:${String(Math.floor(totalMin % 60)).padStart(2, '0')}`;
                t.continuousDriving += (simSecondsPerTick / 60);

                // Break logic
                if (t.continuousDriving > 240 && !t.onBreak) {
                    t.onBreak = true;
                    t.breakTimeLeft = t.pauseRequired * (60 / simSecondsPerTick); // convert minutes to ticks
                    t.continuousDriving = 0;
                    addAdvAlert('warning', `Pause obligatoire — Camion ${t.idx + 1}`, `Arrêt de ${t.pauseRequired} min appliqué à ${t.currentTime}`);
                }
            }

            // Apply Break Pause
            if (t.onBreak) {
                t.breakTimeLeft--;
                if (t.breakTimeLeft <= 0) {
                    t.onBreak = false;
                    addAdvAlert('info', `Fin de pause — Camion ${t.idx + 1}`, `Reprend le service à ${t.currentTime}`);
                } else {
                    t.step--; // Don't advance physical position
                    break;
                }
            }

            // Out of shift logic
            let [curH, curM] = t.currentTime.split(':').map(Number);
            let [endH, endM] = t.shiftEnd.split(':').map(Number);

            // Handle midnight rollover for duration checking
            let curTot = curH * 60 + curM;
            let endTot = endH * 60 + endM;
            let startTot = parseInt(t.shiftStart.split(':')[0]) * 60 + parseInt(t.shiftStart.split(':')[1]);

            // If end time is technically the next day (e.g start 20:00, end 04:00)
            if (endTot < startTot) endTot += 24 * 60;
            // If current time rolled over past midnight but we started before midnight
            if (curTot < startTot && endTot > 24 * 60) curTot += 24 * 60;

            if (curTot > endTot && !t.done && !t.returningHome) {
                t.returningHome = true;
                addAdvAlert('danger', `Fin de service — Camion ${t.idx + 1}`, `Horaires dépassés (${t.currentTime}). Retour dépôt immédiat.`);

                // Truncate entirely and route to depot
                t.paused = true;
                const [curLat, curLng] = seg.coords[t.step];
                buildDetourPath(curLat, curLng, depot.lat, depot.lng).then(toDepotPath => {
                    t.segments = [{ coords: toDepotPath, visitTriggers: [] }];
                    t.segIdx = 0;
                    t.step = 0;
                    t.nextTrigger = 0;
                    t.paused = false;
                }).catch(e => {
                    console.error("Failed to build depot detour", e);
                    t.paused = false;
                });
                break;
            }

            // Immobilize if totally out of fuel
            if (t.currentFuel <= 0 && !t.done) {
                t.phase = 'out_of_fuel';
                if (!t._outOfFuelAlerted) {
                    addAdvAlert('danger', `Camion ${t.idx + 1} immobilisé`, 'Panne sèche totale');
                    t._outOfFuelAlerted = true;
                }
                break;
            }

            // Check visit triggers (collection points & landfill stops)
            if (seg.visitTriggers && t.nextTrigger < seg.visitTriggers.length) {
                const trigger = seg.visitTriggers[t.nextTrigger];
                if (t.step >= trigger.stepIdx) {
                    t.nextTrigger++;

                    if (trigger.isLandfill) {
                        // Truck arrives at landfill — dump load
                        simLandfillVisits++;
                        simLandfillTotal += t.loaded; // Add the exact amount loaded
                        t.totalDumped += t.loaded;
                        t.loaded = 0;
                        t.tripsToLandfill++;

                        if (document.getElementById('advLandfillVisits')) {
                            document.getElementById('advLandfillVisits').textContent = simLandfillVisits;
                            document.getElementById('advLandfillTotal').textContent = Math.round(simLandfillTotal);
                        }
                        addAdvAlert('success', `Camion ${t.idx + 1} à la décharge`, `Vidange #${t.tripsToLandfill} effectuée`);

                        t.marker.setPopupContent(
                            `<b>Camion ${t.idx + 1}</b><br>` +
                            `🏗️ Vidange #${t.tripsToLandfill} à la décharge`
                        );
                    } else {
                        // Truck arrives at collection point
                        t.loaded += trigger.volume;
                        const pct = Math.min(100, Math.round((t.loaded / t.capacity) * 100));
                        const barColor = pct >= 90 ? '#DC2626' : pct >= 60 ? '#EA580C' : '#16A34A';

                        // Add service time to clock
                        let [hh, mm] = t.currentTime.split(':').map(Number);
                        const serviceTimeMin = 5;
                        let totalMin = hh * 60 + mm + serviceTimeMin;
                        t.currentTime = `${String(Math.floor(totalMin / 60) % 24).padStart(2, '0')}:${String(Math.floor(totalMin % 60)).padStart(2, '0')}`;
                        t.continuousDriving += serviceTimeMin;

                        t.marker.setPopupContent(
                            `<b>Camion ${t.idx + 1}</b><br>` +
                            `🕒 ${t.currentTime} (Fin: ${t.shiftEnd})<br>` +
                            `📦 ${pct}% chargé (${Math.round(t.loaded)}/${t.capacity} kg)<br>` +
                            `<div style="background:#eee;border-radius:4px;height:6px;margin-top:4px">` +
                            `<div style="background:${barColor};height:100%;width:${pct}%;border-radius:4px"></div></div>`
                        );
                    }
                }
            }
        }

        totalCollectedNow += t.totalDumped + t.loaded;
    });

    if (document.getElementById('advSimCollected')) {
        document.getElementById('advSimCollected').textContent = Math.round(totalCollectedNow);
    }

    if (document.getElementById('advSimDone')) {
        document.getElementById('advSimDone').textContent = doneCount;
    }

    if (doneCount === simTrucks.length && simTrucks.length > 0) {
        stopSimulation();
        addAdvAlert('success', 'Mission terminée', 'Tous les camions sont rentrés');
        showToast('✅ Simulation terminée', 'success');
    }

    updateAdvTruckCards();
}

function stopSimulation() {
    if (simInterval) { clearInterval(simInterval); simInterval = null; }
    updateAdvTruckCards();
}

// ── Live sidebar status during simulation ────────────────
let _simSidebarTick = 0;
function updateAdvTruckCards() {
    const el = document.getElementById('advTruckStatuses');
    if (!el || !simTrucks || simTrucks.length === 0) return;

    // Throttle: update every 8 ticks (~400ms)
    _simSidebarTick++;
    if (_simSidebarTick % 8 !== 0 && simInterval) return;

    el.innerHTML = simTrucks.map(t => {
        const pct = Math.min(100, Math.round((t.loaded / t.capacity) * 100));
        const barColor = pct >= 90 ? '#DC2626' : pct >= 60 ? '#EA580C' : '#16A34A';

        const color = t.color;

        const fuelPct = Math.max(0, (t.currentFuel / t.fuelCapacity) * 100);
        const fuelColor = fuelPct > 50 ? '#16A34A' : fuelPct > 20 ? '#EA580C' : '#DC2626';

        let phaseLabel = '';
        let phaseIcon = '';
        if (t.done) {
            phaseLabel = 'Terminé (Dépôt)';
            phaseIcon = '✅';
        } else if (t.currentFuel <= 0) {
            phaseLabel = 'Panne sèche';
            phaseIcon = '⛽';
        } else if (t.onBreak) {
            phaseLabel = 'En Pause (4h)';
            phaseIcon = '☕';
        } else if (t.returningHome) {
            phaseLabel = 'Fin de Service';
            phaseIcon = '⏳';
        } else if (t.isRefueling) {
            phaseLabel = t.refuelPhase === 'to_station' ? 'Vers station' : 'Retour route';
            phaseIcon = '⛽';
        } else if (t.paused) {
            phaseLabel = 'Calcul route...';
            phaseIcon = '⏳';
        } else if (t.segIdx > 0 && t.segments[t.segIdx] && t.segments[t.segIdx].visitTriggers.length === 0) {
            // On a detour segment (no visit triggers = going to/from landfill)
            phaseLabel = 'Décharge';
            phaseIcon = '🏗️';
        } else {
            phaseLabel = 'Collecte';
            phaseIcon = '🚛';
        }

        const vidangeInfo = t.tripsToLandfill > 0
            ? `<span style="font-size:9px;color:var(--accent-orange)"> · ${t.tripsToLandfill} vidange${t.tripsToLandfill > 1 ? 's' : ''}</span>`
            : '';

        return `
            <div class="item-card" style="padding:6px 8px;margin-bottom:4px">
                <div class="dot" style="background:${color};flex-shrink:0"></div>
                <div class="info" style="flex:1;min-width:0">
                    <div class="name" style="font-size:11px;display:flex;align-items:center;gap:4px">
                        ${phaseIcon} Camion ${t.idx + 1}
                        <span style="font-size:9px;color:var(--text-muted);margin-left:auto">${phaseLabel} · 🕒 ${t.currentTime}</span>
                    </div>
                    <div style="display:flex;align-items:center;gap:6px;margin-top:3px">
                        <div style="flex:1;background:#eee;border-radius:3px;height:5px;overflow:hidden">
                            <div style="background:${barColor};height:100%;width:${pct}%;border-radius:3px;transition:width .3s"></div>
                        </div>
                        <span style="font-size:10px;font-weight:600;color:${barColor};min-width:28px">${pct}%</span>
                    </div>
                    <!-- FUEL BAR -->
                    <div style="display:flex;align-items:center;gap:6px;margin-top:2px">
                        <div style="font-size:10px;min-width:14px">⛽</div>
                        <div style="flex:1;background:#eee;border-radius:3px;height:4px;overflow:hidden">
                            <div style="background:${fuelColor};height:100%;width:${fuelPct}%;border-radius:3px;transition:width .3s"></div>
                        </div>
                        <span style="font-size:9px;color:var(--text-muted);min-width:28px">${t.currentFuel.toFixed(0)}L</span>
                    </div>
                    <div class="detail" style="font-size:9px;margin-top:1px">
                        ${Math.round(t.loaded)}/${t.capacity} kg${vidangeInfo}
                    </div>
                </div>
            </div>`;
    }).join('');
}

// ── Pulse animation for full points ──
const style = document.createElement('style');
style.textContent = `
@keyframes pulse {
    0%,100% { transform: scale(1); box-shadow: 0 2px 8px rgba(220,38,38,.4); }
    50% { transform: scale(1.15); box-shadow: 0 4px 16px rgba(220,38,38,.6); }
}`;
document.head.appendChild(style);
