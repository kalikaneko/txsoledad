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

class Sync(object):

    # needs:
    # .state
    # .sync_exchange_class -- pluggable!!

    # GET TODO
    @defer.inlineCallbacks
    def _start_sync(self, request, dbname, source_replica_uid):
        # TODO 1. get sync info for source replica uid
        # XXX this is stored in soledad state.ServerSyncState
        _utils.set_json_ctype(request)

        target = self.get_target(dbname)
        result = yield target.get_sync_info(source_replica_uid)

        response = {'target_replica_uid': result[0],
                    'target_replica_generation': result[1],
                    'target_replica_transaction_id': result[2],
                    'source_replica_uid': source_replica_uid,
                    'source_replica_generation': result[3],
                    'source_transaction_id': result[4]}
        defer.returnValue(json.dumps(response))

    # POST TODO 
    def _post_sync(self, request, dbname, source_replica_uid):
        _utils.set_json_ctype(request)
        args = request.args
        last_known_generation = args.get('last_known_generation')
        last_known_trans_id = args.get('last_known_trans_id')
        ensure = args.get('ensure')

        # XXX get database etc
        if ensure:
            db, self.replica_uid = foobar
        else:
            pass
        response = {'dbname': dbname, 'action': 'POST',
                    'sync-from': source_replica_uid}
        return json.dumps(response)

    # PUT TODO
    def _put_sync(self, request, dbname, source_replica_uid):
        _utils.set_json_ctype(request)
        response = {'dbname': dbname, 'action': 'PUT',
                    'sync-from': source_replica_uid}
        return json.dumps(response)

    def get_target(self, dbname):
        return self.state.open_database(dbname).get_sync_target()
