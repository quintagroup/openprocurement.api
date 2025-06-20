from datetime import timedelta
from unittest.mock import patch

from openprocurement.api.utils import get_now
from openprocurement.tender.belowthreshold.tests.base import test_tender_below_lots
from openprocurement.tender.competitiveordering.tests.award import (
    BaseTenderCOContentWebTest,
    TenderAwardPendingResourceTestCase,
)
from openprocurement.tender.competitiveordering.tests.base import (
    test_tender_co_bids,
    test_tender_co_data,
)
from openprocurement.tender.core.tests.qualification_milestone import (
    TenderAwardMilestone24HMixin,
    TenderAwardMilestoneALPMixin,
)


@patch(
    "openprocurement.tender.competitiveordering.procedure.state.award.NEW_ARTICLE_17_CRITERIA_REQUIRED",
    get_now() + timedelta(days=1),
)
class TenderAwardMilestone24HTestCase(TenderAwardMilestone24HMixin, TenderAwardPendingResourceTestCase):
    initial_lots = test_tender_below_lots


class TenderAwardMilestoneALPTestCase(TenderAwardMilestoneALPMixin, BaseTenderCOContentWebTest):
    initial_data = test_tender_co_data
    initial_bids = test_tender_co_bids
    initial_lots = test_tender_below_lots * 2
