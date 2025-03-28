from cornice.resource import resource

from openprocurement.tender.cfaua.procedure.state.complaint_post import (
    CFAUAComplaintPostState,
)
from openprocurement.tender.core.procedure.views.award_complaint_post import (
    BaseAwardComplaintPostResource,
)


@resource(
    name="closeFrameworkAgreementUA:Tender Award Complaint Posts",
    collection_path="/tenders/{tender_id}/awards/{award_id}/complaints/{complaint_id}/posts",
    path="/tenders/{tender_id}/awards/{award_id}/complaints/{complaint_id}/posts/{post_id}",
    procurementMethodType="closeFrameworkAgreementUA",
    description="Tender award complaint posts",
)
class CFAUAAwardComplaintPostResource(BaseAwardComplaintPostResource):
    state_class = CFAUAComplaintPostState
