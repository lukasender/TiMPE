import time

from timpe.app.model import genuuid
from crate.client.exceptions import ProgrammingError
from .exceptions import ProcessError

MAX_RETRIES = 10


class TransactionUtil(object):

    def __init__(self, connection):
        self.cursor = connection.cursor()

    def set_transaction_state(self, transaction, state, occ_safe=False):
        """
        Update the state of a given transaction.
        """
        tries = 1 if not occ_safe else MAX_RETRIES
        cursor = self.cursor
        while tries > 0:
            tries -= 1
            # refresh and get the actual value
            self.refresh("transactions")
            stmt = "SELECT _version, state FROM transactions WHERE id = ?"
            cursor.execute(stmt, (transaction['id'],))
            _version, orig_state = cursor.fetchone()
            if orig_state == state:
                return True
            # update
            stmt = "UPDATE transactions "\
                   "SET state = ? WHERE id = ? AND _version = ?"
            cursor.execute(stmt, (state, transaction['id'], _version,))
            if cursor.rowcount == 1:
                return True
        raise ProcessError("could not update transaction state to '{0}' "\
                           "for transaction '{1}'".format(state,
                                                          transaction['id']))

    def get_balance_for(self, user_id):
        cursor = self.cursor
        self.refresh("user_transactions")
        stmt = "SELECT sum(amount) "\
               "FROM user_transactions WHERE user_id = ? AND state = ?"
        cursor.execute(stmt, (user_id, "finished",))
        return cursor.fetchone()[0]

    def insert_user_balance(self, user_id, transaction_id, amount, state):
        cursor = self.cursor
        try:
            stmt = "INSERT INTO user_transactions (id, user_id, "\
                   "\"timestamp\", amount, transaction_id, state) "\
                   "VALUES (?,?,?,?,?,?)"
            args = (genuuid(), user_id, time.time(), amount,
                    transaction_id, state,)
            cursor.execute(stmt, args)
        except ProgrammingError, e:
            assert e.message.endswith('exists already]')
            # Reduce concurrency effects. It is safe to assume that the
            # user_transaction is updated already.

    def update_pending_user_transaction(self, transaction_id, user_id):
        cursor = self.cursor
        self.refresh("user_transactions")
        stmt = "UPDATE user_transactions "\
               "SET state = ? "\
               "WHERE transaction_id = ? AND user_id = ?"
        args = ("finished", transaction_id, user_id,)
        cursor.execute(stmt, args)
        if cursor.rowcount != 1:
            msg = "could not update pending user_transactions "\
                  "for transaction '{0}', user_id '{1}'".format(transaction_id,
                                                                user_id)
            raise ProcessError(msg)

    def user_balance_sufficient(self, sender, amount):
        return self.get_balance_for(sender) >= amount

    def get_user_transactions(self, transaction):
        cursor = self.cursor
        transaction_id = transaction['id']
        sender = transaction['sender']
        self.refresh("user_transactions")
        stmt = "SELECT id, transaction_id, user_id, \"timestamp\", state, "\
               "amount, _version FROM user_transactions "\
               "WHERE transaction_id = ?"
        cursor.execute(stmt, (transaction_id,))
        user_transactions = cursor.fetchall()

        def create_user_transaction(user_transaction):
            return {
                'id': user_transaction[0],
                'transaction_id': user_transaction[1],
                'user_id': user_transaction[2],
                'timestamp': user_transaction[3],
                'state': user_transaction[4],
                'amount': user_transaction[5],
                '_version': user_transaction[6],
            }

        result = {}
        assert len(user_transactions) <= 2
        for user_transaction in user_transactions:
            u_ta_dict = create_user_transaction(user_transaction)
            if u_ta_dict['user_id'] == sender:
                result['sender'] = u_ta_dict
            else:
                result['recipient'] = u_ta_dict
        return result

    def user_exists(self, user_id):
        cursor = self.cursor
        stmt = "SELECT id FROM users WHERE id = ?"
        cursor.execute(stmt, (user_id,))
        return cursor.rowcount == 1

    def refresh(self, table):
        self.cursor.execute("REFRESH TABLE {0}".format(table))
