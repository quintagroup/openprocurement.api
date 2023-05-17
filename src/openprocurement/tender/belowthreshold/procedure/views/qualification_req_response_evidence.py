from cornice.resource import resource

from openprocurement.tender.core.procedure.views.qualification_req_response_evidence import (
    QualificationReqResponseEvidenceResource as BaseReqResponseEvidenceResource,
)


@resource(
    name="belowThreshold:Qualification Requirement Response Evidence",
    collection_path="/tenders/{tender_id}/qualifications/{qualification_id}"
                    "/requirement_responses/{requirement_response_id}/evidences",
    path="/tenders/{tender_id}/qualifications/{qualification_id}/"
         "requirement_responses/{requirement_response_id}/evidences/{evidence_id}",
    procurementMethodType="belowThreshold",
    description="belowThreshold qualification evidences",
)
class QualificationReqResponseResource(BaseReqResponseEvidenceResource):
    pass
