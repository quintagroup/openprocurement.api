from cornice.resource import resource

from openprocurement.tender.core.procedure.views.award_complaint_post import (
    BaseAwardComplaintPostResource,
)
from openprocurement.tender.open.constants import ABOVE_THRESHOLD


@resource(
    name=f"{ABOVE_THRESHOLD}:Tender Award Complaint Posts",
    collection_path="/tenders/{tender_id}/awards/{award_id}/complaints/{complaint_id}/posts",
    path="/tenders/{tender_id}/awards/{award_id}/complaints/{complaint_id}/posts/{post_id}",
    procurementMethodType=ABOVE_THRESHOLD,
    description="Tender award complaint posts",
)
class OpenAwardComplaintPostResource(BaseAwardComplaintPostResource):
    pass
