# -*- coding: utf-8 -*-
# lock_resource.py
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
Shared Database Resource.
"""
import json

from twisted.internet import defer

import _utils


class Shared(object):

    @defer.inlineCallbacks
    def _get_shared_doc(self, request, shared_doc):
        _utils.set_json_ctype(request)

        shared = self.state.open_shared_database()

        request.setHeader('x-u1db-rev', '')
        request.setHeader('x-u1db-has-conflicts', 'false')

        try:
            doc = yield shared.openDoc(docId=shared_doc)
            response = doc.content
        except Exception:
            request.setResponseCode(404)
            response = {'error': 'document does not exist'}
        defer.returnValue(json.dumps(response))

    @defer.inlineCallbacks
    def _put_shared_doc(self, request, shared_doc):
        shared = self.state.open_shared_database()
        body = json.loads(request.content.read())
        yield shared.saveDoc(body, docId=shared_doc)
        defer.returnValue(json.dumps({'put': 'ok', 'rev': '0'}))
