from openprocurement.api.utils import json_view
from openprocurement.tender.core.procedure.views.award import resolve_award
from openprocurement.tender.core.procedure.views.document import BaseDocumentResource, resolve_document
from pyramid.security import Allow, Everyone
from openprocurement.tender.core.procedure.validation import get_award_document_role


class BaseAwardDocumentResource(BaseDocumentResource):
    item_name = "award"

    def __acl__(self):
        acl = [
            (Allow, Everyone, "view_tender"),
            (Allow, "g:brokers", "upload_award_documents"),
            (Allow, "g:brokers", "edit_award_documents"),

            (Allow, "g:admins", "upload_award_documents"),
            (Allow, "g:admins", "edit_award_documents"),

            (Allow, "g:bots", "upload_award_documents"),
        ]
        return acl

    def __init__(self, request, context=None):
        super().__init__(request, context)  # resolve tender
        resolve_award(request)
        resolve_document(request, self.item_name, self.container)

    def set_doc_author(self, doc):
        doc["author"] = get_award_document_role(self.request)
        return doc

    @json_view(permission="view_tender")
    def collection_get(self):
        return super(BaseAwardDocumentResource, self).collection_get()

    @json_view(permission="view_tender")
    def get(self):
        return super(BaseAwardDocumentResource, self).get()
