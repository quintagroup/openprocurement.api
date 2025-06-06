from cornice.resource import resource

from openprocurement.tender.core.procedure.views.auction import (
    TenderAuctionResource as BaseTenderAuctionResource,
)
from openprocurement.tender.open.constants import ABOVE_THRESHOLD
from openprocurement.tender.open.procedure.state.tender import OpenTenderState


@resource(
    name=f"{ABOVE_THRESHOLD}:Tender Auction",
    collection_path="/tenders/{tender_id}/auction",
    path="/tenders/{tender_id}/auction/{auction_lot_id}",
    procurementMethodType=ABOVE_THRESHOLD,
    description="Tender auction data",
)
class TenderAuctionResource(BaseTenderAuctionResource):
    state_class = OpenTenderState
