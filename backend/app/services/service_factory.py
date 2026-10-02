"""Select the configured persistence/retrieval service."""

from backend.app.services.mongo_vectorless_service import MongoVectorlessKnowledgeService


def get_knowledge_service() -> MongoVectorlessKnowledgeService:
    """Return the single MongoDB-backed vectorless service instance."""
    return MongoVectorlessKnowledgeService()
