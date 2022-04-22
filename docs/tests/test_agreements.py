# -*- coding: utf-8 -*-
import os
from copy import deepcopy
from datetime import timedelta
from uuid import uuid4

from openprocurement.api.utils import get_now
from openprocurement.tender.cfaua.tests.base import (
    BaseTenderWebTest, test_tender_data, test_lots
)
from openprocurement.framework.electroniccatalogue.tests.base import (
    test_electronicCatalogue_data,
    ban_milestone_data_with_documents,
    disqualification_milestone_data_with_documents,
    BaseElectronicCatalogueWebTest,
)

from tests.base.data import tenderer
from tests.base.test import DumpsWebTestApp, MockWebTestMixin
from tests.base.constants import DOCS_URL

BASE_DIR = 'docs/source/agreements/http/'
TARGET_DIR = BASE_DIR + "cfaua/"


class TenderResourceTest(BaseTenderWebTest, MockWebTestMixin):
    AppClass = DumpsWebTestApp

    relative_to = os.path.dirname(__file__)
    docservice = True
    docservice_url = DOCS_URL
    database_keys = ("agreements",)
    enable_couch = True

    def setUp(self):
        super(TenderResourceTest, self).setUp()
        self.setUpMock()

    def tearDown(self):
        self.tearDownMock()
        super(TenderResourceTest, self).tearDown()

    def test_docs(self):
        self.app.authorization = ('Basic', ('broker', ''))

        # empty tenders listing
        response = self.app.get('/tenders')
        self.assertEqual(response.json['data'], [])

        # create cfaua tender, first prepare data
        lot = deepcopy(test_lots[0])
        lot['id'] = uuid4().hex
        test_tender_data['lots'] = [lot]
        test_tender_data['items'][0]['relatedLot'] = lot['id']
        test_tender_data["tenderPeriod"]["endDate"] = (get_now() + timedelta(days=31)).isoformat()

        response = self.app.post_json('/tenders', {'data': test_tender_data})
        tender_id = self.tender_id = response.json['data']['id']
        owner_token = response.json['access']['token']

        # switch to complete - dirty hack
        self.set_status('complete')

        # check status
        with open(TARGET_DIR + 'example_tender.http', 'wb') as self.app.file_obj:
            response = self.app.get('/tenders/{}'.format(tender_id))
            self.assertEqual(response.json['data']['status'], 'complete')
            tender = response.json['data']

        with open(TARGET_DIR + 'example_agreement.http', 'wb') as self.app.file_obj:
            response = self.app.get('/tenders/{}/agreements/{}'.format(
                tender_id, response.json['data']['agreements'][0]['id']))
        test_agreement_data = response.json['data']

        # empty agreements listing
        request_path = '/agreements'

        #### Exploring basic rules
        with open(TARGET_DIR + 'agreements-listing-0.http', 'wb') as self.app.file_obj:
            self.app.authorization = None
            response = self.app.get(request_path)
            self.assertEqual(response.status, '200 OK')

        #### Sync agreement (i.e. simulate agreement databridge sync actions)

        self.app.authorization = ('Basic', ('contracting', ''))

        response = self.app.get('/tenders/{}/extract_credentials'.format(tender_id))
        test_agreement_data['owner'] = response.json['data']['owner']
        test_agreement_data['tender_token'] = response.json['data']['tender_token']
        test_agreement_data['tender_id'] = tender_id
        test_agreement_data['procuringEntity'] = tender['procuringEntity']

        self.app.authorization = ('Basic', ('agreements', ''))
        response = self.app.post_json(request_path, {'data': test_agreement_data})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.json['data']['status'], 'active')
        self.app.get(request_path)  # need to start couchdb indexing views, so next request gives results

        # Getting agreement
        self.app.authorization = None

        with open(TARGET_DIR + 'agreement-view.http', 'wb') as self.app.file_obj:
            response = self.app.get('/agreements/{}'.format(test_agreement_data['id']))
            self.assertEqual(response.status, '200 OK')
            agreement = response.json['data']

        # Getting access
        self.app.authorization = ('Basic', ('broker', ''))
        with open(TARGET_DIR + 'agreement-credentials.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/agreements/{}/credentials?acc_token={}'.format(
                    test_agreement_data['id'], owner_token))
            self.assertEqual(response.status, '200 OK')
        agreement_token = response.json['access']['token']
        agreement_id = test_agreement_data['id']

        with open(TARGET_DIR + 'agreements-listing-1.http', 'wb') as self.app.file_obj:
            response = self.app.get(request_path)
            self.assertEqual(response.status, '200 OK')
            self.assertEqual(len(response.json['data']), 1)

        # Modifying agreement

        # Submitting agreement change
        with open(TARGET_DIR + 'add-agreement-change.http', 'wb') as self.app.file_obj:
            response = self.app.post_json(
                '/agreements/{}/changes?acc_token={}'.format(
                    agreement_id, agreement_token),
                {'data': {
                    'rationale': 'Опис причини змін егріменту',
                    'rationale_en': 'Agreement change cause',
                    'rationaleType': 'taxRate'
                }})
            self.assertEqual(response.status, '201 Created')
            change = response.json['data']

        with open(TARGET_DIR + 'view-agreement-change.http', 'wb') as self.app.file_obj:
            response = self.app.get('/agreements/{}/changes/{}'.format(agreement_id, change['id']))
            self.assertEqual(response.status, '200 OK')
            self.assertEqual(response.json['data']['id'], change['id'])

        with open(TARGET_DIR + 'patch-agreement-change.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/agreements/{}/changes/{}?acc_token={}'.format(
                    agreement_id, change['id'], agreement_token),
                {'data': {'rationale': 'Друга і третя поставка має бути розфасована'}})
            self.assertEqual(response.status, '200 OK')
            change = response.json['data']

        # add agreement change document
        with open(TARGET_DIR + 'add-agreement-change-document.http', 'wb') as self.app.file_obj:
            response = self.app.post('/agreements/{}/documents?acc_token={}'.format(
                agreement_id, agreement_token),
                upload_files=[('file', 'agreement_changes.doc', b'content')])
            self.assertEqual(response.status, '201 Created')
            doc_id = response.json["data"]['id']

        with open(TARGET_DIR + 'set-document-of-change.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/agreements/{}/documents/{}?acc_token={}'.format(
                    agreement_id, doc_id, agreement_token),
                {"data": {
                    "documentOf": "change",
                    "relatedItem": change['id'],
                }})
            self.assertEqual(response.status, '200 OK')

        # patching change with modification
        with open(TARGET_DIR + 'add-agreement-change-modification.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/agreements/{}/changes/{}?acc_token={}'.format(
                    agreement_id, change['id'], agreement_token),
                {'data': {
                    'modifications': [{
                        'itemId': agreement['items'][0]['id'],
                        'factor': 0.1605
                    }]
                }})
            self.assertEqual(response.status, '200 OK')
            change = response.json['data']

        # preview agreement
        with open(TARGET_DIR + 'agreement_preview.http', 'wb') as self.app.file_obj:
            response = self.app.get('/agreements/{}/preview?acc_token={}'.format(agreement_id, agreement_token))
            self.assertEqual(response.status, '200 OK')

        # apply agreement change
        with open(TARGET_DIR + 'apply-agreement-change.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/agreements/{}/changes/{}?acc_token={}'.format(
                    agreement_id, change['id'], agreement_token),
                {'data': {'status': 'active', 'dateSigned': get_now().isoformat()}})
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_DIR + 'view-all-agreement-changes.http', 'wb') as self.app.file_obj:
            response = self.app.get('/agreements/{}/changes'.format(agreement_id))
            self.assertEqual(response.status, '200 OK')
            self.assertEqual(len(response.json['data']), 1)

        with open(TARGET_DIR + 'view-agreement.http', 'wb') as self.app.file_obj:
            response = self.app.get('/agreements/{}'.format(agreement_id))
            self.assertEqual(response.status, '200 OK')
            self.assertIn('changes', response.json['data'])

        # Uploading documentation
        with open(TARGET_DIR + 'upload-agreement-document.http', 'wb') as self.app.file_obj:
            response = self.app.post('/agreements/{}/documents?acc_token={}'.format(
                agreement_id, agreement_token),
                upload_files=[('file', 'agreement.doc', b'content')])

        with open(TARGET_DIR + 'agreement-documents.http', 'wb') as self.app.file_obj:
            response = self.app.get('/agreements/{}/documents?acc_token={}'.format(
                agreement_id, agreement_token))

        with open(TARGET_DIR + 'upload-agreement-document-2.http', 'wb') as self.app.file_obj:
            response = self.app.post('/agreements/{}/documents?acc_token={}'.format(
                agreement_id, agreement_token),
                upload_files=[('file', 'agreement_additional_docs.doc', b'additional info')])

        doc_id = response.json['data']['id']

        with open(TARGET_DIR + 'upload-agreement-document-3.http', 'wb') as self.app.file_obj:
            response = self.app.put('/agreements/{}/documents/{}?acc_token={}'.format(
                agreement_id, doc_id, agreement_token),
                upload_files=[('file', 'agreement_additional_docs.doc', b'extended additional info')])

        with open(TARGET_DIR + 'get-agreement-document-3.http', 'wb') as self.app.file_obj:
            response = self.app.get('/agreements/{}/documents/{}?acc_token={}'.format(
                agreement_id, doc_id, agreement_token))

        # Finalize agreement
        with open(TARGET_DIR + 'agreement-termination.http', 'wb') as self.app.file_obj:
            response = self.app.patch_json(
                '/agreements/{}?acc_token={}'.format(
                    agreement_id, agreement_token),
                {'data': {"status": "terminated"}})
            self.assertEqual(response.status, '200 OK')


TARGET_EC_DIR = BASE_DIR + "frameworks/"


class ElectronicCatalogueResourceTest(BaseElectronicCatalogueWebTest, MockWebTestMixin):
    AppClass = DumpsWebTestApp

    relative_to = os.path.dirname(__file__)
    initial_data = test_electronicCatalogue_data
    docservice = True
    docservice_url = DOCS_URL

    def setUp(self):
        super(ElectronicCatalogueResourceTest, self).setUp()
        self.setUpMock()

    def tearDown(self):
        self.tearDownMock()
        super(ElectronicCatalogueResourceTest, self).tearDown()

    def test_docs(self):
        self.create_framework()
        auth = self.app.authorization
        self.set_status("active")

        self.tick(delta=timedelta(days=16))

        self.app.authorization = ('Basic', ('broker', ''))

        response = self.app.post_json(
            '/submissions',
            {'data': {
                "tenderers": [tenderer],
                "frameworkID": self.framework_id,
            }}
        )
        self.submission_1_id = response.json["data"]["id"]
        self.submission_1_token = response.json["access"]["token"]

        local_tenderer = deepcopy(tenderer)
        local_tenderer["identifier"]["id"] = "00137257"

        response = self.app.post_json(
            '/submissions',
            {'data': {
                "tenderers": [local_tenderer],
                "frameworkID": self.framework_id,
            }}
        )
        self.submission_2_id = response.json["data"]["id"]
        self.submission_2_token = response.json["access"]["token"]

        response = self.app.patch_json(
            f'/submissions/{self.submission_1_id}?acc_token={self.submission_1_token}',
            {'data': {"status": "active"}},
        )
        self.qualification_1_id = response.json["data"]["qualificationID"]

        response = self.app.patch_json(
            f'/submissions/{self.submission_2_id}?acc_token={self.submission_2_token}',
            {'data': {"status": "active"}},
        )
        self.qualification_2_id = response.json["data"]["qualificationID"]

        request_path = "/agreements"
        with open(TARGET_EC_DIR + 'agreements-listing-0.http', 'wb') as self.app.file_obj:
            self.app.authorization = None
            response = self.app.get(request_path)
            self.assertEqual(response.status, '200 OK')


        self.app.authorization = auth

        response = self.app.patch_json(
            f'/qualifications/{self.qualification_1_id}?acc_token={self.framework_token}',
            {'data': {"status": "active"}},
        )

        response = self.app.patch_json(
            f'/qualifications/{self.qualification_2_id}?acc_token={self.framework_token}',
            {'data': {"status": "active"}},
        )

        response = self.app.get(f"/frameworks/{self.framework_id}")
        self.agreement_id = response.json["data"]["agreementID"]

        with open(TARGET_EC_DIR + 'example-framework.http', 'wb') as self.app.file_obj :
            response = self.app.get(f'/frameworks/{self.framework_id}')
            self.assertEqual(response.status, '200 OK')

        with open(TARGET_EC_DIR + 'agreement-view.http', 'wb') as self.app.file_obj:
            response = self.app.get(f'/agreements/{self.agreement_id}')
            self.assertEqual(response.status, '200 OK')

        contract_1_id = response.json['data']['contracts'][0]['id']
        contract_2_id = response.json['data']['contracts'][1]['id']

        ban_milestone = deepcopy(ban_milestone_data_with_documents)
        ban_milestone["documents"][0]["url"] = self.generate_docservice_url()

        with open(TARGET_EC_DIR + 'post-milestone-ban.http', 'wb') as self.app.file_obj:
            response = self.app.post_json(
                f"/agreements/{self.agreement_id}/contracts/{contract_1_id}/milestones?acc_token={self.framework_token}",
                {'data': ban_milestone},
            )

        disqualification_milestone = deepcopy(disqualification_milestone_data_with_documents)
        disqualification_milestone["documents"][0]["url"] = self.generate_docservice_url()

