import os
from twisted.internet import reactor
from leap.soledad.client import Soledad


def _get_soledad_instance(uuid, passphrase, basedir, server_url, cert_file,
                          token):
    # setup soledad info
    # logger.info('UUID is %s' % uuid)
    # logger.info('Server URL is %s' % server_url)
    secrets_path = os.path.join(
        basedir, '%s.secret' % uuid)
    local_db_path = os.path.join(
        basedir, '%s.db' % uuid)
    # instantiate soledad
    return Soledad(
        uuid,
        unicode(passphrase),
        secrets_path=secrets_path,
        local_db_path=local_db_path,
        server_url=server_url,
        cert_file=cert_file,
        auth_token=token,
        defer_encryption=True,
        syncable=True)


def notify_when_ready(result):
    print "Sync is ready sir!", result
    reactor.stop()

sol = _get_soledad_instance(
    'defd3db2cc8a749d12a9b56a638b9993', 'pass', '/tmp/',
    'http://localhost:2323', '', '')
sol.create_doc({'test': 42})

d = sol.sync()
d.addCallback(notify_when_ready)

reactor.run()
