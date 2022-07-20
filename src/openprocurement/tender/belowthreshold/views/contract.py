# -*- coding: utf-8 -*-
from openprocurement.api.utils import (
    get_now,
    json_view,
    context_unpack,
    raise_operation_error,
)
from openprocurement.api.views.base import BaseResource
from openprocurement.tender.core.utils import (
    save_tender,
    optendersresource,
    apply_patch,
)
from openprocurement.tender.core.validation import (
    validate_contract_data,
    validate_contract_signing,
    validate_patch_contract_data,
    validate_update_contract_value,
    validate_update_contract_only_for_active_lots,
    validate_contract_operation_not_in_allowed_status,
    validate_update_contract_value_with_award,
    validate_update_contract_value_amount,
    validate_update_contract_value_net_required,
    validate_update_contract_status_by_supplier,
    validate_activate_contract,
    validate_update_contract_status,
)
from openprocurement.tender.belowthreshold.utils import check_tender_status


# @optendersresource(
#     name="belowThreshold:Tender Contracts",
#     collection_path="/tenders/{tender_id}/contracts",
#     path="/tenders/{tender_id}/contracts/{contract_id}",
#     procurementMethodType="belowThreshold",
#     description="Tender contracts",
# )
class TenderAwardContractResource(BaseResource):
    @staticmethod
    def check_tender_status_method(request):
        return check_tender_status(request)

    @json_view(
        content_type="application/json",
        permission="create_contract",
        validators=(
            validate_contract_data,
            validate_contract_operation_not_in_allowed_status,
        ),
    )
    def collection_post(self):
        """
        Post a contract for award
        """
        tender = self.request.validated["tender"]
        contract = self.request.validated["contract"]
        tender.contracts.append(contract)
        if save_tender(self.request):
            self.LOGGER.info(
                "Created tender contract {}".format(contract.id),
                extra=context_unpack(
                    self.request, {"MESSAGE_ID": "tender_contract_create"}, {"contract_id": contract.id}
                ),
            )
            self.request.response.status = 201
            self.request.response.headers["Location"] = self.request.route_url(
                "{}:Tender Contracts".format(tender.procurementMethodType),
                tender_id=tender.id,
                contract_id=contract["id"],
            )
            return {"data": contract.serialize()}

    @json_view(permission="view_tender")
    def collection_get(self):
        """
        List contracts for award
        """
        return {"data": [i.serialize() for i in self.request.context.contracts]}

    @json_view(permission="view_tender")
    def get(self):
        """
        Retrieving the contract for award
        """
        return {"data": self.request.validated["contract"].serialize()}

    @json_view(
        content_type="application/json",
        permission="edit_contract",
        validators=(
            validate_patch_contract_data,
            validate_contract_operation_not_in_allowed_status,
            validate_update_contract_only_for_active_lots,
            validate_update_contract_status_by_supplier,
            validate_update_contract_status,
            validate_update_contract_value,
            validate_contract_signing,
            validate_update_contract_value_net_required,
            validate_update_contract_value_with_award,
            validate_update_contract_value_amount,
        ),
    )
    def patch(self):
        """
        Update of contract
        """
        prev_status = self.request.context.status
        apply_patch(self.request, save=False, src=self.request.context.serialize())
        if prev_status != "active" and self.request.context.status == "active":
            validate_activate_contract(self.request)
        if self.request.context.status == "active" and not self.request.context.dateSigned:
            self.request.context.dateSigned = get_now()
        self.check_tender_status_method(self.request)
        if save_tender(self.request):
            self.LOGGER.info(
                "Updated tender contract {}".format(self.request.context.id),
                extra=context_unpack(self.request, {"MESSAGE_ID": "tender_contract_patch"}),
            )
            return {"data": self.request.context.serialize()}
