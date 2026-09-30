// Keep chat on the known live backend. A stale Vercel BACKEND_API_URL can
// otherwise make only this serverless route fail while the other API routes
// continue to work through vercel.json rewrites.
const BACKEND_CHAT_URL = 'https://insightgraph-rag-api.onrender.com/api/chat';

export const config = {
  maxDuration: 60,
};

export default async function handler(request, response) {
  if (request.method !== 'POST') {
    if (request.method === 'GET') {
      return response.status(200).json({
        service: 'InsightGraph RAG chat',
        status: 'ready',
        method: 'POST',
        message: "Send a POST request with a JSON body containing 'query' to ask a question.",
      });
    }
    response.setHeader('Allow', 'GET, POST');
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
