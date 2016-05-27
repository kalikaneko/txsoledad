Soledad Sync Protocol
---------------------

This is an attempt at writing down the SOLEDAD SYNC protocol, which
diverged from the original u1db http sync protocol.
https://pythonhosted.org/u1db/conflicts.html#synchronisation

terms
~~~~~
- replica_generation: (either source or target) an autoincremental integer that
  is increased on each database transaction.
- transaction_id: an unique identifier for each transaction, allows resuming
  interrupted operations.

Pre-step: Storage of Secrets on the shared-db
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

(1) GET /shared/doc/da59347fd73047711fb8d6b9cfa33c48821a6a3bd6360a2f6423453a5d4259ee?include_deleted=false

# BUG: Current CLIENT implementation is doing this request *twice*

(2) PUT ... 

(** can a client PUT data to any other doc????? are we protecting from this attack?)


Synchronisation of SOLEDAD replicas over HTTP 
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

(1) Source Replica gets Synchronization info.

    The application wishing to synchronize sends the following GET request to
    the SOLEDAD server:

    -->
    GET /thedb/sync-from/my_replica_uid

    Where thedb is the name of the database to be synchronised, and
    my_replica_uid is the replica id of the application’s (i.e. the local, or
    synchronisation source) database.

    To this request, the target responds with a JSON document that looks like
    this:

    <--
    Content-Type: application/json.

    {
    "target_replica_uid": "other_replica_uid",
    "target_replica_generation": 12,
    "target_replica_transaction_id": "T-sdkfj92292j",
    "source_replica_uid": "my_replica_uid",
    "source_replica_generation": 23,
    "source_transaction_id": "T-39299sdsfla8"
    }

    With all the information it has stored for the most recent synchronisation
    between itself and this particular source replica. In this case it tells us
    that the synchronisation target believes that when it and the source were
    last synchronised, the target was at generation 12 and the source at
    generation 23.

    # Proposal: The server can announce a CAPABILITIES array in this GET
    response. (For instance, for announcing batching).


(2) Client SENDS docs to server.

    The client does this serially. To reduce the communication overhead,
    batching can be enabled (experimental feature by the moment), but the
    server implementation has to announce clearly that it supports it.

    -->
    POST /thedb/sync-from/my_replica_uid
    content-type: application/x-soledad-sync-put

    [{
    "sync_id": "0f625b90-8a10-4730-b6a9-81e4a232ac11",
    "last_known_trans_id": "",
    "last_known_generation": 0,
    "ensure": false},
    {"rev": "3805d05a466c40f3a977234a3d0fd94d:1",
    "gen": 12,
    "content": "{\"_mac_method\": \"hmac\", \"_enc_scheme\": \"symkey\", \"_enc_json\": \"38a69e1c53806f629d229872\", \"_mac\": \"dfa9364d04ce06c20522db57bb8df9138a1f96cbeea5edd8f47f44aebc2d5a73\", \"_enc_iv\": \"/CQI697We0dVa2PR53tLzQ==\\n\", \"_enc_method\": \"aes-256-ctr\"}",
    "doc_idx": 1,
    "id": "D-cd6eb284177046c297ecd023f1840eed",
    "trans_id": "T-59a8e7f281e2468aba465fb36ce175a5",
    "number_of_docs": 3}
    ]

    <--
    Content-Type: application/x-soledad-sync-response.

    [
    {"new_transaction_id": "T-029900ff67f14417b6288da7e2770406",
    "new_generation": 8}.
    ]

    # TODO: DOCUMENT the  x-soledad-sync-response format (subset of json)



(3) Client DOWNLOADs docs from server.

    In this step, the client can issue several simultaneous requests.


    -->
    POST /thedb/sync-from/my_replica_uid
    content-type: application/x-soledad-sync-get
    [{
    "sync_id": "9900e18b-6fa1-4d3a-a785-c100736f991c",
    "last_known_trans_id": "T-b90384c2c004483496f54f554767bf09",
    "last_known_generation": 1,
    "ensure": false},
    {"received": 0}]

    <--
    Content-Type: application/x-soledad-sync-response.

    [{
    "new_transaction_id": "T-b52b0c6676ef4ca19e1670263d70019e",
    "new_generation": 12,
    "number_of_changes": 3},

    # IF numer_of_changes > 0 ---------------------------------
    {
    'id': "aaaaaaa",
    "rev": 1,
    "content": "aaaaaa",
    "gen": 1,
    "trans_id": "T-aaaaaaaaaaaaaaaaaaaaaaaaaaa"
    }
    # ENDIF ---------------------------------------------------
    ]

    * Note: each document needs to be in its own line, for the client to parse
      the stream correctly.


(4) (Optional) Client informs Target of its new Synchronization State.

    When the source has processed all the changes it received from the target,
    and it detects that there have been no changes to its database since the
    start of the synchronisation that were not a direct result of the
    synchronisation, it now performs a final PUT request, to inform the target
    of its new generation and transaction id, so that the next synchronisation
    can start there, rather than with the generation the source was at when this
    synchronisation started:

    -->
    PUT /thedb/sync-from/my_replica_uid
    Content-Type: application/json.

    {"generation": 53, "transaction_id": "T-camcmls92"}

    <--
    Content-Type: application/json.

    {"ok": true}.

