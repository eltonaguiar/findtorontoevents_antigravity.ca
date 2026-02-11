// MOVIESHOWS TikTok-Style App JS
// -- Insert your TMDB API key below --
const TMDB_API_KEY = 'YOUR_TMDB_API_KEY_HERE';
const TMDB_BASE_URL = 'https://api.themoviedb.org/3';
const TMDB_IMAGE_BASE = 'https://image.tmdb.org/t/p/w500';

const cardContainer = document.getElementById('cardContainer');
const filtersDiv = document.getElementById('filters');
const saveBtn = document.getElementById('savePlaylist');
const shareBtn = document.getElementById('sharePlaylist');
const importBtn = document.getElementById('importBtn');
const importInput = document.getElementById('importPlaylist');
const toast = document.getElementById('toast');

let allContent = [];
let filteredContent = [];
let playlist = [];
let genresList = [];
let selectedGenres = [];

// --- Fetch genres from TMDB ---
async function fetchGenres() {
  const res = await fetch(`${TMDB_BASE_URL}/genre/movie/list?api_key=${TMDB_API_KEY}&language=en-US`);
  const data = await res.json();
  genresList = data.genres.map(g => g.name);
}

// --- Fetch movies/TV (2025+) from TMDB ---
async function fetchContent() {
  let movies = await fetchPaged(`${TMDB_BASE_URL}/discover/movie?api_key=${TMDB_API_KEY}&language=en-US&sort_by=release_date.desc&primary_release_date.gte=2025-01-01&page=1`);
  let tv = await fetchPaged(`${TMDB_BASE_URL}/discover/tv?api_key=${TMDB_API_KEY}&language=en-US&sort_by=first_air_date.desc&first_air_date.gte=2025-01-01&page=1`);
  allContent = [...movies, ...tv].slice(0, 60); // Limit for performance
}

async function fetchPaged(url) {
  let results = [];
  let page = 1;
  while (results.length < 50 && page <= 3) {
    let res = await fetch(url.replace(/page=\d+/, `page=${page}`));
    let data = await res.json();
    if (!data.results) break;
    results = results.concat(data.results);
    if (data.page >= data.total_pages) break;
    page++;
  }
  return results;
}

// --- Render genre filters ---
function renderFilters() {
  filtersDiv.innerHTML = '';
  genresList.forEach(genre => {
    const btn = document.createElement('button');
    btn.textContent = genre;
    btn.className = 'genre-filter' + (selectedGenres.includes(genre) ? ' active' : '');
    btn.onclick = () => {
      if (selectedGenres.includes(genre)) {
        selectedGenres = selectedGenres.filter(g => g !== genre);
      } else {
        selectedGenres.push(genre);
      }
      updateURL();
      renderCards();
    };
    filtersDiv.appendChild(btn);
  });
}

// --- Render cards ---
function renderCards() {
  filteredContent = allContent.filter(item =>
    selectedGenres.length === 0 || (item.genre_ids && item.genre_ids.some(id => genresList.includes(getGenreName(id))))
  );
  cardContainer.innerHTML = '';
  filteredContent.forEach(item => {
    const card = createCard(item);
    cardContainer.appendChild(card);
  });
}

function getGenreName(id) {
  // TMDB genre id to name mapping
  const genre = window.tmdbGenres && window.tmdbGenres.find(g => g.id === id);
  return genre ? genre.name : '';
}

function createCard(item) {
  const card = document.createElement('section');
  card.className = 'card';
  // Poster
  const img = document.createElement('img');
  img.className = 'poster';
  img.src = item.poster_path ? `${TMDB_IMAGE_BASE}${item.poster_path}` : 'https://via.placeholder.com/320x480?text=No+Image';
  img.alt = `${item.title || item.name} poster`;
  card.appendChild(img);
  // Info
  const info = document.createElement('div');
  info.className = 'info';
  // Title
  const title = document.createElement('div');
  title.className = 'title';
  title.textContent = item.title || item.name;
  info.appendChild(title);
  // Meta
  const meta = document.createElement('div');
  meta.className = 'meta';
  meta.textContent = `${item.release_date || item.first_air_date || ''}`;
  info.appendChild(meta);
  // Genres
  const genres = document.createElement('div');
  genres.className = 'genres';
  (item.genre_ids || []).forEach(id => {
    const g = document.createElement('span');
    g.className = 'genre';
    g.textContent = getGenreName(id);
    genres.appendChild(g);
  });
  info.appendChild(genres);
  card.appendChild(info);
  // Trailers (fetch on demand)
  const trailersDiv = document.createElement('div');
  trailersDiv.className = 'trailers';
  trailersDiv.textContent = 'Loading trailers...';
  fetchTrailers(item).then(trailers => {
    trailersDiv.innerHTML = '';
    if (trailers.length === 0) {
      trailersDiv.textContent = 'No trailers available.';
    } else {
      trailers.forEach(trailer => {
        const iframe = document.createElement('iframe');
        iframe.src = trailer.url;
        iframe.allow = 'autoplay; encrypted-media';
        iframe.width = '320';
        iframe.height = '180';
        iframe.frameBorder = '0';
        trailersDiv.appendChild(iframe);
      });
    }
  });
  card.appendChild(trailersDiv);
  // Synopses
  const synopsesDiv = document.createElement('div');
  synopsesDiv.className = 'synopses';
  const mainSynopsis = document.createElement('div');
  mainSynopsis.textContent = item.overview || 'No synopsis available.';
  synopsesDiv.appendChild(mainSynopsis);
  card.appendChild(synopsesDiv);
  // Playlist button
  const btn = document.createElement('button');
  btn.className = 'playlist-btn' + (playlist.includes(item.id) ? ' active' : '');
  btn.textContent = playlist.includes(item.id) ? 'Remove from Playlist' : 'Add to Playlist';
  btn.onclick = () => {
    if (playlist.includes(item.id)) {
      playlist = playlist.filter(id => id !== item.id);
      btn.classList.remove('active');
      btn.textContent = 'Add to Playlist';
      showToast('Removed from playlist');
    } else {
      playlist.push(item.id);
      btn.classList.add('active');
      btn.textContent = 'Remove from Playlist';
      showToast('Added to playlist');
    }
    updateURL();
    savePlaylistLocal();
  };
  card.appendChild(btn);
  return card;
}

// --- Fetch trailers from TMDB (YouTube embeds) ---
async function fetchTrailers(item) {
  let type = item.title ? 'movie' : 'tv';
  let res = await fetch(`${TMDB_BASE_URL}/${type}/${item.id}/videos?api_key=${TMDB_API_KEY}&language=en-US`);
  let data = await res.json();
  if (!data.results) return [];
  return data.results.filter(v => v.site === 'YouTube').slice(0, 3).map(v => ({
    source: 'youtube',
    url: `https://www.youtube.com/embed/${v.key}`
  }));
}

// --- Playlist Save/Share/Import ---
function savePlaylistLocal() {
  localStorage.setItem('playlist', JSON.stringify(playlist));
}

function loadPlaylistLocal() {
  let pl = localStorage.getItem('playlist');
  if (pl) playlist = JSON.parse(pl);
}

saveBtn.onclick = exportPlaylistTxt;
shareBtn.onclick = () => {
  updateURL();
  navigator.clipboard.writeText(window.location.href);
  showToast('Shareable URL copied!');
};
importBtn.onclick = () => importInput.click();
importInput.onchange = importPlaylistTxt;

function exportPlaylistTxt() {
  let lines = ['# MOVIESHOWS PLAYLIST', `Created: ${new Date().toISOString()}`];
  let selected = allContent.filter(item => playlist.includes(item.id));
  selected.forEach((item, i) => {
    lines.push(`\n${i+1}. ${item.title || item.name} (${item.release_date || item.first_air_date || ''})`);
    lines.push(`   Genre: ${(item.genre_ids || []).map(getGenreName).join(', ')}`);
    lines.push(`   Poster: ${item.poster_path ? TMDB_IMAGE_BASE + item.poster_path : ''}`);
    lines.push(`   Trailers:`);
    lines.push(`     - https://www.themoviedb.org/${item.title ? 'movie' : 'tv'}/${item.id}/videos`);
    lines.push(`   Synopses:`);
    lines.push(`     - ${item.overview || 'No synopsis.'}`);
  });
  let blob = new Blob([lines.join('\n')], {type: 'text/plain'});
  let a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'movieshows_playlist.txt';
  a.click();
}

function importPlaylistTxt(e) {
  let file = e.target.files[0];
  if (!file) return;
  let reader = new FileReader();
  reader.onload = function(evt) {
    let text = evt.target.result;
    let ids = [];
    let lines = text.split(/\r?\n/);
    lines.forEach(line => {
      let m = line.match(/\((\d{4}-\d{2}-\d{2})\)/);
      if (m) {
        let title = line.replace(/\(.*\)/, '').replace(/^\d+\.\s*/, '').trim();
        let found = allContent.find(item => (item.title || item.name) === title);
        if (found) ids.push(found.id);
      }
    });
    playlist = ids;
    savePlaylistLocal();
    renderCards();
    showToast('Playlist imported!');
  };
  reader.readAsText(file);
}

function updateURL() {
  let params = new URLSearchParams();
  if (playlist.length) params.set('playlist', playlist.join(','));
  if (selectedGenres.length) params.set('genres', selectedGenres.join(','));
  history.replaceState({}, '', `${location.pathname}?${params}`);
}

function showToast(msg) {
  toast.textContent = msg;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 2000);
}

// --- Init ---
(async function init() {
  await fetchGenres();
  window.tmdbGenres = await fetch(`${TMDB_BASE_URL}/genre/movie/list?api_key=${TMDB_API_KEY}&language=en-US`).then(r=>r.json()).then(d=>d.genres);
  await fetchContent();
  loadPlaylistLocal();
  renderFilters();
  renderCards();
  // Parse URL params
  let params = new URLSearchParams(window.location.search);
  if (params.get('playlist')) playlist = params.get('playlist').split(',');
  if (params.get('genres')) selectedGenres = params.get('genres').split(',');
  renderFilters();
  renderCards();
})();
