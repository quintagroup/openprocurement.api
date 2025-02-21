from datetime import datetime
from unittest.mock import Mock

import pytest

from openprocurement.api.constants import AUCTION_DAY_END, AUCTION_DAY_START
from openprocurement.api.context import set_now
from openprocurement.tender.core.procedure.state.auction import ShouldStartAfterMixing


@pytest.mark.parametrize(
    "now,tender_period_end,expected_should_start_after,expected_auction_date",
    (
        (
            "2025-01-10T09:00:00+02:00",
            "2025-01-17T00:00:00+02:00",
            "2025-01-17T00:00:00+02:00",
            "2025-01-17",
        ),
        (
            "2025-01-10T09:00:00+02:00",
            "2025-01-18T00:00:04.857084+02:00",
            "2025-01-19T00:00:00+02:00",
            "2025-01-20",
        ),
    ),
)
def test_validation_before_release(
    now: str,
    tender_period_end: str,
    expected_should_start_after: str,
    expected_auction_date: str,
):
    set_now(datetime.fromisoformat(now))

    auction_period = {}
    tender = {
        "config": {
            "hasAuction": True,
            "hasPrequalification": False,
        },
        "status": "active.tendering",  # active.auction active.pre-qualification.stand-still
        "lots": [{"id": "1", "status": "active", "auctionPeriod": auction_period}],
        "tenderPeriod": {
            "endDate": tender_period_end,
        },
    }

    state_instance = ShouldStartAfterMixing()
    state_instance.count_lot_bids_number = Mock(return_value=3)

    state_instance.calc_auction_periods(tender)

    assert auction_period["shouldStartAfter"] == expected_should_start_after
    assert auction_period["startDate"].startswith(expected_auction_date)

    auction_start = datetime.fromisoformat(auction_period["startDate"])
    assert AUCTION_DAY_START <= auction_start.time() < AUCTION_DAY_END
