# -*- coding: utf-8 -*-
# state.py
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
Data structures that keep ServerState, using asynchronous couchdb connections
as a backend.
"""
# FIXME see legacy leap.soledad.common.couch.state

import paisley

from backend_couch import CouchDatabase


class ServerState(object):

    def __init__(self):
        self.db = paisley.CouchDB('localhost')

    def open_database(self, dbname):
        return CouchDatabase.open_database(dbname, create=False, ensure_ddocs=False)

    def open_shared_database(self):
        return paisley.CouchDB('localhost', dbName='shared')

    def create_dabase(self, dbname):
        return self.db.createDB(dbname)

    def check_database(self, dbname):
        pass

    def ensure_database(self, dbname):
        pass
