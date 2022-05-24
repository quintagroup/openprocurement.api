from openprocurement.tender.openua.procedure.state.tender_details import TenderDetailsState
from openprocurement.tender.openuadefense.constants import TENDERING_EXTRA_PERIOD


class DefenseTenderDetailsState(TenderDetailsState):
    tendering_period_extra = TENDERING_EXTRA_PERIOD
    tendering_period_extra_working_days = True

    @staticmethod
    def validate_tender_exclusion_criteria(before, after):
        pass

    @staticmethod
    def validate_tender_language_criteria(before, after):
        pass
