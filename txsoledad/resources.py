# -*- coding: utf-8 -*-
# resources.py
# Copyright (C) 2016 LEAP Encryption Access Project
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

"""
import json

import u1db


class Global(object):

    def _info(self, request):
        _set_json_ctype(request)
        response = {
            'u1db_version': u1db.__version__,
            'soledad_version': '0.10.0'}
        return json.dumps(response)


class Database(object):

    def _create_database(self, request, dbname):
        def createdCb(ignored):
            response = {'created': 'ok'}
            return json.dumps(response)

        _set_json_ctype(request)
        d = self.state.db.createDB(dbname)
        d.addCallback(createdCb)
        return d

    # TODO
    def _update_database(self, request, dbname):
        _set_json_ctype(request)
        try:
            body = json.loads(request.content.read())
        except ValueError:
            body = ''
        self._items[dbname] = body
        return json.dumps({'success': 'NOT IMPLEMENTED'})

    # TODO
    def _delete_database(self, request, dbname):
        request.setHeader('Content-Type', 'application/json')
        response = {'deleted': 'NOT IMPLEMENTED'}
        return json.dumps(response)


class AllDocs(object):

    def _get_all_docs(self, request, dbname):
        def get_all_docs_Cb(result):
            response = {'result': result}
            return json.dumps(response)

        _set_json_ctype(request)
        d = self.state.db.listDoc(dbname)
        d.addCallback(get_all_docs_Cb)
        return d


class Documents(object):

    # TODO
    def _get_docs(self, request, dbname):
        _set_json_ctype(request)
        response = {'result': []}
        return json.dumps(response)


class Document(object):

    def _get_doc(self, request, dbname, doc_id):
        def _get_doc_cb(result):
            response = {'result': result, 'action': 'GET'}
            return json.dumps(response)

        _set_json_ctype(request)
        d = self.state.db.openDoc(dbname, doc_id)
        d.addCallback(_get_doc_cb)
        return d

    def _update_doc(self, request, dbname, doc_id):
        def _update_doc_cb(result):
            response = {'result': 'ok', 'action': 'PUT'}
            return json.dumps(response)

        _set_json_ctype(request)
        _body = json.loads(request.content.getvalue())
        body = {"content": _body['body']}
        d = self.state.db.saveDoc(
            dbname, json.dumps(body),
            docId=unicode(doc_id))
        d.addCallback(_update_doc_cb)
        return d

    def _delete_doc(self, request, dbname, doc_id):
        _set_json_ctype(request)
        response = {'result': 'NOT IMPLEMENTED', 'action': 'DELETE'}
        return json.dumps(response)


class Sync(object):

    # needs:
    # .responder
    # .state
    # .replica_uid
    # .sync_exchange_class -- pluggable!!

    # GET
    def _start_sync(self, request, dbname, source_replica_uid):
        _set_json_ctype(request)
        response = {'dbname': dbname, 'action': 'GET',
                    'sync-from': source_replica_uid}
        return json.dumps(response)

    # PUT
    def _put_sync(self, request, dbname, source_replica_uid):
        _set_json_ctype(request)
        response = {'dbname': dbname, 'action': 'PUT',
                    'sync-from': source_replica_uid}
        return json.dumps(response)

    # POST
    def _post_sync(self, request, dbname, source_replica_uid):
        _set_json_ctype(request)
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

    def get_target(self):
        return self.state.open_database(self.dbname).get_sync_target()


def _set_json_ctype(request):
    request.setHeader('Content-Type', 'application/json')