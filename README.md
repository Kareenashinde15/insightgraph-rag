# InsightGraph — Vectorless Document Intelligence

InsightGraph is a document assistant that stores original files in Cloudinary,
stores page-aware text sections in MongoDB Atlas, retrieves evidence with
ordinary MongoDB text search, and generates grounded answers through Groq.

The application intentionally does not use embeddings, a vector database, or
PageIndex. Entity and relationship extraction remains optional enrichment.

## Architecture

- React + Vite frontend
- FastAPI backend
- Cloudinary for original PDFs and other uploaded files
- MongoDB Atlas for documents, sections, jobs, sessions, and graph data
- MongoDB text indexes for vectorless lexical retrieval
- Groq for grounded answer generation
- Optional entity and relationship extraction

## Run locally

1. Install backend dependencies:

   ```powershell
   py -3 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
   ```

2. Configure `.env`:

   ```text
   STORAGE_BACKEND=mongodb
   MONGODB_URI=mongodb+srv://username:password@cluster.example.mongodb.net/?retryWrites=true&w=majority
   MONGODB_DATABASE=insightgraph
   CLOUDINARY_CLOUD_NAME=your-cloud-name
   CLOUDINARY_API_KEY=your-api-key
   CLOUDINARY_API_SECRET=your-api-secret
   GROQ_API_KEY=your-key
   GROQ_MODEL=openai/gpt-oss-120b
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

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [DEPLOYMENT.md](DEPLOYMENT.md)
for the data flow and deployment configuration.
