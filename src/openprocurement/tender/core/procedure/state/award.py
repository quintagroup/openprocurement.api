from datetime import timedelta

from openprocurement.api.constants import QUALIFICATION_AFTER_COMPLAINT_FROM
from openprocurement.api.context import get_now
from openprocurement.api.procedure.context import get_tender
from openprocurement.api.utils import raise_operation_error
from openprocurement.tender.core.procedure.context import get_request
from openprocurement.tender.core.procedure.contracting import add_contracts
from openprocurement.tender.core.procedure.models.contract import Contract
from openprocurement.tender.core.procedure.state.tender import TenderState
from openprocurement.tender.core.procedure.utils import tender_created_after
from openprocurement.tender.core.utils import calculate_tender_business_date


class AwardStateMixing:
    contract_model = Contract
    award_stand_still_time: timedelta
    award_stand_still_working_days: bool = True

    def validate_award_patch(self, before, after):
        tender = get_tender()
        self.validate_cancellation_blocks(self.request, tender, lot_id=before.get("lotID"))
        self.validate_action_with_exist_inspector_review_request(lot_id=before.get("lotID"))

    def award_on_patch(self, before, award):
        if before["status"] != award["status"]:
            self.invalidate_review_requests(lot_id=award.get("lotID", ""))
            self.award_status_up(before["status"], award["status"], award)
        elif award["status"] == "pending":
            pass  # allowing to update award in pending status
        else:
            raise_operation_error(self.request, f"Can't update award in current ({before['status']}) status")

    def award_status_up(self, before, after, award):
        assert before != after, "Statuses must be different"
        tender = get_tender()
        now = get_now().isoformat()

        if before == "pending" and after == "active":
            self.award_status_up_from_pending_to_active(award, tender)

        elif before == "active" and after == "cancelled":
            self.award_status_up_from_active_to_cancelled(award, tender)

        elif before == "pending" and after == "unsuccessful":
            self.award_status_up_from_pending_to_unsuccessful(award, tender)

        elif before == "unsuccessful" and after == "cancelled":
            self.award_status_up_from_unsuccessful_to_cancelled(award, tender)

        else:  # any other state transitions are forbidden
            raise_operation_error(self.request, f"Can't update award in current ({before}) status")

        # date updated when status updated
        award["date"] = now

    def award_status_up_from_pending_to_active(self, award, tender):
        if tender["config"]["hasAwardingOrder"] is False:
            self.check_active_awards(award, tender)
        award["complaintPeriod"] = {
            "startDate": get_now().isoformat(),
            "endDate": calculate_tender_business_date(
                get_now(),
                self.award_stand_still_time,
                get_tender(),
                self.award_stand_still_working_days,
            ).isoformat(),
        }
        self.request.validated["contracts_added"] = add_contracts(self.request, award)
        self.add_next_award()

    def award_status_up_from_active_to_cancelled(self, award, tender):
        self.set_award_complaints_cancelled(award)
        self.cancel_award(award)
        self.add_next_award()

    def award_status_up_from_pending_to_unsuccessful(self, award, tender):
        award["complaintPeriod"] = {
            "startDate": get_now().isoformat(),
            "endDate": calculate_tender_business_date(
                get_now(),
                self.award_stand_still_time,
                get_tender(),
                self.award_stand_still_working_days,
            ).isoformat(),
        }
        self.add_next_award()

    def award_status_up_from_unsuccessful_to_cancelled(self, award, tender):
        if not self.has_considered_award_complaints(award, tender):
            raise_operation_error(self.request, "Can't update award in current (unsuccessful) status")

        if tender["status"] == "active.awarded":
            # Go back to active.qualification status
            # because there is no active award anymore
            # for at least one of the lots
            tender["awardPeriod"].pop("endDate", None)
            self.get_change_tender_status_handler("active.qualification")(tender)

        if tender["config"]["hasAwardingOrder"]:
            # If hasAwardingOrder is True, then the current award should be found through all
            # tender awards/lot awards. Then the current award and next ones after it should be cancelled.
            # The new 'pending' award will be generated instead of current one.
            # And qualification will be continued starting from this new award.
            skip = True
            for i in tender.get("awards"):
                # skip all award before the context one
                if i["id"] == award["id"]:
                    skip = False
                if skip:
                    continue
                # skip different lot awards
                if i.get("lotID") != award.get("lotID"):
                    continue
                self.set_award_complaints_cancelled(i)
                self.cancel_award(i)

        self.set_award_complaints_cancelled(award)
        self.cancel_award(award)
        self.add_next_award()

    @staticmethod
    def is_available_to_cancel_award(award, include_awards_ids=None):
        if not include_awards_ids:
            include_awards_ids = []
        is_created_after = tender_created_after(QUALIFICATION_AFTER_COMPLAINT_FROM)
        return (
            is_created_after
            and award["status"] in ("pending", "active")
            or not is_created_after
            or award["id"] in include_awards_ids
        )

    @staticmethod
    def check_active_awards(current_award, tender):
        for award in tender.get("awards", []):
            if (
                award["id"] != current_award["id"]
                and award["status"] == "active"
                and award.get("lotID") == current_award.get("lotID")
            ):
                raise_operation_error(
                    get_request(),
                    f"Can't activate award as tender already has "
                    f"active award{' for this lot' if current_award.get('lotID') else ''}",
                    status=422,
                    name="awards",
                )

    def cancel_award(self, award, end_complaint_period=True):
        if end_complaint_period:
            now = get_now().isoformat()
            period = award.get("complaintPeriod")
            if period and (not period.get("endDate") or period["endDate"] > now):
                period["endDate"] = now
        self.set_object_status(award, "cancelled")
        self.request.validated["cancelled_contract_ids"] = self.set_award_contracts_cancelled(award)

    # helpers
    @classmethod
    def set_award_contracts_cancelled(cls, award):
        tender = get_tender()
        cancelled_contracts_ids = []
        for contract in tender.get("contracts", tuple()):
            if contract["awardID"] == award["id"]:
                if contract["status"] != "active":
                    cls.set_object_status(contract, "cancelled")
                    cancelled_contracts_ids.append(contract["id"])
                else:
                    raise_operation_error(get_request(), "Can't cancel award contract in active status")
        return cancelled_contracts_ids

    @classmethod
    def set_award_complaints_cancelled(cls, award):
        for complaint in award.get("complaints", ""):
            if complaint["status"] not in ("invalid", "resolved", "declined"):
                cls.set_object_status(complaint, "cancelled")
                complaint["cancellationReason"] = "cancelled"
                complaint["dateCanceled"] = get_now().isoformat()

    @staticmethod
    def has_considered_award_complaints(current_award, tender):
        return any(
            i["status"] in ("claim", "answered", "pending", "resolved") for i in current_award.get("complaints", "")
        )


# example use
class AwardState(AwardStateMixing, TenderState):
    pass
