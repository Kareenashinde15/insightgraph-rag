# InsightGraph RAG deployment

This project is prepared for a split hobby deployment:

- Vercel hosts the React/Vite frontend.
- Render hosts the FastAPI backend, local embeddings, SQLite, uploads, and Groq calls.

The frontend reads `VITE_API_BASE_URL` at build time. Leave it empty for local development; set it to the deployed backend API URL in Vercel, including `/api`, for example:

```text
VITE_API_BASE_URL=https://insightgraph-rag-api.onrender.com/api
```

## 1. Before deployment

1. Create a new Groq API key. Do not reuse a key that has been exposed in chat or committed to a repository.
2. Push the project to a private or public GitHub repository.
3. Do not commit `.env`, `data/knowledge.db`, `uploads/`, or private PDFs.

## 2. Deploy the backend on Render

Create a Render Web Service from the repository. The included `render.yaml` contains the build command, start command, health check, and safe defaults.

Set these values in Render:

```text
GROQ_API_KEY=<new Groq key>
CORS_ORIGINS=https://<your-vercel-project>.vercel.app
```

The remaining variables are already defined in `render.yaml`. After deployment, verify:

```text
https://<your-render-service>.onrender.com/health
```

## 3. Deploy the frontend on Vercel

Create a Vercel project from the same repository with:

```text
Root directory: frontend
Framework preset: Vite
Build command: npm run build
Output directory: dist
```

Add this Vercel environment variable for Production and Preview environments:

```text
VITE_API_BASE_URL=https://<your-render-service>.onrender.com/api
```

Redeploy after adding the variable. Then open the Vercel URL and test upload, processing, search, and Ask Knowledge.

## Runtime expectations

The default deployment uses the local SQLite database and filesystem. On hosts with an ephemeral filesystem, uploaded files and SQLite data can reset after a restart or redeploy. This is acceptable for an interviewer demo because the interviewer can upload a PDF during the session. Persistent storage can be added later if long-term document retention is needed.

Keep `ENABLE_KNOWLEDGE_GRAPH=false` for the default demo. Enable it only when demonstrating the optional entity and relationship extraction feature.
