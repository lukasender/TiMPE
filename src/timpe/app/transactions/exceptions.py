
class Error(Exception):

    def __init__(self, msg=None):
        super(Error, self).__init__()
        self.msg = msg

class ProcessError(Error):
    pass
