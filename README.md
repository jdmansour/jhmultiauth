# MultiAuthenticator for JupyterHub

This package allows you to use multiple authenticators in JupyterHub at the same time.  For example, you can allow logins via LTI, and alternatively logins via OAuth and local accounts.

## Installation

Install the package via pip into the hub.  If you are using TLJH, you can do:

    /opt/tljh/hub/bin/pip install https://github.com/jdmansour/jhmultiauth

For a development installation, clone the source and do:

    /opt/tljh/hub/bin/pip install -e .

## Configuration

Add the following to your JupyterHub configuration:

    c.JupyterHub.authenticator_class = 'multiauthenticator'

    c.MultiAuthenticator.authenticators = [
        (ltiauthenticator.lti11.LTI11Authenticator, ''),
        ('native', '/native'),
    ]

`MultiAuthenticator.authenticators` is a list of tuples.  The first entry gives the authenticator class to use.  You can pass anything that you can pass to `JupyterHub.authenticator_class` - either a class object, a string containing the module and class name, or the "short name" aka "entry point" of the class.

The second entry in the tuple is the path prefix to use for this authenticator.  For example, if it is '/native', the authenticator will use `/hub/native/login` instead of `/hub/login`.  `/hub/login` will show a button linking to each login possibility.

You may also use no prefix for one authenticator, if that authenticator does not provide a GET handler for `/hub/login`.  This is the case for the `ltiauthenticator` package, for example.

## Known bugs

Note that this package is currently experimental, and not all Authenticators work perfectly.

For example, if you use NativeAuthenticator, some of the paths in the rendered HTML will be wrong, and the link to create a new account will not work.

