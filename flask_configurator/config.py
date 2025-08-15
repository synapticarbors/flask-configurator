import os
import errno
import json
from dotenv import dotenv_values
from flask import Config as FlaskConfig
import typing as t


class Config(FlaskConfig):
    def __init__(self, root_path=None, defaults=None, env_prefix="FLASK", logger=None):
        super().__init__(root_path, defaults)
        self.env_prefix = env_prefix
        self.logger = logger

    def load(self, filename="config.yml", default_env=None, **from_file_kwargs):
        if default_env:
            self["ENV"] = default_env
        if self.env_prefix:
            self.from_prefixed_env()
        self.from_dotenv()
        if filename:
            from_file_kwargs.setdefault("silent", True)
            self.from_file(filename, **from_file_kwargs)

    def from_dotenv(self, env: t.Optional[str] = None):
        update_config_from_dotenv(self, logger=self.logger, prefix=self.env_prefix)
        if not env:
            env = self.get("ENV")
        if env:
            update_config_from_dotenv(
                self, envified_dotenv_path(".env", env), logger=self.logger, prefix=self.env_prefix
            )

    def from_envvar(self, variable_name: str, silent: bool = False, **kwargs) -> bool:
        rv = os.environ.get(variable_name)
        if not rv:
            if silent:
                return False
            raise RuntimeError(
                f"The environment variable {variable_name!r} is not set"
                " and as such configuration could not be loaded. Set"
                " this variable and make it point to a configuration"
                " file"
            )
        return self.from_file(rv, silent=silent, **kwargs)

    def from_prefixed_env(self, prefix: t.Optional[str] = None, **kwargs) -> bool:
        return super().from_prefixed_env(prefix or self.env_prefix, **kwargs)

    def from_file(self, filename: str, **kwargs) -> bool:
        if self.root_path:
            filename = os.path.join(self.root_path, filename)
        kwargs.setdefault("env", self.get("ENV"))
        kwargs.setdefault("logger", self.logger)
        return update_config_from_file(self, filename, **kwargs)


def update_config_from_file(
    config,
    filename: str,
    env: t.Optional[str] = None,
    silent: bool = False,
    text: bool = True,
    deep_update: bool = False,
    logger=None,
    load=None,
) -> bool:
    if filename.endswith(".py"):
        return config.from_pyfile(filename, silent)

    loaded_config = read_config_file(filename, silent, text, load)
    if loaded_config is not False and logger:
        logger.info("Loaded config from %s" % filename)

    if env:
        env_filename = envified_config_filename(filename, env)
        env_config = read_config_file(env_filename, silent=True, text=text)
        if env_config is not False and logger:
            logger.info("Loaded config from %s" % env_filename)
        if env_config:
            deep_update_dict(loaded_config, env_config)
        elif loaded_config is False:
            return False
    elif loaded_config is False:
        return False

    if deep_update:
        deep_update_dict(config, loaded_config)
    else:
        config.update(loaded_config)
    return True


def envified_config_filename(filename, env):
    if not env:
        return
    filename, ext = os.path.splitext(filename)
    return filename + "." + env + ext


def update_config_from_dotenv(config, dotenv_path=".env", prefix="FLASK", logger=None):
    if logger:
        logger.info(f"Loading {dotenv_path} file")
    values = dotenv_values(dotenv_path)
    if prefix:
        prefix = f"{prefix}_"
        prefix_len = len(prefix)
        values = {k[prefix_len:]: v for k, v in values.items() if k.startswith(prefix)}
    if not values:
        return False
    config.update(values)
    return True


def envified_dotenv_path(dotenv_path, env):
    if not env:
        return dotenv_path
    return f"{dotenv_path}.{env}"


class CannotLoadConfigFileError(Exception):
    pass


def read_config_file(
    filename: str, silent: bool = False, text: bool = True, load=None
) -> bool | t.Mapping[str, t.Any]:
    if not load and filename.endswith(".js") or filename.endswith(".json"):
        load = json.load
    elif not load and filename.endswith(".yml") or filename.endswith(".yaml"):
        import yaml

        load = yaml.safe_load
    elif not load and filename.endswith(".toml"):
        import tomllib

        load = tomllib.load
    elif not load:
        if silent:
            return False
        raise CannotLoadConfigFileError()

    try:
        with open(filename, "r" if text else "rb") as f:
            config = load(f)
    except OSError as e:
        if silent and e.errno in (errno.ENOENT, errno.EISDIR):
            return False
        e.strerror = f"Unable to load configuration file ({e.strerror})"
        raise

    return {k.upper(): v for k, v in config.items()}


def deep_update_dict(a, b):
    for k, v in b.items():
        if k not in a:
            a[k] = v
        elif isinstance(a[k], dict) and isinstance(v, dict):
            deep_update_dict(a[k], v)
        elif isinstance(a[k], list) and isinstance(v, list):
            a[k].extend(v)
        elif isinstance(v, list) and not isinstance(a[k], list):
            a[k] = [a[k]] + v
        else:
            a[k] = v
    return a
