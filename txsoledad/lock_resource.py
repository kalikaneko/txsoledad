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
Syncing lock.
"""
import json

# TODO bring lock_resource from soledad_server
import _utils


class Lock(object):

    def _put_lock(self, request, source_replica_uid):
        _utils.set_json_ctype(request)
        response = {'put-lock': 'ok', 'uid': source_replica_uid, 'token':
                'aaa', 'timeout': '000'}
        return json.dumps(response)

    def _delete_lock(self, request, source_replica_uid):
        _utils.set_json_ctype(request)
        response = {'delete-lock': 'ok', 'uid': source_replica_uid}
        return json.dumps(response)

