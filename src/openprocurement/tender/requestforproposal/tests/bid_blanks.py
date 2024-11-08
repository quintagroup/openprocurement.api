from openprocurement.tender.core.tests.utils import set_bid_items
from openprocurement.tender.requestforproposal.tests.base import (
    test_tender_rfp_organization,
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

    rr_data = [
        {
            "requirement": {
                "id": requirement["id"],
            },
            "values": ["Українська"],
            "evidences": evidences,
        }
    ]

    # POST
    bid_data = {
        "requirementResponses": rr_data,
        "tenderers": [test_tender_rfp_organization],
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
        "tenderers": [test_tender_rfp_organization],
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
            "tenderers": [test_tender_rfp_organization],
            "value": {"amount": 469, "currency": "UAH", "valueAddedTaxIncluded": True},
        },
        {
            "parameters": [{"code": i["code"], "value": 0.15} for i in self.initial_data["features"]],
            "tenderers": [test_tender_rfp_organization],
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
