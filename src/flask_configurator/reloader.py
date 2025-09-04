from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from blinker import signal
from .config import envified_dotenv_path, envified_config_filename


config_reloaded = signal("config-reloaded")


class ReloadHandler(FileSystemEventHandler):
    def __init__(self, app):
        self.app = app

    def on_modified(self, event):
        self.app.logger.info("Reloading config")
        self.app.config.load()
        config_reloaded.send(self.app)


def watch_config(app, filename="config.yml", dotenv=True, env=None):
    observer = Observer()
    for filename in get_config_watch_paths(app, filename, dotenv, env):
        observer.schedule(ReloadHandler(app), filename)
    observer.start()
    return observer


def get_config_watch_paths(app, filename="config.yml", dotenv=True, env=None):
    paths = []
    if env is None:
        env = app.config.get("ENV")
    if filename:
        paths.extend([filename, envified_config_filename(filename, env)])
    if dotenv:
        paths.extend([".env", envified_dotenv_path(".env", env)])
    return paths