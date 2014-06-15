TiMPE - Transactions in Massively Parallel Environments
=======================================================

The main setup and structure of this project is taken from [lovely.microblog/backend](https://github.com/lovelysystems/lovely.microblog/tree/master/backend).

Requirements
------------

**Python 2.7**

``brew install python``

or

``port install python``

**Libevent**

``brew install libevent``

or

``port install libevent``

Development setup
-----------------

All needed programs can be started under supervisor control.
But, to run supervisor successfully you need to make some directories first.

``mkdir -p var/log/supervisor; mkdir -p var/run``

Now you are ready to start the supervisor:

``./bin/supervisord``

Check the status of the programs:

``./bin/supervisorctl status``

The API is available at [http://localhost:9100](http://localhost:9100)

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

For debugging the Pyramid app can be started in the foreground. Take care
to stop the apps in the supervisor controller, then run:

``./bin/app``

The crate servers are running on port 4200 and 4201 and the admin interface
is reachable at [http://localhost:4200/admin](http://localhost:4200/admin).

The status interface for the HAProxy is available at
[http://localhost:9100/__haproxy_stats](http://localhost:9100/__haproxy_stats)

Setup crate database
--------------------

To initialize a empty crate database run the command

``./bin/crate_setup``

If the database has been setup already the script will raise an error but
no data will get destroyed.

Clean up crate database
-----------------------

To reset the crate database to it's initial state run the command

``bin/crate_cleanup``

CAUTION: This command will delete all data!

Test framework
--------------

Run the test framework with the command

``./bin/test``

The setup is done by ``src/timpe/testing/tests.py``. DocTests are located
in ``docs``.

Documentation
-------------

Generate a documentation by running the command

``./bin/sphinx``

A html document will be generated and moved to ``out/html/``.

