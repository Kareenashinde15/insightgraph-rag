import os
import uuid
from pathlib import Path
from secrets import token_hex
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from typing import List
from backend.app.services.knowledge_service import KnowledgeService
from backend.app.models.schema import DocumentModel, ProcessingJobModel

router = APIRouter(prefix="/api/documents", tags=["Documents"])
UPLOAD_DIR = os.path.abspath(os.getenv(
    "UPLOAD_DIR",
    os.path.join(os.path.dirname(__file__), "../../../uploads"),
))
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(50 * 1024 * 1024)))
ALLOWED_EXTENSIONS = {"txt", "md", "markdown", "html", "htm", "pdf", "docx"}
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("", response_model=List[DocumentModel])
def list_documents():
    ks = KnowledgeService()
    return list(ks.documents.values())

@router.get("/{doc_id}")
def get_document(doc_id: str):
    ks = KnowledgeService()
    if doc_id not in ks.documents:
        raise HTTPException(status_code=404, detail="Document not found")
    doc = ks.documents[doc_id]
    chunks = ks.document_chunks.get(doc_id, [])

    # Get extracted entities and relationships for this document
    entities = [n for n in ks.graph_engine.get_all_nodes() if doc_id in n.document_ids]
    relationships = [e for e in ks.graph_engine.get_all_edges() if e.source_document == doc_id]

    return {
        "document": doc,
        "chunks": chunks,
        "entities": entities,
        "relationships": relationships,
    }

@router.get("/{doc_id}/status")
def get_document_status(doc_id: str):
    ks = KnowledgeService()
    if doc_id not in ks.documents:
        raise HTTPException(status_code=404, detail="Document not found")
    doc = ks.documents[doc_id]
    return {
        "id": doc.id,
        "status": doc.status,
        "current_stage": doc.current_stage,
        "progress": doc.progress,
        "chunks": doc.chunk_count,
        "entities": doc.entity_count,
        "relationships": doc.relationship_count,
    }

@router.delete("/{doc_id}")
def delete_document(doc_id: str):
    ks = KnowledgeService()
    if doc_id not in ks.documents:
        raise HTTPException(status_code=404, detail="Document not found")

    document = ks.documents[doc_id]
    storage_path = document.storage_path

    # Remove document records and all derived graph/vector state.
    del ks.documents[doc_id]
    ks.db.delete("documents", doc_id)
    if doc_id in ks.document_chunks:
        del ks.document_chunks[doc_id]
    for chunk_key in list(ks.db.load("chunks")):
        if chunk_key.startswith(f"{doc_id}_"):
            ks.db.delete("chunks", chunk_key)

    # Clean vector store
    ks.vector_store.delete_by_document(doc_id)
    ks.graph_engine.delete_by_document(doc_id)
    for job_id in [jid for jid, job in ks.jobs.items() if job.document_id == doc_id]:
        del ks.jobs[job_id]
        ks.db.delete("jobs", job_id)
    ks.persist_graph()
    ks.persist_vectors()

    # Only delete files contained in the configured upload directory.
    if storage_path:
        upload_root = Path(UPLOAD_DIR).resolve()
        candidate = Path(storage_path).resolve()
        if upload_root == candidate.parent or upload_root in candidate.parents:
            try:
                candidate.unlink(missing_ok=True)
            except OSError:
                pass

    return {"message": "Document deleted successfully", "id": doc_id}

@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    ks = KnowledgeService()
    original_name = (file.filename or "").strip()
    safe_name = Path(original_name).name
    extension = Path(safe_name).suffix.lower().lstrip(".")
    if not safe_name or safe_name in {".", ".."} or safe_name != original_name:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail=f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}")

    content = await file.read(MAX_UPLOAD_SIZE + 1)
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail=f"File exceeds the {MAX_UPLOAD_SIZE} byte limit")

    doc_id = f"doc_{uuid.uuid4().hex[:8]}"
    file_path = os.path.join(UPLOAD_DIR, f"{doc_id}_{token_hex(8)}.{extension}")

    with open(file_path, "wb") as buffer:
        buffer.write(content)

    doc_model = DocumentModel(
        id=doc_id,
        filename=safe_name,
        file_type=extension,
        file_size=len(content),
        storage_path=file_path,
        status="processing",
        current_stage="Upload",
        progress=5,
    )
    ks.documents[doc_id] = doc_model
    ks.persist_document(doc_model)

    job_id = f"job_{uuid.uuid4().hex[:8]}"
    job = ProcessingJobModel(
        id=job_id,
        document_id=doc_id,
        filename=safe_name,
        status="processing",
        current_stage="Upload",
        progress=5,
    )
    ks.jobs[job_id] = job
    ks.persist_job(job)

    # Execute asynchronous pipeline
    background_tasks.add_task(
        ks.process_document,
        document=doc_model,
        file_path=file_path,
        job=job
    )

    return {
        "message": "File uploaded and processing initiated",
        "document_id": doc_id,
        "job_id": job_id,
        "status": "processing"
    }

@router.post("/{doc_id}/reprocess")
def reprocess_document(doc_id: str, background_tasks: BackgroundTasks):
    ks = KnowledgeService()
    if doc_id not in ks.documents:
        raise HTTPException(status_code=404, detail="Document not found")
    doc = ks.documents[doc_id]
    if not doc.storage_path or not os.path.exists(doc.storage_path):
        raise HTTPException(status_code=409, detail="The original document is unavailable; upload it again before reprocessing")

    ks.vector_store.delete_by_document(doc_id)
    ks.graph_engine.delete_by_document(doc_id)
    ks.document_chunks.pop(doc_id, None)
    ks.db.delete("documents", doc_id)
    for chunk_key in list(ks.db.load("chunks")):
        if chunk_key.startswith(f"{doc_id}_"):
            ks.db.delete("chunks", chunk_key)
    ks.persist_graph()
    ks.persist_vectors()

    doc.status = "processing"
    doc.progress = 5
    job_id = f"job_{uuid.uuid4().hex[:8]}"
    job = ProcessingJobModel(
        id=job_id,
        document_id=doc_id,
        filename=doc.filename,
        status="processing",
    )
    ks.jobs[job_id] = job
    ks.persist_document(doc)
    ks.persist_job(job)

    background_tasks.add_task(
        ks.process_document,
        document=doc,
        file_path=doc.storage_path,
        job=job
    )
    return {"message": "Reprocessing started", "job_id": job_id}
