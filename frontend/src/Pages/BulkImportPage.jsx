import { useEffect, useState } from 'react';
import { apiGet, getCsrfToken } from '../utils/api';

export default function BulkImportPage() {
  const [apiKey, setApiKey] = useState(null);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    apiGet('/api/auth/landlord-api-key/')
      .then((data) => setApiKey(data.api_key))
      .catch((err) => setError(err.message));
  }, []);

  async function handleUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    setResult(null);
    try {
      const csrfToken = await getCsrfToken();
      const formData = new FormData();
      formData.append('file', file);

      const res = await fetch('/api/listings/bulk-import/', {
        method: 'POST',
        credentials: 'include',
        headers: { 'X-CSRFToken': csrfToken },
        body: formData,
      });
      const data = await res.json();
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  }

  if (error) {
    return (
      <div>
        <h2>Bulk Import</h2>
        <div className="alert alert-error">{error}</div>
        <p className="muted">Bulk import is only available to verified landlords. Complete KYC verification to unlock this feature.</p>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 600 }}>
      <h2>Bulk Import Listings</h2>

      {apiKey && (
        <div className="card p-3" style={{ marginBottom: 20 }}>
          <p className="muted" style={{ marginBottom: 4 }}>Your API Key</p>
          <code style={{ wordBreak: 'break-all' }}>{apiKey}</code>
        </div>
      )}

      <p className="muted">
        Upload a CSV with columns: title, description, price, property_type, listing_type, bedrooms, bathrooms, neighborhood (neighborhood ID).
      </p>

      <input type="file" accept=".csv" onChange={handleUpload} disabled={uploading} />

      {uploading && <p>Uploading...</p>}

      {result && (
        <div className="alert alert-success" style={{ marginTop: 16 }}>
          <p>Created {result.created_count} listing(s).</p>
          {result.errors && result.errors.length > 0 && (
            <div>
              <p><strong>Errors:</strong></p>
              <ul>
                {result.errors.map((e, i) => (
                  <li key={i}>Row {e.row}: {JSON.stringify(e.errors)}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}