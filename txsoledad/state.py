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
Data structures that keep state on the server.
"""

import paisley


class ServerState(object):

    def __init__(self):
        self.db = paisley.CouchDB('localhost')

    def create_dabase(self, dbname):
        return self.db.createDB(dbname)

    def check_database(self, dbname):
        pass

    def ensure_database(self, dbname):
        pass
