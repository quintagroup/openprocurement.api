from datetime import timedelta
from unittest import mock

from openprocurement.api.utils import get_now
from openprocurement.tender.core.tests.utils import change_auth
from openprocurement.tender.core.utils import calculate_tender_full_date
from openprocurement.tender.open.constants import POST_SUBMIT_TIME

RELEASE_2020_04_19_TEST_ENABLED = get_now() - timedelta(days=1)
RELEASE_2020_04_19_TEST_DISABLED = get_now() + timedelta(days=1)


@mock.patch("openprocurement.tender.core.procedure.utils.RELEASE_2020_04_19", RELEASE_2020_04_19_TEST_DISABLED)
def create_complaint_post_release_forbidden(self):
    # try in draft
    with change_auth(self.app, ("Basic", ("reviewer", ""))):
        response = self.post_post(
            {
                "title": "Lorem ipsum",
                "description": "Lorem ipsum dolor sit amet",
                "recipient": "complaint_owner",
                "relatedObjection": self.objection_id,
            },
            status=403,
        )
    self.assertEqual(response.status, "403 Forbidden")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(response.json["errors"][0]["description"], "Forbidden")


@mock.patch("openprocurement.tender.core.procedure.utils.RELEASE_2020_04_19", RELEASE_2020_04_19_TEST_ENABLED)
def create_complaint_post_status_forbidden(self):
    # try in draft
    with change_auth(self.app, ("Basic", ("reviewer", ""))):
        response = self.post_post(
            {
                "title": "Lorem ipsum",
                "description": "Lorem ipsum dolor sit amet",
                "recipient": "complaint_owner",
                "relatedObjection": self.objection_id,
            },
            status=403,
        )
    self.assertEqual(response.status, "403 Forbidden")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(
        response.json["errors"][0]["description"], "Can't submit or edit post in current (draft) complaint status"
    )


@mock.patch("openprocurement.tender.core.procedure.utils.RELEASE_2020_04_19", RELEASE_2020_04_19_TEST_ENABLED)
def create_complaint_post_review_date_forbidden(self):
    # make complaint status pending
    with change_auth(self.app, ("Basic", ("bot", ""))):
        response = self.patch_complaint({"status": "pending"}, self.complaint_owner_token)
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.json["data"]["status"], "pending")

    # make complaint status accepted
    with change_auth(self.app, ("Basic", ("reviewer", ""))):
        response = self.patch_complaint(
            {
                "status": "accepted",
                "reviewDate": get_now().isoformat(),
                "reviewPlace": "some",
            },
            self.complaint_owner_token,
        )
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.json["data"]["status"], "accepted")

    # create post by reviewer
    with change_auth(self.app, ("Basic", ("reviewer", ""))):
        response = self.post_post(
            {
                "title": "Lorem ipsum",
                "description": "Lorem ipsum dolor sit amet",
                "recipient": "complaint_owner",
                "relatedObjection": self.objection_id,
            },
            status=403,
        )

    self.assertEqual(response.status, "403 Forbidden")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(
        response.json["errors"][0]["description"],
        "Can submit or edit post not later than 3 full business days before reviewDate",
    )


@mock.patch("openprocurement.tender.core.procedure.utils.RELEASE_2020_04_19", RELEASE_2020_04_19_TEST_ENABLED)
def create_complaint_post_claim_forbidden(self):
    # make complaint type claim
    response = self.post_claim()
    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.json["data"]["status"], "claim")

    # try in claim
    with change_auth(self.app, ("Basic", ("reviewer", ""))):
        response = self.post_post(
            {
                "title": "Lorem ipsum",
                "description": "Lorem ipsum dolor sit amet",
                "recipient": "complaint_owner",
                "relatedObjection": self.objection_id,
            },
            status=403,
        )
    self.assertEqual(response.status, "403 Forbidden")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(
        response.json["errors"][0]["description"], "Can't submit or edit post in current (claim) complaint type"
    )


@mock.patch("openprocurement.tender.core.procedure.utils.RELEASE_2020_04_19", RELEASE_2020_04_19_TEST_ENABLED)
def create_complaint_post_complaint_owner(self):
    # make complaint status pending
    with change_auth(self.app, ("Basic", ("bot", ""))):
        response = self.patch_complaint({"status": "pending"}, self.complaint_owner_token)
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.json["data"]["status"], "pending")

    # create post by reviewer
    with change_auth(self.app, ("Basic", ("reviewer", ""))):
        response = self.post_post(
            {
                "title": "Lorem ipsum",
                "description": "Lorem ipsum dolor sit amet",
                "recipient": "complaint_owner",
                "relatedObjection": self.objection_id,
            }
        )
    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(response.json["data"]["author"], "aboveThresholdReviewers")

    post = response.json["data"]

    # create answer by complaint owner
    response = self.post_post(
        {
            "title": "Lorem ipsum",
            "description": "Lorem ipsum dolor sit amet",
            "recipient": "aboveThresholdReviewers",
            "relatedPost": post["id"],
            "relatedObjection": self.objection_id,
        },
        acc_token=self.complaint_owner_token,
    )
    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(response.json["data"]["author"], "complaint_owner")


@mock.patch("openprocurement.tender.core.procedure.utils.RELEASE_2020_04_19", RELEASE_2020_04_19_TEST_ENABLED)
def create_complaint_post_tender_owner(self):
    # make complaint status pending
    with change_auth(self.app, ("Basic", ("bot", ""))):
        response = self.patch_complaint({"status": "pending"}, self.complaint_owner_token)
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.json["data"]["status"], "pending")

    # create post by reviewer
    with change_auth(self.app, ("Basic", ("reviewer", ""))):
        response = self.post_post(
            {
                "title": "Lorem ipsum",
                "description": "Lorem ipsum dolor sit amet",
                "recipient": "tender_owner",
                "relatedObjection": self.objection_id,
            }
        )
    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(response.json["data"]["author"], "aboveThresholdReviewers")

    post = response.json["data"]

    # create answer by complaint owner
    response = self.post_post(
        {
            "title": "Lorem ipsum",
            "description": "Lorem ipsum dolor sit amet",
            "recipient": "aboveThresholdReviewers",
            "relatedPost": post["id"],
            "relatedObjection": self.objection_id,
        },
        acc_token=self.tender_token,
    )
    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(response.json["data"]["author"], "tender_owner")


@mock.patch("openprocurement.tender.core.procedure.utils.RELEASE_2020_04_19", RELEASE_2020_04_19_TEST_ENABLED)
def create_complaint_post_validate_recipient(self):
    # make complaint status pending
    with change_auth(self.app, ("Basic", ("bot", ""))):
        response = self.patch_complaint({"status": "pending"}, self.complaint_owner_token)
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.json["data"]["status"], "pending")

    # create post by reviewer with invalid recipient
    with change_auth(self.app, ("Basic", ("reviewer", ""))):
        response = self.post_post(
            {
                "title": "Lorem ipsum",
                "description": "Lorem ipsum dolor sit amet",
                "recipient": "aboveThresholdReviewers",
                "relatedObjection": self.objection_id,
            },
            status=422,
        )
    self.assertEqual(response.status, "422 Unprocessable Entity")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(response.json["status"], "error")
    self.assertIn("Value must be one of ['complaint_owner', 'tender_owner'].", str(response.json["errors"]))

    # create post by reviewer
    with change_auth(self.app, ("Basic", ("reviewer", ""))):
        response = self.post_post(
            {
                "title": "Lorem ipsum",
                "description": "Lorem ipsum dolor sit amet",
                "recipient": "complaint_owner",
                "relatedObjection": self.objection_id,
            }
        )
    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(response.json["data"]["author"], "aboveThresholdReviewers")

    post = response.json["data"]

    # create answer by complaint owner invalid recipient
    response = self.post_post(
        {
            "title": "Lorem ipsum",
            "description": "Lorem ipsum dolor sit amet",
            "recipient": "complaint_owner",
            "relatedPost": post["id"],
            "relatedObjection": self.objection_id,
        },
        acc_token=self.complaint_owner_token,
        status=422,
    )
    self.assertEqual(response.status, "422 Unprocessable Entity")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(response.json["status"], "error")
    self.assertIn("Value must be one of ['aboveThresholdReviewers'].", str(response.json["errors"]))


@mock.patch("openprocurement.tender.core.procedure.utils.RELEASE_2020_04_19", RELEASE_2020_04_19_TEST_ENABLED)
def create_complaint_post_validate_related_post(self):
    # make complaint status pending
    with change_auth(self.app, ("Basic", ("bot", ""))):
        response = self.patch_complaint({"status": "pending"}, self.complaint_owner_token)
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.json["data"]["status"], "pending")

    # create post by reviewer
    with change_auth(self.app, ("Basic", ("reviewer", ""))):
        response = self.post_post(
            {
                "title": "Lorem ipsum",
                "description": "Lorem ipsum dolor sit amet",
                "recipient": "tender_owner",
                "relatedObjection": self.objection_id,
            }
        )
    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(response.json["data"]["author"], "aboveThresholdReviewers")

    post = response.json["data"]

    # create answer by complaint owner invalid recipient
    response = self.post_post(
        {
            "title": "Lorem ipsum",
            "description": "Lorem ipsum dolor sit amet",
            "recipient": "aboveThresholdReviewers",
            "relatedPost": post["id"],
            "relatedObjection": self.objection_id,
        },
        acc_token=self.complaint_owner_token,
        status=422,
    )
    self.assertEqual(response.status, "422 Unprocessable Entity")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(response.json["status"], "error")
    self.assertIn("relatedPost invalid recipient.", str(response.json["errors"]))

    # create answer by complaint owner invalid recipient
    with change_auth(self.app, ("Basic", ("reviewer", ""))):
        response = self.post_post(
            {
                "title": "Lorem ipsum",
                "description": "Lorem ipsum dolor sit amet",
                "recipient": "aboveThresholdReviewers",
                "relatedPost": post["id"],
                "relatedObjection": self.objection_id,
            },
            acc_token=self.complaint_owner_token,
            status=422,
        )
    self.assertEqual(response.status, "422 Unprocessable Entity")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(response.json["status"], "error")
    self.assertIn("relatedPost can't have the same author.", str(response.json["errors"]))

    # create answer by complaint owner invalid recipient
    response = self.post_post(
        {
            "title": "Lorem ipsum",
            "description": "Lorem ipsum dolor sit amet",
            "recipient": "aboveThresholdReviewers",
            "relatedPost": "some_id",
            "relatedObjection": self.objection_id,
        },
        acc_token=self.complaint_owner_token,
        status=422,
    )
    self.assertEqual(response.status, "422 Unprocessable Entity")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(response.json["status"], "error")
    self.assertIn("relatedPost should be one of posts.", str(response.json["errors"]))

    # create answer by tender owner without related post
    response = self.post_post(
        {
            "title": "Lorem ipsum",
            "description": "Lorem ipsum dolor sit amet",
            "recipient": "aboveThresholdReviewers",
            "relatedObjection": self.objection_id,
        },
        acc_token=self.tender_token,
        status=422,
    )
    self.assertEqual(response.status, "422 Unprocessable Entity")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(response.json["status"], "error")
    self.assertIn("This field is required.", str(response.json["errors"]))

    # create answer by tender owner
    response = self.post_post(
        {
            "title": "Lorem ipsum",
            "description": "Lorem ipsum dolor sit amet",
            "recipient": "aboveThresholdReviewers",
            "relatedPost": post["id"],
            "relatedObjection": self.objection_id,
        },
        acc_token=self.tender_token,
    )
    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(response.json["data"]["author"], "tender_owner")

    # create answer by tender owner invalid recipient
    response = self.post_post(
        {
            "title": "Lorem ipsum",
            "description": "Lorem ipsum dolor sit amet",
            "recipient": "aboveThresholdReviewers",
            "relatedPost": post["id"],
            "relatedObjection": self.objection_id,
        },
        acc_token=self.tender_token,
        status=422,
    )
    self.assertEqual(response.status, "422 Unprocessable Entity")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(response.json["status"], "error")
    self.assertIn("relatedPost must be unique.", str(response.json["errors"]))


@mock.patch("openprocurement.tender.core.procedure.utils.RELEASE_2020_04_19", RELEASE_2020_04_19_TEST_ENABLED)
def patch_complaint_post(self):
    # make complaint status pending
    with change_auth(self.app, ("Basic", ("bot", ""))):
        response = self.patch_complaint({"status": "pending"}, self.complaint_owner_token)
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.json["data"]["status"], "pending")

    # create post by reviewer
    with change_auth(self.app, ("Basic", ("reviewer", ""))):
        response = self.post_post(
            {
                "title": "Lorem ipsum",
                "description": "Lorem ipsum dolor sit amet",
                "recipient": "complaint_owner",
                "relatedObjection": self.objection_id,
            }
        )
    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")

    post = response.json["data"]
    self.post_id = post["id"]

    # try patch post by reviewer
    with change_auth(self.app, ("Basic", ("reviewer", ""))):
        response = self.patch_post({"title": "Test"}, status=405)
    self.assertEqual(response.status, "405 Method Not Allowed")
    self.assertEqual(response.content_type, "text/plain")


@mock.patch("openprocurement.tender.core.procedure.utils.RELEASE_2020_04_19", RELEASE_2020_04_19_TEST_ENABLED)
def get_complaint_post(self):
    # make complaint status pending
    with change_auth(self.app, ("Basic", ("bot", ""))):
        response = self.patch_complaint({"status": "pending"}, self.complaint_owner_token)
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.json["data"]["status"], "pending")

    # create post by reviewer
    with change_auth(self.app, ("Basic", ("reviewer", ""))):
        response = self.post_post(
            {
                "title": "Lorem ipsum",
                "description": "Lorem ipsum dolor sit amet",
                "recipient": "complaint_owner",
                "relatedObjection": self.objection_id,
            }
        )
    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")

    post = response.json["data"]

    self.post_id = post["id"]

    response = self.get_post()
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(
        set(response.json["data"]),
        {"id", "title", "description", "author", "recipient", "datePublished", "relatedObjection"},
    )

    self.post_id = "some_id"

    response = self.get_post(status=404)
    self.assertEqual(response.status, "404 Not Found")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(response.json["status"], "error")
    self.assertEqual(response.json["errors"], [{"description": "Not Found", "location": "url", "name": "post_id"}])


@mock.patch("openprocurement.tender.core.procedure.utils.RELEASE_2020_04_19", RELEASE_2020_04_19_TEST_ENABLED)
def get_complaint_posts(self):
    # make complaint status pending
    with change_auth(self.app, ("Basic", ("bot", ""))):
        response = self.patch_complaint({"status": "pending"}, self.complaint_owner_token)
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.json["data"]["status"], "pending")

    # create post by reviewer
    with change_auth(self.app, ("Basic", ("reviewer", ""))):
        response = self.post_post(
            {
                "title": "Lorem ipsum",
                "description": "Lorem ipsum dolor sit amet",
                "recipient": "complaint_owner",
                "relatedObjection": self.objection_id,
            }
        )
    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")

    response = self.get_posts()
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(
        set(response.json["data"][0]),
        {"id", "title", "description", "author", "recipient", "datePublished", "relatedObjection"},
    )


@mock.patch("openprocurement.tender.core.procedure.utils.RELEASE_2020_04_19", RELEASE_2020_04_19_TEST_ENABLED)
def get_tender_complaint_post_document_json(self):
    # make complaint status pending
    with change_auth(self.app, ("Basic", ("bot", ""))):
        response = self.patch_complaint({"status": "pending"}, self.complaint_owner_token)
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.json["data"]["status"], "pending")

    # create post by reviewer
    with change_auth(self.app, ("Basic", ("reviewer", ""))):
        response = self.post_post(
            {
                "title": "Lorem ipsum",
                "description": "Lorem ipsum dolor sit amet",
                "recipient": "complaint_owner",
                "relatedObjection": self.objection_id,
                "documents": [
                    {
                        "title": "name.doc",
                        "url": self.generate_docservice_url(),
                        "hash": "md5:" + "0" * 32,
                        "format": "application/msword",
                    }
                ],
            }
        )
    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")

    post = response.json["data"]

    self.post_id = post["id"]

    # create document by reviewer
    with change_auth(self.app, ("Basic", ("reviewer", ""))):
        response = self.post_post_document(
            {
                "title": "укр.doc",
                "url": self.generate_docservice_url(),
                "hash": "md5:" + "0" * 32,
                "format": "application/msword",
            }
        )

    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")
    document = response.json["data"]
    self.assertIn(document["id"], response.headers["Location"])
    self.assertEqual("укр.doc", document["title"])
    self.assertIn("Signature=", document["url"])
    self.assertIn("KeyID=", document["url"])
    self.assertNotIn("Expires=", document["url"])
    key = document["url"].split("/")[-1].split("?")[0]

    response = self.get_post()
    post = response.json["data"]
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.content_type, "application/json")
    self.assertIn(key, post["documents"][-1]["url"])
    self.assertIn("Signature=", post["documents"][-1]["url"])
    self.assertIn("KeyID=", post["documents"][-1]["url"])
    self.assertNotIn("Expires=", post["documents"][-1]["url"])

    response = self.get_post_documents()
    documents = response.json["data"]
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(document["id"], documents[-1]["id"])
    self.assertEqual("укр.doc", documents[-1]["title"])

    response = self.get_post_documents(params={"all": "true"})
    documents = response.json["data"]
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(document["id"], documents[-1]["id"])
    self.assertEqual("укр.doc", documents[-1]["title"])

    # put document by reviewer
    with change_auth(self.app, ("Basic", ("reviewer", ""))):
        response = self.post_post_document(
            {
                "title": "укр.doc",
                "url": self.generate_docservice_url(),
                "hash": "md5:" + "0" * 32,
                "format": "application/msword",
            }
        )

    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")
    document = response.json["data"]
    self.assertEqual("укр.doc", document["title"])
    dateModified = document["dateModified"]
    datePublished = document["datePublished"]
    self.assertIn(document["id"], response.headers["Location"])

    self.document_id = document["id"]

    with change_auth(self.app, ("Basic", ("reviewer", ""))):
        response = self.put_post_document(
            {
                "title": "укр.doc",
                "url": self.generate_docservice_url(),
                "hash": "md5:" + "0" * 32,
                "format": "application/msword",
            }
        )
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.content_type, "application/json")
    document = response.json["data"]
    self.assertEqual(self.document_id, document["id"])
    self.assertIn("Signature=", document["url"])
    self.assertIn("KeyID=", document["url"])
    self.assertNotIn("Expires=", document["url"])
    key = document["url"].split("/")[-1].split("?")[0]

    response = self.get_post()
    post = response.json["data"]
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.content_type, "application/json")
    self.assertIn(key, post["documents"][-1]["url"])
    self.assertIn("Signature=", post["documents"][-1]["url"])
    self.assertIn("KeyID=", post["documents"][-1]["url"])
    self.assertNotIn("Expires=", post["documents"][-1]["url"])

    response = self.get_post_document()
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.content_type, "application/json")
    document = response.json["data"]
    self.assertEqual(self.document_id, document["id"])
    dateModified2 = document["dateModified"]
    self.assertTrue(dateModified < dateModified2)
    self.assertEqual(dateModified, document["previousVersions"][0]["dateModified"])
    self.assertNotEqual(document["datePublished"], datePublished)

    response = self.get_post_documents(params={"all": "true"})
    documents = response.json["data"]
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(dateModified, documents[-2]["dateModified"])
    self.assertEqual(dateModified2, documents[-1]["dateModified"])


@mock.patch("openprocurement.tender.core.procedure.utils.RELEASE_2020_04_19", RELEASE_2020_04_19_TEST_ENABLED)
def create_tender_complaint_post_document_json(self):
    # make complaint status pending
    with change_auth(self.app, ("Basic", ("bot", ""))):
        response = self.patch_complaint({"status": "pending"}, self.complaint_owner_token)
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.json["data"]["status"], "pending")

    # create post by reviewer
    with change_auth(self.app, ("Basic", ("reviewer", ""))):
        response = self.post_post(
            {
                "title": "Lorem ipsum",
                "description": "Lorem ipsum dolor sit amet",
                "recipient": "complaint_owner",
                "relatedObjection": self.objection_id,
            }
        )
    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")

    post = response.json["data"]

    self.post_id = post["id"]

    # create document by reviewer
    with change_auth(self.app, ("Basic", ("reviewer", ""))):
        response = self.post_post_document(
            {
                "title": "укр.doc",
                "url": self.generate_docservice_url(),
                "hash": "md5:" + "0" * 32,
                "format": "application/msword",
            }
        )

    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")
    post = response.json["data"]

    # create document by complaint_owner
    response = self.post_post_document(
        {
            "title": "укр.doc",
            "url": self.generate_docservice_url(),
            "hash": "md5:" + "0" * 32,
            "format": "application/msword",
        },
        acc_token=self.complaint_owner_token,
        status=403,
    )

    self.assertEqual(response.status, "403 Forbidden")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(response.json["errors"][0]["description"], "Can add document only by post author")

    # create document by tender_owner
    response = self.post_post_document(
        {
            "title": "укр.doc",
            "url": self.generate_docservice_url(),
            "hash": "md5:" + "0" * 32,
            "format": "application/msword",
        },
        acc_token=self.tender_token,
        status=403,
    )

    self.assertEqual(response.status, "403 Forbidden")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(response.json["errors"][0]["description"], "Can add document only by post author")

    # make complaint status accepted
    with change_auth(self.app, ("Basic", ("reviewer", ""))):
        response = self.patch_complaint(
            {
                "status": "accepted",
                "reviewDate": get_now().isoformat(),
                "reviewPlace": "some",
            },
            self.complaint_owner_token,
        )
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.json["data"]["status"], "accepted")

    # create document by reviewer
    with change_auth(self.app, ("Basic", ("reviewer", ""))):
        response = self.post_post_document(
            {
                "title": "укр.doc",
                "url": self.generate_docservice_url(),
                "hash": "md5:" + "0" * 32,
                "format": "application/msword",
            },
            status=403,
        )

    self.assertEqual(response.status, "403 Forbidden")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(
        response.json["errors"][0]["description"],
        "Can submit or edit post not later than 3 full business days before reviewDate",
    )

    # change complaint reviewDate
    with change_auth(self.app, ("Basic", ("reviewer", ""))):
        response = self.patch_complaint(
            {
                "reviewDate": calculate_tender_full_date(
                    get_now(), POST_SUBMIT_TIME + timedelta(days=1), tender={}, working_days=True
                ).isoformat(),
            },
            self.complaint_owner_token,
        )
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.json["data"]["status"], "accepted")

    # create post by reviewer
    with change_auth(self.app, ("Basic", ("reviewer", ""))):
        response = self.post_post_document(
            {
                "title": "укр.doc",
                "url": self.generate_docservice_url(),
                "hash": "md5:" + "0" * 32,
                "format": "application/msword",
            }
        )
    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")


@mock.patch("openprocurement.tender.core.procedure.utils.RELEASE_2020_04_19", RELEASE_2020_04_19_TEST_ENABLED)
def create_tender_complaint_post_by_complaint_owner_document_json(self):
    # make complaint status pending
    with change_auth(self.app, ("Basic", ("bot", ""))):
        response = self.patch_complaint({"status": "pending"}, self.complaint_owner_token)
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.json["data"]["status"], "pending")

    # create post by reviewer
    with change_auth(self.app, ("Basic", ("reviewer", ""))):
        response = self.post_post(
            {
                "title": "Lorem ipsum",
                "description": "Lorem ipsum dolor sit amet",
                "recipient": "complaint_owner",
                "relatedObjection": self.objection_id,
            }
        )
    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")

    post = response.json["data"]

    self.post_id = post["id"]

    # create post by complaint_owner
    response = self.post_post(
        {
            "title": "Lorem ipsum",
            "description": "Lorem ipsum dolor sit amet",
            "recipient": "aboveThresholdReviewers",
            "relatedPost": post["id"],
            "relatedObjection": self.objection_id,
        },
        acc_token=self.complaint_owner_token,
    )
    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")

    post = response.json["data"]

    self.post_id = post["id"]

    # create document by complaint_owner
    response = self.post_post_document(
        {
            "title": "укр.doc",
            "url": self.generate_docservice_url(),
            "hash": "md5:" + "0" * 32,
            "format": "application/msword",
        },
        acc_token=self.complaint_owner_token,
    )

    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")


@mock.patch("openprocurement.tender.core.procedure.utils.RELEASE_2020_04_19", RELEASE_2020_04_19_TEST_ENABLED)
def create_tender_complaint_post_by_tender_owner_document_json(self):
    # make complaint status pending
    with change_auth(self.app, ("Basic", ("bot", ""))):
        response = self.patch_complaint({"status": "pending"}, self.complaint_owner_token)
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.json["data"]["status"], "pending")

    # create post by reviewer
    with change_auth(self.app, ("Basic", ("reviewer", ""))):
        response = self.post_post(
            {
                "title": "Lorem ipsum",
                "description": "Lorem ipsum dolor sit amet",
                "recipient": "tender_owner",
                "relatedObjection": self.objection_id,
            }
        )
    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")

    post = response.json["data"]

    self.post_id = post["id"]

    # create post by tender_owner
    response = self.post_post(
        {
            "title": "Lorem ipsum",
            "description": "Lorem ipsum dolor sit amet",
            "recipient": "aboveThresholdReviewers",
            "relatedPost": post["id"],
            "relatedObjection": self.objection_id,
        },
        acc_token=self.tender_token,
    )
    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")

    post = response.json["data"]

    self.post_id = post["id"]

    # create document by tender_owner
    response = self.post_post_document(
        {
            "title": "укр.doc",
            "url": self.generate_docservice_url(),
            "hash": "md5:" + "0" * 32,
            "format": "application/msword",
        },
        acc_token=self.tender_token,
    )

    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")


@mock.patch("openprocurement.tender.core.procedure.utils.RELEASE_2020_04_19", RELEASE_2020_04_19_TEST_ENABLED)
def put_tender_complaint_document_json(self):
    # make complaint status pending
    with change_auth(self.app, ("Basic", ("bot", ""))):
        response = self.patch_complaint({"status": "pending"}, self.complaint_owner_token)
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.json["data"]["status"], "pending")

    # create post by reviewer
    with change_auth(self.app, ("Basic", ("reviewer", ""))):
        response = self.post_post(
            {
                "title": "Lorem ipsum",
                "description": "Lorem ipsum dolor sit amet",
                "recipient": "complaint_owner",
                "relatedObjection": self.objection_id,
            }
        )
    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")

    post = response.json["data"]

    self.post_id = post["id"]

    # put document by reviewer
    with change_auth(self.app, ("Basic", ("reviewer", ""))):
        response = self.post_post_document(
            {
                "title": "укр.doc",
                "url": self.generate_docservice_url(),
                "hash": "md5:" + "0" * 32,
                "format": "application/msword",
            }
        )

    self.assertEqual(response.status, "201 Created")
    self.assertEqual(response.content_type, "application/json")

    document = response.json["data"]

    self.document_id = document["id"]

    # put document by complaint_owner
    response = self.put_post_document(
        {
            "title": "укр.doc",
            "url": self.generate_docservice_url(),
            "hash": "md5:" + "0" * 32,
            "format": "application/msword",
        },
        status=403,
        acc_token=self.complaint_owner_token,
    )

    self.assertEqual(response.status, "403 Forbidden")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(response.json["errors"][0]["description"], "Can update document only author")

    # put document by tender_owner
    response = self.put_post_document(
        {
            "title": "укр.doc",
            "url": self.generate_docservice_url(),
            "hash": "md5:" + "0" * 32,
            "format": "application/msword",
        },
        status=403,
        acc_token=self.tender_token,
    )

    self.assertEqual(response.status, "403 Forbidden")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(response.json["errors"][0]["description"], "Can update document only author")

    # make complaint status accepted
    with change_auth(self.app, ("Basic", ("reviewer", ""))):
        response = self.patch_complaint(
            {
                "status": "accepted",
                "reviewDate": get_now().isoformat(),
                "reviewPlace": "some",
            },
            self.complaint_owner_token,
        )
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.json["data"]["status"], "accepted")

    # put document by reviewer
    with change_auth(self.app, ("Basic", ("reviewer", ""))):
        response = self.put_post_document(
            {
                "title": "укр.doc",
                "url": self.generate_docservice_url(),
                "hash": "md5:" + "0" * 32,
                "format": "application/msword",
            },
            status=403,
        )

    self.assertEqual(response.status, "403 Forbidden")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(
        response.json["errors"][0]["description"],
        "Can submit or edit post not later than 3 full business days before reviewDate",
    )

    # change complaint reviewDate
    with change_auth(self.app, ("Basic", ("reviewer", ""))):
        response = self.patch_complaint(
            {
                "reviewDate": calculate_tender_full_date(
                    get_now(), POST_SUBMIT_TIME + timedelta(days=1), tender={}, working_days=True
                ).isoformat(),
            },
            self.complaint_owner_token,
        )
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.json["data"]["status"], "accepted")

    # put document by reviewer
    with change_auth(self.app, ("Basic", ("reviewer", ""))):
        response = self.put_post_document(
            {
                "title": "укр.doc",
                "url": self.generate_docservice_url(),
                "hash": "md5:" + "0" * 32,
                "format": "application/msword",
            }
        )
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.content_type, "application/json")


def create_complaint_post_explanation_invalid(self):
    with change_auth(self.app, ("Basic", ("bot", ""))):
        self.patch_complaint(
            {"status": "pending"},
            self.complaint_owner_token,
        )
    # make complaint status accepted
    with change_auth(self.app, ("Basic", ("reviewer", ""))):
        response = self.patch_complaint(
            {
                "status": "accepted",
                "reviewDate": get_now().isoformat(),
                "reviewPlace": "some",
            },
            self.complaint_owner_token,
        )
    self.assertEqual(response.status, "200 OK")
    self.assertEqual(response.json["data"]["status"], "accepted")

    # try to create post-explanation by tender owner with recipient
    response = self.post_post(
        {
            "title": "Lorem ipsum",
            "description": "Lorem ipsum dolor sit amet",
            "recipient": "complaint_owner",
            "relatedObjection": self.objection_id,
        },
        acc_token=self.tender_token,
        status=422,
    )
    self.assertEqual(
        response.json["errors"][0]["description"][0],
        "Forbidden to add recipient without relatedPost for ['complaint_owner', 'tender_owner']",
    )

    # try to add explanation without relatedObjection
    response = self.post_post(
        {
            "title": "Lorem ipsum",
            "description": "Lorem ipsum dolor sit amet",
        },
        acc_token=self.tender_token,
        status=422,
    )
    self.assertEqual(
        response.json["errors"][0],
        {"location": "body", "name": "relatedObjection", "description": ["This field is required."]},
    )

    # try to add explanation with invalid relatedObjection
    response = self.post_post(
        {
            "title": "Lorem ipsum",
            "description": "Lorem ipsum dolor sit amet",
            "relatedObjection": "foobar",
        },
        acc_token=self.tender_token,
        status=422,
    )
    self.assertEqual(
        response.json["errors"][0],
        {"location": "body", "name": "relatedObjection", "description": "should be one of complaint objections id"},
    )

    # try to add explanation without title
    response = self.post_post(
        {
            "description": "Lorem ipsum dolor sit amet",
            "relatedObjection": self.objection_id,
        },
        acc_token=self.tender_token,
        status=422,
    )
    self.assertEqual(
        response.json["errors"][0],
        {"location": "body", "name": "title", "description": ["This field is required."]},
    )

    # try to add explanation without description
    response = self.post_post(
        {
            "title": "Lorem ipsum",
            "relatedObjection": self.objection_id,
        },
        acc_token=self.tender_token,
        status=422,
    )
    self.assertEqual(
        response.json["errors"][0],
        {"location": "body", "name": "description", "description": ["This field is required."]},
    )

    # reviewDate too soon
    response = self.post_post(
        {
            "title": "Lorem ipsum",
            "description": "Lorem ipsum dolor sit amet",
            "relatedObjection": self.objection_id,
        },
        acc_token=self.tender_token,
        status=403,
    )
    self.assertEqual(response.status, "403 Forbidden")
    self.assertEqual(response.content_type, "application/json")
    self.assertEqual(
        response.json["errors"][0]["description"],
        "Can submit or edit post not later than 3 full business days before reviewDate",
    )

    # change reviewDate
    with change_auth(self.app, ("Basic", ("reviewer", ""))):
        self.patch_complaint(
            {
                "reviewDate": calculate_tender_full_date(
                    get_now(), POST_SUBMIT_TIME + timedelta(days=1), tender={}, working_days=True
                ).isoformat(),
            },
            self.complaint_owner_token,
        )

    # create successfully explanation
    response = self.post_post(
        {
            "title": "Lorem ipsum",
            "description": "Lorem ipsum dolor sit amet",
            "relatedObjection": self.objection_id,
        },
        acc_token=self.complaint_owner_token,
    )
    post_id = response.json["data"]["id"]

    # try to answer to explanation
    response = self.post_post(
        {
            "title": "Lorem ipsum",
            "description": "Lorem ipsum dolor sit amet",
            "relatedObjection": self.objection_id,
            "recipient": "aboveThresholdReviewers",
            "relatedPost": post_id,
        },
        acc_token=self.tender_token,
        status=422,
    )
    self.assertEqual(
        response.json["errors"][0],
        {"location": "body", "name": "relatedPost", "description": ["forbidden to answer to explanations"]},
    )


def create_complaint_post_explanation(self):
    with change_auth(self.app, ("Basic", ("bot", ""))):
        response = self.patch_complaint(
            {"status": "pending"},
            self.complaint_owner_token,
        )

    # create post-explanation by tender owner with recipient
    response = self.post_post(
        {
            "title": "Lorem ipsum",
            "description": "Lorem ipsum dolor sit amet",
            "relatedObjection": self.objection_id,
        },
        acc_token=self.tender_token,
    )
    self.assertEqual(response.status, "201 Created")
