# InsightGraph deployment

The deployment is split between Vercel and Render:

- Vercel hosts the React frontend.
- Render hosts the FastAPI backend.
- Cloudinary stores original uploaded files.
- MongoDB Atlas stores indexed sections and application state.
- Groq generates grounded answers.

## Render environment variables

Set these in the Render service:

```text
STORAGE_BACKEND=mongodb
MONGODB_URI=<MongoDB Atlas connection string>
MONGODB_DATABASE=insightgraph
CLOUDINARY_CLOUD_NAME=<Cloudinary cloud name>
CLOUDINARY_API_KEY=<Cloudinary API key>
CLOUDINARY_API_SECRET=<Cloudinary API secret>
GROQ_API_KEY=<new Groq key>
CORS_ORIGINS=https://insightsrag.vercel.app,https://insightgraph.vercel.app,https://frontend-ashen-three-16.vercel.app
ENABLE_KNOWLEDGE_GRAPH=false
OPENDATALOADER_HYBRID=
OPENDATALOADER_HYBRID_URL=<optional hybrid server URL>
OPENDATALOADER_HYBRID_MODE=
```

The MongoDB URI and all provider keys are secrets. Never commit them to GitHub.

## PDF parsing

OpenDataLoader is the primary PDF parser. The Render runtime must have Java
11 or newer available because the parser runs its local JVM engine. Complex or
image-only PDFs can use an OpenDataLoader hybrid server by setting
`OPENDATALOADER_HYBRID`, `OPENDATALOADER_HYBRID_URL`, and optionally
`OPENDATALOADER_HYBRID_MODE`. Without hybrid mode, the backend keeps a bounded
OCR fallback for scanned PDFs.

## MongoDB setup

Create an Atlas database named `insightgraph` and allow the Render service to
connect. The backend creates its collections and text indexes on startup:

- `documents`
- `chunks` (plain text chunks, without embeddings)
- `processing_jobs`
- `chat_sessions`
- `metrics`
- `settings`
- `graph_nodes`
- `graph_edges`

## Vercel environment

For the frontend, use:

```text
VITE_API_BASE_URL=https://insightgraph-rag-api.onrender.com/api
```

Redeploy the frontend after changing this value. Verify the backend with:

```text
https://insightgraph-rag-api.onrender.com/health
```

The public frontend origin must remain exactly:
`https://insightsrag.vercel.app`.
