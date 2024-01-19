from openprocurement.tender.core.procedure.views.contract_document import TenderContractDocumentResource
from openprocurement.api.utils import json_view
from openprocurement.tender.core.procedure.models.document import PostDocument, PatchDocument, Document
from openprocurement.tender.core.procedure.validation import (
    validate_contract_supplier,

    validate_role_for_contract_document_operation,
    validate_contract_document_status,
    validate_forbid_contract_action_after_date,
)
from openprocurement.api.procedure.validation import (
    validate_patch_data,
    validate_data_model,
    validate_input_data,
    unless_admins, unless_bots, validate_upload_document, update_doc_fields_on_put_document,
)
from cornice.resource import resource


@resource(
    name="belowThreshold:Tender Contract Documents",
    collection_path="/tenders/{tender_id}/contracts/{contract_id}/documents",
    path="/tenders/{tender_id}/contracts/{contract_id}/documents/{document_id}",
    procurementMethodType="belowThreshold",
    description="Tender contract documents",
)
class BelowThresholdContractDocumentResource(TenderContractDocumentResource):
    @json_view(
        validators=(
                validate_forbid_contract_action_after_date("contract document"),
                unless_bots(unless_admins(validate_contract_supplier())),
                validate_input_data(PostDocument, allow_bulk=True),
                validate_role_for_contract_document_operation,
                validate_contract_document_status(operation="add"),
        ),
        permission="upload_contract_documents",
    )
    def collection_post(self):
        return super().collection_post()

    @json_view(
        validators=(
                unless_bots(unless_admins(validate_contract_supplier())),
                validate_input_data(PostDocument),
                validate_role_for_contract_document_operation,
                validate_contract_document_status(operation="update"),

                update_doc_fields_on_put_document,
                validate_upload_document,
                validate_data_model(Document),
        ),
        permission="upload_contract_documents",
    )
    def put(self):
        return super().put()

    @json_view(
        validators=(
                unless_bots(unless_admins(validate_contract_supplier())),
                validate_input_data(PatchDocument, none_means_remove=True),
                validate_patch_data(Document, item_name="document"),
                validate_role_for_contract_document_operation,
                validate_contract_document_status(operation="update"),
        ),
        permission="upload_contract_documents",
    )
    def patch(self):
        return super().patch()
