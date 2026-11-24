import uuid

from fastapi import Depends

from app.core.response.envelope import ApiRouter
from app.dependencies import get_activity_logger, get_visit_question_service
from app.middleware.auth_middleware import admin_only
from app.schemas.voucher_qr_schema import VisitQuestionResponse, VisitQuestionsReplace
from app.services.activity_logger import Action, ActivityLogger, Module
from app.services.visit_question_service import VisitQuestionService

router = ApiRouter(prefix="/visit-questions", tags=["Visit Question"])

@router.get("/", response_model=list[VisitQuestionResponse], dependencies=[Depends(admin_only)])
def list_questions(
    company_id: uuid.UUID | None = None,
    service: VisitQuestionService = Depends(get_visit_question_service),
):
    return service.get_for_company(company_id)

@router.put("/", response_model=list[VisitQuestionResponse], dependencies=[Depends(admin_only)])
def replace_questions(
    data: VisitQuestionsReplace,
    service: VisitQuestionService = Depends(get_visit_question_service),
    activity: ActivityLogger = Depends(get_activity_logger),
):
    questions = service.replace_all(data.company_id, data.questions)
    activity.record(Action.update, Module.master, "Mengubah pertanyaan customer visit")
    return questions
