# -*- coding: utf-8 -*-
from copy import deepcopy

# TenderSwitchPreQualificationResourceTest


def active_tendering_to_pre_qual(self):
    response = self.set_status('active.tendering', 'end')
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']["status"], "active.tendering")
    self.app.authorization = ('Basic', ('chronograph', ''))
    response = self.app.patch_json('/tenders/{}'.format(self.tender_id), {'data': {'id': self.tender_id}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']["status"], "active.pre-qualification")


def pre_qual_switch_to_stand_still(self):
    self.set_status('active.pre-qualification', 'end')
    self.app.authorization = ('Basic', ('chronograph', ''))
    response = self.app.patch_json('/tenders/{}'.format(self.tender_id), {'data': {'id': self.tender_id}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']["status"], "active.pre-qualification")

# TenderSwitchAuctionResourceTest


def switch_to_auction(self):
    response = self.set_status('active.pre-qualification.stand-still', 'end')
    self.assertEqual(response.json['data']["status"], "active.pre-qualification.stand-still")
    self.app.authorization = ('Basic', ('chronograph', ''))
    response = self.app.patch_json('/tenders/{}'.format(self.tender_id), {'data': {'id': self.tender_id}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']["status"], "active.auction")


# TenderComplaintSwitchResourceTest


def switch_to_complaint(self):
    user_data = deepcopy(self.author_data)
    for status in ['invalid', 'resolved', 'declined']:
        response = self.app.post_json('/tenders/{}/complaints'.format(self.tender_id), {'data': {
            'title': 'complaint title',
            'description': 'complaint description',
            'author': user_data,
            'status': 'claim'
        }})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.json['data']['status'], 'claim')
        complaint = response.json['data']

        response = self.app.patch_json('/tenders/{}/complaints/{}?acc_token={}'.format(self.tender_id, complaint['id'], self.tender_token), {"data": {
            "status": "answered",
            "resolution": status * 4,
            "resolutionType": status
        }})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data']["status"], "answered")
        self.assertEqual(response.json['data']["resolutionType"], status)
    response = self.set_status(self.initial_status, 'end')
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']["status"], "active.tendering")
    self.app.authorization = ('Basic', ('chronograph', ''))
    response = self.app.patch_json('/tenders/{}'.format(self.tender_id), {'data': {'id': self.tender_id}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']["status"], "active.pre-qualification")
    self.assertEqual(response.json['data']["complaints"][-1]['status'], status)


def switch_to_unsuccessful(self):
    self.set_status(self.initial_status, 'end')
    self.app.authorization = ('Basic', ('chronograph', ''))
    response = self.app.patch_json('/tenders/{}'.format(self.tender_id), {'data': {'id': self.tender_id}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']["status"], "unsuccessful")
    if self.initial_lots:
        self.assertEqual(set([i['status'] for i in response.json['data']["lots"]]), set(["unsuccessful"]))


# TenderSwitchPreQualificationStandStillResourceTest


def switch_to_awarded(self):
    self.set_status(self.initial_status, 'end')
    self.app.authorization = ('Basic', ('chronograph', ''))
    response = self.app.patch_json('/tenders/{}'.format(self.tender_id), {'data': {'id': self.tender_id}})
    self.assertEqual((response.status, response.content_type), ('200 OK', 'application/json'))

    self.assertEqual(response.json['data']['status'], 'active.awarded')
    self.assertEqual(len(response.json['data']['agreements']), 1)
    self.app.authorization = ('Basic', ('broker', ''))
    self.assertEqual(response.json['data']['features'], response.json['data']['agreements'][0]['features'])
