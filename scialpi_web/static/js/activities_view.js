// Vista attivita con mappa/lista
/* global L */
document.addEventListener('DOMContentLoaded', () => {
  const map = L.map('activities-map').setView([46.0, 11.0], 6);
  const osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: 'OpenStreetMap contributors'
  });
  const topo = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
    attribution: 'OpenTopoMap (CC-BY-SA) OpenStreetMap contributors'
  });
  function tile2lat(y, z) {
    const n = Math.PI - (2 * Math.PI * y) / Math.pow(2, z);
    return (180 / Math.PI) * Math.atan(Math.sinh(n));
  }

  function createSlopeLayer() {
    const SlopeLayer = L.GridLayer.extend({
      createTile(coords, done) {
        const size = this.getTileSize();
        const tile = document.createElement('canvas');
        tile.width = size.x;
        tile.height = size.y;
        const ctx = tile.getContext('2d');
        const img = new Image();
        img.crossOrigin = 'anonymous';
        img.onload = () => {
          ctx.drawImage(img, 0, 0);
          const data = ctx.getImageData(0, 0, size.x, size.y).data;
          const output = ctx.createImageData(size.x, size.y);
          const step = 2;
          const lat = tile2lat(coords.y + 0.5, coords.z);
          const metersPerPixel = (156543.03392 * Math.cos((lat * Math.PI) / 180)) / Math.pow(2, coords.z);
          const width = size.x;
          const height = size.y;

          function elevationAt(x, y) {
            const idx = (y * width + x) * 4;
            const r = data[idx];
            const g = data[idx + 1];
            const b = data[idx + 2];
            return r * 256 + g + b / 256 - 32768;
          }

          for (let y = 1; y < height - 1; y += step) {
            for (let x = 1; x < width - 1; x += step) {
              const riseX = elevationAt(x + 1, y) - elevationAt(x - 1, y);
              const riseY = elevationAt(x, y + 1) - elevationAt(x, y - 1);
              const dzdx = riseX / (2 * metersPerPixel);
              const dzdy = riseY / (2 * metersPerPixel);
              const slope = Math.atan(Math.sqrt(dzdx * dzdx + dzdy * dzdy)) * (180 / Math.PI);
              if (slope >= 30) {
                let r = 220;
                let g = 60;
                let b = 60;
                let a = 170;
                if (slope >= 50) {
                  r = 245;
                  g = 200;
                  b = 70;
                  a = 210;
                } else if (slope >= 40) {
                  r = 148;
                  g = 90;
                  b = 220;
                  a = 185;
                }
                for (let oy = 0; oy < step; oy += 1) {
                  for (let ox = 0; ox < step; ox += 1) {
                    const px = x + ox;
                    const py = y + oy;
                    if (px >= width || py >= height) continue;
                    const outIdx = (py * width + px) * 4;
                    output.data[outIdx] = r;
                    output.data[outIdx + 1] = g;
                    output.data[outIdx + 2] = b;
                    output.data[outIdx + 3] = a;
                  }
                }
              }
            }
          }
          ctx.putImageData(output, 0, 0);
          done(null, tile);
        };
        img.onerror = () => {
          done(null, tile);
        };
        img.src = `https://s3.amazonaws.com/elevation-tiles-prod/terrarium/${coords.z}/${coords.x}/${coords.y}.png`;
        return tile;
      }
    });
    return new SlopeLayer({ opacity: 0.35 });
  }

  const slopeLayer = createSlopeLayer();
  topo.addTo(map);
  slopeLayer.addTo(map);
  L.control.layers(
    { Strade: osm, 'Curve di livello': topo },
    { 'Pendii >30': slopeLayer }
  ).addTo(map);

  const viewMapBtn = document.getElementById('activity-view-map');
  const viewListBtn = document.getElementById('activity-view-list');
  const listEl = document.getElementById('activities-list');

  const detailRouteEl = document.getElementById('activity-route-name');
  const detailDateEl = document.getElementById('activity-date');
  const detailGainEl = document.getElementById('activity-gain');
  const detailDistanceEl = document.getElementById('activity-distance');
  const detailSnowEl = document.getElementById('activity-snow');
  const detailWeatherEl = document.getElementById('activity-weather');
  const detailPerformanceEl = document.getElementById('activity-performance');
  const detailLinkEl = document.getElementById('activity-detail-link');

  const filterForm = document.getElementById('activity-filters-form');
  const filterVisibilityEl = document.getElementById('activity-filter-visibility');
  const filterDateEl = document.getElementById('activity-filter-date');
  const filterGroupListEl = document.getElementById('activity-filter-groups');
  const filterDistanceMinEl = document.getElementById('activity-filter-distance-min');
  const filterDistanceMaxEl = document.getElementById('activity-filter-distance-max');
  const filterGainMinEl = document.getElementById('activity-filter-gain-min');
  const filterGainMaxEl = document.getElementById('activity-filter-gain-max');
  const filterDifficultyEl = document.getElementById('activity-filter-difficulty');
  const filterClearBtn = document.getElementById('activity-filter-clear');

  const searchForm = document.getElementById('activity-search-form');
  const queryEl = document.getElementById('activity-place-query');
  const resultsEl = document.getElementById('activity-search-results');

  let markersLayer = L.layerGroup().addTo(map);
  let filterGroupIds = [];
  let dateFilterActive = false;

  function setView(mode) {
    const isMap = mode === 'map';
    if (listEl) listEl.classList.toggle('d-none', isMap);
    if (map && map.getContainer()) {
      map.getContainer().classList.toggle('d-none', !isMap);
    }
    if (viewMapBtn && viewListBtn) {
      viewMapBtn.classList.toggle('btn-primary', isMap);
      viewMapBtn.classList.toggle('btn-outline-primary', !isMap);
      viewListBtn.classList.toggle('btn-primary', !isMap);
      viewListBtn.classList.toggle('btn-outline-primary', isMap);
    }
    if (isMap) {
      setTimeout(() => map.invalidateSize(), 50);
    }
  }

  function formatLocalDate(value) {
    const year = value.getFullYear();
    const month = String(value.getMonth() + 1).padStart(2, '0');
    const day = String(value.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  function defaultFilterDate() {
    const now = new Date();
    const base = new Date(now);
    if (now.getHours() < 16) {
      base.setDate(base.getDate() - 1);
    }
    return formatLocalDate(base);
  }

  function parseDayDate(value) {
    if (!value) return null;
    if (value.includes('-')) {
      const parsed = new Date(value);
      return Number.isNaN(parsed.getTime()) ? null : parsed;
    }
    if (value.length === 8) {
      const day = parseInt(value.slice(0, 2), 10);
      const month = parseInt(value.slice(2, 4), 10) - 1;
      const year = parseInt(value.slice(4, 8), 10);
      const parsed = new Date(year, month, day);
      return Number.isNaN(parsed.getTime()) ? null : parsed;
    }
    return null;
  }

  function filterRecent(items, daysWindow) {
    const cutoff = new Date();
    cutoff.setHours(0, 0, 0, 0);
    cutoff.setDate(cutoff.getDate() - (daysWindow - 1));
    return items.filter((item) => {
      const dateObj = parseDayDate(item.date);
      if (!dateObj) return false;
      dateObj.setHours(0, 0, 0, 0);
      return dateObj >= cutoff;
    });
  }

  function photoUrl(item) {
    if (item.photo_url) return item.photo_url;
    if (!item.photo_filename) return null;
    return `/days/photos/${encodeURIComponent(item.photo_filename)}`;
  }

  function updateDetails(item) {
    if (!item) return;
    if (detailRouteEl) detailRouteEl.textContent = item.route_name || '-';
    if (detailDateEl) detailDateEl.textContent = item.date || '-';
    if (detailGainEl) detailGainEl.textContent = item.route_gain ? `${item.route_gain} m` : '-';
    if (detailDistanceEl) detailDistanceEl.textContent = item.route_distance_km ? `${item.route_distance_km} km` : '-';
    if (detailSnowEl) detailSnowEl.textContent = item.snow_quality || '-';
    if (detailWeatherEl) detailWeatherEl.textContent = item.weather || '-';
    const perfBits = [];
    if (item.activity_pace_min_km) perfBits.push(`Passo ${item.activity_pace_min_km} min/km`);
    if (item.activity_vam) perfBits.push(`VAM ${item.activity_vam} m/h`);
    if (item.activity_up_hours) perfBits.push(`H up ${item.activity_up_hours}h`);
    if (item.activity_down_hours) perfBits.push(`H down ${item.activity_down_hours}h`);
    detailPerformanceEl.textContent = perfBits.length ? perfBits.join(' · ') : '-';
    if (detailLinkEl) detailLinkEl.href = `/activities/${item.id}`;
  }

  function renderList(items) {
    if (!listEl) return;
    listEl.innerHTML = '';
    if (!items.length) {
      listEl.innerHTML = '<div class="text-muted">Nessuna attivita con questi filtri.</div>';
      return;
    }
    const grid = document.createElement('div');
    grid.className = 'd-grid gap-3';
    items.forEach((item) => {
      const card = document.createElement('div');
      card.className = 'feed-card';
      const img = document.createElement('img');
      const src = photoUrl(item);
      const fallback = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="600" height="450"><rect width="100%25" height="100%25" fill="%23eef4ff"/></svg>';
      img.src = src || fallback;
      img.onerror = () => {
        img.src = fallback;
      };
      img.className = 'feed-photo';
      img.alt = 'Foto giornata';
      const body = document.createElement('div');
      body.className = 'feed-body';
      const title = document.createElement('div');
      title.className = 'feed-title';
      title.textContent = item.route_name || 'Percorso';
      const meta = document.createElement('div');
      meta.className = 'feed-meta';
      const owner = item.owner_name ? ` · ${item.owner_name}` : '';
      meta.textContent = `${item.date || '-'}${owner}`;
      const conditions = document.createElement('div');
      conditions.className = 'feed-meta';
      const snow = item.snow_quality || 'Neve n/d';
      const weather = item.weather || 'Meteo n/d';
      conditions.textContent = `${snow} · ${weather}`;
      const link = document.createElement('a');
      link.href = `/activities/${item.id}`;
      link.className = 'btn btn-outline-primary btn-sm mt-2';
      link.textContent = 'Apri dettaglio';
      body.appendChild(title);
      body.appendChild(meta);
      body.appendChild(conditions);
      body.appendChild(link);
      card.appendChild(img);
      card.appendChild(body);
      card.addEventListener('click', (event) => {
        if (event.target === link) return;
        updateDetails(item);
      });
      grid.appendChild(card);
    });
    listEl.appendChild(grid);
  }

  function renderMarkers(items) {
    markersLayer.clearLayers();
    items.forEach((item) => {
      if (typeof item.lat !== 'number' || typeof item.lon !== 'number') return;
      const url = photoUrl(item);
      const icon = url
        ? L.divIcon({ className: 'photo-marker', html: `<div class="photo-marker" style="background-image:url('${url}')"></div>`, iconSize: [34, 34], iconAnchor: [17, 17] })
        : L.divIcon({ className: 'photo-marker', html: '<div class="photo-marker"></div>', iconSize: [34, 34], iconAnchor: [17, 17] });
      const marker = L.marker([item.lat, item.lon], { icon });
      marker.bindPopup(`${item.route_name || 'Percorso'}<br>${item.date || ''}`);
      marker.on('click', () => {
        updateDetails(item);
      });
      marker.addTo(markersLayer);
    });
  }

  function updateSelectedFilterGroups() {
    if (!filterGroupListEl) return;
    const selected = [];
    filterGroupListEl.querySelectorAll('input[type="checkbox"]').forEach((checkbox) => {
      if (checkbox.checked) selected.push(checkbox.value);
    });
    filterGroupIds = selected;
  }

  function setGroupFilterEnabled(enabled) {
    if (!filterGroupListEl) return;
    filterGroupListEl.querySelectorAll('input[type="checkbox"]').forEach((checkbox) => {
      checkbox.disabled = !enabled;
    });
  }

  function renderFilterGroups(groups) {
    if (!filterGroupListEl) return;
    filterGroupListEl.innerHTML = '';
    if (!groups.length) {
      filterGroupListEl.innerHTML = '<div class="list-group-item">Nessun gruppo.</div>';
      return;
    }
    groups.forEach((group) => {
      const item = document.createElement('label');
      item.className = 'list-group-item d-flex align-items-center gap-2';
      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.className = 'form-check-input';
      checkbox.value = group.id;
      checkbox.addEventListener('change', updateSelectedFilterGroups);
      const text = document.createElement('span');
      text.textContent = group.name || 'Gruppo';
      item.appendChild(checkbox);
      item.appendChild(text);
      filterGroupListEl.appendChild(item);
    });
    updateSelectedFilterGroups();
    setGroupFilterEnabled(filterVisibilityEl && filterVisibilityEl.value === 'groups');
  }

  function loadGroups() {
    fetch('/api/groups')
      .then((res) => res.json())
      .then((groups) => {
        if (Array.isArray(groups)) {
          renderFilterGroups(groups);
        }
      })
      .catch(() => {
        if (filterGroupListEl) {
          filterGroupListEl.innerHTML = '<div class="list-group-item">Errore nel caricamento.</div>';
        }
      });
  }

  function buildQuery() {
    const params = new URLSearchParams();
    const visibility = filterVisibilityEl ? filterVisibilityEl.value : 'all';
    if (visibility && visibility !== 'all') {
      params.set('visibility', visibility);
    }
    if (dateFilterActive && filterDateEl && filterDateEl.value) {
      params.set('date', filterDateEl.value);
    }
    if (visibility === 'groups') {
      updateSelectedFilterGroups();
      if (filterGroupIds.length) {
        params.set('group_ids', filterGroupIds.join(','));
      }
    }
    if (filterDistanceMinEl && filterDistanceMinEl.value) {
      params.set('min_distance', filterDistanceMinEl.value);
    }
    if (filterDistanceMaxEl && filterDistanceMaxEl.value) {
      params.set('max_distance', filterDistanceMaxEl.value);
    }
    if (filterGainMinEl && filterGainMinEl.value) {
      params.set('min_gain', filterGainMinEl.value);
    }
    if (filterGainMaxEl && filterGainMaxEl.value) {
      params.set('max_gain', filterGainMaxEl.value);
    }
    if (filterDifficultyEl && filterDifficultyEl.value.trim()) {
      params.set('difficulty', filterDifficultyEl.value.trim());
    }
    const query = params.toString();
    return query ? `?${query}` : '';
  }

  function loadActivities() {
    fetch(`/api/days${buildQuery()}`)
      .then((res) => res.json())
      .then((items) => {
        if (!Array.isArray(items)) return;
        const markerItems = filterRecent(items, 2);
        renderMarkers(markerItems);
        renderList(items);
        if (items.length) {
          updateDetails(items[0]);
        }
      });
  }

  function clearResults() {
    if (resultsEl) resultsEl.innerHTML = '';
  }

  function addResultItem(item) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'list-group-item list-group-item-action';
    button.textContent = item.display_name;
    button.addEventListener('click', () => {
      const lat = parseFloat(item.lat);
      const lon = parseFloat(item.lon);
      map.setView([lat, lon], 12);
      clearResults();
    });
    resultsEl.appendChild(button);
  }

  let searchTimer = null;
  let searchController = null;

  function runSearch(query) {
    if (!resultsEl) return;
    if (searchController) searchController.abort();
    searchController = new AbortController();
    resultsEl.innerHTML = '<div class="list-group-item">Ricerca in corso...</div>';
    fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=6`, {
      headers: { 'Accept-Language': 'it' },
      signal: searchController.signal
    })
      .then((res) => res.json())
      .then((data) => {
        clearResults();
        if (!data.length) {
          resultsEl.innerHTML = '<div class="list-group-item">Nessun risultato.</div>';
          return;
        }
        data.forEach(addResultItem);
      })
      .catch(() => {
        if (searchController && searchController.signal.aborted) return;
        resultsEl.innerHTML = '<div class="list-group-item">Errore durante la ricerca.</div>';
      });
  }

  if (viewMapBtn) viewMapBtn.addEventListener('click', () => setView('map'));
  if (viewListBtn) viewListBtn.addEventListener('click', () => setView('list'));
  if (filterVisibilityEl) {
    filterVisibilityEl.addEventListener('change', () => {
      setGroupFilterEnabled(filterVisibilityEl.value === 'groups');
    });
  }
  if (filterDateEl) {
    filterDateEl.addEventListener('change', () => {
      dateFilterActive = true;
      loadActivities();
    });
  }
  if (filterForm) {
    filterForm.addEventListener('submit', (e) => {
      e.preventDefault();
      dateFilterActive = true;
      loadActivities();
    });
  }
  if (filterClearBtn) {
    filterClearBtn.addEventListener('click', () => {
      if (filterVisibilityEl) filterVisibilityEl.value = 'all';
      if (filterDateEl) filterDateEl.value = defaultFilterDate();
      dateFilterActive = false;
      if (filterDistanceMinEl) filterDistanceMinEl.value = '';
      if (filterDistanceMaxEl) filterDistanceMaxEl.value = '';
      if (filterGainMinEl) filterGainMinEl.value = '';
      if (filterGainMaxEl) filterGainMaxEl.value = '';
      if (filterDifficultyEl) filterDifficultyEl.value = '';
      filterGroupIds = [];
      renderFilterGroups([]);
      loadGroups();
      loadActivities();
    });
  }
  if (searchForm) {
    searchForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const query = queryEl.value.trim();
      if (query.length < 3) {
        resultsEl.innerHTML = '<div class="list-group-item">Scrivi almeno 3 caratteri.</div>';
        return;
      }
      runSearch(query);
    });
  }
  if (queryEl) {
    queryEl.addEventListener('input', () => {
      const query = queryEl.value.trim();
      clearTimeout(searchTimer);
      if (query.length < 3) {
        clearResults();
        return;
      }
      searchTimer = setTimeout(() => runSearch(query), 300);
    });
  }

  setView('list');
  if (filterDateEl && !filterDateEl.value) {
    filterDateEl.value = defaultFilterDate();
  }
  loadGroups();
  loadActivities();
});
