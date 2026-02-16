from itertools import chain

from schematics.exceptions import ValidationError
from schematics.types import StringType

from openprocurement.api.constants_env import PLAN_ADDRESS_KIND_REQUIRED_FROM
from openprocurement.api.procedure.models.base import Model
from openprocurement.api.procedure.models.organization import CommonOrganization
from openprocurement.api.procedure.models.period import Period
from openprocurement.api.procedure.types import ModelType
from openprocurement.api.procedure.utils import is_obj_const_active
from openprocurement.planning.api.constants import PROCEDURES
from openprocurement.planning.api.procedure.context import get_plan


class PlanTender(Model):
    procurementMethod = StringType(choices=list(PROCEDURES.keys()), default="")
    procurementMethodType = StringType(choices=list(chain(*PROCEDURES.values())), default="")
    tenderPeriod = ModelType(Period, required=True)

    def validate_procurementMethodType(self, tender, procurement_method_type):
        plan = get_plan()
        method = tender.get("procurementMethod")
        if is_obj_const_active(plan, PLAN_ADDRESS_KIND_REQUIRED_FROM) and method == "":
            procurement_method_types = ("centralizedProcurement",)
        else:
            procurement_method_types = PROCEDURES[method]
        if procurement_method_type not in procurement_method_types:
            raise ValidationError("Value must be one of {!r}.".format(procurement_method_types))


class PreValidationTender(Model):
    """
    Only required fields for plan/tender validation with non strict mode
    Actual tender validation will be handled by dedicated tender models in tender view
    """

    procurementMethod = StringType()
    procurementMethodType = StringType()
    procuringEntity = ModelType(CommonOrganization, required=True, strict=False)
