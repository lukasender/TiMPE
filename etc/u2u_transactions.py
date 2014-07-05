# -*- coding: utf-8; -*-
import sys
import requests
import json
import time
import argparse

from threading import Thread, Lock
from Queue import Queue


USERS = ["elon_musk", "albert_einstein", "nikola_tesla", "lovelace"]

lock = Lock()

BASEURL = 'http://localhost:9100'
headers = {'content-type':'application/json'}


def release_the_kraken(immediate, x_transactions, max_concurrent_transactions):
    try:
        sender, recipient = get_users(['elon_musk', 'nikola_tesla'])
        initial_balance_sender = sender['balance']
        initial_balance_recipient = recipient['balance']

        transactions_queue = Queue(max_concurrent_transactions * 2)

        args_transaction = (sender, recipient, immediate, transactions_queue)
        start_daemons(max_concurrent_transactions, transaction,
                      args_transaction)
        with Timer() as t:
            start_task_and_wait(x_transactions, transactions_queue)

        excepted_balance = (pow(x_transactions, 2) + x_transactions) / 2
        print ""
        print "Done! Total balance of {0} transferred in {1} ms".format(
            excepted_balance,
            t.msecs
        )

        sender, recipient = get_users(['elon_musk', 'nikola_tesla'])
        updated_balance_sender = sender['balance']
        updated_balance_recipient = recipient['balance']

        print ""
        print "Initial balance"
        print "---------------"
        print "{0} (sender): {1}".format(sender['nickname'],
                                         initial_balance_sender)
        print "{0} (recipient): {1}".format(recipient['nickname'],
                                            initial_balance_recipient)
        print ""
        print "Updated balance"
        print "---------------"
        print "{0} (sender): {1}, difference to initial balance: {2}".format(
            sender['nickname'],
            updated_balance_sender,
            updated_balance_sender - initial_balance_sender
        )
        print "{0} (recipient): {1}, difference to initial balance: {2}".format(
            recipient['nickname'],
            updated_balance_recipient,
            updated_balance_recipient - initial_balance_recipient
        )

        average = benchmark_calculate_user_balance(sender)
        print ""
        print "On average, calculating a user balance now takes {0} ms "\
              "(including HTTP overhead)".format(average)
    except KeyboardInterrupt:
        sys.exit(1)


def get_users(filter_users):
    url_users = BASEURL + '/users'
    r = requests.get(url_users)
    return [user for user in r.json()['data']['users'] if user['nickname'] in filter_users]


def benchmark_calculate_user_balance(user, x_times=10):
    msecs = []
    for _ in range(x_times):
        url_user = BASEURL + '/users/{0}'.format(user['id'])
        with Timer() as t:
            requests.get(url_user)
        msecs.append(t.msecs)
    return sum(msecs) / x_times


def start_daemons(max_concurrency, target, thread_args):
    for _ in range(max_concurrency):
        th = Thread(target=target, args=thread_args)
        th.setDaemon(True)
        th.start()


def start_task_and_wait(num_tasks, task_queue):
    for i in range(1, num_tasks + 1):
        task_queue.put(i)
    task_queue.join()


def transaction(sender, recipient, immediate, queue):
    while True:
        try:
            i = queue.get()
            amount = i
            cmt = "Sending {0} from {1} to {2}".format(
                amount,
                sender['nickname'],
                recipient['nickname']
            )
            url = BASEURL + '/transactions'
            if immediate:
                url += '/immediately'
            payload = {
                'sender': sender['id'],
                'recipient': recipient['id'],
                'amount': amount
            }
            r = requests.post(url, data=json.dumps(payload), headers=headers)
            rJson = r.json()
            with lock:
                print "[task_id: {0}] transaction: {1}, '{2}'".format(i, cmt,
                                                                    rJson)
        except ValueError as e:
            with lock:
                print_error(e)
        finally:
            with lock:
                queue.task_done()


def print_error(e):
    print '-'*40
    print type(e)
    print e
    print '-'*40


class Timer(object):
    """ http://www.huyng.com/posts/python-performance-analysis/ """
    def __init__(self, verbose=False):
        self.start = None
        self.secs = 0
        self.msecs = 0
        self.end = 0
        self.verbose = verbose

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        self.end = time.time()
        self.secs = self.end - self.start
        self.msecs = self.secs * 1000  # millisecs
        if self.verbose:
            print 'elapsed time: %f ms' % self.msecs


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Transfer user balance concurrently.'
    )
    parser.add_argument(
        '-i',
        '--immediate',
        action='store_true',
        required=False,
        help='process the transactions immediately'
    )
    parser.add_argument(
        '-t',
        '--transactions',
        type=int,
        default=100,
        required=False
    )
    parser.add_argument(
        '-c',
        '--concurrent',
        type=int,
        default=10,
        required=False
    )
    args = parser.parse_args()
    release_the_kraken(args.immediate, args.transactions, args.concurrent)
