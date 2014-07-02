from lovely.pyrest.rest import RestService, rpcmethod_route
from lovely.pyrest.validation import validate

from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from ..model import genuuid, CRATE_CONNECTION

from .service_util import TransactionUtil
from .exceptions import Error, ProcessError

import time


TRANSACTIONS_SCHEMA = {
    'type': 'object',
    'properties': {
        'sender': {
            'type': 'string'
        },
        'recipient': {
            'type': 'string'
        },
        'amount': {
            'type': 'number'
        }
    }
}


@RestService('transactions')
class TransactionsService(object):

    def __init__(self, request):
        self.request = request
        self.cursor = CRATE_CONNECTION().cursor()
        self.util = TransactionUtil(CRATE_CONNECTION())

    @rpcmethod_route()
    def transactions(self):
        cursor = self.cursor
        stmt = "SELECT id, sender, recipient, amount, "\
                      "timestamp, state "\
               "FROM transactions "\
               "ORDER BY timestamp"
        cursor.execute(stmt)
        transactions = cursor.fetchall()
        result = []
        for transaction in transactions:
            t = {
                'id': transaction[0],
                'sender': transaction[1],
                'recipient': transaction[2],
                'amount': transaction[3],
                'timestamp': transaction[4],
                'state': transaction[5]
            }
            result.append(t)
        return {"status": "success", "data": result}

    @rpcmethod_route(request_method="POST")
    @validate(TRANSACTIONS_SCHEMA)
    def transaction_user_to_user(self, sender, recipient, amount):
        try:
            self._transaction_user_to_user(sender, recipient, amount)
            return {"status": "success"}
        except ProcessError, e:
            return bad_request(e.msg, self.request)

    @rpcmethod_route(route_suffix="/immediately", request_method="POST")
    @validate(TRANSACTIONS_SCHEMA)
    def transaction_user_to_user_immediate(self, sender, recipient, amount):
        try:
            transaction = self._transaction_user_to_user(sender, recipient,
                                                         amount)
            result = self._process_transactions([transaction])
            if result['status'] == 'success':
                return {"status": "success"}
            return result
        except ProcessError, e:
            return bad_request(e.msg, self.request)

    def _transaction_user_to_user(self, sender, recipient, amount):
        if amount <= 0:
            raise Error("'amount' must be a number > 0.")
        self.util.refresh("users")
        if not self.util.user_exists(sender):
            raise ProcessError("unknown 'sender'")
        if not self.util.user_exists(recipient):
            raise ProcessError("unknown 'recipient'")
        cursor = self.cursor
        if not self.util.user_balance_sufficient(sender, amount):
            raise ProcessError("sender balance is insufficient")
        stmt = "INSERT INTO transactions "\
               "(id,\"timestamp\",sender,recipient,amount,state) "\
               "VALUES (?, ?, ?, ? ,?, ?)"
        transaction_id = genuuid()
        args = (
            transaction_id,
            time.time(),
            sender,
            recipient,
            amount,
            'initial',
        )
        try:
            cursor.execute(stmt, args)
            if cursor.rowcount != 1:
                raise ProcessError("could not add the new transaction.")
            transaction = [
                transaction_id,
                sender,
                recipient,
                amount,
                'initial'
            ]
            return transaction
        except (NoResultFound, MultipleResultsFound):
            raise ProcessError("user balance insufficient.")

    @rpcmethod_route(route_suffix="/process", request_method="POST")
    def process(self):
        cursor = self.cursor
        self.util.refresh("transactions")
        stmt = "SELECT id, sender, recipient, amount, state "\
               "FROM transactions WHERE state != ?"
        cursor.execute(stmt, ("finished",))
        transactions = cursor.fetchall()
        return self._process_transactions(transactions)

    def _process_transactions(self, transactions):
        failed_transactions = []
        for t in transactions:
            transaction = {
                'id': t[0],
                'sender': t[1],
                'recipient': t[2],
                'amount': t[3],
                'state': t[4]
            }
            try:
                self.__process_transactions(transaction)
            except ProcessError, e:
                print e.msg
                failed_transactions.append({
                    "transaction":transaction,
                    "reason":e.msg
                })
        status = "success" if len(failed_transactions) == 0 else "failed"
        return {
            "status":status,
            "msg":"processed all transactions",
            "failed_transactions": failed_transactions
        }

    def __process_transactions(self, transaction):
        """ initial -> in progress -> committed -> finished """
        def __get_process(state):
            if state == 'initial':
                return self._process_transaction_initial
            elif state == 'in progress':
                return self._process_transaction_inprogress
            elif state == 'committed':
                return self._process_transaction_committed
            return self._process_critial_error

        process = __get_process(transaction['state'])
        return process(transaction)

    def _process_transaction_initial(self, transaction):
        """
        Processes a transaction with the state 'initial'.
        """
        self.util.set_transaction_state(transaction, 'in progress')
        self._update_balance_sender(transaction, 'pending')
        self._update_balance_recipient(transaction, 'pending')
        self.util.set_transaction_state(transaction, 'committed')
        self._update_pending_user_transaction(transaction['sender'], transaction)
        self._update_pending_user_transaction(transaction['recipient'], transaction)
        return self.util.set_transaction_state(transaction, 'finished',
                                               occ_safe=True)

    def _process_transaction_inprogress(self, transaction):
        """
        A transaction was found with state 'in progress'.
        """
        user_transactions = self.util.get_user_transactions(transaction)
        u_ta_sender = user_transactions.get('sender', None)
        u_ta_recipient = user_transactions.get('recipient', None)
        if u_ta_sender is None:
            self._update_balance_sender(transaction, 'pending')
        if u_ta_recipient is None:
            self._update_balance_recipient(transaction, 'pending')
        self.util.set_transaction_state(transaction, 'committed')
        self._update_pending_user_transaction(transaction['sender'], transaction)
        self._update_pending_user_transaction(transaction['recipient'], transaction)
        return self.util.set_transaction_state(transaction, 'finished',
                                               occ_safe=True)

    def _process_transaction_committed(self, transaction):
        """
        A transaction was found with the state 'committed'.
        """
        user_transactions = self.util.get_user_transactions(transaction)
        u_ta_sender = user_transactions['sender']
        u_ta_recipient = user_transactions['recipient']
        if u_ta_sender['state'] == 'pending':
            self._update_pending_user_transaction(transaction['sender'], transaction)
        if u_ta_recipient['state'] == 'pending':
            self._update_pending_user_transaction(transaction['recipient'], transaction)
        return self.util.set_transaction_state(transaction, 'finished',
                                               occ_safe=True)

    def _process_critial_error(self, transaction):
        """
        Mother of god! A critical error occurred. Only a human can help now...
        """
        # notify a human
        raise ProcessError("Mother of god! A critical error occurred. "\
                           "Only a human can help now...", transaction)

    def _update_balance_sender(self, transaction, state):
        ta_id = transaction['id']
        sender = transaction['sender']
        amount = -transaction['amount']
        self.util.insert_user_balance(
            user_id=sender,
            transaction_id=ta_id,
            amount=amount,
            state=state
        )

    def _update_balance_recipient(self, transaction, state):
        ta_id = transaction['id']
        recipient = transaction['recipient']
        amount = transaction['amount']
        self.util.insert_user_balance(
            user_id=recipient,
            transaction_id=ta_id,
            amount=amount,
            state=state
        )

    def _update_pending_user_transaction(self, user_id, transaction):
        transaction_id = transaction['id']
        self.util.update_pending_user_transaction(transaction_id,
                                                  user_id)


def bad_request(msg=None, request=None):
    if request:
        request.response.status = 400
    br = {"status": "failed"}
    if msg:
        br['msg'] = msg
    return br


def includeme(config):
    config.add_route('transactions', '/transactions', static=True)
