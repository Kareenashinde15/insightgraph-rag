const BACKEND_URL = 'https://insightgraph-rag-api.onrender.com/api/chat';

// Keep this function within the platform request window and fail over to a
// controlled JSON response instead of allowing an opaque gateway 502.
export const config = { maxDuration: 10 };

export default async function handler(request, response) {
  if (request.method !== 'POST') {
    response.setHeader('Allow', 'POST');
    return response.status(405).json({ detail: 'Method not allowed' });
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);

  try {
    const upstream = await fetch(BACKEND_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request.body || {}),
      signal: controller.signal,
    });
    const payload = await upstream.text();
    response.status(upstream.status);
    response.setHeader(
      'Content-Type',
      upstream.headers.get('content-type') || 'application/json'
    );
    return response.send(payload);
  } catch (error) {
    console.error('Ask Knowledge proxy failed:', error);
    return response.status(200).json({
      id: `fallback_${Date.now()}`,
      session_id: request.body?.session_id || 'session_default',
      role: 'assistant',
      content: 'The document service is waking up. Please retry once in a few seconds.',
      citations: [],
      retrieval_trace: { proxy_fallback: true },
    });
  } finally {
    clearTimeout(timeout);
  }
}
