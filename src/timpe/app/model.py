import uuid
from hashlib import sha1

from crate.client import connect


class CrateConnection(object):

    def __init__(self):
        self.connection = None

    def __call__(self):
        return self.connection

    def configure(self, hosts):
        self.connection = connect(hosts)
        return self.connection


CRATE_CONNECTION = CrateConnection()

def genuuid():
    return str(uuid.uuid4())


def genid(s):
    """ generate a deterministic id for 's' """
    if isinstance(s, unicode):
        str_8bit = s.encode('UTF-8')
    else:
        str_8bit = s
    return sha1('salt' + str_8bit).hexdigest()
