from openprocurement.api.auth import AccreditationLevel
from openprocurement.api.procedure.context import get_tender
from openprocurement.tender.core.procedure.state.tender_details import (
    TenderDetailsMixing,
)
from openprocurement.tender.requestforproposal.constants import TENDERING_EXTRA_PERIOD
from openprocurement.tender.requestforproposal.procedure.models.tender import (
    PatchActiveTender,
    PatchDraftTender,
    PatchTender,
)
from openprocurement.tender.requestforproposal.procedure.state.tender import (
    RequestForProposalTenderState,
)


class RequestForProposalTenderDetailsMixing(TenderDetailsMixing):
    tender_create_accreditations = (AccreditationLevel.ACCR_1, AccreditationLevel.ACCR_5)
    tender_central_accreditations = (AccreditationLevel.ACCR_5,)
    tender_edit_accreditations = (AccreditationLevel.ACCR_2,)

    tendering_period_extra_working_days = False
    tendering_period_extra = TENDERING_EXTRA_PERIOD
    should_validate_notice_doc_required = True
    enquiry_before_tendering = True
    contract_template_required = False
    contract_template_name_patch_statuses = ("draft", "active.enquiries", "active.tendering")
    qualification_complain_duration_working_days = True

    def get_patch_data_model(self):
        tender = get_tender()
        if tender.get("status", "") == "active.tendering":
            return PatchActiveTender
        elif tender.get("status", "") in ("draft", "active.enquiries"):
            return PatchDraftTender
        return PatchTender


class RequestForProposalTenderDetailsState(RequestForProposalTenderDetailsMixing, RequestForProposalTenderState):
    pass
