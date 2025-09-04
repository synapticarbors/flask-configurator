from .config import Config
from .reloader import config_reloaded as config_reloaded, watch_config


class Configurator(Config):
    def __init__(self, app=None, **kwargs):
        if app:
            self.init_app(app, **kwargs)

    def init_app(self, app, default_file="config.yml", default_env=None, env_prefix="FLASK", watch=False):
        if default_env is None:
            default_env = "development" if app.debug else "production"
        super().__init__(app.root_path, env_prefix=env_prefix, logger=app.logger)
        self.load(default_file, default_env)
        app.config.update(self)
        if watch:
            watch_config(app, default_file)