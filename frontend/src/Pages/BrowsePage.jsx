import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

async function fetchAllNeighborhoods() {
  // The neighborhoods endpoint is paginated (12/page by default), but a
  // filter dropdown needs the full list of ~88 — follow `next` until
  // there's nothing left.
  //
  // DRF returns `next` as an ABSOLUTE URL (e.g. http://127.0.0.1:8080/...).
  // Fetching that directly bypasses Vite's dev proxy and hits Django
  // cross-origin, which gets silently blocked — strip the scheme+host so
  // every page request stays relative and keeps going through the proxy.
  let url = '/api/listings/neighborhoods/';
  let all = [];
  while (url) {
    const res = await fetch(url);
    const data = await res.json();
    all = all.concat(data.results || []);
    url = data.next ? data.next.replace(/^https?:\/\/[^/]+/, '') : null;
  }
  return all;
}

export default function BrowsePage() {
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [neighborhoods, setNeighborhoods] = useState([]);
  const [hasSearched, setHasSearched] = useState(false);

  // Filter form state — separate from the applied filters below, so
  // typing in price fields doesn't refetch on every keystroke.
  const [neighborhoodInput, setNeighborhoodInput] = useState('');
  const [minPrice, setMinPrice] = useState('');
  const [maxPrice, setMaxPrice] = useState('');
  const [bedrooms, setBedrooms] = useState('');
  const [appliedFilters, setAppliedFilters] = useState({});

  useEffect(() => {
    fetchAllNeighborhoods()
      .then(setNeighborhoods)
      .catch((err) => console.error('Failed to load neighborhoods', err));
  }, []);

  useEffect(() => {
    if (!hasSearched) return;

    setLoading(true);
    const params = new URLSearchParams();
    Object.entries(appliedFilters).forEach(([key, value]) => {
      if (value) params.set(key, value);
    });
    const query = params.toString();

    fetch(`/api/listings/${query ? `?${query}` : ''}`)
      .then((res) => res.json())
      .then((data) => {
        setListings(data.results || data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load listings', err);
        setLoading(false);
      });
  }, [appliedFilters, hasSearched]);

  function handleSearch(e) {
    e.preventDefault();
    // The datalist input's value is free text — resolve it to a real
    // neighborhood id by matching against the fetched list. If what was
    // typed doesn't match any known neighborhood (partial text, typo),
    // just omit that filter rather than sending a nonsense value.
    const trimmed = neighborhoodInput.trim().toLowerCase();
    const matched = neighborhoods.find((n) => n.name.toLowerCase() === trimmed);

    setAppliedFilters({
      neighborhood: matched ? matched.id : '',
      min_price: minPrice,
      max_price: maxPrice,
      bedrooms,
    });
    setHasSearched(true);
  }

  function handleClear() {
    setNeighborhoodInput('');
    setMinPrice('');
    setMaxPrice('');
    setBedrooms('');
    setAppliedFilters({});
    setListings([]);
    setHasSearched(false);
  }

  const hasActiveFilters = Object.values(appliedFilters).some(Boolean);

  return (
    <div>
      <h2 style={{ marginBottom: 20 }}>Browse Listings</h2>

      <form
        onSubmit={handleSearch}
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 12,
          alignItems: 'flex-end',
          marginBottom: 24,
          padding: 16,
          background: 'white',
          borderRadius: 14,
          border: '1px solid var(--line)',
        }}
      >
        <div style={{ minWidth: 200 }}>
          <label style={{ marginTop: 0 }}>Neighborhood</label>
          <input
            type="text"
            list="neighborhood-options"
            placeholder="Type or choose a neighborhood"
            value={neighborhoodInput}
            onChange={(e) => setNeighborhoodInput(e.target.value)}
            autoComplete="off"
          />
          <datalist id="neighborhood-options">
            {neighborhoods.map((n) => (
              <option key={n.id} value={n.name} />
            ))}
          </datalist>
        </div>

        <div style={{ minWidth: 120 }}>
          <label style={{ marginTop: 0 }}>Min price (KES)</label>
          <input
            type="number"
            min="0"
            placeholder="e.g. 20000"
            value={minPrice}
            onChange={(e) => setMinPrice(e.target.value)}
          />
        </div>

        <div style={{ minWidth: 120 }}>
          <label style={{ marginTop: 0 }}>Max price (KES)</label>
          <input
            type="number"
            min="0"
            placeholder="e.g. 80000"
            value={maxPrice}
            onChange={(e) => setMaxPrice(e.target.value)}
          />
        </div>

        <div style={{ minWidth: 140 }}>
          <label style={{ marginTop: 0 }}>Bedrooms</label>
          <select value={bedrooms} onChange={(e) => setBedrooms(e.target.value)}>
            <option value="">Any</option>
            <option value="1">1</option>
            <option value="2">2</option>
            <option value="3">3</option>
            <option value="4">4</option>
            <option value="5">5</option>
          </select>
        </div>

        <div style={{ display: 'flex', gap: 8 }}>
          <button type="submit" className="btn btn-primary">Search</button>
          {hasActiveFilters && (
            <button type="button" onClick={handleClear} className="btn-outline btn-sm" style={{ height: 36 }}>
              Clear
            </button>
          )}
        </div>
      </form>

      {!hasSearched ? (
        <p className="muted">Use the filters above and click Search to find listings.</p>
      ) : loading ? (
        <p className="muted">Loading listings...</p>
      ) : listings.length === 0 ? (
        <p className="muted">No listings match those filters.</p>
      ) : (
        <div className="grid">
          {listings.map((listing) => (
            <Link key={listing.id} to={`/listings/${listing.id}`} className="card">
              {listing.images && listing.images[0] && (
                <img
                  src={listing.images[0].image}
                  alt={listing.title}
                  className="card-img"
                />
              )}
              <div className="card-body">
                <h3 style={{ fontSize: '1rem', margin: '0 0 6px' }}>{listing.title}</h3>
                <p className="price-tag">KES {listing.price}</p>
                <p className="muted" style={{ fontSize: '0.85rem', margin: '6px 0 0' }}>
                  {listing.neighborhood?.name}
                </p>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}