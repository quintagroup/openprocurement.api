# -*- coding: utf-8 -*-
from openprocurement.tender.core.views.bid_rr_evidence import BaseBidRequirementResponseEvidenceResource
from openprocurement.tender.core.utils import optendersresource


# @optendersresource(
#     name="simple.defense:Bid Requirement Response Evidence",
#     collection_path="/tenders/{tender_id}/bids/{bid_id}/requirement_responses/{requirement_response_id}/evidences",
#     path="/tenders/{tender_id}/bids/{bid_id}/requirement_responses/{requirement_response_id}/evidences/{evidence_id}",
#     procurementMethodType="simple.defense",
#     description="Tender simple.defense bidder evidences",
# )
class BidRequirementResponseEvidenceResource(
    BaseBidRequirementResponseEvidenceResource
):
    pass
