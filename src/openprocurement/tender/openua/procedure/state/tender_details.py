from openprocurement.tender.core.procedure.state.tender_details import TenderDetailsMixing
from openprocurement.tender.core.procedure.context import get_request, get_now
from openprocurement.tender.core.procedure.utils import dt_from_iso
from openprocurement.tender.openua.procedure.state.tender import OpenUATenderState
from openprocurement.tender.openua.constants import (
    TENDERING_EXTRA_PERIOD,
    ENQUIRY_PERIOD_TIME,
    ENQUIRY_STAND_STILL_TIME,
)
from openprocurement.tender.core.utils import (
    calculate_tender_business_date,
    calculate_clarif_business_date,
    check_auction_period,
)
from openprocurement.api.utils import raise_operation_error


class TenderDetailsState(TenderDetailsMixing, OpenUATenderState):

    tendering_period_extra = TENDERING_EXTRA_PERIOD
    tendering_period_extra_working_days = False

    enquiry_period_timedelta = - ENQUIRY_PERIOD_TIME
    enquiry_stand_still_timedelta = ENQUIRY_STAND_STILL_TIME

    def on_post(self, tender):
        super().on_post(tender)  # TenderDetailsMixing.on_post
        self.initialize_enquiry_period(tender)

    def on_patch(self, before, after):
        super().on_patch(before, after)  # TenderDetailsMixing.on_patch

        # validate items cpv group
        cpv_group_lists = {i["classification"]["id"][:3] for i in before.get("items")}
        for item in after.get("items", ""):
            cpv_group_lists.add(item["classification"]["id"][:3])
        if len(cpv_group_lists) != 1:
            raise_operation_error(
                get_request(),
                "Can't change classification",
                name="item"
            )

        # bid invalidation rules
        if before["status"] == "active.tendering":
            self.validate_tender_period_extension(after)
            self.invalidate_bids_data(after)
        elif after["status"] == "active.tendering":
            after["enquiryPeriod"]["invalidationDate"] = get_now().isoformat()

    def validate_tender_period_extension(self, tender):
        if "tenderPeriod" in tender and "endDate" in tender["tenderPeriod"]:
            # self.request.validated["tender"].tenderPeriod.import_data(data["tenderPeriod"])
            tendering_end = dt_from_iso(tender["tenderPeriod"]["endDate"])
            if calculate_tender_business_date(get_now(), self.tendering_period_extra, tender) > tendering_end:
                raise_operation_error(
                    get_request(),
                    "tenderPeriod should be extended by {0.days} {1}".format(
                        self.tendering_period_extra,
                        "working days" if self.tendering_period_extra_working_days else "days",
                    )
                )
            self.initialize_enquiry_period(tender)

    @staticmethod
    def initialize_enquiry_period(tender):
        tendering_end = dt_from_iso(tender["tenderPeriod"]["endDate"])
        end_date = calculate_tender_business_date(tendering_end, -ENQUIRY_PERIOD_TIME, tender)
        clarifications_until = calculate_clarif_business_date(end_date, ENQUIRY_STAND_STILL_TIME, tender, True)
        enquiry_period = tender.get("enquiryPeriod")
        tender["enquiryPeriod"] = dict(
            startDate=tender["tenderPeriod"]["startDate"],
            endDate=end_date.isoformat(),
            clarificationsUntil=clarifications_until.isoformat(),
        )
        invalidation_date = enquiry_period and enquiry_period.get("invalidationDate")
        if invalidation_date:
            tender["enquiryPeriod"]["invalidationDate"] = invalidation_date

    @classmethod
    def invalidate_bids_data(cls, tender):
        cls.check_auction_time(tender)
        tender["enquiryPeriod"]["invalidationDate"] = get_now().isoformat()
        for bid in tender.get("bids", ""):
            if bid.get("status") not in ("deleted", "draft"):
                bid["status"] = "invalid"

    @staticmethod
    def check_auction_time(tender):
        if check_auction_period(tender.get("auctionPeriod", {}), tender):
            del tender["auctionPeriod"]["startDate"]

        for lot in tender.get("lots", ""):
            if check_auction_period(lot.get("auctionPeriod", {}), tender):
                del lot["auctionPeriod"]["startDate"]
