import logging
from types import MethodType
from typing import List, NamedTuple, Tuple, Type, Union

import traitlets
from jupyterhub.auth import Authenticator
from jupyterhub.handlers import BaseHandler
from jupyterhub.objects import Hub
from jupyterhub.traitlets import EntryPointType
from jupyterhub.utils import url_path_join
from tornado.web import RequestHandler

from .utils import resolve_authenticator

log = logging.getLogger(__name__)

KlassOrString = Union[str, Type[Authenticator]]


class AuthenticatorWithScope(NamedTuple):
    instance: Authenticator
    url_scope: str


class MultiAuthenticator(Authenticator):
    authenticators: List[Tuple[KlassOrString, str]] = traitlets.List(
        trait=traitlets.Tuple(
            EntryPointType(
                klass=Authenticator, entry_point_group="jupyterhub.authenticators"
            ),
            traitlets.Unicode(),
        ),
        help="List of sub-authenticators to use",
    ).tag(config=True)

    _authenticators: List[AuthenticatorWithScope]

    def __init__(self, *arg, config=None, **kwargs):
        super().__init__(*arg, config=config, **kwargs)
        self._authenticators = []
        for klass_desc, url_scope in self.authenticators:
            # klass_desc can be a string or a class, ensure we have a class:
            AuthenticatorKlass = resolve_authenticator(klass_desc)
            auth = AuthenticatorKlass(
                parent=self, _deprecated_db_session=self._deprecated_db_session
            )

            # get the login url for this authenticator, e.g. 'login' for PAM, 'oauth_login' for Google
            login_url = auth.login_url("")

            # capture the current values of url_scope and login_url using default args
            # without this, the values of url_scope and login_url will be the last ones in the loop
            def custom_login_url(
                self, base_url, url_scope=url_scope, login_url=login_url
            ):
                return url_path_join(base_url, url_scope, login_url)

            auth.login_url = MethodType(custom_login_url, auth)
            self._authenticators.append(AuthenticatorWithScope(auth, url_scope))

    def get_handlers(self, app):
        routes = []
        for auth, url_scope in self._authenticators:
            self.log.info("Authenticator: %r, url_scope: %r", auth, url_scope)
            for path, HandlerKlass in auth.get_handlers(app):
                self.log.info(
                    "  path: %r, HandlerKlass: %r, authenticator: %r",
                    path,
                    HandlerKlass,
                    HandlerKlass.authenticator,
                )

                # Overriding authenticator, so that e.g. the login page shown is the one for the sub-authenticator
                # Using a subclass instead of setattr, because multiple handlers might return the same class
                # https://github.com/jupyterhub/oauthenticator/issues/136#issuecomment-735137366
                class SubHandler(HandlerKlass):  # type: ignore
                    authenticator = auth

                    # def __init__(self, *args, **kwargs):
                    #     super().__init__(*args, **kwargs)
                    #     self.log.info("type of settings: %r", type(self.settings))
                    #     self.log.info("SubHandler.__init__")
                    #     self.settings['login_url'] = self.authenticator.login_url(self.hub.base_url)

                    @BaseHandler.template_namespace.getter
                    def template_namespace(self):
                        result = super().template_namespace
                        # Attempt to fix sign-up link on the login page of NativeAuthenticator
                        # However, this messes up e.g. the JupyteHub logo
                        result["base_url"] = (
                            url_path_join(self.hub.base_url, url_scope) + "/"
                        )
                        return result

                    # Replace the base_url as seen by the authenticator:
                    # This would fix /hub/native/authorize, but breaks login and
                    # sends us in a login loop over /hub/api/oauth2/authorize...
                    # @BaseHandler.hub.getter
                    # def hub(self):
                    #     # self.log.info("Accessing .hub property")
                    #     # self.log.info("type of super().hub: %r", type(super().hub))
                    #     return HubWrapper(super().hub, url_path_join(super().hub.base_url, with_trailing_slash(url_scope)))

                    @BaseHandler.settings.getter
                    def settings(self):
                        result = super().settings.copy()
                        result["login_url"] = auth.login_url(result["hub"].base_url)
                        return result

                routes.append((url_path_join(url_scope, path), SubHandler))

            if url_scope != "":
                # This fixes e.g. the logo on the login page of NativeAuthenticator
                # We just redirect the wrong paths: /hub/native/logo -> /hub/logo
                routes.append(
                    (url_path_join(url_scope, r"(.+)$"), RedirectHandler)
                )
                # This fixes the path when you click on the logo: /hub/native/ -> /hub
                routes.append((with_trailing_slash(url_scope), RedirectHandler))

        for route in routes:
            self.log.info("route %r", route)

        return routes

    # No need to implement authenticate(), since we set authenticator in get_handlers()
    async def authenticate(self, handler, data):
        raise NotImplementedError()
        # return super().authenticate(handler, data)

    def get_custom_html(self, base_url):
        html = [
            '<div class="service-login">',
            "<h2>Please sign in below</h2>",
        ]
        for authenticator in self._authenticators:
            login_service = authenticator.instance.login_service or "Local User"
            url = authenticator.instance.login_url(base_url)

            html.append(
                f"""
                <div style="margin-bottom:10px;">
                    <a style="width:20%;" role="button" class='btn btn-jupyter btn-lg' href='{url}'>
                    Sign in with {login_service}
                    </a>
                </div>
                """
            )
        footer_html = [
            "</div>",
        ]
        return "\n".join(html + footer_html)


def with_trailing_slash(path: str):
    if not path.endswith("/"):
        path += "/"
    return path


# class HubWrapper(object):
#     """ Wraps a jupyterhub.objects.Hub instance, and overrides the base_url. """
#     def __init__(self, wrappee: Hub, base_url):
#         self.wrappee = wrappee
#         self.base_url = base_url

#     def __getattr__(self, attr):
#         return getattr(self.wrappee, attr)


class RedirectHandler(RequestHandler):
    def get(self, path="", *args):
        """ Redirects to /hub/<path>. """
        new_url = f"/hub/{path}"
        self.redirect(new_url)
