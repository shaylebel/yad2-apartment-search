const state = {
    sortBy: 'date_scraped',
    sortOrder: 'DESC',
    page: 1,
    perPage: 50,
    polling: null,
    cities: {},
    view: 'grid',
    currentResults: [],
    listingDetailsCache: {},
};

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

async function loadCities() {
    try {
        const resp = await fetch('/api/filters/cities');
        state.cities = await resp.json();

        const datalist = $('#city-list');
        datalist.innerHTML = Object.entries(state.cities)
            .sort((a, b) => a[0].localeCompare(b[0], 'he'))
            .map(([name, code]) => `<option value="${name}" data-code="${code}">`)
            .join('');
    } catch (err) {
        console.error('Failed to load cities:', err);
    }
}

function getCityCode() {
    const input = $('#city-input').value.trim();
    if (!input) return '';
    const code = state.cities[input];
    return code !== undefined ? String(code) : '';
}

function getCityName() {
    return $('#city-input').value.trim();
}

function getSearchFilters() {
    const filters = {};

    const cityCode = getCityCode();
    if (cityCode) filters.city = cityCode;

    const roomsMin = $('#rooms_min').value;
    const roomsMax = $('#rooms_max').value;
    if (roomsMin) filters.rooms_min = parseFloat(roomsMin);
    if (roomsMax) filters.rooms_max = parseFloat(roomsMax);

    const priceMin = $('#price_min').value;
    const priceMax = $('#price_max').value;
    if (priceMin) filters.price_min = parseInt(priceMin);
    if (priceMax) filters.price_max = parseInt(priceMax);

    return filters;
}

function getDbFilters() {
    const filters = {};

    const cityName = getCityName();
    if (cityName) filters.city = cityName;

    const roomsMin = $('#rooms_min').value;
    const roomsMax = $('#rooms_max').value;
    if (roomsMin) filters.rooms_min = parseFloat(roomsMin);
    if (roomsMax) filters.rooms_max = parseFloat(roomsMax);

    const priceMin = $('#price_min').value;
    const priceMax = $('#price_max').value;
    if (priceMin) filters.price_min = parseInt(priceMin);
    if (priceMax) filters.price_max = parseInt(priceMax);

    const sizeMin = $('#size_min')?.value;
    const sizeMax = $('#size_max')?.value;
    if (sizeMin) filters.size_min = parseInt(sizeMin);
    if (sizeMax) filters.size_max = parseInt(sizeMax);

    const booleans = [
        'has_elevator', 'has_parking', 'has_balcony',
        'has_ac', 'is_furnished', 'pets_allowed', 'has_mamad'
    ];
    for (const id of booleans) {
        const el = $(`#${id}`);
        if (el && el.checked) filters[id] = true;
    }

    return filters;
}

function setStatus(msg, type = 'info') {
    const bar = $('#status-bar');
    const text = $('#status-text');
    bar.classList.remove('hidden', 'error', 'success');
    if (type === 'error') bar.classList.add('error');
    if (type === 'success') bar.classList.add('success');
    text.textContent = msg;
}

function hideStatus() {
    $('#status-bar').classList.add('hidden');
}

async function startSearch() {
    const cityCode = getCityCode();
    const cityName = getCityName();
    if (cityName && !cityCode) {
        setStatus(`City "${cityName}" not found. Pick from the suggestions.`, 'error');
        return;
    }

    const btn = $('#btn-search');
    btn.disabled = true;
    state.page = 1;
    setStatus('Starting search...');

    try {
        const filters = getSearchFilters();
        const resp = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(filters),
        });

        if (resp.status === 409) {
            setStatus('A search is already running.', 'error');
            btn.disabled = false;
            return;
        }

        pollStatus();
    } catch (err) {
        setStatus(`Failed to start search: ${err.message}`, 'error');
        btn.disabled = false;
    }
}

function pollStatus() {
    if (state.polling) clearInterval(state.polling);

    state.polling = setInterval(async () => {
        try {
            const resp = await fetch('/api/status');
            const data = await resp.json();

            if (data.running) {
                setStatus(data.progress || 'Working...');
                loadResults();
            } else {
                clearInterval(state.polling);
                state.polling = null;
                $('#btn-search').disabled = false;

                if (data.error) {
                    setStatus(`Error: ${data.error}`, 'error');
                } else {
                    setStatus(data.progress || 'Done!', 'success');
                    loadResults({});
                }
            }
        } catch {
            clearInterval(state.polling);
            state.polling = null;
            $('#btn-search').disabled = false;
        }
    }, 2000);
}

async function loadResults(overrideFilters) {
    const filters = overrideFilters !== undefined ? overrideFilters : getDbFilters();
    const params = new URLSearchParams({
        ...Object.fromEntries(
            Object.entries(filters).map(([k, v]) => [k, String(v)])
        ),
        sort_by: state.sortBy,
        sort_order: state.sortOrder,
        page: state.page,
        per_page: state.perPage,
    });

    try {
        const resp = await fetch(`/api/results?${params}`);
        const data = await resp.json();
        renderResults(data.results, data.total, data.page);
    } catch (err) {
        console.error('Failed to load results:', err);
    }
}

function getPropertyType(r) {
    const addr = (r.address_full || '').toLowerCase();
    if (addr.includes('פנטהאוז') || addr.includes('penthouse')) return 'penthouse';
    if (addr.includes('סאבלט') || addr.includes('sublet')) return 'sublet';
    return 'apartment';
}

function getBadgeClass(type) {
    if (type === 'penthouse') return 'badge-penthouse';
    if (type === 'sublet') return 'badge-sublet';
    return 'badge-apartment';
}

function getBadgeLabel(type) {
    if (type === 'penthouse') return 'Penthouse';
    if (type === 'sublet') return 'Sublet';
    return 'Apartment';
}

function buildFeatureTags(r) {
    const tags = [];
    if (r.has_elevator) tags.push('Elevator');
    if (r.has_parking) tags.push('Parking');
    if (r.has_balcony) tags.push('Balcony');
    if (r.has_ac) tags.push('A/C');
    if (r.is_furnished) tags.push('Furnished');
    if (r.pets_allowed) tags.push('Pets');
    if (r.has_mamad) tags.push('Mamad');
    return tags;
}

function renderResults(results, total, page) {
    state.currentResults = results;
    $('#results-count').textContent = total > 0 ? `${total} listings found` : 'No results yet';

    if (state.view === 'grid') {
        renderGridView(results, total, page);
    } else {
        renderListView(results, total, page);
    }
    renderPagination(total, page);
}

function renderGridView(results, total, page) {
    const grid = $('#results-grid');

    if (!results.length) {
        grid.innerHTML = `
            <div class="no-results-card">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><path d="m21 21-4.3-4.3"></path></svg>
                <p>No listings found. Try adjusting your filters or running a new search.</p>
            </div>`;
        return;
    }

    grid.innerHTML = results.map(r => {
        const type = getPropertyType(r);
        const tags = buildFeatureTags(r);
        const floorText = r.floor != null ? `Floor ${r.floor}${r.total_floors ? '/' + r.total_floors : ''}` : '–';

        return `
        <div class="listing-card" onclick="openModal(${results.indexOf(r)})">
            <div class="card-image">
                ${r.thumbnail_url
                    ? `<img src="${r.thumbnail_url}" alt="Apartment" loading="lazy">`
                    : `<div class="card-image-placeholder">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect width="18" height="18" x="3" y="3" rx="2" ry="2"></rect><circle cx="9" cy="9" r="2"></circle><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"></path></svg>
                       </div>`
                }
            </div>
            <div class="card-body">
                <div class="card-price-row">
                    <span class="card-price">${r.price ? '₪ ' + r.price.toLocaleString() : '–'}</span>
                    <span class="card-badge ${getBadgeClass(type)}">${getBadgeLabel(type)}</span>
                </div>
                <div class="card-address">${r.address_full || '–'}</div>
                <div class="card-stats">
                    <span class="stat">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 4v16"></path><path d="M2 8h18a2 2 0 0 1 2 2v10"></path><path d="M2 17h20"></path><path d="M6 8v9"></path></svg>
                        ${r.rooms || '–'} rooms
                    </span>
                    <span class="stat">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 3 21 3 21 9"></polyline><polyline points="9 21 3 21 3 15"></polyline><line x1="21" x2="14" y1="3" y2="10"></line><line x1="3" x2="10" y1="21" y2="14"></line></svg>
                        ${r.size_sqm || '–'} m²
                    </span>
                    <span class="stat">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 2 4 4-1.5 1.5L12 5l-2.5 2.5L8 6z"></path><path d="M5 8 1 12l4 4 1.5-1.5L4 12l2.5-2.5z"></path><path d="m19 8 4 4-4 4-1.5-1.5L20 12l-2.5-2.5z"></path><path d="m12 22-4-4 1.5-1.5L12 19l2.5-2.5L16 18z"></path></svg>
                        ${floorText}
                    </span>
                </div>
                <div class="card-divider"></div>
                <div class="card-footer">
                    <div class="card-tags">
                        ${tags.slice(0, 3).map(t => `<span class="card-tag">${t}</span>`).join('')}
                    </div>
                    <button class="card-fav" onclick="event.stopPropagation()" title="Save listing">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"></path></svg>
                    </button>
                </div>
            </div>
        </div>`;
    }).join('');
}

function renderListView(results, total, page) {
    const body = $('#results-body');

    if (!results.length) {
        body.innerHTML = '<tr><td colspan="8" class="no-results">No listings found. Try adjusting your filters or running a new search.</td></tr>';
        return;
    }

    body.innerHTML = results.map(r => `
        <tr>
            <td>
                ${r.thumbnail_url
                    ? `<img src="${r.thumbnail_url}" class="listing-thumb" alt="Apartment">`
                    : '<div class="listing-thumb" style="display:flex;align-items:center;justify-content:center;color:#D1D5DB;font-size:11px">No image</div>'
                }
            </td>
            <td class="price-cell">${r.price ? '₪ ' + r.price.toLocaleString() : '–'}</td>
            <td>${r.rooms || '–'}</td>
            <td>${r.size_sqm || '–'}</td>
            <td>${r.floor != null ? r.floor + (r.total_floors ? '/' + r.total_floors : '') : '–'}</td>
            <td>${r.address_full || '–'}</td>
            <td>
                <div class="feature-tags">
                    ${buildFeatureTags(r).map(t => `<span class="feature-tag">${t}</span>`).join('')}
                </div>
            </td>
            <td>
                ${r.url ? `<a href="${r.url}" target="_blank" class="listing-link">View</a>` : '–'}
            </td>
        </tr>
    `).join('');
}

function renderPagination(total, currentPage) {
    const container = $('#pagination');
    const totalPages = Math.ceil(total / state.perPage);

    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }

    let html = '';
    const start = Math.max(1, currentPage - 2);
    const end = Math.min(totalPages, currentPage + 2);

    if (currentPage > 1) {
        html += `<button class="page-nav" onclick="goToPage(${currentPage - 1})">Prev</button>`;
    }

    for (let i = start; i <= end; i++) {
        html += `<button class="${i === currentPage ? 'active' : ''}" onclick="goToPage(${i})">${i}</button>`;
    }

    if (currentPage < totalPages) {
        html += `<button class="page-nav" onclick="goToPage(${currentPage + 1})">Next</button>`;
    }

    container.innerHTML = html;
}

function goToPage(page) {
    state.page = page;
    loadResults();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function clearSearch() {
    closeModal();
    clearFiltersOnly();

    const sortSelect = $('#sort-select');
    if (sortSelect) sortSelect.value = 'date_scraped-DESC';
    state.sortBy = 'date_scraped';
    state.sortOrder = 'DESC';
    state.page = 1;
    state.listingDetailsCache = {};
    state.currentResults = [];

    hideStatus();
    renderResults([], 0, 1);
    $('#pagination').innerHTML = '';
}

function clearFiltersOnly() {
    $('#city-input').value = '';
    $('#city').value = '';

    [
        'rooms_min', 'rooms_max',
        'price_min', 'price_max',
        'size_min', 'size_max',
    ].forEach(id => {
        const el = $(`#${id}`);
        if (el) el.value = '';
    });

    $$('.chip input[type="checkbox"]').forEach(cb => {
        cb.checked = false;
    });
}

function initChips() {
    // CSS :has(input:checked) handles the visual toggle.
    // Nothing needed here, but keeping for future extensibility.
}

function initViewToggle() {
    $$('.view-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const view = btn.dataset.view;
            state.view = view;

            $$('.view-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            if (view === 'grid') {
                $('#results-grid').classList.remove('hidden');
                $('#results-list').classList.add('hidden');
            } else {
                $('#results-grid').classList.add('hidden');
                $('#results-list').classList.remove('hidden');
            }

            loadResults();
        });
    });
}

function initSortSelect() {
    const select = $('#sort-select');
    if (!select) return;

    select.addEventListener('change', () => {
        const [field, order] = select.value.split('-');
        state.sortBy = field;
        state.sortOrder = order;
        state.page = 1;
        loadResults();
    });
}

function buildFeaturesHtml(data) {
    const allFeatures = [
        ['Elevator', data.has_elevator],
        ['Parking', data.has_parking],
        ['Balcony', data.has_balcony],
        ['A/C', data.has_ac],
        ['Furnished', data.is_furnished],
        ['Pets', data.pets_allowed],
        ['Mamad', data.has_mamad],
        ['Bars', data.has_bars],
    ];
    const active = allFeatures.filter(([, val]) => val);
    if (!active.length) return '<span style="color:#9CA3AF;font-size:13px">No features listed</span>';
    return active.map(([label]) => `
        <span class="modal-feature active">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            ${label}
        </span>
    `).join('');
}

function getListingCacheKey(listingId, listingUrl) {
    if (listingId) return `id:${listingId}`;
    if (listingUrl) return `url:${listingUrl}`;
    return '';
}

function applyListingDetailsToModal(data) {
    const featuresEl = $('#modal-features');
    if (!featuresEl) return;

    featuresEl.innerHTML = buildFeaturesHtml(data);

    const descSection = $('#modal-desc-section');
    if (data.description && descSection) {
        $('#modal-description').textContent = data.description;
        descSection.style.display = '';
    } else if (descSection) {
        descSection.style.display = 'none';
    }
}

function mergeListingDetailsIntoState(listingId, listingUrl, data) {
    const cacheKey = getListingCacheKey(listingId, listingUrl);
    if (cacheKey) {
        state.listingDetailsCache[cacheKey] = data;
    }

    const listing = state.currentResults.find(r =>
        (listingId && r.listing_id === listingId) ||
        (listingUrl && r.url === listingUrl)
    );
    if (!listing) return;

    Object.assign(listing, {
        has_elevator: data.has_elevator,
        has_parking: data.has_parking,
        has_balcony: data.has_balcony,
        has_ac: data.has_ac,
        is_furnished: data.is_furnished,
        pets_allowed: data.pets_allowed,
        has_mamad: data.has_mamad,
        has_bars: data.has_bars,
        description: data.description,
    });
}

function showDetailsUnavailable() {
    const featuresEl = $('#modal-features');
    if (featuresEl) {
        featuresEl.innerHTML = '<span style="color:#9CA3AF;font-size:13px">No features listed</span>';
    }

    const descSection = $('#modal-desc-section');
    if (descSection) {
        descSection.style.display = 'none';
    }
}

function openModal(index) {
    const r = state.currentResults[index];
    if (!r) return;

    closeModal();

    const type = getPropertyType(r);
    const floorText = r.floor != null ? `${r.floor}${r.total_floors ? '/' + r.total_floors : ''}` : '–';

    const imageHtml = r.thumbnail_url
        ? `<img src="${r.thumbnail_url}" alt="Apartment">`
        : `<div class="modal-img-placeholder"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect width="18" height="18" x="3" y="3" rx="2" ry="2"></rect><circle cx="9" cy="9" r="2"></circle><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"></path></svg></div>`;

    const overlay = document.createElement('div');
    overlay.id = 'modal-overlay';
    overlay.className = 'modal-overlay';
    overlay.onclick = closeModal;
    overlay.innerHTML = `
        <div class="modal" onclick="event.stopPropagation()">
            <button class="modal-close" onclick="closeModal()">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"></path><path d="m6 6 12 12"></path></svg>
            </button>
            <div class="modal-image">${imageHtml}</div>
            <div class="modal-body">
                <div class="modal-price-row">
                    <span class="modal-price">${r.price ? '₪ ' + r.price.toLocaleString() : '–'}</span>
                    <span class="card-badge ${getBadgeClass(type)}">${getBadgeLabel(type)}</span>
                </div>
                <div class="modal-address">${r.address_full || '–'}</div>
                <div class="modal-details-grid">
                    <div class="modal-detail"><span class="modal-detail-label">Rooms</span><span class="modal-detail-value">${r.rooms || '–'}</span></div>
                    <div class="modal-detail"><span class="modal-detail-label">Size</span><span class="modal-detail-value">${r.size_sqm ? r.size_sqm + ' m²' : '–'}</span></div>
                    <div class="modal-detail"><span class="modal-detail-label">Floor</span><span class="modal-detail-value">${floorText}</span></div>
                    <div class="modal-detail"><span class="modal-detail-label">City</span><span class="modal-detail-value">${r.city || '–'}</span></div>
                    <div class="modal-detail"><span class="modal-detail-label">Neighborhood</span><span class="modal-detail-value">${r.neighborhood || '–'}</span></div>
                    <div class="modal-detail"><span class="modal-detail-label">Street</span><span class="modal-detail-value">${r.street || '–'}</span></div>
                </div>
                <div class="modal-section">
                    <span class="modal-section-title">Features</span>
                    <div id="modal-features" class="modal-features">
                        <div class="modal-loading">
                            <div class="spinner"></div>
                            <span>Loading details...</span>
                        </div>
                    </div>
                </div>
                <div id="modal-desc-section" class="modal-section" style="display:none">
                    <span class="modal-section-title">Description</span>
                    <p id="modal-description" class="modal-description"></p>
                </div>
                ${r.url ? `<div class="modal-actions"><a href="${r.url}" target="_blank" class="modal-btn-primary" onclick="event.stopPropagation()">View on Yad2 <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" x2="21" y1="14" y2="3"></line></svg></a></div>` : ''}
            </div>
        </div>`;

    document.body.appendChild(overlay);
    document.body.style.overflow = 'hidden';

    if (r.listing_id) {
        const cacheKey = getListingCacheKey(r.listing_id, r.url);
        const cachedDetails = cacheKey ? state.listingDetailsCache[cacheKey] : null;
        if (cachedDetails) {
            applyListingDetailsToModal(cachedDetails);
        } else if (
            r.description ||
            r.has_elevator || r.has_parking || r.has_balcony || r.has_ac ||
            r.is_furnished || r.pets_allowed || r.has_mamad || r.has_bars
        ) {
            const existingDetails = {
                description: r.description || null,
                has_elevator: !!r.has_elevator,
                has_parking: !!r.has_parking,
                has_balcony: !!r.has_balcony,
                has_ac: !!r.has_ac,
                is_furnished: !!r.is_furnished,
                pets_allowed: !!r.pets_allowed,
                has_mamad: !!r.has_mamad,
                has_bars: !!r.has_bars,
            };
            mergeListingDetailsIntoState(r.listing_id, r.url, existingDetails);
            applyListingDetailsToModal(existingDetails);
        } else {
            fetchListingDetails(r.listing_id, r.url);
        }
    }
}

async function fetchListingDetails(listingId, listingUrl) {
    const featuresEl = $('#modal-features');
    if (!featuresEl) return;

    try {
        const params = new URLSearchParams();
        if (listingUrl) params.set('url', listingUrl);
        const query = params.toString();
        const resp = await fetch(`/api/listing/${listingId}/details${query ? `?${query}` : ''}`);
        const data = await resp.json().catch(() => null);

        if (!resp.ok || !data || typeof data !== 'object') {
            showDetailsUnavailable();
            return;
        }

        mergeListingDetailsIntoState(listingId, listingUrl, data);
        applyListingDetailsToModal(data);
    } catch {
        showDetailsUnavailable();
    }
}

function closeModal() {
    const overlay = $('#modal-overlay');
    if (overlay) {
        overlay.remove();
        document.body.style.overflow = '';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadCities();

    $('#btn-search')?.addEventListener('click', startSearch);
    $('#btn-filter')?.addEventListener('click', () => {
        state.page = 1;
        loadResults();
    });
    $('#btn-clear')?.addEventListener('click', clearFiltersOnly);
    $('#btn-clear-all')?.addEventListener('click', clearSearch);

    initChips();
    initViewToggle();
    initSortSelect();

    document.addEventListener('click', (e) => {
        const clearBtn = e.target.closest('#btn-clear, .clear-btn');
        if (clearBtn) {
            e.preventDefault();
            clearFiltersOnly();
            return;
        }

        const clearSearchBtn = e.target.closest('#btn-clear-all, .clear-search-btn');
        if (!clearSearchBtn) return;
        e.preventDefault();
        clearSearch();
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });

    loadResults({});
});
