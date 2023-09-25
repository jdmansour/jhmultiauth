import os
from typing import Optional, Type, Union

import psutil
import traitlets.config
from jupyterhub.app import JupyterHub
from jupyterhub.auth import Authenticator
from traitlets.utils.importstring import import_item


def get_configfile_from_cmdline() -> Optional[str]:
    """Tries to find the JupyterHub configuration file, when the service is ran
    as a subprocess of JupyterHub."""
    cmdline = psutil.Process().parent().cmdline()
    try:
        i = cmdline.index("-f")
    except ValueError:
        return None
    if i == len(cmdline) - 1:
        return None
    return cmdline[i + 1]


def get_jupyterhub_config():
    if getattr(get_jupyterhub_config, "_config", None) is not None:
        return get_jupyterhub_config._config

    """ Gets the LTI 1.1 consumer keys and secrets from the configuration file."""
    configfile = get_configfile()

    # Load the traitlets configuration
    app2 = traitlets.config.Application()
    app2.load_config_file(configfile)

    get_jupyterhub_config._config = app2.config
    return get_jupyterhub_config._config


def get_configfile() -> str:
    """Finds the JupyterHub configuration file."""
    filename = get_configfile_from_cmdline()
    if filename:
        return filename

    if os.path.exists("/etc/jupyterhub/jupyterhub_config.py"):
        return "/etc/jupyterhub/jupyterhub_config.py"

    if os.path.exists(
        "/opt/tljh/hub/lib/python3.8/site-packages/tljh/jupyterhub_config.py"
    ):
        return "/opt/tljh/hub/lib/python3.8/site-packages/tljh/jupyterhub_config.py"

    raise FileNotFoundError("Could not find JupyterHub configuration file")


def resolve_authenticator(
    config_value: Union[str, Type[Authenticator]]
) -> Type[Authenticator]:
    """Resolves the authenticator class from the configuration file.
    `config_value` can either be a string or the class object itself.
    If it is a string, it can be the fully qualified name including module
    and class name, or it can be a short name using JupyterHubs "entry
    point" function.

    Examples:
        # Class object
        from nativeauthenticator import NativeAuthenticator
        config_value = NativeAuthenticator

        # Fully qualified name
        config_value = "nativeauthenticator.NativeAuthenticator"

        # Short name
        config_value = "nativeauthenticator"
    """
    entry_points = JupyterHub.authenticator_class.load_entry_points()
    if config_value in entry_points:
        AuthKlass = entry_points[config_value].load()
    elif isinstance(config_value, str):
        AuthKlass = import_item(config_value)
    else:
        AuthKlass = config_value
    assert issubclass(AuthKlass, Authenticator)
    return AuthKlass


# def get_auth_from_multiauth(AuthKlass: Authenticator) -> LTI11Authenticator:
#     """ If we are using MultiAuthenticator, get the correct sub-authenticator.
#         Otherwise, just return the authenticator. """
#     try:
#         from jhmultiauth import MultiAuthenticator
#     except ImportError:
#         return AuthKlass

#     if not issubclass(AuthKlass, MultiAuthenticator):
#         return AuthKlass

#     config = get_jupyterhub_config()
#     for value, prefix in config.MultiAuthenticator.authenticators:
#         klass = resolve_authenticator(value)
#         # klass = value
#         # log.info("klass: %r", klass)
#         if issubclass(klass, LTI11Authenticator):
#             return klass

#     raise RuntimeError("No LTI11Authenticator found in MultiAuthenticator configuration")
