from cornice.resource import resource

from openprocurement.tender.core.procedure.views.award_req_response import (
    AwardReqResponseResource as BaseAwardReqResponseResource,
)


@resource(
    name="requestForProposal:Award Requirement Response",
    collection_path="/tenders/{tender_id}/awards/{award_id}/requirement_responses",
    path="/tenders/{tender_id}/awards/{award_id}/requirement_responses/{requirement_response_id}",
    procurementMethodType="requestForProposal",
    description="Tender award requirement responses",
)
class AwardReqResponseResource(BaseAwardReqResponseResource):
    pass
