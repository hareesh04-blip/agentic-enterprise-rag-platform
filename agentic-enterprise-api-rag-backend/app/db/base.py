from app.db.base_class import Base


# Import models so Alembic can discover metadata.
from app.models.api_auth_profile import ApiAuthProfile  # noqa: E402,F401
from app.models.api_document import ApiDocument  # noqa: E402,F401
from app.models.api_endpoint import ApiEndpoint  # noqa: E402,F401
from app.models.api_error_code import ApiErrorCode  # noqa: E402,F401
from app.models.api_parameter import ApiParameter  # noqa: E402,F401
from app.models.api_project import ApiProject  # noqa: E402,F401
from app.models.api_sample import ApiSample  # noqa: E402,F401
from app.models.chat import ChatMessage, ChatSession  # noqa: E402,F401
from app.models.document_chunk import DocumentChunk  # noqa: E402,F401
from app.models.ingestion_job import IngestionJob  # noqa: E402,F401
from app.models.ingestion_run import IngestionRun  # noqa: E402,F401
from app.models.knowledge_base import KnowledgeBase, UserKnowledgeBaseAccess  # noqa: E402,F401
from app.models.permission import Permission, RolePermission  # noqa: E402,F401
from app.models.role import Role, UserRole  # noqa: E402,F401
from app.models.user import User  # noqa: E402,F401
from app.models.user_profile import UserProfile  # noqa: E402,F401
from app.models.query_feedback import QueryFeedback  # noqa: E402,F401
from app.models.improvement_task import ImprovementTask  # noqa: E402,F401
from app.models.audit_log import AuditLog  # noqa: E402,F401
