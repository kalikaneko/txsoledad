# -*- coding: utf-8 -*-
# sync.py
# Copyright (C) 2014-2016 LEAP Encryption Access Project
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
"""
Server side synchronization infrastructure.
"""
# TODO -- the skeleton for this should be in soledad itself.

from twisted.internet import defer

from u1db import sync

from leap.soledad.server.state import ServerSyncState


MAX_REQUEST_SIZE = 200  # in Mb
MAX_ENTRY_SIZE = 200  # in Mb


class SyncExchange(sync.SyncExchange):

    def __init__(self, db, source_replica_uid, last_known_generation, sync_id):
        """
        :param db: The target syncing database.
        :type db: SoledadBackend

        :param source_replica_uid: The uid of the source syncing replica.
        :type source_replica_uid: str

        :param last_known_generation: The last target replica generation the
                                      source replica knows about.
        :type last_known_generation: int

        :param sync_id: The id of the current sync session.
        :type sync_id: str
        """
        self._db = db
        self.source_replica_uid = source_replica_uid
        self.source_last_known_generation = last_known_generation
        self.sync_id = sync_id
        self.new_gen = None
        self.new_trans_id = None
        self._trace_hook = None

        # recover sync state
        self._sync_state = ServerSyncState(self.source_replica_uid, sync_id)

    @defer.inlineCallbacks
    def find_changes_to_return(self, received):
        """
        Find changes to return.

        Find changes since last_known_generation in db generation
        order using whats_changed. It excludes documents ids that have
        already been considered (superseded by the sender, etc).

        :param received: How many documents the source replica has already
                         received during the current sync process.
        :type received: int

        :return: the generation of this database, which the caller can
                 consider themselves to be synchronized after processing
                 allreturned documents, and the amount of documents to be sent
                 to the source syncing replica.
        :rtype: int
        """
        # check if changes to return have already been calculated
        new_gen, new_trans_id, number_of_changes = self._sync_state.sync_info()
        print "NUMBER_OF_CHANGES", number_of_changes
        if number_of_changes is None:
            self._trace('before whats_changed')
            new_gen, new_trans_id, changes = yield self._db.whats_changed(
                self.source_last_known_generation)
            self._trace('after whats_changed')

            seen_ids = self._sync_state.seen_ids()
            # changed docs that weren't superseded by or converged with
            changes_to_return = [
                (doc_id, gen, trans_id) for (doc_id, gen, trans_id) in changes
                # there was a subsequent update
                if doc_id not in seen_ids or seen_ids.get(doc_id) < gen]
            self._sync_state.put_changes_to_return(
                new_gen, new_trans_id, changes_to_return)
            number_of_changes = len(changes_to_return)
        # query server for stored changes
        _, _, next_change_to_return = \
            self._sync_state.next_change_to_return(received)
        self.new_gen = new_gen
        self.new_trans_id = new_trans_id
        # and append one change
        self.change_to_return = next_change_to_return
        defer.returnValue([self.new_gen, number_of_changes])

    @defer.inlineCallbacks
    def return_one_doc(self, return_doc_cb):
        """
        Return one changed document and its last change generation to the
        source syncing replica by invoking the callback return_doc_cb.

        This is called once for each document to be transferred from target to
        source.

        :param return_doc_cb: is a callback used to return the documents with
                              their last change generation to the target
                              replica.
        :type return_doc_cb: callable(doc, gen, trans_id)
        """
        if self.change_to_return is not None:
            changed_doc_id, gen, trans_id = self.change_to_return
            doc = yield self._db.get_doc(changed_doc_id, include_deleted=True)
            return_doc_cb(doc, gen, trans_id)

    def batched_insert_from_source(self, entries, sync_id):
        # FIXME --- enable batch
        self._db.batch_start()
        for entry in entries:
            doc, gen, trans_id, number_of_docs, doc_idx = entry
            self.insert_doc_from_source(doc, gen, trans_id, number_of_docs,
                                        doc_idx, sync_id)
        self._db.batch_end()

    @defer.inlineCallbacks
    def insert_doc_from_source(
            self, doc, source_gen, trans_id,
            number_of_docs=None, doc_idx=None, sync_id=None):
        """Try to insert synced document from source.

        Conflicting documents are not inserted but will be sent over
        to the sync source.

        It keeps track of progress by storing the document source
        generation as well.

        The 1st step of a sync exchange is to call this repeatedly to
        try insert all incoming documents from the source.

        :param doc: A Document object.
        :type doc: Document
        :param source_gen: The source generation of doc.
        :type source_gen: int
        :param trans_id: The transaction id of that document change.
        :type trans_id: str
        :param number_of_docs: The total amount of documents sent on this sync
                               session.
        :type number_of_docs: int
        :param doc_idx: The index of the current document.
        :type doc_idx: int
        :param sync_id: The id of the current sync session.
        :type sync_id: str
        """

        state, at_gen = yield self._db._put_doc_if_newer(
            doc, save_conflict=False, replica_uid=self.source_replica_uid,
            replica_gen=source_gen, replica_trans_id=trans_id,
            number_of_docs=number_of_docs, doc_idx=doc_idx, sync_id=sync_id)

        if state == 'inserted':
            self._sync_state.put_seen_id(doc.doc_id, at_gen)
        elif state == 'converged':
            # magical convergence
            self._sync_state.put_seen_id(doc.doc_id, at_gen)
        elif state == 'superseded':
            # we have something newer that we will return
            pass
        else:
            # conflict that we will returne
            assert state == 'conflicted'
