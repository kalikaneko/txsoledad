"""
Experimental module to expose u1db http app using twisted.
TO-DO:
    [X] stub all the REST resources in the api.
    [ ] correctly get all the possible params
    [ ] make sure this runs on pypy
    [ ] run on python3
    [ ] use txaio
    [ ] pass server state
    [ ] use an atomic cache layer
    [ ] add multi-core support
"""
from klein import Klein

from resources import Global, Database, AllDocs
from resources import Documents, Document, Sync
from state import ServerState


GET = 'GET'
POST = 'POST'
PUT = 'PUT'
DELETE = 'DELETE'


class HTTPApp(Global, Database, AllDocs, Documents, Document, Sync):

    app = Klein()

    DB_RESOURCE_URI = '/<string:dbname>'
    DOCS_RESOURCE_URI = '/<string:dbname>/docs'
    ALL_DOCS_RESOURCE_URI = '/<string:dbname>/all-docs'
    DOC_RESOURCE_URI = '/<string:dbname>/doc/<string:doc_id>'
    SYNC_RESOURCE_URI = (
        '/<string:dbname>/sync-from'
        '/<string:source_replica_uid>')

    def __init__(self):
        self.state = ServerState()

    # Global resource

    @app.route('/')
    def info(self, request):
        return self._info(request)

    # Database resource
    # XXX soledad SHOULDNT have privileges to modify databases,
    # but getting this here for API completion. It might be useful during
    # tests.

    @app.route(DB_RESOURCE_URI, methods=[GET])
    def create_database(self, request, dbname):
        return self._create_database(request, dbname)

    @app.route(DB_RESOURCE_URI, methods=[DELETE])
    def delete_database(self, request, dbname):
        return self._delete_database(request, dbname)

    @app.route(DB_RESOURCE_URI, methods=[PUT])
    def update_database(self, request, dbname):
        return self._update_database(request, dbname)

    # Documents resource

    @app.route(DOCS_RESOURCE_URI, methods=[GET])
    def get_docs(self, request, dbname):
        return self._get_docs(request, dbname)

    # AllDocs resource

    @app.route(ALL_DOCS_RESOURCE_URI, methods=[GET])
    def get_all_docs(self, request, dbname):
        return self._get_all_docs(request, dbname)

    # Document resource

    @app.route(DOC_RESOURCE_URI, methods=[GET])
    def get_doc(self, request, dbname, doc_id):
        return self._get_doc(request, dbname, doc_id)

    @app.route(DOC_RESOURCE_URI, methods=[PUT])
    def update_doc(self, request, dbname, doc_id):
        return self._update_doc(request, dbname, doc_id)

    @app.route(DOC_RESOURCE_URI, methods=[DELETE])
    def delete_doc(self, request, dbname, doc_id):
        return self._delete_doc(request, dbname, doc_id)

    # Sync resource

    # Need to instantiate a sync_resource for each ongoing sync?

    @app.route(SYNC_RESOURCE_URI, methods=[GET])
    def start_sync(self, request, dbname, source_replica_uid):
        return self._start_sync(request, dbname, source_replica_uid)

    @app.route(SYNC_RESOURCE_URI, methods=[PUT])
    def put_sync(self, request, dbname, source_replica_uid):
        return self._put_sync(request, dbname, source_replica_uid)

    @app.route(SYNC_RESOURCE_URI, methods=[POST])
    def post_sync(self, request, dbname, source_replica_uid):
        return self._post_sync(request, dbname, source_replica_uid)


if __name__ == '__main__':
    store = HTTPApp()
    store.app.run('localhost', 2323)
