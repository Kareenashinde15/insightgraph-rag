const BACKEND_CHAT_URL =
  process.env.BACKEND_API_URL
    ? `${process.env.BACKEND_API_URL.replace(/\/$/, '')}/api/chat`
    : 'https://insightgraph-rag-api.onrender.com/api/chat';

export default async function handler(request, response) {
  if (request.method !== 'POST') {
    response.setHeader('Allow', 'POST');
    return response.status(405).json({ detail: 'Method not allowed' });
  }

  try {
    const upstream = await fetch(BACKEND_CHAT_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request.body || {}),
    });
    const payload = await upstream.text();
    response.status(upstream.status);
    response.setHeader(
      'Content-Type',
      upstream.headers.get('content-type') || 'application/json'
    );
    return response.send(payload);
  } catch (error) {
    console.error('Chat proxy failed:', error);
    return response.status(502).json({
      detail: 'Chat backend is temporarily unavailable. Please try again.',
    });
  }
}
