from cornice.resource import resource

from openprocurement.tender.competitiveordering.constants import COMPETITIVE_ORDERING
from openprocurement.tender.core.procedure.views.award_req_response_evidence import (
    AwardReqResponseEvidenceResource as BaseReqResponseEvidenceResource,
)


@resource(
    name=f"{COMPETITIVE_ORDERING}:Award Requirement Response Evidence",
    collection_path="/tenders/{tender_id}/awards/{award_id}/requirement_responses/{requirement_response_id}/evidences",
    path="/tenders/{tender_id}/awards/{award_id}/requirement_responses/{requirement_response_id}/evidences/{evidence_id}",
    procurementMethodType=COMPETITIVE_ORDERING,
    description="Tender award evidences",
)
class COAwardReqResponseResource(BaseReqResponseEvidenceResource):
    pass
