import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiGet, getCsrfToken } from '../utils/api';

export default function EditListingPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [neighborhoods, setNeighborhoods] = useState([]);
  const [form, setForm] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    Promise.all([
      apiGet('/api/listings/neighborhoods/'),
      apiGet(`/api/listings/mine/`),
    ]).then(([neighborhoodData, mine]) => {
      setNeighborhoods(neighborhoodData.results || neighborhoodData);
      const listing = (mine.results || mine).find((l) => String(l.id) === id);
      if (listing) {
        setForm({
          title: listing.title,
          description: listing.description || '',
          price: listing.price,
          property_type: listing.property_type,
          listing_type: listing.listing_type,
          bedrooms: listing.bedrooms || '',
          bathrooms: listing.bathrooms || '',
          neighborhood: listing.neighborhood?.id || '',
        });
      }
    });
  }, [id]);

  function handleChange(e) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const csrfToken = await getCsrfToken();
      const res = await fetch(`/api/listings/${id}/edit/`, {
        method: 'PATCH',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({
          ...form,
          price: parseFloat(form.price),
          bedrooms: form.bedrooms ? parseInt(form.bedrooms) : null,
          bathrooms: form.bathrooms ? parseInt(form.bathrooms) : null,
          neighborhood: parseInt(form.neighborhood),
        }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(JSON.stringify(data));
      }
      navigate('/mine');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (!form) return <p>Loading...</p>;

  return (
    <div style={{ maxWidth: 500 }}>
      <h2>Edit Listing</h2>
      {error && <div style={{ background: '#FDECEE', color: '#E05263', padding: 12, borderRadius: 8, marginBottom: 16 }}>{error}</div>}
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
          {loading ? 'Saving...' : 'Save Changes'}
        </button>
      </form>
    </div>
  );
}