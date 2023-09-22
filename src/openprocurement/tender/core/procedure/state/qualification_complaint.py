from openprocurement.tender.core.procedure.utils import is_item_owner, dt_from_iso
from openprocurement.tender.core.procedure.state.complaint import ComplaintState
from openprocurement.tender.core.procedure.context import get_tender
from openprocurement.api.context import get_now
from openprocurement.api.validation import OPERATIONS
from logging import getLogger
from openprocurement.api.utils import raise_operation_error


LOGGER = getLogger(__name__)


class QualificationComplaintState(ComplaintState):
    create_allowed_tender_statuses = ("active.pre-qualification.stand-still",)
    update_allowed_tender_statuses = ("active.pre-qualification", "active.pre-qualification.stand-still")

    def complaint_on_post(self, complaint):
        request = self.request
        if lot_id := request.validated["qualification"].get("lotID"):
            complaint["relatedLot"] = lot_id

        if request.authenticated_role == "bid_owner":
            complaint["bid_id"] = self.request.validated["bid"]["id"]
        super().complaint_on_post(complaint)
        
    def validate_complaint_on_post(self, complaint):
        tender = get_tender()
        if not any(  # should be an "active" or "unsuccessful" bidder
            is_item_owner(self.request, bid)
            for bid in tender.get("bids", "")
            if bid.get("status") in ("active", "unsuccessful")
        ):
            raise_operation_error(self.request, "Can add complaint only on unsuccessful or active bid")

        super().validate_complaint_on_post(complaint)

    def validate_tender_in_complaint_period(self, tender):
        period = tender.get("qualificationPeriod")
        period_start = period.get("startDate")
        period_end = period.get("endDate")
        now = get_now()
        if period_start and now < dt_from_iso(period_start) or period_end and now > dt_from_iso(period_end):
            raise_operation_error(self.request, "Can add complaint only in qualificationPeriod")

    def validate_lot_status(self):
        tender = get_tender()
        qualification = self.request.validated["qualification"]
        lot_id = qualification.get("lotID")
        if lot_id and any(
            lot.get("status") != "active"
            for lot in tender.get("lots", [])
            if lot["id"] == lot_id
        ):
            operation = OPERATIONS.get(self.request.method)
            raise_operation_error(self.request, f"Can {operation} complaint only in active lot status")

    def get_related_lot_obj(self, tender, complaint):
        qualification = self.request.validated["qualification"]
        if related_lot := qualification.get("lotID"):
            for lot in tender.get("lots"):
                if lot["id"] == related_lot:
                    return lot

    def reviewers_satisfied_handler(self, complaint):
        super().reviewers_satisfied_handler(complaint)
        tender = get_tender()
        del tender["qualificationPeriod"]["endDate"]
        self.get_change_tender_status_handler("active.pre-qualification")(tender)