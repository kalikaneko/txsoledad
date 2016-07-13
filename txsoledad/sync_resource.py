# -*- coding: utf-8 -*-
# sync_resource.py
# Copyright (C) 2016 LEAP Encryption Acess Project
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Sync Resource.
"""
import json
from twisted.internet import defer

import _utils
from sync import SyncExchange

from leap.soledad.common.l2db import Document


class SyncExchangeCollection(object):
    """
    Primitive Sync Session management.
    It keeps SyncExchange objects in memory.

    This could be moved to a persistent data-store like Redis.
    """

    def __init__(self, state):
        self._d = {}
        self.state = state

    def get_or_create(self, dbname, source_replica_uid, gen, sync_id):
        # TODO is it enough to index by the sync_id alone?
        sync_exch = self._d.get(sync_id, None)
        if not sync_exch:
            sync_exch = self._create_sync_exch(
                dbname, source_replica_uid, gen, sync_id)
            self._d[sync_id] = sync_exch
        return sync_exch

    def _create_sync_exch(self, dbname, source_replica_uid, gen, sync_id):
        db = self.state.open_database(dbname)
        return SyncExchange(db, source_replica_uid, gen, sync_id)


class Sync(object):

    @defer.inlineCallbacks
    def _start_sync(self, request, dbname, source_replica_uid):
        # XXX this is stored in soledad state.ServerSyncState
        _utils.set_json_ctype(request)

        target = self.get_target(dbname)
        sync_info = yield target.get_sync_info(source_replica_uid)

        response = {'target_replica_uid': sync_info[0],
                    'target_replica_generation': sync_info[1],
                    'target_replica_transaction_id': sync_info[2],
                    'source_replica_uid': source_replica_uid,
                    'source_replica_generation': sync_info[3] or 0,
                    'source_transaction_id': sync_info[4] or ''}
        defer.returnValue(json.dumps(response))

    @defer.inlineCallbacks
    def _post_sync(self, request, dbname, source_replica_uid):

        ctype = request.getHeader('content-type')
        if ctype == 'application/x-soledad-sync-put':
            doctype = 'INCOMING'  # incoming docs
        elif ctype == 'application/x-soledad-sync-get':
            doctype = 'OUTGOING'  # outgoing docs
        else:
            raise RuntimeError('Bad Request!')

        # TODO use a stream parser instead
        payload = request.content.read()
        body = json.loads(payload)

        # FIXME make batching work!!
        args, doc = body
        sync_id = args.get('sync_id')
        last_known_gen = args.get('last_known_generation')
        # last_known_trans_id = args.get('last_known_trans_id')
        # ensure = args.get('ensure')
        # TODO -- should validate the info client has about server replica
        # db.validate_gen_and_trans_id(gen, last_known_trans_id)

        sync_col = getattr(self, 'sync_collection', None)
        if not sync_col:
            sync_col = SyncExchangeCollection(self.state)
            self.sync_col = sync_col

        sync_exch = sync_col.get_or_create(
            dbname, source_replica_uid, last_known_gen, sync_id)

        if doctype == 'INCOMING':
            trans_id = doc['trans_id']
            gen = doc['gen']
            response = yield self._process_incoming_doc(
                sync_exch,
                dbname, source_replica_uid,  # TODO -- remove these?
                doc, gen, trans_id)
        elif doctype == 'OUTGOING':
            received = doc['received']
            response = yield self._process_outgoing_doc(
                sync_exch,
                dbname, received)

        # FIXME -- used???
        # request.setHeader('new_generation', new_gen)
        # request.setHeader('new_transaction_id', self.sync_exch.new_trans_id)
        # request.setHeader('replica_uid', self.replica_uid)

        request.setHeader(
            'content-type',
            'application/x-soledad-sync-response')

        # each item needs to be on its own line, for the client to
        # parse the stream correctly.
        payload = ',\n'.join([json.dumps(item) for item in response])
        defer.returnValue('[\n' + payload + '\n]')

    @defer.inlineCallbacks
    def _process_incoming_doc(self, sync_exch, dbname, source_replica_uid,
                              doc_data, gen, trans_id):
        # TODO --- When batching enabled, at the end we SHOULD trigger a
        # sync_exch.batched_insert_from_source(staging, sync_id)
        # sync_exch.insert_doc_from_source(doc, gen, trans_id)
        # -----------------------------------------------------------
        id = doc_data['id']
        rev = doc_data['rev']
        content = doc_data['content']
        number_of_docs = doc_data['number_of_docs']
        doc_idx = doc_data['doc_idx']

        doc = Document(id, rev, content)
        yield sync_exch.insert_doc_from_source(
            doc, gen, trans_id,
            number_of_docs=number_of_docs,
            doc_idx=doc_idx)

        new_gen, new_trans_id = yield sync_exch._db._get_generation_info()
        response = {
            'new_transaction_id': new_trans_id,
            'new_generation': new_gen}
        defer.returnValue([response])

    @defer.inlineCallbacks
    def _process_outgoing_doc(self, sync_exch, dbname, received):
        new_gen, number_of_changes = yield sync_exch.find_changes_to_return(
            received)

        # FIXME -- used?
        # header[new_generation] = new_gen
        # header[new_transaction_id] = sync_exch.new_trans_id
        # header[number_of_changes] = number_of_changes
        # header[replica_uid] = replica_uid

        docs = []

        def append_doc(doc, gen, trans_id):
            entry = dict(id=doc.doc_id, rev=doc.rev, content=doc.get_json(),
                         gen=gen, trans_id=trans_id)
            docs.append(entry)

        yield sync_exch.return_one_doc(append_doc)

        new_gen, new_trans_id = yield sync_exch._db._get_generation_info()
        status = {
            'new_transaction_id': new_trans_id,
            'new_generation': new_gen,
            'number_of_changes': number_of_changes}
        defer.returnValue([status] + docs)

    @defer.inlineCallbacks
    def _put_sync(self, request, dbname, source_replica_uid):
        payload = request.content.read()
        body = json.loads(payload)
        generation = body['generation']
        trans_id = body['transaction_id']

        yield self.get_target(dbname).record_sync_info(
            source_replica_uid, generation, trans_id)

        _utils.set_json_ctype(request)
        response = {'ok': True}
        defer.returnValue(json.dumps(response))

    # Utils

    def get_target(self, dbname):
        db = self.state.open_database(dbname)
        return db.get_sync_target()
