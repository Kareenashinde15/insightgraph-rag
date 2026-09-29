# Local Knowledge Graph + RAG Hobby App

This is a single-user local application for uploading documents, creating local semantic embeddings, searching knowledge, and asking grounded questions through Groq. Entity and relationship extraction is optional enrichment, not a prerequisite for arbitrary PDF RAG.

## Local architecture

- React + Vite frontend
- FastAPI backend
- SQLite database at `data/knowledge.db`
- Original uploads in `uploads/`
- In-process vector search, with an optional in-process graph
- Groq as the only external AI provider
- Sentence Transformers for free local embeddings

No Docker, PostgreSQL, Redis, Neo4j, Qdrant, or MinIO is required.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the data flows, component rationale, and deliberate non-goals.

## Run locally

1. Install backend dependencies:

   ```powershell
   py -3 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
   ```

2. Configure Groq in a local `.env` or shell environment:

   ```text
   GROQ_API_KEY=your-key
   GROQ_MODEL=openai/gpt-oss-120b
   EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
   ENABLE_KNOWLEDGE_GRAPH=false
   ```

3. Start the backend from the project root:

   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000
   ```

4. Start the frontend in a second terminal:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

The first embedding operation downloads `sentence-transformers/all-MiniLM-L6-v2` to the local model cache. Without `GROQ_API_KEY`, document upload and search still work, but generated chat answers will explain that Groq is not configured.
