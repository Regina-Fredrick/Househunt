import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiGet, apiPost, getCsrfToken } from '../utils/api';

async function fetchAllNeighborhoods() {
  // Same fix as BrowsePage.jsx: DRF's `next` link is an absolute URL,
  // which bypasses the Vite dev proxy and fails cross-origin if fetched
  // directly — strip the scheme+host so every page stays same-origin.
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

export default function CreateListingPage() {
  const [neighborhoods, setNeighborhoods] = useState([]);
  const [form, setForm] = useState({
    title: '', description: '', price: '', property_type: 'apartment',
    listing_type: 'rent', bedrooms: '', bathrooms: '', neighborhood: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [createdListing, setCreatedListing] = useState(null);
  const [images, setImages] = useState([]);
  const [uploading, setUploading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    fetchAllNeighborhoods()
      .then(setNeighborhoods)
      .catch((err) => console.error('Failed to load neighborhoods', err));
  }, []);

  function handleChange(e) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const listing = await apiPost('/api/listings/create/', {
        ...form,
        price: parseFloat(form.price),
        bedrooms: form.bedrooms ? parseInt(form.bedrooms) : null,
        bathrooms: form.bathrooms ? parseInt(form.bathrooms) : null,
        neighborhood: parseInt(form.neighborhood),
      });
      setCreatedListing(listing);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleImageUpload(e) {
    const file = e.target.files[0];
    if (!file || !createdListing) return;

    setUploading(true);
    try {
      const csrfToken = await getCsrfToken();
      const formData = new FormData();
      formData.append('image', file);

      const res = await fetch(`/api/listings/${createdListing.id}/upload-image/`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'X-CSRFToken': csrfToken },
        body: formData,
      });
      if (!res.ok) throw new Error('Upload failed');
      const data = await res.json();
      setImages([...images, data]);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  }

  if (createdListing) {
    return (
      <div style={{ maxWidth: 500 }}>
        <h2>Add Photos</h2>
        <p className="muted">
          Listing "{createdListing.title}" created and submitted for review.
          Upload 1-5 photos below.
        </p>

        {error && <div className="alert alert-error">{error}</div>}

        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 16 }}>
          {images.map((img) => (
            <img key={img.id} src={img.image} alt="" style={{ width: 100, height: 100, objectFit: 'cover', borderRadius: 8 }} />
          ))}
        </div>

        {images.length < 5 && (
          <input type="file" accept="image/*" onChange={handleImageUpload} disabled={uploading} />
        )}

        <div style={{ marginTop: 20 }}>
          <button className="btn btn-primary" onClick={() => navigate('/mine')}>
            Done — Go to My Listings
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 500 }}>
      <h2>New Listing</h2>
      {error && <div className="alert alert-error">{error}</div>}
      <form onSubmit={handleSubmit}>
        <label>Title</label>
        <input name="title" value={form.title} onChange={handleChange} required />

        <label>Description</label>
        <textarea name="description" value={form.description} onChange={handleChange} required rows={4} />

        <label>Price (KES)</label>
        <input name="price" type="number" value={form.price} onChange={handleChange} required />

        <label>Property Type</label>
        <select name="property_type" value={form.property_type} onChange={handleChange}>
          <option value="apartment">Apartment</option>
          <option value="house">House</option>
          <option value="land">Land</option>
          <option value="commercial">Commercial</option>
        </select>

        <label>Listing Type</label>
        <select name="listing_type" value={form.listing_type} onChange={handleChange}>
          <option value="rent">Rent</option>
          <option value="sale">Sale</option>
        </select>

        <label>Bedrooms</label>
        <input name="bedrooms" type="number" value={form.bedrooms} onChange={handleChange} />

        <label>Bathrooms</label>
        <input name="bathrooms" type="number" value={form.bathrooms} onChange={handleChange} />

        <label>Neighborhood</label>
        <select name="neighborhood" value={form.neighborhood} onChange={handleChange} required>
          <option value="">Select...</option>
          {neighborhoods.map((n) => (
            <option key={n.id} value={n.id}>{n.name}</option>
          ))}
        </select>

        <button type="submit" className="btn btn-primary" disabled={loading} style={{ marginTop: 16 }}>
          {loading ? 'Submitting...' : 'Submit Listing'}
        </button>
      </form>
    </div>
  );
}