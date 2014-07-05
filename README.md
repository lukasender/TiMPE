# TiMPE - Transactions in Massively Parallel Environments

TiMPE is a prototype and allows `User to User transactions` (u2u) using the
eventually consitent datastore Crate Data. Users can be reigstered. Via the
REST API, a user can issue a new transaction and transfer some of her
balance to another users its balance. The application structure fits in a
`shared-nothing` architecture. Meaning, each `application node` is like any
other application node and no centralised application node is required
(i.e. no there is no single point of failure).

The transaction system relies on a combination of the `append-only`-technique,
a suitable data model and a 2PC (see `./docs`).

(It shall be mentioned: The project is in `research condition`. Meaning, it
is sparsely documented and not ready for a production setup.)

The service of the app TiMPE is available via the API through
[http://localhost:9100](http://localhost:9100). Data is exchanged via JSON.

The major part of the prototype is implemented in
`./src/timpe/app/transactions/*`.

**REST API Endpoints:**

------------------------

```
GET /users
    Returns a list of all registered users.

    Data:
    {
      'status': 'success',
      'data': [
        {
          'id': 'a-user-id',  // As of now, the sha-1 hash of a user's nickname
          'nickname': 'nickname of a user',
          'balance': 0        // The current balance of a user.
        }
        //, { more users... }
      ]
    }
```
```
POST /users
    Register a new user.

    Data:
    {
      'nickname': 'a required nickname',
      'balance' 0           // Initial balance, optional (defaults to 0).
    }
```
```
POST /transactions
    Issue a new transaction. This endpoint *does not* initiate the 2. phase
    of the 2PC immediately.

    Data:
    {
      'sender': 'user-id of the sender',
      'recipient': 'user-id of the recipient',
      'amount': 100         // The amount which a sender wants to transfer.
                            // Must be > 0.
    }
```
```
POST /transactions/immediately
    Issue a new transaction. Immediately initiates the 2. phase of the 2PC.

    Data:
    'see POST /transactions'

```
```
POST /process
    Initialises the 2. phase of the 2PC.

    No data required.
```

The local topology of the individual services looks as follows:

```
              +----------------+
              | haproxy (9100) |
              +----------------+
                 |          |
           +-----+          +------+
           |                       |
           v                       v
    +-------------+         +-------------+
    | app  (9210) |         | app2 (9211) |
    +-------------+         +-------------+
           |                       |
           |                       |
           v                       v
...............................................
:               crate cluster                 :
:                                             :
:  +---------------+       +---------------+  :
:  | crate  (4200) | <---> | crate2 (4201) |  :
:  +---------------+       +---------------+  :
:                                             :
:.............................................:

```

# Development Setup & Requirements

Installation setup is optimised for OS X (migrating to *NIX shouldn't be a
big problem) - Sorry in advance, if you are not an OS X user :)

## Requirements

**Python 2.7**

    brew install python

or

    port install python

**Libevent**

    brew install libevent

or

    port install libevent

## Installation

To install, run the following scripts:

    python boostrap.py

followed by:

    ./bin/buildout -N

In some cases, the Python library ``reqeusts`` does not get installed
automatically. In such a case, install it manually via:

    pip install requests

All needed programs can be started under supervisor control.
But, to run supervisor successfully we need to set up some directories first.

    mkdir -p var/log/supervisor; mkdir -p var/run

Now you are ready to start the supervisor:

    ./bin/supervisord

Check the status of the programs:

    ./bin/supervisorctl status

For debugging the Pyramid app can be started in the foreground. Take care
to stop the apps in the supervisor controller, then run:

    ./bin/app

The crate servers are running on port 4200 and 4201 and the admin interface
is reachable at [http://localhost:4200/admin](http://localhost:4200/admin).

The status interface for the HAProxy is available at
[http://localhost:9100/__haproxy_stats](http://localhost:9100/__haproxy_stats)

# Crate Data Database

## Setup

To initialize a empty Crate Data database run the command:

    ./bin/crate_setup

If the database has been setup already the script will raise an error but
no data will get destroyed.

## Clean Up

To reset the crate database to it's initial state run the command:

    ./bin/crate_cleanup

CAUTION: This command will delete all data!

## Test Data

To initialize the Crate Data database with some test data, run the command:

    ./bin/crate_testdata

Currently, the test data consists of 4 users (see `./etc/crate_testdata.sh`).

# Test Framework

Run the test framework with the command:

    ./bin/test

The setup is done by ``src/timpe/testing/tests.py``. DocTests are located
in ``docs``.

Another script one can use is ``u2u_transactions``. It allows a user to
issue several transactions (e.g. ``-t 200`` issues 200 new transactions)
concurrently (e.g. ``-c 100`` instantiates 100 threads).

    ./bin/u2u_transactions -i -t 200 -c 100

By default, the script uses the endpoint ``/transactions``. This gives a
developer to insert transactions, but the 2. phase of the 2PC will be started.
The parameter ``-i`` uses the endpoint ``/transactions/immediately`` and thus,
the 2. phase of the 2PC is immediately started.

To verify, run the two commands:

    echo 'SELECT * FROM users' | ./bin/crash
    echo 'SELECT user_id, sum(amount) FROM user_transactions GROUP BY user_id' | bin/crash

CAUTION: `.bin/u2u_transactions` uses the scripts `cleanup, setup and testdata`.
As a result, all data in the affected tables is lost.

# Documentation

Generate a documentation by running the command

    ./bin/sphinx

A html document will be generated and moved to ``out/html/``.

