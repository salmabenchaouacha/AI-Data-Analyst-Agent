async function request(path, options = {}) {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status} ${detail}`);
  }
  return res.json();
}

export const api = {
  config: () => request("/config"),
  ask: (body) => request("/ask", { method: "POST", body: JSON.stringify(body) }),
  runs: () => request("/eval/runs"),
  run: (id) => request(`/eval/runs/${encodeURIComponent(id)}`),
};
