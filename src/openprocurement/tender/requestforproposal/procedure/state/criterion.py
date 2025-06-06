from pyramid.request import Request

from openprocurement.tender.core.procedure.state.criterion import CriterionStateMixin
from openprocurement.tender.core.procedure.validation import (
    base_validate_operation_ecriteria_objects,
)
from openprocurement.tender.requestforproposal.procedure.state.tender import (
    RequestForProposalTenderState,
)


class BaseRequestForProposalCriterionStateMixin:
    request: Request

    def _validate_operation_criterion_in_tender_status(self) -> None:
        valid_statuses = ["draft", "active.enquiries"]
        base_validate_operation_ecriteria_objects(self.request, valid_statuses)


class RequestForProposalCriterionStateMixin(BaseRequestForProposalCriterionStateMixin, CriterionStateMixin):
    def validate_on_patch(self, before: dict, after: dict) -> None:
        self._validate_operation_criterion_in_tender_status()
        self._validate_criterion_uniq_patch(before, after)
        self.validate_action_with_exist_inspector_review_request()


class RequestForProposalCriterionState(RequestForProposalCriterionStateMixin, RequestForProposalTenderState):
    pass
