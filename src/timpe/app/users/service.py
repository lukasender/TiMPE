from lovely.pyrest.rest import RestService, rpcmethod_route
from lovely.pyrest.validation import validate
from crate.client.exceptions import ProgrammingError

from timpe.app.model import CRATE_CONNECTION, genid, genuuid

import time


REGISTER_SCHEMA = {
    'type': 'object',
    'properties': {
        'nickname': {
            'type': 'string'
        },
        'balance': {
            'type': 'number',
            'required': False
        }
    }
}


@RestService('users')
class UserService(object):

    def __init__(self, request):
        self.cursor = CRATE_CONNECTION().cursor()
        self.request = request

    @rpcmethod_route()
    def list(self):
        """ List all registered users """
        # Performs an application side JOIN to check if both parts
        # ('transactions', 'user_transaction')of a transaction is
        # 'finished' . The join can be described as  follows:
        # SELECT ...
        # FROM user_transcation AS ut
        # JOIN transactions AS t ON t.id = ut.transaction_id
        # WHERE t.state = 'finished' AND ut.state = 'finished'
        cursor = self.cursor
        users_stmt = "SELECT id, nickname FROM users ORDER BY nickname"
        user_ta_stmt = "SELECT transaction_id, amount FROM user_transactions "\
                       "WHERE user_id = ? AND state = ?"
        cursor.execute("REFRESH TABLE users")
        cursor.execute("REFRESH TABLE user_transactions")
        cursor.execute("REFRESH TABLE transactions")
        cursor.execute(users_stmt)
        users = cursor.fetchall()
        result = []
        for user in users:
            user_id = user[0]
            nickname = user[1]
            cursor.execute(user_ta_stmt, (user_id, u'finished',))
            user_transactions = cursor.fetchall()
            balance = self._calculate_balance(user_transactions)
            result.append({
                "id": user_id,
                "nickname": nickname,
                "balance": balance
            })
        return {"data": {"users": result}}

    def _calculate_balance(self, user_transactions):
        cursor = self.cursor
        balance = 0
        stmt = "SELECT id FROM transactions "\
               "WHERE id IN ({0})"
        ut_ids = [u[0] for u in user_transactions]
        place_holders = ['?' for _ in xrange(len(ut_ids))]
        stmt = stmt.format(', '.join(place_holders))
        cursor.execute(stmt, ut_ids)
        transactions = cursor.fetchall()
        for user_id, amount in user_transactions:
            if [user_id] in transactions or user_id == u'register':
                balance += amount
        return balance

    @rpcmethod_route(route_suffix="/register", request_method="POST")
    @validate(REGISTER_SCHEMA)
    def register(self, nickname, balance=0):
        """ Register a new user """
        cursor = self.cursor
        user_id = genid(nickname)
        # add user
        stmt = "INSERT INTO users (id, nickname) VALUES (?, ?)"
        try:
            cursor.execute(stmt, (user_id, nickname,))
        except ProgrammingError:
            self.request.response.status = 400
            return {"status": "failed"}
        # initialise the user's transaction table
        stmt = "INSERT INTO user_transactions "\
               "(id, user_id, \"timestamp\", amount, transaction_id, state) "\
               "VALUES (?,?,?,?,?,?)"
        ta_id = genuuid()
        args = (ta_id, user_id, time.time(), balance, "register", "finished",)
        try:
            cursor.execute(stmt, args)
        except ProgrammingError:
            self.request.response.status = 400
            return {"status": "failed"}
        cursor.execute("REFRESH TABLE users")
        cursor.execute("REFRESH TABLE user_transactions")
        return {"status": "success"}


def includeme(config):
    config.add_route('users', '/users', static=True)
