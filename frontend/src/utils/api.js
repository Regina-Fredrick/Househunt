const API_BASE = '';

export async function getCsrfToken() {
  const res = await fetch(`${API_BASE}/api/auth/csrf/`, { credentials: 'include' });
  const data = await res.json();
  return data.csrfToken;
}

export async function apiPost(url, body) {
  const csrfToken = await getCsrfToken();
  const res = await fetch(`${API_BASE}${url}`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
    },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || JSON.stringify(data));
  }
  return data;
}

export async function apiGet(url) {
  const res = await fetch(`${API_BASE}${url}`, { credentials: 'include' });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || 'Request failed');
  }
  return data;
}