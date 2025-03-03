from openprocurement.tender.core.procedure.state.contract import ContractStateMixing
from openprocurement.tender.requestforproposal.procedure.state.tender import (
    RequestForProposalTenderState,
)


class RequestForProposalContractState(ContractStateMixing, RequestForProposalTenderState):
    def check_tender_status_method(self) -> None:
        super().check_tender_status_method()
        tender = self.request.validated["tender"]
        self.check_ignored_claim(tender)

    def contract_on_patch(self, before: dict, after: dict):
        self.validate_contract_items(before, after)
        self.validate_contract_signing(before, after)
        super().contract_on_patch(before, after)

    def _validate_contract_signing_with_pending_complaints(self, award: dict):
        pass
