# -*- coding: utf-8 -*-
import unittest
from copy import deepcopy

from openprocurement.api.tests.base import snitch

from openprocurement.tender.belowthreshold.tests.base import test_features_tender_data, test_lots
from openprocurement.tender.belowthreshold.tests.auction import (
    TenderAuctionResourceTestMixin,
    TenderMultipleLotAuctionResourceTestMixin,
)
from openprocurement.tender.belowthreshold.tests.auction_blanks import (
    # TenderSameValueAuctionResourceTest
    post_tender_auction_not_changed,
    post_tender_auction_reversed,
    # TenderMultipleLotAuctionResourceTest
    patch_tender_lots_auction,
    # TenderFeaturesAuctionResourceTest
    get_tender_auction_feature,
    post_tender_auction_feature,
    # TenderFeaturesMultilotAuctionResourceTest
    get_tender_lots_auction_features,
    post_tender_lots_auction_features,
)

from openprocurement.tender.open.tests.base import (
    BaseTenderUAContentWebTest,
    test_features_tender_ua_data,
    test_bids,
)


class TenderAuctionResourceTest(BaseTenderUAContentWebTest, TenderAuctionResourceTestMixin):
    docservice = True
    initial_status = "active.tendering"
    initial_bids = test_bids


class TenderSameValueAuctionResourceTest(BaseTenderUAContentWebTest):
    docservice = True
    initial_status = "active.auction"
    initial_bids = [
        test_bids[0]
        for i in range(3)
    ]

    test_post_tender_auction_not_changed = snitch(post_tender_auction_not_changed)
    test_post_tender_auction_reversed = snitch(post_tender_auction_reversed)


class TenderMultipleLotAuctionResourceTest(TenderMultipleLotAuctionResourceTestMixin, TenderAuctionResourceTest):
    docservice = True
    initial_lots = 2 * test_lots

    test_patch_tender_auction = snitch(patch_tender_lots_auction)


class TenderFeaturesAuctionResourceTest(BaseTenderUAContentWebTest):
    docservice = True
    initial_data = test_features_tender_ua_data
    initial_status = "active.tendering"

    test_get_tender_auction = snitch(get_tender_auction_feature)
    test_post_tender_auction = snitch(post_tender_auction_feature)

    def setUp(self):
        self.initial_bids = deepcopy(test_bids[:2])
        self.initial_bids[0]["parameters"] = [{"code": i["code"], "value": 0.1} for i in test_features_tender_data["features"]]
        self.initial_bids[1]["parameters"] = [{"code": i["code"], "value": 0.15} for i in test_features_tender_data["features"]]
        super(TenderFeaturesAuctionResourceTest, self).setUp()


class TenderFeaturesMultilotAuctionResourceTest(
    TenderMultipleLotAuctionResourceTestMixin, TenderFeaturesAuctionResourceTest
):
    docservice = True
    initial_lots = test_lots * 2
    test_get_tender_auction = snitch(get_tender_lots_auction_features)
    test_post_tender_auction = snitch(post_tender_lots_auction_features)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TenderAuctionResourceTest))
    suite.addTest(unittest.makeSuite(TenderSameValueAuctionResourceTest))
    suite.addTest(unittest.makeSuite(TenderFeaturesAuctionResourceTest))
    suite.addTest(unittest.makeSuite(TenderFeaturesMultilotAuctionResourceTest))
    return suite


if __name__ == "__main__":
    unittest.main(defaultTest="suite")