from copy import deepcopy
from datetime import timedelta
from unittest import mock

from openprocurement.api.utils import get_now
from openprocurement.tender.core.tests.utils import (
    generate_req_response,
    set_bid_items,
    set_bid_lotvalues,
)
from openprocurement.tender.requestforproposal.tests.base import (
    test_tender_rfp_supplier,
)


def update_tender_bid_pmr_related_doc(self):
    criteria = self.app.get("/tenders/{}".format(self.tender_id)).json["data"]["criteria"]
    requirement = criteria[0]["requirementGroups"][0]["requirements"][0]

    evidences = [
        {
            "relatedDocument": {"id": "a" * 32, "title": "name.doc"},
            "type": "document",
            "id": "f77bda2a24e74f5286ede23cbe8f6b1e",
            "title": "вид та умови надання забезпечення гарантія1",
        }
    ]

    rr_data = [generate_req_response(requirement)]
    rr_data[0]["evidences"] = evidences

    # POST
    bid_data = {
        "requirementResponses": rr_data,
        "tenderers": [test_tender_rfp_supplier],
        "value": {"amount": 500},
    }
    set_bid_items(self, bid_data)

    response = self.app.post_json(
        "/tenders/{}/bids".format(self.tender_id),
        {"data": bid_data},
    )
    bid_id = response.json["data"]["id"]
    bid_token = response.json["access"]["token"]
    response = self.app.patch_json(
        f"/tenders/{self.tender_id}/bids/{bid_id}?acc_token={bid_token}", {"data": {"status": "pending"}}, status=422
    )
    self.assertEqual(
        response.json["errors"][0],
        {
            "location": "body",
            "name": "requirementResponses",
            "description": [
                {"evidences": [{"relatedDocument": ["relatedDocument.id should be one of bid documents"]}]}
            ],
        },
    )

    # you cannot set document.id, so you cannot post requirementResponses with relatedDocument.id
    bid_data = {
        "requirementResponses": rr_data,
        "tenderers": [test_tender_rfp_supplier],
        "value": {"amount": 500},
        "documents": [
            {
                "id": "a" * 32,
                "title": "name.doc",
                "url": self.generate_docservice_url(),
                "hash": "md5:" + "0" * 32,
                "format": "application/msword",
            }
        ],
    }
    set_bid_items(self, bid_data)
    del rr_data[0]["evidences"]
    response = self.app.post_json(
        "/tenders/{}/bids".format(self.tender_id),
        {"data": bid_data},
    )
    bid = response.json["data"]
    bid_id = bid["id"]
    bid_token = response.json["access"]["token"]

    # patch invalid
    rr_data[0]["evidences"] = evidences
    rr_data[0]["evidences"][0]["relatedDocument"]["id"] = "b" * 32
    response = self.app.patch_json(
        f"/tenders/{self.tender_id}/bids/{bid_id}?acc_token={bid_token}",
        {"data": {"requirementResponses": rr_data, "status": "active"}},
        status=422,
    )
    self.assertEqual(
        response.json["errors"][0],
        {
            "location": "body",
            "name": "requirementResponses",
            "description": [
                {"evidences": [{"relatedDocument": ["relatedDocument.id should be one of bid documents"]}]}
            ],
        },
    )

    # patch valid relatedDocument.id
    response = self.app.post_json(
        "/tenders/{}/bids/{}/documents?acc_token={}".format(self.tender_id, bid_id, bid_token),
        {
            "data": {
                "title": "name.doc",
                "url": self.generate_docservice_url(),
                "hash": "md5:" + "0" * 32,
                "format": "application/msword",
            }
        },
    )
    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")
    rr_data[0]["evidences"][0]["relatedDocument"]["id"] = response.json["data"]["id"]

    self.app.patch_json(
        f"/tenders/{self.tender_id}/bids/{bid_id}?acc_token={bid_token}",
        {"data": {"requirementResponses": rr_data}},
        status=200,
    )


def features_bid(self):
    test_features_bids = [
        {
            "parameters": [{"code": i["code"], "value": 0.1} for i in self.initial_data["features"]],
            "status": "pending",
            "tenderers": [test_tender_rfp_supplier],
            "value": {"amount": 469, "currency": "UAH", "valueAddedTaxIncluded": True},
        },
        {
            "parameters": [{"code": i["code"], "value": 0.15} for i in self.initial_data["features"]],
            "tenderers": [test_tender_rfp_supplier],
            "status": "draft",
            "value": {"amount": 479, "currency": "UAH", "valueAddedTaxIncluded": True},
        },
    ]
    for i in test_features_bids:
        bid, bid_token = self.create_bid(self.tender_id, i)
        bid.pop("date")
        bid.pop("id")
        bid.pop("submissionDate", None)
        bid.pop("items", None)
        i.pop("items", None)
        for k in ("documents", "lotValues"):
            self.assertEqual(bid.pop(k, []), [])
        self.assertEqual(bid, i)


# TenderWithDisabledValueCurrencyEquality


def post_tender_bid_with_disabled_value_currency_equality(self):
    tender = self.mongodb.tenders.get(self.tender_id)
    items = tender.get("items")
    items = [
        {
            "quantity": 7,
            "description": "футляри до державних нагород",
            "id": items[0]['id'],
            "unit": {
                "name": "Item",
                "code": "KGM",
                "value": {"amount": 100, "currency": "EUR", "valueAddedTaxIncluded": False},
            },
        },
    ]
    response = self.app.post_json(
        f"/tenders/{self.tender_id}/bids",
        {
            "data": {
                "tenderers": [test_tender_rfp_supplier],
                "value": {"amount": 200, "currency": "UAH"},
                "items": items,
            }
        },
    )
    self.assertEqual(response.status, "201 Created")


def patch_tender_bid_with_disabled_value_currency_equality(self):
    tender = self.mongodb.tenders.get(self.tender_id)
    items = tender.get("items")
    items = [
        {
            "quantity": 7,
            "description": "футляри до державних нагород",
            "id": items[0]['id'],
            "unit": {
                "name": "Item",
                "code": "KGM",
                "value": {"amount": 100, "currency": "EUR", "valueAddedTaxIncluded": False},
            },
        },
    ]
    response = self.app.post_json(
        f"/tenders/{self.tender_id}/bids",
        {
            "data": {
                "tenderers": [test_tender_rfp_supplier],
                "value": {"amount": 400, "currency": "UAH"},
                "items": items,
            }
        },
    )
    self.assertEqual(response.status, "201 Created")
    bid_id = response.json["data"]["id"]
    token = response.json["access"]["token"]

    response = self.app.patch_json(
        f"/tenders/{self.tender_id}/bids/{bid_id}?acc_token={token}",
        {"data": {"tenderers": [test_tender_rfp_supplier], "value": {"amount": 600, "currency": "EUR"}}},
    )
    self.assertEqual(response.status, "200 OK")


# TenderLotsWithDisabledValueCurrencyEquality


def post_tender_bid_with_disabled_lot_values_currency_equality(self):
    tender = self.mongodb.tenders.get(self.tender_id)
    items = tender.get("items")
    lots = tender.get("lots")

    bid = deepcopy(self.test_bids_data[0])
    value = bid.pop("value", None)
    value["currency"] = "EUR"
    value["amount"] = 650
    bid["lotValues"] = [{"value": value, "relatedLot": lots[0]["id"]}]
    bid["items"] = [
        {
            "quantity": 7,
            "description": "футляри до державних нагород",
            "id": items[0]['id'],
            "unit": {
                "name": "Item",
                "code": "DMQ",
                "value": {"amount": 100, "currency": "UAH", "valueAddedTaxIncluded": False},
            },
        },
    ]
    response = self.app.post_json("/tenders/{}/bids".format(self.tender_id), {"data": bid})
    self.assertEqual(response.status, "201 Created")


def patch_tender_bid_with_disabled_lot_values_currency_equality(self):
    tender = self.mongodb.tenders.get(self.tender_id)
    items = tender.get("items")
    lots = tender.get("lots")

    bid = deepcopy(self.test_bids_data[0])
    value = bid.pop("value", None)
    value["currency"] = "UAH"
    bid["lotValues"] = [{"value": value, "relatedLot": lots[0]["id"]}]
    bid["items"] = [
        {
            "quantity": 7,
            "description": "футляри до державних нагород",
            "id": items[0]['id'],
            "unit": {
                "name": "Item",
                "code": "KGM",
                "value": {"amount": 100, "currency": "UAH", "valueAddedTaxIncluded": False},
            },
        },
    ]
    response = self.app.post_json(f"/tenders/{self.tender_id}/bids", {"data": bid})
    self.assertEqual(response.status, "201 Created")
    bid_id = response.json["data"]["id"]
    token = response.json["access"]["token"]
    lot_values = response.json["data"]["lotValues"]

    # patch lotValue with another currency that in lot
    value["currency"] = "EUR"
    value["amount"] = 650
    bid["lotValues"] = [{**lot_values[0], "value": value, "relatedLot": lots[0]["id"]}]
    response = self.app.patch_json(
        f"/tenders/{self.tender_id}/bids/{bid_id}?acc_token={token}",
        {"data": bid},
    )
    self.assertEqual(response.status, "200 OK")


@mock.patch("openprocurement.tender.core.procedure.models.item.UNIT_PRICE_REQUIRED_FROM", get_now() - timedelta(days=1))
def post_bid_multi_currency(self):
    tender = self.mongodb.tenders.get(self.tender_id)
    items = tender.get("items")

    bid = deepcopy(self.test_bids_data[0])
    value = bid.pop("value", None)
    value["currency"] = "EUR"
    value["amount"] = 650
    bid["lotValues"] = [{"value": value, "relatedLot": tender["lots"][0]["id"]}]

    # try to add bid without items
    response = self.app.post_json("/tenders/{}/bids".format(self.tender_id), {"data": bid}, status=422)
    self.assertEqual(response.status, "422 Unprocessable Entity")
    self.assertEqual(
        response.json["errors"][0]["description"],
        "This field is required.",
    )
    # try to change valueAddedTaxIncluded different from lot
    bid["lotValues"] = [{"value": value, "relatedLot": tender["lots"][0]["id"]}]
    bid["items"] = [
        {
            "quantity": 7,
            "description": "футляри до державних нагород",
            "id": items[0]['id'],
            "unit": {
                "name": "Item",
                "code": "KGM",
                "value": {"amount": 100, "currency": "EUR", "valueAddedTaxIncluded": False},
            },
        },
    ]

    # try to post bid without quantity in items
    del bid["items"][0]["quantity"]
    response = self.app.post_json("/tenders/{}/bids".format(self.tender_id), {"data": bid}, status=422)
    self.assertEqual(response.status, "422 Unprocessable Entity")
    self.assertEqual(
        response.json["errors"][0]["description"],
        [{"quantity": ["This field is required."]}],
    )

    # try to post bid with items for another lot
    bid["items"][0]["quantity"] = 7
    bid["lotValues"][0]["relatedLot"] = tender["lots"][1]["id"]
    response = self.app.post_json("/tenders/{}/bids".format(self.tender_id), {"data": bid}, status=422)
    self.assertEqual(response.status, "422 Unprocessable Entity")
    self.assertEqual(
        response.json["errors"][0]["description"],
        "Bid items ids should be on tender items ids for current lot",
    )
    bid["lotValues"][0]["relatedLot"] = tender["lots"][0]["id"]

    # try to post bid without items.unit.value for tender with funders
    del bid["items"][0]["unit"]["value"]
    response = self.app.post_json("/tenders/{}/bids".format(self.tender_id), {"data": bid}, status=422)
    self.assertEqual(response.status, "422 Unprocessable Entity")
    self.assertEqual(
        response.json["errors"][0]["description"],
        "items.unit.value is required for tender with funders",
    )

    # try to change amount and currency different from lot
    bid["items"][0]["unit"]["value"] = {"amount": 0.5, "currency": "USD", "valueAddedTaxIncluded": False}
    response = self.app.post_json("/tenders/{}/bids".format(self.tender_id), {"data": bid})
    self.assertEqual(response.status, "201 Created")
    bid_unit_value = response.json["data"]["items"][0]["unit"]["value"]
    self.assertNotEqual(tender["value"]["currency"], bid_unit_value["currency"])
    self.assertNotEqual(tender["lots"][0]["value"]["currency"], bid_unit_value["currency"])
    self.assertNotEqual(response.json["data"]["lotValues"][0]["value"]["currency"], bid_unit_value["currency"])


def patch_bid_multi_currency(self):
    tender = self.mongodb.tenders.get(self.tender_id)
    items = tender.get("items")

    bid = deepcopy(self.test_bids_data[0])
    value = bid.pop("value", None)
    value["currency"] = "UAH"
    bid["lotValues"] = [{"value": value, "relatedLot": tender["lots"][0]["id"]}]
    # try to change valueAddedTaxIncluded different from lot
    bid["items"] = [
        {
            "quantity": 7,
            "description": "футляри до державних нагород",
            "id": items[0]['id'],
            "unit": {
                "name": "Item",
                "code": "KGM",
                "value": {"amount": 100, "currency": "UAH", "valueAddedTaxIncluded": False},
            },
        },
    ]
    response = self.app.post_json(f"/tenders/{self.tender_id}/bids", {"data": bid})
    self.assertEqual(response.status, "201 Created")
    bid_id = response.json["data"]["id"]
    token = response.json["access"]["token"]
    lot_values = response.json["data"]["lotValues"]

    # patch lotValue with another currency that in lot
    value["currency"] = "EUR"
    value["amount"] = 650
    bid["lotValues"] = [{**lot_values[0], "value": value, "relatedLot": tender["lots"][0]["id"]}]

    # try to change amount and currency different from lot
    bid["items"][0]["unit"]["value"] = {"amount": 0, "currency": "USD", "valueAddedTaxIncluded": False}
    response = self.app.patch_json(
        f"/tenders/{self.tender_id}/bids/{bid_id}?acc_token={token}",
        {"data": bid},
    )
    self.assertEqual(response.status, "200 OK")


def patch_tender_with_bids_lots_none(self):
    bid = self.test_bids_data[0].copy()
    lots = self.mongodb.tenders.get(self.tender_id).get("lots")

    set_bid_lotvalues(bid, lots)

    self.create_bid(self.tender_id, bid)

    response = self.app.patch_json(
        "/tenders/{}?acc_token={}".format(self.tender_id, self.tender_token), {"data": {"lots": None}}, status=422
    )
    self.assertEqual(
        response.json["errors"],
        [
            {"location": "body", "name": "milestones", "description": ["relatedLot should be one of the lots."]},
            {
                "location": "body",
                "name": "items",
                "description": [{"relatedLot": ["relatedLot should be one of lots"]}],
            },
        ],
    )
