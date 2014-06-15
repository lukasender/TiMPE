from pyramid.settings import aslist
from pyramid.config import Configurator

from .model import CRATE_CONNECTION


def app_factory(global_config, **settings):
    """Setup the main application for paste

    This must be setup as the paste.app_factory in the egg entry-points.
    """
    config = Configurator(settings=settings,
                          autocommit=True,
                          )
    config.include('timpe.app.probestatus.probestatus')
    config.scan('timpe.app.probestatus')
    config.include('timpe.app.users.service')
    config.scan('timpe.app.users')
    config.include('timpe.app.transactions.service')
    config.scan('timpe.app.transactions')
    crate_init(config)
    return config.make_wsgi_app()


def crate_init(config):
    settings = config.get_settings()
    CRATE_CONNECTION.configure(aslist(settings['crate.hosts']))
