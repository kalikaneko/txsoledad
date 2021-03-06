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
import json
import paisley
import time

from twisted.internet import defer

from leap.soledad.common.document import ServerDocument
from backend_soledad import SoledadBackend


class NoDesignDocError(Exception):
    pass


# TODO -- this needs *extensive* migration to paisley.

class CouchDatabase(object):
    """
    A soledad/u1db compliant backend.
    """

    @classmethod
    def open_database(cls, dbname, create, ensure_ddocs=False,
                      replica_uid=None, database_security=None):
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
        try:
            doc = yield self._database.openDoc(docId=doc_id)

        except Exception:
            replica = {'generation': None, 'transaction_id': None}
            yield self._database.saveDoc(replica, docId=doc_id)
            doc = yield self._database.openDoc(docId=doc_id)

        result = tuple([doc['generation'], doc['transaction_id']])
        defer.returnValue(result)

    @defer.inlineCallbacks
    def whats_changed(self, old_generation=0):
        """
        Return a list of documents that have changed since old_generation.

        :param old_generation: The generation of the database in the old
                               state.
        :type old_generation: int

        :return: (generation, trans_id, [(doc_id, generation, trans_id),...])
                 The current generation of the database, its associated
                 transaction id, and a list of of changed documents since
                 old_generation, represented by tuples with for each document
                 its doc_id and the generation and transaction id corresponding
                 to the last intervening change and sorted by generation (old
                 changes first)
        :rtype: (int, str, [(str, int, str)])
        """
        # query a couch list function
        ddoc_path = [
            '_design', 'transactions', '_list', 'whats_changed', 'log'
        ]
        response = yield self.json_from_resource(
            ddoc_path, old_gen=old_generation)
        results = map(
            lambda row:
                (row['generation'], row['doc_id'], row['transaction_id']),
            response['transactions'])
        results.reverse()
        cur_gen = old_generation
        seen = set()
        changes = []
        newest_trans_id = ''
        for generation, doc_id, trans_id in results:
            if doc_id not in seen:
                changes.append((doc_id, generation, trans_id))
                seen.add(doc_id)
        if changes:
            cur_gen = changes[0][1]  # max generation
            newest_trans_id = changes[0][2]
            changes.reverse()
        else:
            cur_gen, newest_trans_id = yield self.get_generation_info()
        defer.returnValue([cur_gen, newest_trans_id, changes])

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
        try:
            info = yield self.json_from_resource(ddoc_path)
        except Exception:
            raise NoDesignDocError()
        result = (info['generation'], info['transaction_id'])
        defer.returnValue(result)

    @defer.inlineCallbacks
    def json_from_resource(self, ddoc_path, check_missing_ddoc=True,
                           **kwargs):
        """
        Get a resource from its path and gets a doc's JSON using provided
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
            res = yield self._database.openList(
                docId=ddoc_name, listId=list_id, **kwargs)
        defer.returnValue(res)

    # TODO ------ patch paisley with this List stuff ----------------------
    # def openList(self, dbName, docId, listId, **kwargs):
    #   uri = '/%s/_design/%s/_list/%s' % (dbName, quote(docId), listId)
    #    return self.get(uri).addCallback(self.parseResult)
    # ----------------------------------------------------------------------

    # TODO cache this?
    @defer.inlineCallbacks
    def get_replica_uid(self):
        try:
            doc = yield self._database.openDoc(docId='u1db_config')
        except Exception:
            replica = {'replica_uid': None}
            yield self._database.saveDoc(replica, docId='u1db_config')
            doc = yield self._database.openDoc(docId='u1db_config')
        defer.returnValue(doc['replica_uid'])

    @defer.inlineCallbacks
    def get_doc(self, doc_id, check_for_conflicts):
        try:
            # TODO -------------------------------------------
            # move to a convenience function
            # TODO send the 2 in parallel, use gatherResults
            couch_doc = yield self._database.openDoc(
                docId=doc_id)
            content = yield self._database.openDoc(
                docId=doc_id, attachment="u1db_content")
            couch_doc['_attachments']['u1db_content'] = content
            # TODO get the conflicts attachment too.
            # --------------------------------------------------
        except Exception:
            couch_doc = None

        if couch_doc:
            doc = self.__parse_doc_from_couch(couch_doc, doc_id)
            defer.returnValue(doc)
        else:
            defer.returnValue(None)

    # FIXME ----  lot of complexity in here.
    # Bring from soledad.common.couch.__init__
    @defer.inlineCallbacks
    def save_document(self, old_doc, doc, transaction_id):
        attachments = {}  # we save content and conflicts as attachments
        # save content as attachment
        if doc.is_tombstone() is False:
            content = doc.get_json()
            attachments['u1db_content'] = content

        # XXX
        # TODO take this to a convenience function ---------------------------
        # store old transactions, if any
        transactions = old_doc.transactions[:] if old_doc is not None else []

        # create a new transaction id and timestamp it so the transaction log
        # is consistent when querying the database.
        transactions.append(
            # here we store milliseconds to keep consistent with javascript
            # Date.prototype.getTime() which was used before inside a couchdb
            # update handler.
            (int(time.time() * 1000),
             transaction_id))
        # -----------------------------------------------------------------------
        # build the couch document
        couch_doc = {
            '_id': doc.doc_id,
            'u1db_rev': doc.rev,
            'u1db_transactions': transactions,
        }
        self._database.addAttachments(couch_doc, attachments)

        # if we are updating a doc we have to add the couch doc revision
        if old_doc is not None and hasattr(old_doc, 'couch_rev'):
            couch_doc['_rev'] = old_doc.couch_rev

        # FIXME lots of missing stuff in here
        # save it
        doc = yield self._database.saveDoc(
            couch_doc, docId=doc.doc_id)
        defer.returnValue(doc)

    @defer.inlineCallbacks
    def set_replica_gen_and_trans_id(
            self, other_replica_uid, other_generation, other_transaction_id):
        """
        Set the last-known generation and transaction id for the other
        database replica.

        We have just performed some synchronization, and we want to track what
        generation the other replica was at. See also
        get_replica_gen_and_trans_id.

        :param other_replica_uid: The U1DB identifier for the other replica.
        :type other_replica_uid: str
        :param other_generation: The generation number for the other replica.
        :type other_generation: int
        :param other_transaction_id: The transaction id associated with the
                                     generation.
        :type other_transaction_id: str
        """
        doc_id = 'u1db_sync_%s' % other_replica_uid
        try:
            doc = yield self._database.openDoc(doc_id)
        except Exception:
            doc = {'_id': doc_id}
        doc['generation'] = other_generation
        doc['transaction_id'] = other_transaction_id
        yield self._database.saveDoc(doc, docId=doc_id)

    def __parse_doc_from_couch(self, result, doc_id,
                               check_for_conflicts=False):
        # restrict to u1db documents
        if 'u1db_rev' not in result:
            return None
        doc = ServerDocument(doc_id, result['u1db_rev'])
        # set contents or make tombstone

        if '_attachments' not in result \
                or 'u1db_content' not in result['_attachments']:
            doc.make_tombstone()
        else:
            doc.content = json.loads(
                result['_attachments']['u1db_content'])
        # determine if there are conflicts
        if check_for_conflicts \
                and '_attachments' in result \
                and 'u1db_conflicts' in result['_attachments']:
            doc.set_conflicts(
                self._build_conflicts(
                    doc.doc_id,
                    result['_attachments']['u1db_conflicts']))
        # store couch revision
        doc.couch_rev = result['_rev']
        # store transactions
        doc.transactions = result['u1db_transactions']
        return doc
