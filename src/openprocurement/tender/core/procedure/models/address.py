from openprocurement.tender.core.procedure.context import get_tender, get_now
from openprocurement.api.constants import VALIDATE_ADDRESS_FROM, COUNTRIES, UA_REGIONS
from openprocurement.api.utils import get_first_revision_date
from openprocurement.api.models import Model
from schematics.types import StringType
from schematics.validate import ValidationError


class PatchAddress(Model):
    streetAddress = StringType()
    locality = StringType()
    region = StringType()
    postalCode = StringType()
    countryName = StringType()
    countryName_en = StringType()
    countryName_ru = StringType()


class PostAddress(PatchAddress):
    countryName = StringType(required=True)

    def validate_countryName(self, _, value):
        if get_first_revision_date(get_tender(), default=get_now()) > VALIDATE_ADDRESS_FROM:
            if value not in COUNTRIES:
                raise ValidationError("field address:countryName not exist in countries catalog")

    def validate_region(self, data, value):
        if data["countryName"] == "Україна":
            if get_first_revision_date(get_tender(), default=get_now()) > VALIDATE_ADDRESS_FROM:
                if value and value not in UA_REGIONS:
                    raise ValidationError("field address:region not exist in ua_regions catalog")

    # @staticmethod
    # def skip_address_validation():
    #     tender = get_tender()  # TODO add methods for contracts, agreements, etc
    #     if tender["procurementMethodType"] in ('competitiveDialogueUA.stage2', 'competitiveDialogueEU.stage2',
    #                                            'closeFrameworkAgreementSelectionUA'):
    #         return True
    #
    #     if get_first_revision_date(tender, default=get_now()) < VALIDATE_ADDRESS_FROM:
    #         return True
    #     return False


class Address(PostAddress):
    pass