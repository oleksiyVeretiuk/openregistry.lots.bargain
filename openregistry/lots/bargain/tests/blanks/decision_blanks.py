# -*- coding: utf-8 -*-
from copy import deepcopy

from openregistry.lots.core.utils import (
    get_now,
)
from openregistry.lots.bargain.tests.fixtures import (
    check_patch_status_200,
    move_lot_to_pending,
    move_lot_to_verification
)


def create_decision(self):
    self.app.authorization = ('Basic', ('broker', ''))

    decision_data = deepcopy(self.initial_decision_data)

    response = self.app.get('/{}'.format(self.resource_id))
    old_decs_count = len(response.json['data'].get('decisions', []))

    decision_data.update({
        'relatedItem': '1' * 32,
        'decisionOf': 'asset'
    })
    response = self.app.post_json(
        '/{}/decisions'.format(self.resource_id),
        {"data": decision_data},
        headers=self.access_header
    )
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.json['data']['decisionDate'], decision_data['decisionDate'])
    self.assertEqual(response.json['data']['decisionID'], decision_data['decisionID'])
    self.assertEqual(response.json['data']['decisionOf'], 'lot')
    self.assertNotIn('relatedItem', response.json['data'])

    response = self.app.get('/{}'.format(self.resource_id))
    present_decs_count = len(response.json['data'].get('decisions', []))
    self.assertEqual(old_decs_count + 1, present_decs_count)


def patch_decision(self):
    self.app.authorization = ('Basic', ('broker', ''))
    self.initial_status = 'draft'
    self.create_resource()

    move_lot_to_pending(self, {'id': self.resource_id}, self.access_header)

    self.app.authorization = ('Basic', ('broker', ''))
    decisions = self.app.get('/{}/decisions'.format(self.resource_id)).json['data']
    asset_decision_id = filter(lambda d: d['decisionOf'] == 'asset', decisions)[0]['id']
    lot_decision_id = filter(lambda d: d['decisionOf'] == 'lot', decisions)[0]['id']

    decision_data = {'title': 'Some Title'}
    response = self.app.patch_json(
        '/{}/decisions/{}'.format(self.resource_id, asset_decision_id),
        params={'data': decision_data},
        status=403,
        headers=self.access_header
    )
    self.assertEqual(response.status, '403 Forbidden')
    self.assertEqual(
        response.json['errors'][0]['description'],
        'Can edit only decisions which have decisionOf equal to \'lot\'.'
    )

    response = self.app.patch_json(
        '/{}/decisions/{}'.format(self.resource_id, lot_decision_id),
        params={'data': decision_data},
        headers=self.access_header
    )
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.json['data']['id'], lot_decision_id)
    self.assertEqual(response.json['data']['title'], decision_data['title'])


def patch_decisions_with_lot_by_concierge(self):
    self.app.authorization = ('Basic', ('broker', ''))
    self.initial_status = 'draft'
    self.create_resource()

    decision_data = [
        {
            'decisionID': 'decID',
            'decisionDate': get_now().isoformat(),
            'relatedItem': '1' * 32,
            'decisionOf': 'asset'
        }
    ]
    decision_data = {
        'decisions': decision_data
    }

    move_lot_to_verification(self, {'id': self.resource_id}, self.access_header)

    self.app.authorization = ('Basic', ('concierge', ''))
    response = self.app.patch_json(
        '/{}'.format(self.resource_id),
        params={'data': decision_data},
        headers=self.access_header
    )
    decision = response.json['data']['decisions'][0]
    self.assertEqual(decision['decisionID'], decision_data['decisions'][0]['decisionID'])
    self.assertEqual(decision['decisionDate'], decision_data['decisions'][0]['decisionDate'])
    self.assertEqual(decision['relatedItem'], decision_data['decisions'][0]['relatedItem'])
    self.assertEqual(decision['decisionOf'], decision_data['decisions'][0]['decisionOf'])
    decision_id = decision['id']

    response = self.app.get('/{}/decisions/{}'.format(self.resource_id, decision_id))
    self.assertEqual(response.json['data']['id'], decision_id)
    self.assertEqual(response.json['data']['decisionID'], decision_data['decisions'][0]['decisionID'])
    self.assertEqual(response.json['data']['decisionDate'], decision_data['decisions'][0]['decisionDate'])
    self.assertEqual(response.json['data']['relatedItem'], decision_data['decisions'][0]['relatedItem'])
    self.assertEqual(response.json['data']['decisionOf'], decision_data['decisions'][0]['decisionOf'])


def create_or_patch_decision_in_not_allowed_status(self):
    self.app.authorization = ('Basic', ('broker', ''))
    self.initial_status = 'draft'
    self.create_resource()

    move_lot_to_verification(self, {'id': self.resource_id}, self.access_header)

    decision_data = {
        'decisionDate': get_now().isoformat(),
        'decisionID': 'decisionLotID'
    }
    response = self.app.post_json(
        '/{}/decisions'.format(self.resource_id),
        {"data": decision_data},
        headers=self.access_header,
        status=403
    )
    self.assertEqual(response.status, '403 Forbidden')
    self.assertEqual(
        response.json['errors'][0]['description'],
        'Can\'t update decisions in current (verification) lot status'
    )


def patch_decisions_with_lot_by_broker(self):
    self.app.authorization = ('Basic', ('broker', ''))
    self.initial_status = 'draft'
    self.create_resource()

    decision_data = [
        {
            'decisionID': 'decID',
            'decisionDate': get_now().isoformat()
        },
        {
            'decisionID': 'decID2',
            'decisionDate': get_now().isoformat()
        }
    ]
    decision_data = {
        'decisions': decision_data
    }

    check_patch_status_200(self, '/{}'.format(self.resource_id), 'composing', self.access_header)
    response = self.app.patch_json(
        '/{}'.format(self.resource_id),
        params={'data': decision_data},
        headers=self.access_header
    )
    self.assertNotIn('decisions', response.json)


def create_decisions_with_lot(self):
    data = deepcopy(self.initial_data)
    decision_1 = {'id': '1' * 32, 'decisionID': 'decID', 'decisionDate': get_now().isoformat()}
    decision_2 = deepcopy(decision_1)
    decision_2['id'] = '2' * 32
    data['decisions'] = [
        decision_1, decision_2
    ]
    response = self.app.post_json('/', params={'data': data})
    decision_1['decisionOf'] = 'lot'
    decision_2['decisionOf'] = 'lot'
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(len(response.json['data']['decisions']), 2)
    self.assertEqual(response.json['data']['decisions'][0], decision_1)
    self.assertEqual(response.json['data']['decisions'][1], decision_2)

    del decision_1['decisionOf']
    del decision_2['decisionOf']

    decision_2['id'] = '1' * 32
    data['decisions'] = [
        decision_1, decision_2
    ]
    response = self.app.post_json('/', params={'data': data}, status=422)
    self.assertEqual(response.status, '422 Unprocessable Entity')
    self.assertEqual(
        response.json['errors'][0]['description'][0],
        u'Decision id should be unique for all decisions'
    )
