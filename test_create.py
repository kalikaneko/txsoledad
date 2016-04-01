import sys

import paisley

from twisted.web import http
from twisted.internet import reactor, defer
from twisted.python import log


def test():
    print "STARTING TEST"
    foo = paisley.CouchDB('localhost')
    print "\nCreate database 'testdb':"
    d = foo.createDB('testdb1')
    d.addCallback(lambda f: log.err(f))
    wfd = defer.waitForDeferred(d)
    yield wfd
    try:
        print wfd.getResult()
    except Exception as e:
        # FIXME: not sure why Error.status is a str compared to http constants
        if hasattr(e, 'status') and e.status == str(http.UNAUTHORIZED):
            print "\nError: not allowed to create databases"
            reactor.stop()
            return
        else:
            raise

    print "\nList databases on server:"
    d = foo.listDB()
    wfd = defer.waitForDeferred(d)
    yield wfd
    print wfd.getResult()
    reactor.stop()


test = defer.deferredGenerator(test)


if __name__ == "__main__":
    log.startLogging(sys.stdout)
    reactor.callWhenRunning(test)
    reactor.run()
