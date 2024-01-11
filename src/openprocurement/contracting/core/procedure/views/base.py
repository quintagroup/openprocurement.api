from pyramid.security import Allow, Everyone, ALL_PERMISSIONS

from openprocurement.api.procedure.context import init_object
from openprocurement.api.views.base import BaseResource
from openprocurement.api.utils import get_tender_by_id
from openprocurement.contracting.core.procedure.serializers.config import ContractConfigSerializer
from openprocurement.contracting.core.procedure.state.contract import BaseContractState
from openprocurement.tender.core.procedure.serializers.config import TenderConfigSerializer


class ContractBaseResource(BaseResource):

    state_class = BaseContractState

    def __acl__(self):
        acl = [
            (Allow, Everyone, "view_contract"),
            (Allow, Everyone, "view_listing"),
            (Allow, "g:contracting", "create_contract"),
            (Allow, "g:brokers", "edit_contract"),
            (Allow, "g:Administrator", "edit_contract"),

            (Allow, "g:brokers", "upload_contract_documents"),
            (Allow, "g:brokers", "edit_contract_documents"),

            (Allow, "g:bots", "edit_contract_transactions"),
            (Allow, "g:brokers", "edit_contract_transactions"),

            (Allow, "g:admins", ALL_PERMISSIONS),    # some tests use this, idk why
        ]
        return acl

    def __init__(self, request, context=None):
        super().__init__(request, context)

        self.state = self.state_class(request)

        # https://github.com/Cornices/cornice/issues/479#issuecomment-388407385
        # init is called twice (with and without context), thanks to cornice.

        if not context:

            match_dict = request.matchdict
            if match_dict and match_dict.get("contract_id"):

                contract_doc = request.contract_doc
                init_object("contract", contract_doc, config_serializer=ContractConfigSerializer)

                if "buyer" in contract_doc:
                    tender_doc = get_tender_by_id(request, contract_doc["tender_id"])
                    init_object("tender", tender_doc, config_serializer=TenderConfigSerializer)
                    award = [
                        award for award in tender_doc.get("awards", [])
                        if award.get("id") == contract_doc.get("awardID")
                    ][0]
                    request.validated["award"] = award
