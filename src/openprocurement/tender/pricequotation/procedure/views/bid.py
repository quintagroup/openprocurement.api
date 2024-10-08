from logging import getLogger

from cornice.resource import resource

from openprocurement.api.auth import ACCR_2
from openprocurement.api.procedure.validation import (
    unless_administrator,
    validate_accreditation_level,
    validate_data_documents,
    validate_input_data,
    validate_item_owner,
    validate_patch_data_simple,
)
from openprocurement.api.utils import context_unpack, json_view
from openprocurement.tender.belowthreshold.procedure.views.bid import TenderBidResource
from openprocurement.tender.core.procedure.models.bid import (
    filter_administrator_bid_update,
)
from openprocurement.tender.core.procedure.state.bid import BidState
from openprocurement.tender.core.procedure.utils import save_tender
from openprocurement.tender.core.procedure.validation import (
    validate_bid_operation_not_in_tendering,
    validate_bid_operation_period,
    validate_update_deleted_bid,
)
from openprocurement.tender.pricequotation.constants import PQ
from openprocurement.tender.pricequotation.procedure.models.bid import (
    Bid,
    PatchBid,
    PostBid,
)

LOGGER = getLogger(__name__)


@resource(
    name="{}:Tender Bids".format(PQ),
    collection_path="/tenders/{tender_id}/bids",
    path="/tenders/{tender_id}/bids/{bid_id}",
    procurementMethodType=PQ,
    description="Tender bids",
)
class TenderBidResource(TenderBidResource):
    state_class = BidState

    @json_view(
        content_type="application/json",
        permission="create_bid",
        validators=(
            validate_accreditation_level(
                levels=(ACCR_2,),
                item="bid",
                operation="creation",
            ),
            validate_bid_operation_not_in_tendering,
            validate_bid_operation_period,
            validate_input_data(PostBid),
            validate_data_documents(route_key="bid_id", uid_key="id"),
        ),
    )
    def collection_post(self):
        return super().collection_post()

    @json_view(
        content_type="application/json",
        permission="edit_bid",
        validators=(
            unless_administrator(validate_item_owner("bid")),
            validate_update_deleted_bid,
            validate_input_data(
                PatchBid,
                filters=(filter_administrator_bid_update,),
                none_means_remove=True,
            ),
            validate_patch_data_simple(Bid, item_name="bid"),
            validate_bid_operation_not_in_tendering,
            validate_bid_operation_period,
        ),
    )
    def patch(self):
        return super().patch()

    @json_view(
        permission="edit_bid",
        validators=(
            validate_item_owner("bid"),
            validate_bid_operation_not_in_tendering,
            validate_bid_operation_period,
        ),
    )
    def delete(self):
        """
        Cancelling the proposal.
        """
        bid = self.request.validated["bid"]
        bid["status"] = "deleted"

        if save_tender(self.request, modified=False):
            self.LOGGER.info(
                f"Deleted tender bid {bid['id']}",
                extra=context_unpack(self.request, {"MESSAGE_ID": "tender_bid_delete"}),
            )
            return {"data": self.serializer_class(bid).data}
