from openprocurement.api.auth import ACCR_1, ACCR_2, ACCR_3, ACCR_4, ACCR_5
from openprocurement.api.utils import raise_operation_error
from openprocurement.tender.core.procedure.context import get_request
from openprocurement.tender.core.procedure.state.tender_details import (
    TenderDetailsMixing,
)
from openprocurement.tender.limited.procedure.state.tender import NegotiationTenderState


class ReportingTenderDetailsState(TenderDetailsMixing, NegotiationTenderState):
    tender_create_accreditations = (ACCR_1, ACCR_3, ACCR_5)
    tender_central_accreditations = (ACCR_5,)
    tender_edit_accreditations = (ACCR_2,)
    should_initialize_enquiry_period = False
    should_validate_related_lot_in_items = False

    contract_template_name_patch_statuses = []


class NegotiationTenderDetailsState(TenderDetailsMixing, NegotiationTenderState):
    tender_create_accreditations = (ACCR_3, ACCR_5)
    tender_central_accreditations = (ACCR_5,)
    tender_edit_accreditations = (ACCR_4,)
    should_initialize_enquiry_period = False
    should_validate_related_lot_in_items = True

    contract_template_name_patch_statuses = ("draft", "active")

    def on_patch(self, before, after):
        if before.get("awards"):
            raise_operation_error(
                get_request(),
                "Can't update tender when there is at least one award.",
            )
        super().on_patch(before, after)

    @staticmethod
    def set_lot_guarantee(tender: dict, data: dict) -> None:
        pass

    @staticmethod
    def set_lot_minimal_step(tender: dict, data: dict) -> None:
        pass


class NegotiationQuickTenderDetailsState(NegotiationTenderDetailsState):
    pass
