// Mappa per le gite con percorsi e giornate
/* global L */
document.addEventListener('DOMContentLoaded', () => {
  const map = L.map('trips-map').setView([46.0, 11.0], 6);
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

  const resultsEl = document.getElementById('search-results');
  const searchForm = document.getElementById('trip-search-form');
  const queryEl = document.getElementById('place-query');

  const routeForm = document.getElementById('route-form');
  const routeIdEl = document.getElementById('route-id');
  const routeNameEl = document.getElementById('route-name');
  const routeDescEl = document.getElementById('route-description');
  const routeDifficultyEl = document.getElementById('route-difficulty');
  const routeStatusEl = document.getElementById('route-status');
  const viewMapBtn = document.getElementById('view-map');
  const viewListBtn = document.getElementById('view-list');
  const viewLatestBtn = document.getElementById('view-latest');
  const routesListEl = document.getElementById('routes-list');
  const latestDaysListEl = document.getElementById('latest-days-list');

  const dayForm = document.getElementById('day-form');
  const dayIdEl = document.getElementById('day-id');
  const dayRouteIdEl = document.getElementById('day-route-id');
  const dayDateEl = document.getElementById('day-date');
  const snowQualityEl = document.getElementById('snow-quality');
  const dayDescriptionEl = document.getElementById('day-description');
  const dayWeatherEl = document.getElementById('day-weather');
  const dayAvalanchesEl = document.getElementById('day-avalanches');
  const dayStatusEl = document.getElementById('day-status');
  const dayVisibilityEl = document.getElementById('day-visibility');
  const dayGroupsEl = document.getElementById('day-groups');
  const dayPeopleEl = document.getElementById('day-people');
  const groupListEl = document.getElementById('group-list');
  const filterForm = document.getElementById('route-filters');
  const filterVisibilityEl = document.getElementById('filter-visibility');
  const filterGroupListEl = document.getElementById('filter-group-list');
  const filterDistanceMinEl = document.getElementById('filter-distance-min');
  const filterDistanceMaxEl = document.getElementById('filter-distance-max');
  const filterGainMinEl = document.getElementById('filter-gain-min');
  const filterGainMaxEl = document.getElementById('filter-gain-max');
  const filterDifficultyEl = document.getElementById('filter-difficulty');
  const filterClearBtn = document.getElementById('filter-clear');

  const photoToggle = document.getElementById('photo-toggle');
  const photoClear = document.getElementById('photo-clear');
  const photoFileEl = document.getElementById('photo-file');
  const photoLatEl = document.getElementById('photo-lat');
  const photoLonEl = document.getElementById('photo-lon');
  const photoUpload = document.getElementById('photo-upload');
  const photoStatus = document.getElementById('photo-status');
  const photoGallery = document.getElementById('photo-gallery');

  const detailName = document.getElementById('detail-route-name');
  const detailDesc = document.getElementById('detail-route-desc');
  const detailDifficulty = document.getElementById('detail-route-difficulty');
  const detailGain = document.getElementById('detail-route-gain');
  const detailDistance = document.getElementById('detail-route-distance');
  const detailEstimate = document.getElementById('detail-route-estimate');
  const detailSlope = document.getElementById('detail-route-slope');
  const detailProfile = document.getElementById('detail-route-profile');
  const dayList = document.getElementById('day-list');
  const detailDayDate = document.getElementById('detail-day-date');
  const detailDaySnow = document.getElementById('detail-day-snow');
  const detailDayWeather = document.getElementById('detail-day-weather');
  const detailDayAvalanches = document.getElementById('detail-day-avalanches');
  const detailDayNotes = document.getElementById('detail-day-notes');
  const detailDayLink = document.getElementById('detail-day-link');
  const dayCollapseEl = document.getElementById('day-collapse');
  const dayToggleBtn = document.getElementById('day-toggle');

  const gpxInput = document.getElementById('gpx');
  const trackToggle = document.getElementById('track-toggle');
  const trackClear = document.getElementById('track-clear');
  const trackInput = document.getElementById('track-points');

  let routesLayer = L.layerGroup().addTo(map);
  let trackLayer = L.layerGroup().addTo(map);
  let editLayer = L.layerGroup().addTo(map);
  let photoLayer = L.layerGroup().addTo(map);
  let trackPoints = [];
  let traceMode = false;
  let photoMode = false;
  let photoDraftMarker = null;
  let currentRouteId = null;
  let filterGroupIds = [];
  let showLatestDays = false;
  const dayCollapse = dayCollapseEl && window.bootstrap
    ? new window.bootstrap.Collapse(dayCollapseEl, { toggle: false })
    : null;

  const tripIcon = L.divIcon({
    className: 'trip-triangle',
    iconSize: [16, 16],
    iconAnchor: [8, 12]
  });

  function updateDetail(el, value) {
    if (!el) return;
    el.textContent = value || '-';
  }

  function clearResults() {
    resultsEl.innerHTML = '';
  }

  function estimateHours(distanceKm, gainM) {
    if (!distanceKm && !gainM) return null;
    const distancePart = (distanceKm || 0) / 3;
    const gainPart = (gainM || 0) / 400;
    return distancePart + gainPart;
  }

  function formatEstimate(hours) {
    if (!hours && hours !== 0) return '-';
    const totalMinutes = Math.round(hours * 60);
    const h = Math.floor(totalMinutes / 60);
    const m = totalMinutes % 60;
    if (!h) return `${m}m`;
    if (!m) return `${h}h`;
    return `${h}h ${m}m`;
  }

  function haversineMeters(lat1, lon1, lat2, lon2) {
    const radius = 6371000;
    const lat1Rad = (lat1 * Math.PI) / 180;
    const lon1Rad = (lon1 * Math.PI) / 180;
    const lat2Rad = (lat2 * Math.PI) / 180;
    const lon2Rad = (lon2 * Math.PI) / 180;
    const dlat = lat2Rad - lat1Rad;
    const dlon = lon2Rad - lon1Rad;
    const a = Math.sin(dlat / 2) ** 2 +
      Math.cos(lat1Rad) * Math.cos(lat2Rad) * Math.sin(dlon / 2) ** 2;
    const c = 2 * Math.asin(Math.sqrt(a));
    return radius * c;
  }

  function computeTrackStats(points) {
    if (!Array.isArray(points) || points.length < 2) {
      return { distanceMeters: null, gainMeters: null, slopeDeg: null, elevations: [] };
    }
    let distanceMeters = 0;
    let gainMeters = 0;
    const elevations = [];
    let prev = points[0];
    for (let i = 1; i < points.length; i += 1) {
      const point = points[i];
      if (typeof prev[0] === 'number' && typeof prev[1] === 'number' &&
          typeof point[0] === 'number' && typeof point[1] === 'number') {
        distanceMeters += haversineMeters(prev[0], prev[1], point[0], point[1]);
      }
      if (prev.length > 2 && point.length > 2) {
        const delta = point[2] - prev[2];
        if (Number.isFinite(delta) && delta > 0) gainMeters += delta;
        if (Number.isFinite(point[2])) elevations.push(point[2]);
      }
      prev = point;
    }
    const slopeDeg = distanceMeters ? Math.atan2(gainMeters, distanceMeters) * (180 / Math.PI) : null;
    return { distanceMeters, gainMeters, slopeDeg, elevations };
  }

  function drawProfile(points) {
    if (!detailProfile) return;
    const ctx = detailProfile.getContext('2d');
    if (!ctx) return;
    const width = detailProfile.clientWidth || 300;
    const height = detailProfile.clientHeight || 90;
    detailProfile.width = width;
    detailProfile.height = height;
    ctx.clearRect(0, 0, width, height);
    if (!Array.isArray(points) || points.length < 2) {
      return;
    }
    const elevations = points
      .map((p) => (p.length > 2 ? p[2] : null))
      .filter((v) => Number.isFinite(v));
    if (elevations.length < 2) return;
    const min = Math.min(...elevations);
    const max = Math.max(...elevations);
    const range = max - min || 1;
    ctx.fillStyle = '#f0f4ff';
    ctx.fillRect(0, 0, width, height);
    ctx.strokeStyle = '#1f6feb';
    ctx.lineWidth = 2;
    ctx.beginPath();
    elevations.forEach((ele, idx) => {
      const x = (idx / (elevations.length - 1)) * (width - 4) + 2;
      const y = height - ((ele - min) / range) * (height - 10) - 5;
      if (idx === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
  }

  function renderDetails(route, days) {
    updateDetail(detailName, route.name);
    updateDetail(detailDesc, route.description);
    updateDetail(detailDifficulty, route.difficulty);
    updateDetail(detailGain, route.gain ? `${route.gain} m` : null);
    updateDetail(detailDistance, route.distance_km ? `${route.distance_km} km` : null);
    const estimate = estimateHours(route.distance_km, route.gain);
    updateDetail(detailEstimate, formatEstimate(estimate));
    if (route.track && Array.isArray(route.track)) {
      const stats = computeTrackStats(route.track);
      updateDetail(detailSlope, stats.slopeDeg ? `${stats.slopeDeg.toFixed(1)} deg` : '-');
      drawProfile(route.track);
    } else {
      updateDetail(detailSlope, '-');
      drawProfile([]);
    }
    renderDayList(days || []);
  }

  function updateDayDetails(day) {
    if (!day) {
      updateDetail(detailDayDate, '-');
      updateDetail(detailDaySnow, '-');
      updateDetail(detailDayWeather, '-');
      updateDetail(detailDayAvalanches, '-');
      updateDetail(detailDayNotes, '-');
      if (detailDayLink) detailDayLink.classList.add('d-none');
      return;
    }
    updateDetail(detailDayDate, day.date);
    updateDetail(detailDaySnow, day.snow_quality);
    updateDetail(detailDayWeather, day.weather);
    updateDetail(detailDayAvalanches, day.avalanches_seen);
    updateDetail(detailDayNotes, day.description);
    if (detailDayLink) {
      detailDayLink.href = `/trips/${day.id}`;
      detailDayLink.classList.remove('d-none');
    }
  }

  function renderDayList(days) {
    dayList.innerHTML = '';
    if (!days.length) {
      dayList.innerHTML = '<div class="list-group-item">Nessuna giornata.</div>';
      return;
    }
    days.forEach((day) => {
      const item = document.createElement('button');
      item.type = 'button';
      item.className = 'list-group-item list-group-item-action';
      item.textContent = `${day.date} ${day.snow_quality ? '- ' + day.snow_quality : ''}`;
      item.addEventListener('click', () => {
        fillDayForm(day);
        updateDayDetails(day);
      });
      dayList.appendChild(item);
    });
  }

  function updateSelectedGroups() {
    if (!groupListEl || !dayGroupsEl) return;
    const selected = [];
    groupListEl.querySelectorAll('input[type="checkbox"]').forEach((checkbox) => {
      if (checkbox.checked) {
        selected.push(checkbox.value);
      }
    });
    dayGroupsEl.value = selected.join(',');
  }

  function renderGroups(groups) {
    if (!groupListEl) return;
    groupListEl.innerHTML = '';
    if (!groups.length) {
      groupListEl.innerHTML = '<div class="list-group-item">Nessun gruppo.</div>';
      return;
    }
    groups.forEach((group) => {
      const item = document.createElement('label');
      item.className = 'list-group-item d-flex align-items-center gap-2';
      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.className = 'form-check-input';
      checkbox.value = group.id;
      checkbox.addEventListener('change', updateSelectedGroups);
      const text = document.createElement('span');
      text.textContent = group.name || 'Gruppo';
      item.appendChild(checkbox);
      item.appendChild(text);
      groupListEl.appendChild(item);
    });
    updateSelectedGroups();
  }

  function updateSelectedFilterGroups() {
    if (!filterGroupListEl) return;
    const selected = [];
    filterGroupListEl.querySelectorAll('input[type="checkbox"]').forEach((checkbox) => {
      if (checkbox.checked) {
        selected.push(checkbox.value);
      }
    });
    filterGroupIds = selected;
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
      checkbox.addEventListener('change', () => {
        updateSelectedFilterGroups();
      });
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
    if (!groupListEl) return;
    fetch('/api/groups')
      .then((res) => res.json())
      .then((groups) => {
        if (!Array.isArray(groups)) {
          renderGroups([]);
          return;
        }
        renderGroups(groups);
        renderFilterGroups(groups);
      })
      .catch(() => {
        groupListEl.innerHTML = '<div class="list-group-item">Errore nel caricamento.</div>';
        if (filterGroupListEl) {
          filterGroupListEl.innerHTML = '<div class="list-group-item">Errore nel caricamento.</div>';
        }
      });
  }

  function setView(mode) {
    if (!routesListEl || !latestDaysListEl) return;
    const isMap = mode === 'map';
    const showList = !isMap;
    routesListEl.classList.toggle('d-none', !showList || showLatestDays);
    latestDaysListEl.classList.toggle('d-none', !showList || !showLatestDays);
    if (map && map.getContainer()) {
      map.getContainer().classList.toggle('d-none', !isMap);
    }
    if (viewMapBtn && viewListBtn) {
      viewMapBtn.classList.toggle('btn-primary', isMap);
      viewMapBtn.classList.toggle('btn-outline-primary', !isMap);
      viewListBtn.classList.toggle('btn-primary', !isMap);
      viewListBtn.classList.toggle('btn-outline-primary', isMap);
    }
    if (viewLatestBtn) {
      viewLatestBtn.classList.toggle('btn-primary', showLatestDays);
      viewLatestBtn.classList.toggle('btn-outline-primary', !showLatestDays);
    }
    if (isMap) {
      setTimeout(() => map.invalidateSize(), 50);
    }
  }

  function renderRouteList(routes) {
    if (!routesListEl) return;
    routesListEl.innerHTML = '';
    if (!routes.length) {
      routesListEl.innerHTML = '<div class="text-muted">Nessuna gita con questi filtri.</div>';
      return;
    }
    const list = document.createElement('div');
    list.className = 'list-group';
    routes.forEach((route) => {
      const item = document.createElement('button');
      item.type = 'button';
      item.className = 'list-group-item list-group-item-action';
      const title = route.name || 'Percorso';
      const distance = route.distance_km ? `${route.distance_km} km` : '-';
      const gain = route.gain ? `${route.gain} m` : '-';
      const diff = route.difficulty || '-';
      item.innerHTML = `<div class="fw-semibold">${title}</div>
        <div class="text-muted small">Distanza ${distance} · Dislivello ${gain} · Difficolta ${diff}</div>`;
      item.addEventListener('click', () => {
        selectRoute(route.id);
      });
      list.appendChild(item);
    });
    routesListEl.appendChild(list);
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

  function renderLatestDays(days) {
    if (!latestDaysListEl) return;
    latestDaysListEl.innerHTML = '';
    if (!days.length) {
      latestDaysListEl.innerHTML = '<div class="text-muted">Nessuna giornata recente.</div>';
      return;
    }
    let currentDate = null;
    let list = null;
    days.forEach((day) => {
      const dateKey = day.date || 'Senza data';
      if (dateKey !== currentDate) {
        currentDate = dateKey;
        const header = document.createElement('div');
        header.className = 'text-muted small mt-2 mb-1';
        header.textContent = dateKey;
        latestDaysListEl.appendChild(header);
        list = document.createElement('div');
        list.className = 'list-group';
        latestDaysListEl.appendChild(list);
      }
      const item = document.createElement('button');
      item.type = 'button';
      item.className = 'list-group-item list-group-item-action';
      const title = day.route_name || 'Percorso';
      const distance = day.route_distance_km ? `${day.route_distance_km} km` : '-';
      const gain = day.route_gain ? `${day.route_gain} m` : '-';
      item.innerHTML = `<div class="fw-semibold">${title}</div>
        <div class="text-muted small">Distanza ${distance} · Dislivello ${gain}</div>`;
      item.addEventListener('click', () => {
        if (day.route_id) {
          selectRoute(day.route_id, day.id);
          setView('map');
        } else if (day.id) {
          window.location.href = `/trips/${day.id}`;
        }
      });
      if (list) list.appendChild(item);
    });
  }

  function setGroupSelection(groupIds) {
    if (!groupListEl) return;
    const target = new Set(groupIds || []);
    groupListEl.querySelectorAll('input[type="checkbox"]').forEach((checkbox) => {
      checkbox.checked = target.has(checkbox.value);
    });
    updateSelectedGroups();
  }

  function setFilterGroupSelection(groupIds) {
    if (!filterGroupListEl) return;
    const target = new Set(groupIds || []);
    filterGroupListEl.querySelectorAll('input[type="checkbox"]').forEach((checkbox) => {
      checkbox.checked = target.has(checkbox.value);
    });
    updateSelectedFilterGroups();
  }

  function setGroupFilterEnabled(enabled) {
    if (!filterGroupListEl) return;
    filterGroupListEl.querySelectorAll('input[type="checkbox"]').forEach((checkbox) => {
      checkbox.disabled = !enabled;
    });
  }

  function setPhotoMode(enabled) {
    photoMode = enabled;
    if (enabled) {
      setTraceMode(false);
    }
    if (photoToggle) {
      photoToggle.textContent = enabled ? 'Termina posizione' : 'Posiziona foto';
      photoToggle.classList.toggle('btn-outline-primary', !enabled);
      photoToggle.classList.toggle('btn-primary', enabled);
    }
  }

  function clearPhotoDraft() {
    if (photoLatEl) photoLatEl.value = '';
    if (photoLonEl) photoLonEl.value = '';
    if (photoDraftMarker) {
      photoLayer.removeLayer(photoDraftMarker);
      photoDraftMarker = null;
    }
  }

  function setPhotoLocation(lat, lon) {
    if (photoLatEl) photoLatEl.value = lat.toFixed(6);
    if (photoLonEl) photoLonEl.value = lon.toFixed(6);
    if (photoDraftMarker) {
      photoLayer.removeLayer(photoDraftMarker);
    }
    photoDraftMarker = L.circleMarker([lat, lon], {
      radius: 6,
      color: '#1f6feb',
      fillColor: '#1f6feb',
      fillOpacity: 0.6
    }).addTo(photoLayer);
  }

  function renderPhotos(photos) {
    if (photoLayer) {
      photoLayer.clearLayers();
      photoDraftMarker = null;
    }
    if (photoGallery) photoGallery.innerHTML = '';
    if (!Array.isArray(photos) || !photos.length) {
      if (photoGallery) {
        photoGallery.innerHTML = '<div class="text-muted">Nessuna foto.</div>';
      }
      return;
    }
    photos.forEach((photo) => {
      const url = `/days/photos/${encodeURIComponent(photo.filename)}`;
      if (typeof photo.lat === 'number' && typeof photo.lon === 'number') {
        const marker = L.circleMarker([photo.lat, photo.lon], {
          radius: 5,
          color: '#2f7fdc',
          fillColor: '#2f7fdc',
          fillOpacity: 0.7
        });
        marker.bindPopup(`<img src="${url}" alt="Foto" style="max-width:200px;border-radius:6px;" />`);
        marker.addTo(photoLayer);
      }
      if (photoGallery) {
        const card = document.createElement('div');
        card.className = 'photo-thumb';
        const img = document.createElement('img');
        img.src = url;
        img.alt = 'Foto giornata';
        card.appendChild(img);
        photoGallery.appendChild(card);
      }
    });
  }

  function fillRouteForm(route) {
    routeIdEl.value = route.id || '';
    routeNameEl.value = route.name || '';
    routeDescEl.value = route.description || '';
    routeDifficultyEl.value = route.difficulty || '';
    dayRouteIdEl.value = route.id || '';
  }

  function fillDayForm(day) {
    if (dayCollapse) dayCollapse.show();
    dayIdEl.value = day.id || '';
    dayRouteIdEl.value = day.route_id || '';
    dayDateEl.value = day.date || '';
    snowQualityEl.value = day.snow_quality || '';
    dayDescriptionEl.value = day.description || '';
    dayWeatherEl.value = day.weather || '';
    dayAvalanchesEl.value = day.avalanches_seen || '';
    if (dayVisibilityEl) dayVisibilityEl.value = day.visibility || 'public';
    if (dayPeopleEl) dayPeopleEl.value = day.people_emails || '';
    setGroupSelection(day.group_ids || []);
  }

  function clearDayForm() {
    dayIdEl.value = '';
    dayDateEl.value = '';
    snowQualityEl.value = '';
    dayDescriptionEl.value = '';
    dayWeatherEl.value = '';
    dayAvalanchesEl.value = '';
    if (dayVisibilityEl) dayVisibilityEl.value = 'public';
    if (dayPeopleEl) dayPeopleEl.value = '';
    setGroupSelection([]);
    updateDayDetails(null);
  }

  function hideDayPanel() {
    if (dayCollapse) {
      dayCollapse.hide();
      return;
    }
    if (dayCollapseEl) dayCollapseEl.classList.remove('show');
  }

  function toLatLngs(points) {
    return points
      .map((p) => [p[0], p[1]])
      .filter((p) => typeof p[0] === 'number' && typeof p[1] === 'number');
  }

  function clearTrackDisplay() {
    trackLayer.clearLayers();
  }

  function drawRouteTrack(points) {
    clearTrackDisplay();
    if (!points || points.length < 2) return;
    const latLngs = toLatLngs(points);
    if (!latLngs.length) return;
    L.polyline(latLngs, { color: '#7fb2f0', weight: 4 }).addTo(trackLayer);
    map.fitBounds(L.latLngBounds(latLngs), { padding: [40, 40] });
  }

  function drawTrack(points) {
    drawRouteTrack(points);
    if (!points || !points.length) return;
    const latLngs = toLatLngs(points);
    const last = latLngs[latLngs.length - 1];
    if (last) {
      L.marker(last).addTo(trackLayer).bindPopup('Arrivo');
    }
  }

  function renderEditTrack() {
    editLayer.clearLayers();
    if (!trackPoints.length) return;
    const latLngs = toLatLngs(trackPoints);
    if (!latLngs.length) return;
    L.polyline(latLngs, { color: '#ff7a00', weight: 3, dashArray: '6 6' }).addTo(editLayer);
    const last = latLngs[latLngs.length - 1];
    if (last) L.circleMarker(last, { radius: 5, color: '#ff7a00' }).addTo(editLayer);
    if (trackInput) trackInput.value = JSON.stringify(trackPoints);
  }

  function setTraceMode(enabled) {
    traceMode = enabled;
    if (enabled) {
      setPhotoMode(false);
    }
    if (trackToggle) {
      trackToggle.textContent = enabled ? 'Termina traccia' : 'Inizia traccia';
      trackToggle.classList.toggle('btn-outline-primary', !enabled);
      trackToggle.classList.toggle('btn-primary', enabled);
    }
  }

  function clearTrackEdit() {
    trackPoints = [];
    if (trackInput) trackInput.value = '';
    editLayer.clearLayers();
    if (gpxInput) gpxInput.value = '';
  }

  function parseGpx(text) {
    const parser = new DOMParser();
    const xml = parser.parseFromString(text, 'application/xml');
    const points = [];
    const nodes = xml.querySelectorAll('trkpt, rtept');
    nodes.forEach((node) => {
      const lat = parseFloat(node.getAttribute('lat'));
      const lon = parseFloat(node.getAttribute('lon'));
      const eleNode = node.querySelector('ele');
      if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
      if (eleNode && eleNode.textContent) {
        const ele = parseFloat(eleNode.textContent);
        if (Number.isFinite(ele)) {
          points.push([lat, lon, ele]);
          return;
        }
      }
      points.push([lat, lon]);
    });
    return points;
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

  function buildRouteQuery() {
    if (!filterVisibilityEl) return '';
    const params = new URLSearchParams();
    const visibility = filterVisibilityEl.value || 'all';
    if (visibility !== 'all') {
      params.set('visibility', visibility);
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

  function loadRoutes(selectId) {
    const query = buildRouteQuery();
    fetch(`/api/routes${query}`)
      .then((res) => res.json())
      .then((routes) => {
        routesLayer.clearLayers();
        renderRouteList(routes);
        routes.forEach((route) => {
          if (typeof route.lat !== 'number' || typeof route.lon !== 'number') return;
          const marker = L.marker([route.lat, route.lon], { icon: tripIcon });
          marker.bindPopup(route.name || 'Percorso');
          marker.on('click', () => {
            selectRoute(route.id);
          });
          marker.addTo(routesLayer);
        });
        if (selectId) {
          selectRoute(selectId);
        }
      });
  }

  function loadLatestDays() {
    const query = buildRouteQuery();
    fetch(`/api/days${query}`)
      .then((res) => res.json())
      .then((days) => {
        if (!Array.isArray(days)) {
          renderLatestDays([]);
          return;
        }
        days.sort((a, b) => {
          const dateA = parseDayDate(a.date);
          const dateB = parseDayDate(b.date);
          if (!dateA || !dateB) return 0;
          return dateB - dateA;
        });
        renderLatestDays(days.slice(0, 50));
      })
      .catch(() => {
        renderLatestDays([]);
      });
  }

  function selectRoute(routeId, dayIdToSelect) {
    currentRouteId = routeId;
    fetch(`/api/routes/${routeId}`)
      .then((res) => res.json())
      .then((payload) => {
        const route = payload.route;
        const days = payload.days || [];
        if (!route) return;
        renderDetails(route, days);
        renderPhotos(payload.photos || []);
        fillRouteForm(route);
        clearDayForm();
        dayRouteIdEl.value = route.id || '';
        if (dayIdToSelect) {
          const match = days.find((day) => day.id === dayIdToSelect);
          if (match) {
            fillDayForm(match);
            updateDayDetails(match);
          }
        }
        clearTrackEdit();
        if (route.track && Array.isArray(route.track)) {
          drawTrack(route.track);
        } else {
          clearTrackDisplay();
        }
      });
  }

  map.on('click', (e) => {
    const lat = e.latlng.lat;
    const lon = e.latlng.lng;
    if (traceMode) {
      trackPoints.push([lat, lon]);
      renderEditTrack();
      return;
    }
    if (photoMode) {
      setPhotoLocation(lat, lon);
      return;
    }
  });

  if (trackToggle) {
    trackToggle.addEventListener('click', () => {
      setTraceMode(!traceMode);
    });
  }

  if (trackClear) {
    trackClear.addEventListener('click', () => {
      clearTrackEdit();
    });
  }

  if (gpxInput) {
    gpxInput.addEventListener('change', (e) => {
      const file = e.target.files && e.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        trackPoints = parseGpx(reader.result);
        renderEditTrack();
        if (trackPoints.length) {
          const last = trackPoints[trackPoints.length - 1];
          map.setView([last[0], last[1]], 12);
        }
        setTraceMode(false);
      };
      reader.readAsText(file);
    });
  }

  if (photoToggle) {
    photoToggle.addEventListener('click', () => {
      setPhotoMode(!photoMode);
    });
  }

  if (photoClear) {
    photoClear.addEventListener('click', () => {
      clearPhotoDraft();
      if (photoStatus) photoStatus.textContent = '';
    });
  }

  if (photoUpload) {
    photoUpload.addEventListener('click', () => {
      if (!dayIdEl.value) {
        if (photoStatus) photoStatus.textContent = 'Salva prima la giornata.';
        return;
      }
      const file = photoFileEl && photoFileEl.files ? photoFileEl.files[0] : null;
      if (!file) {
        if (photoStatus) photoStatus.textContent = 'Seleziona una foto.';
        return;
      }
      const formData = new FormData();
      formData.append('image', file);
      if (photoLatEl && photoLatEl.value) formData.append('lat', photoLatEl.value);
      if (photoLonEl && photoLonEl.value) formData.append('lon', photoLonEl.value);
      if (photoStatus) photoStatus.textContent = 'Caricamento...';
      fetch(`/api/days/${dayIdEl.value}/photos`, {
        method: 'POST',
        body: formData
      })
        .then((res) => res.json())
        .then(() => {
          if (photoStatus) photoStatus.textContent = 'Foto caricata.';
          if (photoFileEl) photoFileEl.value = '';
          clearPhotoDraft();
          if (dayRouteIdEl.value) {
            selectRoute(dayRouteIdEl.value, dayIdEl.value);
          } else if (currentRouteId) {
            selectRoute(currentRouteId, dayIdEl.value);
          }
        })
        .catch(() => {
          if (photoStatus) photoStatus.textContent = 'Errore nel caricamento.';
        });
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

  if (filterVisibilityEl) {
    filterVisibilityEl.addEventListener('change', () => {
      setGroupFilterEnabled(filterVisibilityEl.value === 'groups');
    });
  }

  if (filterForm) {
    filterForm.addEventListener('submit', (e) => {
      e.preventDefault();
      if (showLatestDays) {
        loadLatestDays();
      } else {
        loadRoutes();
      }
    });
  }

  if (filterClearBtn) {
    filterClearBtn.addEventListener('click', () => {
      if (filterVisibilityEl) filterVisibilityEl.value = 'all';
      if (filterDistanceMinEl) filterDistanceMinEl.value = '';
      if (filterDistanceMaxEl) filterDistanceMaxEl.value = '';
      if (filterGainMinEl) filterGainMinEl.value = '';
      if (filterGainMaxEl) filterGainMaxEl.value = '';
      if (filterDifficultyEl) filterDifficultyEl.value = '';
      setFilterGroupSelection([]);
      setGroupFilterEnabled(false);
      if (showLatestDays) {
        loadLatestDays();
      } else {
        loadRoutes();
      }
    });
  }

  if (viewMapBtn) {
    viewMapBtn.addEventListener('click', () => {
      showLatestDays = false;
      setView('map');
    });
  }
  if (viewListBtn) {
    viewListBtn.addEventListener('click', () => {
      showLatestDays = false;
      setView('list');
    });
  }
  if (viewLatestBtn) {
    viewLatestBtn.addEventListener('click', () => {
      showLatestDays = true;
      setView('list');
      loadLatestDays();
    });
  }

  if (routeForm) {
    routeForm.addEventListener('submit', (e) => {
      e.preventDefault();
      if (trackInput && !trackInput.value && trackPoints.length) {
        trackInput.value = JSON.stringify(trackPoints);
      }
      routeStatusEl.textContent = 'Salvataggio...';
      const formData = new FormData(routeForm);
      fetch('/api/routes', {
        method: 'POST',
        body: formData
      })
        .then((res) => res.json())
        .then((route) => {
          routeStatusEl.textContent = 'Percorso salvato.';
          if (route && route.id) {
            loadRoutes(route.id);
          } else {
            loadRoutes();
          }
        })
        .catch(() => {
          routeStatusEl.textContent = 'Errore nel salvataggio.';
        });
    });
  }

  if (dayForm) {
    dayForm.addEventListener('submit', (e) => {
      e.preventDefault();
      if (!dayRouteIdEl.value) {
        dayStatusEl.textContent = 'Seleziona un percorso.';
        return;
      }
      updateSelectedGroups();
      dayStatusEl.textContent = 'Salvataggio...';
      const formData = new FormData(dayForm);
      fetch('/api/days', {
        method: 'POST',
        body: formData
      })
        .then((res) => res.json())
        .then((day) => {
          dayStatusEl.textContent = 'Giornata salvata.';
          if (day && day.route_id) {
            selectRoute(day.route_id, day.id);
          }
          hideDayPanel();
        })
        .catch(() => {
          dayStatusEl.textContent = 'Errore nel salvataggio.';
        });
    });
  }

  if (dayToggleBtn) {
    dayToggleBtn.addEventListener('click', () => {
      clearDayForm();
      if (dayCollapse) dayCollapse.show();
    });
  }

  loadGroups();
  setView('map');
  loadRoutes();
});
