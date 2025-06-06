from copy import deepcopy
from datetime import timedelta

from freezegun import freeze_time

from openprocurement.api.procedure.utils import parse_date
from openprocurement.api.utils import get_now
from openprocurement.tender.belowthreshold.tests.base import (
    test_tender_below_author,
    test_tender_below_complaint,
)
from openprocurement.tender.competitiveordering.constants import COMPETITIVE_ORDERING
from openprocurement.tender.core.tests.utils import change_auth


def switch_to_unsuccessful_lot_0bid(self):
    self.set_status("active.auction", {"status": self.initial_status})
    response = self.check_chronograph()
    self.assertEqual(response.json["data"]["status"], "unsuccessful")
    self.assertEqual({i["status"] for i in response.json["data"]["lots"]}, {"unsuccessful"})


def set_auction_period_lot_0bid(self):
    start_date = "9999-01-01T00:00:00+00:00"
    data = {"data": {"lots": [{"auctionPeriod": {"startDate": start_date}} for i in self.initial_lots]}}
    response = self.check_chronograph(data)
    self.assertEqual(response.json["data"]["lots"][0]["auctionPeriod"]["startDate"], start_date)

    response = self.check_chronograph({"data": {"lots": [{"auctionPeriod": None}]}})
    self.assertEqual(response.json["data"]["lots"][0]["auctionPeriod"]["startDate"], start_date)


def not_switch_to_unsuccessful_lot_1bid(self):
    self.set_status("active.auction", {"status": self.initial_status})
    response = self.check_chronograph()
    self.assertEqual(response.json["data"]["status"], "active.qualification")
    self.assertEqual(len(response.json["data"]["awards"]), 1)


def not_switch_to_unsuccessful_2lot_1bid(self):
    self.set_status("active.auction", {"status": self.initial_status})
    response = self.check_chronograph()
    self.assertEqual(response.json["data"]["status"], "active.qualification")
    self.assertEqual(len(response.json["data"]["awards"]), 2)


def switch_to_auction_lot(self):
    self.set_status("active.auction", {"status": self.initial_status})
    response = self.check_chronograph()
    self.assertEqual(response.json["data"]["status"], "active.auction")


def switch_to_unsuccessful_lot(self):
    self.set_status("active.auction", {"status": self.initial_status})
    response = self.check_chronograph()

    with change_auth(self.app, ("Basic", ("auction", ""))):
        response = self.app.get("/tenders/{}/auction".format(self.tender_id))
        auction_bids_data = response.json["data"]["bids"]
        for lot in response.json["data"]["lots"]:
            response = self.app.post_json(
                "/tenders/{}/auction/{}".format(self.tender_id, lot["id"]),
                {
                    "data": {
                        "bids": [
                            {"id": b["id"], "lotValues": [{"relatedLot": l["relatedLot"]} for l in b["lotValues"]]}
                            for b in auction_bids_data
                        ]
                    }
                },
            )
            self.assertEqual(response.status, "200 OK")

    self.assertEqual(response.json["data"]["status"], "active.qualification")

    response = self.app.get("/tenders/{}/awards".format(self.tender_id))
    while any(i["status"] == "pending" for i in response.json["data"]):
        award_id = [i["id"] for i in response.json["data"] if i["status"] == "pending"][0]
        self.add_sign_doc(self.tender_id, self.tender_token, docs_url=f"/awards/{award_id}/documents")
        unsuccessful_data = {"status": "unsuccessful", "qualified": False}
        if self.initial_data["procurementMethodType"] != COMPETITIVE_ORDERING:
            unsuccessful_data.update({"eligible": False})
        self.app.patch_json(
            "/tenders/{}/awards/{}?acc_token={}".format(self.tender_id, award_id, self.tender_token),
            {"data": unsuccessful_data},
        )
        response = self.app.get("/tenders/{}/awards".format(self.tender_id))

    tender = self.mongodb.tenders.get(self.tender_id)
    for i in tender.get("awards", []):
        i["complaintPeriod"]["endDate"] = i["complaintPeriod"]["startDate"]
    self.mongodb.tenders.save(tender)

    response = self.check_chronograph()
    self.assertEqual(response.json["data"]["status"], "unsuccessful")


def set_auction_period_lot(self):
    response = self.check_chronograph()
    self.assertEqual(response.json["data"]["status"], "active.tendering")
    item = response.json["data"]["lots"][0]
    self.assertIn("auctionPeriod", item)
    self.assertIn("shouldStartAfter", item["auctionPeriod"])
    self.assertGreaterEqual(item["auctionPeriod"]["shouldStartAfter"], response.json["data"]["tenderPeriod"]["endDate"])
    self.assertEqual(
        parse_date(response.json["data"]["next_check"]), parse_date(response.json["data"]["tenderPeriod"]["endDate"])
    )

    start_date = "9999-01-01T00:00:00+00:00"
    data = {"data": {"lots": [{"auctionPeriod": {"startDate": start_date}} for i in self.initial_lots]}}
    response = self.check_chronograph(data)
    item = response.json["data"]["lots"][0]
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(item["auctionPeriod"]["startDate"], start_date)


def set_auction_period_for_satisfied_complaint(self):
    freezer = freeze_time()
    frozen_datetime = freezer.start()

    self.app.authorization = ("Basic", ("broker", ""))

    # create complaint
    complaint_data = deepcopy(test_tender_below_complaint)
    complaint_data["author"] = deepcopy(test_tender_below_author)
    response = self.app.post_json(
        "/tenders/{}/complaints".format(self.tender_id),
        {"data": complaint_data},
    )
    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(response.json["data"]["status"], "draft")

    complaint = response.json["data"]

    self.app.authorization = ("Basic", ("bot", ""))

    # set complaint to pending
    response = self.app.patch_json(
        "/tenders/{}/complaints/{}".format(self.tender_id, complaint["id"]),
        {"data": {"status": "pending"}},
    )
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(response.json["data"]["status"], "pending")

    self.app.authorization = ("Basic", ("reviewer", ""))

    # set complaint to accepted
    response = self.app.patch_json(
        "/tenders/{}/complaints/{}".format(self.tender_id, complaint["id"]),
        {
            "data": {
                "status": "accepted",
                "decision": "complaint decision",
                "reviewDate": get_now().isoformat(),
                "reviewPlace": "some",
            }
        },
    )
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(response.json["data"]["status"], "accepted")

    # get tender
    response = self.app.get("/tenders/{}".format(self.tender_id))
    tender = response.json["data"]

    # wait until tender period ends, so that we have stale auction period
    frozen_datetime.move_to(tender["tenderPeriod"]["endDate"])
    frozen_datetime.tick(delta=timedelta(days=10))

    # check auction period is stale
    should_start_after = parse_date(tender["lots"][0]["auctionPeriod"]["shouldStartAfter"])
    self.assertTrue(should_start_after < get_now())
    start_date = parse_date(tender["lots"][0]["auctionPeriod"]["startDate"])
    self.assertTrue(start_date < get_now())

    # set complaint to satisfied
    response = self.app.patch_json(
        "/tenders/{}/complaints/{}".format(self.tender_id, complaint["id"]),
        {
            "data": {
                "status": "satisfied",
                "decision": "refined complaint decision",
            }
        },
    )
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(response.json["data"]["status"], "satisfied")
    self.assertEqual(response.json["data"]["dateDecision"], get_now().isoformat())

    # get tender
    response = self.app.get("/tenders/{}".format(self.tender_id))
    tender = response.json["data"]

    # check auction period is stale
    should_start_after = parse_date(tender["lots"][0]["auctionPeriod"]["shouldStartAfter"])
    self.assertTrue(should_start_after < get_now())
    start_date = parse_date(tender["lots"][0]["auctionPeriod"]["startDate"])
    self.assertTrue(start_date < get_now())

    # wait more
    frozen_datetime.tick(delta=timedelta(days=10))

    self.app.authorization = ("Basic", ("broker", ""))

    # set complaint to resolved
    response = self.app.patch_json(
        "/tenders/{}/complaints/{}?acc_token={}".format(self.tender_id, complaint["id"], self.tender_token),
        {
            "data": {
                "status": "resolved",
                "tendererAction": "Tenderer action",
            }
        },
    )
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(response.json["data"]["status"], "resolved")
    self.assertEqual(response.json["data"]["tendererActionDate"], get_now().isoformat())

    self.check_chronograph()

    # get tender
    response = self.app.get("/tenders/{}".format(self.tender_id))
    tender = response.json["data"]
    self.assertEqual(tender["status"], "active.auction")

    # check that auction period was updated
    should_start_after = parse_date(tender["lots"][0]["auctionPeriod"]["shouldStartAfter"])
    self.assertTrue(should_start_after > get_now())
    start_date = parse_date(tender["lots"][0]["auctionPeriod"]["startDate"])
    self.assertTrue(start_date > get_now())

    freezer.stop()


def set_auction_period_for_not_satisfied_complaint(self):
    freezer = freeze_time()
    frozen_datetime = freezer.start()

    self.app.authorization = ("Basic", ("broker", ""))

    # create complaint
    complaint_data = deepcopy(test_tender_below_complaint)
    complaint_data["author"] = deepcopy(test_tender_below_author)
    response = self.app.post_json(
        "/tenders/{}/complaints".format(self.tender_id),
        {"data": complaint_data},
    )
    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(response.json["data"]["status"], "draft")

    complaint = response.json["data"]

    self.app.authorization = ("Basic", ("bot", ""))

    # set complaint to pending
    response = self.app.patch_json(
        "/tenders/{}/complaints/{}".format(self.tender_id, complaint["id"]),
        {"data": {"status": "pending"}},
    )
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(response.json["data"]["status"], "pending")

    self.app.authorization = ("Basic", ("reviewer", ""))

    # set complaint to accepted
    response = self.app.patch_json(
        "/tenders/{}/complaints/{}".format(self.tender_id, complaint["id"]),
        {
            "data": {
                "status": "accepted",
                "decision": "complaint decision",
                "reviewDate": get_now().isoformat(),
                "reviewPlace": "some",
            }
        },
    )
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(response.json["data"]["status"], "accepted")

    # get tender
    response = self.app.get("/tenders/{}".format(self.tender_id))
    tender = response.json["data"]

    # wait until tender period ends, so that we have stale auction period
    frozen_datetime.move_to(tender["tenderPeriod"]["endDate"])
    frozen_datetime.tick(delta=timedelta(days=10))

    # check auction period is stale
    should_start_after = parse_date(tender["lots"][0]["auctionPeriod"]["shouldStartAfter"])
    self.assertTrue(should_start_after < get_now())
    start_date = parse_date(tender["lots"][0]["auctionPeriod"]["startDate"])
    self.assertTrue(start_date < get_now())

    # set complaint to satisfied
    response = self.app.patch_json(
        "/tenders/{}/complaints/{}".format(self.tender_id, complaint["id"]),
        {
            "data": {
                "status": "declined",
                "decision": "declined complaint decision",
            }
        },
    )
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(response.json["data"]["status"], "declined")
    self.assertEqual(response.json["data"]["dateDecision"], get_now().isoformat())

    self.check_chronograph()

    # get tender
    response = self.app.get("/tenders/{}".format(self.tender_id))
    tender = response.json["data"]
    self.assertEqual(tender["status"], "active.auction")

    # check that auction period was updated
    should_start_after = parse_date(tender["lots"][0]["auctionPeriod"]["shouldStartAfter"])
    self.assertTrue(should_start_after > get_now())
    start_date = parse_date(tender["lots"][0]["auctionPeriod"]["startDate"])
    self.assertTrue(start_date > get_now())

    freezer.stop()
