# -*- coding: utf-8 -*-
from openprocurement.tender.core.procedure.views.bid_document import TenderBidDocumentResource
from openprocurement.api.utils import json_view
from openprocurement.tender.openua.procedure.models.document import PostDocument, PatchDocument, Document
from openprocurement.tender.openua.procedure.serializers import ConfidentialDocumentSerializer
from openprocurement.tender.core.procedure.validation import (
    validate_input_data,
    validate_patch_data,
    validate_item_owner,
    validate_view_bid_document,
    validate_bid_document_operation_period,
    unless_allowed_by_qualification_milestone,
    validate_upload_document,
    update_doc_fields_on_put_document,
    validate_data_model,
)
from openprocurement.tender.openua.procedure.validation import (
    validate_download_bid_document,
    validate_bid_document_in_tender_status,
    validate_bid_document_operation_in_award_status,
    validate_update_bid_document_confidentiality,
)
from cornice.resource import resource


@resource(
    name="aboveThresholdUA:Tender Bid Documents",
    collection_path="/tenders/{tender_id}/bids/{bid_id}/documents",
    path="/tenders/{tender_id}/bids/{bid_id}/documents/{document_id}",
    procurementMethodType="aboveThresholdUA",
    description="Tender UA bidder documents",
)
class BelowThresholdTenderBidDocumentResource(TenderBidDocumentResource):
    serializer_class = ConfidentialDocumentSerializer

    @json_view(
        validators=(
            validate_view_bid_document,
            validate_download_bid_document,
        ),
        permission="view_tender",
    )
    def get(self):
        return super().get()

    @json_view(
        validators=(
            validate_item_owner("bid"),
            validate_input_data(PostDocument, allow_bulk=True),

            unless_allowed_by_qualification_milestone(
                validate_bid_document_in_tender_status,
                validate_bid_document_operation_in_award_status,
            ),
            validate_bid_document_operation_period,
        ),
        permission="edit_bid",
    )
    def collection_post(self):
        return super(BelowThresholdTenderBidDocumentResource, self).collection_post()

    @json_view(
        validators=(
            validate_item_owner("bid"),
            validate_input_data(PostDocument),

            unless_allowed_by_qualification_milestone(
                validate_bid_document_in_tender_status,
                validate_bid_document_operation_in_award_status,
            ),
            validate_bid_document_operation_period,
            validate_update_bid_document_confidentiality,

            validate_upload_document,
            update_doc_fields_on_put_document,
            validate_data_model(Document),
        ),
        permission="edit_bid",
    )
    def put(self):
        return super(BelowThresholdTenderBidDocumentResource, self).put()

    @json_view(
        content_type="application/json",
        validators=(
            validate_item_owner("bid"),

            validate_input_data(PatchDocument),
            validate_patch_data(Document, item_name="document"),

            unless_allowed_by_qualification_milestone(
                validate_bid_document_in_tender_status,
                validate_bid_document_operation_in_award_status,
            ),
            validate_bid_document_operation_period,
            validate_update_bid_document_confidentiality,
        ),
        permission="edit_bid",
    )
    def patch(self):
        return super(BelowThresholdTenderBidDocumentResource, self).patch()