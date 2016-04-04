# -*- coding: utf-8 -*-
# backend_couch.py
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
Soledad/u1db Backend based in couchdb.
"""
# FIXME: legacy @ leap.soledad.common.couch.__init__

from twisted.internet import defer
import paisley

from backend_soledad import SoledadBackend


# TODO -- this needs *extensive* migration to paisley.

class CouchDatabase(object):
    """
    A soledad/u1db compliant backend.
    """

    @classmethod
    def open_database(cls, dbname, create, ensure_ddocs=False, replica_uid=None,
                      database_security=None):
        """
        Returns a SoledadBackend instance.
        """

        db = cls(dbname, ensure_ddocs=ensure_ddocs,
                 database_security=database_security)
        return SoledadBackend(
            db, replica_uid=replica_uid)

    def __init__(self, dbname, ensure_ddocs=True, database_security=None):
        """
        :param url: Couch server URL with necessary credentials
        :type url: string
        :param dbname: Couch database name
        :type dbname: string
        :param ensure_ddocs: Ensure that the design docs exist on server.
        :type ensure_ddocs: bool
        :param database_security: security rules as CouchDB security doc
        :type database_security: dict
        """
        #self._session = Session(timeout=COUCH_TIMEOUT)
        #self._url = url
        self._dbname = dbname
        self._database = self.get_couch_database(dbname)
        self.batching = False
        self.batch_generation = None
        self.batch_docs = {}
        if ensure_ddocs:
            self.ensure_ddocs_on_db()
            self.ensure_security_ddoc(database_security)

    def get_couch_database(self, dbname):
        return paisley.CouchDB('localhost', dbName=dbname)

    @defer.inlineCallbacks
    def get_replica_gen_and_trans_id(self, other_replica_uid):
        """
        Return the last known generation and transaction id for the other db
        replica.

        When you do a synchronization with another replica, the Database keeps
        track of what generation the other database replica was at, and what
        the associated transaction id was.  This is used to determine what data
        needs to be sent, and if two databases are claiming to be the same
        replica.

        :param other_replica_uid: The identifier for the other replica.
        :type other_replica_uid: str

        :return: A tuple containing the generation and transaction id we
                 encountered during synchronization. If we've never
                 synchronized with the replica, this is (0, '').
        :rtype: (int, str)
        """
        doc_id = 'u1db_sync_%s' % other_replica_uid
        doc = yield self._database.openDoc(docId=doc_id)
        print "SYNC DOC IS...", doc

        result = tuple([doc['generation'], doc['transaction_id']])
        defer.returnValue(result)

    @defer.inlineCallbacks
    def get_generation_info(self):
        """
        Return the current generation.

        :return: A tuple containing the current generation and transaction id.
        :rtype: (int, str)
        """
        if self.batching and self.batch_generation:
            defer.returnValue(self.batch_generation)
        # query a couch list function
        ddoc_path = ['_design', 'transactions', '_list', 'generation', 'log']
        info = yield self.json_from_resource(ddoc_path)
        result = (info['generation'], info['transaction_id'])
        defer.returnValue(result)


    # TODO convert this to paisley..... views???? --------------------------
    # TODO What's the equivalent to "resource" in paisley ------------------
    @defer.inlineCallbacks
    def json_from_resource(self, ddoc_path, check_missing_ddoc=True,
                           **kwargs):
        """
        Get a resource from it's path and gets a doc's JSON using provided
        parameters, also checking for missing design docs by default.

        :param ddoc_path: The path to resource.
        :type ddoc_path: [str]
        :param check_missing_ddoc: Raises info on what design doc is missing.
        :type check_missin_ddoc: bool

        :return: The request's data parsed from JSON to a dict.
        :rtype: dict
        """
        # TODO lots of error handling were done here
        # TODO add patch to paisley for 'list' views... or whatever they are
        # called...
        ddoc_name = ddoc_path[1]
        if ddoc_path[2] == '_list':
            list_id = '/'.join(ddoc_path[3:])
            res = yield self._database.openList(docId=ddoc_name, listId=list_id)
        defer.returnValue(res)


    # TODO ------ patch paisley with this List stuff ----------------------
    def openList(self, dbName, docId, listId, **kwargs):
        uri = '/%s/_design/%s/_list/%s' % (dbName, quote(docId), listId)
        return self.get(uri).addCallback(self.parseResult)
    # ----------------------------------------------------------------------
    
    # TODO cache this?
    @defer.inlineCallbacks
    def get_replica_uid(self):
        doc = yield self._database.openDoc(docId='u1db_config')
        defer.returnValue(doc['replica_uid'])
