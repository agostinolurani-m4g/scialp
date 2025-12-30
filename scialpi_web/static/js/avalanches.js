// Javascript per la mappa delle valanghe
document.addEventListener('DOMContentLoaded', () => {
  const map = L.map('map').setView([46.0, 11.0], 6); // centro approssimativo sulle Alpi
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: 'Ac OpenStreetMap contributors'
  }).addTo(map);
  let markers = {};
  const form = document.getElementById('avalanche-form');
  const statusEl = document.getElementById('avalanche-status');
  const latEl = document.getElementById('lat');
  const lonEl = document.getElementById('lon');

  function markerColor(size) {
    switch (size) {
      case 'large':
        return '#000000';
      case 'medium':
        return '#cc0000';
      case 'small':
        return '#ff7a00';
      default:
        return '#0066cc';
    }
  }

  function buildPopup(item) {
    const parts = [`Segnalazione #${item.id}`];
    if (item.description) parts.push(`Descrizione: ${item.description}`);
    if (item.size) parts.push(`Dimensione: ${item.size}`);
    if (item.danger) parts.push(`Pericolo: ${item.danger}`);
    if (item.slope) parts.push(`Pendenza: ${item.slope} deg`);
    parts.push(`Conferme: ${item.confirmations}`);
    if (item.image) {
      const url = `/avalanches/images/${item.image}`;
      parts.push(`<a href="${url}" target="_blank" rel="noopener">Immagine</a>`);
    }
    return parts.join('<br>');
  }

  function loadAvalanches() {
    const params = new URLSearchParams();
    const startDateEl = document.getElementById('start-date');
    const endDateEl = document.getElementById('end-date');
    const startVal = startDateEl && startDateEl.value;
    const endVal = endDateEl && endDateEl.value;
    if (startVal) {
      // inizio giorno alle 00:00 UTC
      const startDate = new Date(startVal);
      params.append('start', startDate.toISOString());
    }
    if (endVal) {
      // fine giorno alle 23:59 UTC
      const endDate = new Date(endVal);
      endDate.setHours(23, 59, 59, 999);
      params.append('end', endDate.toISOString());
    }
    fetch(`/api/avalanches?${params.toString()}`)
      .then((res) => res.json())
      .then((data) => {
        // Rimuove markers esistenti
        Object.values(markers).forEach((m) => map.removeLayer(m));
        markers = {};
        data.forEach((item) => {
          const marker = L.circleMarker([item.lat, item.lon], {
            radius: 8,
            color: markerColor(item.size),
            fillColor: markerColor(item.size),
            fillOpacity: 0.9
          }).addTo(map);
          marker.bindPopup(buildPopup(item));
          marker.on('click', () => {
            fetch(`/api/avalanches/${item.id}/confirm`, {
              method: 'POST'
            })
              .then((res) => {
                if (!res.ok) {
                  return res.json().then((payload) => {
                    throw new Error(payload.error || 'Errore');
                  });
                }
                return res.json();
              })
              .then((updated) => {
                marker.getPopup().setContent(buildPopup(updated));
                marker.openPopup();
                if (statusEl) statusEl.textContent = '';
              })
              .catch((err) => {
                if (statusEl) statusEl.textContent = err.message;
              });
          });
          markers[item.id] = marker;
        });
      });
  }

  document.getElementById('apply-filter').addEventListener('click', (e) => {
    e.preventDefault();
    loadAvalanches();
  });

  map.on('click', (e) => {
    const lat = e.latlng.lat.toFixed(6);
    const lon = e.latlng.lng.toFixed(6);
    if (latEl) latEl.value = lat;
    if (lonEl) lonEl.value = lon;
  });

  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      if (!latEl.value || !lonEl.value) {
        if (statusEl) statusEl.textContent = 'Seleziona un punto sulla mappa.';
        return;
      }
      if (statusEl) statusEl.textContent = 'Salvataggio in corso...';
      const formData = new FormData(form);
      fetch('/api/avalanches', {
        method: 'POST',
        body: formData
      })
        .then((res) => res.json())
        .then(() => {
          if (statusEl) statusEl.textContent = 'Segnalazione salvata.';
          form.reset();
          loadAvalanches();
        })
        .catch(() => {
          if (statusEl) statusEl.textContent = 'Errore nel salvataggio.';
        });
    });
  }

  // Carica le segnalazioni all'avvio
  loadAvalanches();
});
