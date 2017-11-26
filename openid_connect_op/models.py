from urllib.parse import urlparse, splitquery, parse_qs

from django.db import models
import logging
log = logging.getLogger(__file__)


class AbstractOpenIDClient(models.Model):
    """
    An abstract model that implements OpenID client configuration (client = someone who requests access token)
    """

    #
    # ID of the client, the client sends this id in the access request
    #
    client_id = models.CharField(max_length=128, unique=True)

    #
    # After logging in, browser is redirected to one of these URIs (separated by newline).
    # The actual redirection URI is sent by the client, OpenID server verifies that the URI
    # is among these configured ones. For detail of how this decision is made, see check_redirect_url
    # method.
    #
    redirect_uris = models.TextField(default='')

    class Meta:
        abstract = True

    def has_user_approval(self, user):
        """
        Checks if the user has approved sending his data (including, for example, roles, phone number etc.)
        to this client

        :param user:    django User
        :return:        True if user has approved sending the data (and client's usage policy), False otherwise
        """
        return True

    def check_redirect_url(self, _redirect_uri):
        """
        Checks if the actual redirection uri is among the configured uris. If not, returns False.

        :param _redirect_uri: URI sent in the Authorization request
        :return:            True if it is among the configured URIs, False otherwise
        """
        part = urlparse(_redirect_uri)
        if part.fragment:
            log.debug("Can not contain fragment: %s", _redirect_uri)
            return False

        _base, _query = self.__split_base_query(_redirect_uri)

        for potential_redirect_uri in self.redirect_uris.split():
            redirect_uri_base, redirect_uri_query = self.__split_base_query(potential_redirect_uri)

            # The base of URI MUST exactly match the base
            if _base != redirect_uri_base:
                continue

            class NotFoundException(Exception):
                pass

            try:
                # every registered query component must exist in the
                # redirect_uri
                if redirect_uri_query:
                    for key, vals in redirect_uri_query.items():
                        if not _query or key not in _query:
                            raise NotFoundException()

                        for val in vals:
                            if val and val not in _query[key]:
                                raise NotFoundException()

                # and vice versa, every query component in the redirect_uri
                # must be registered
                if _query:
                    if redirect_uri_query is None:
                        raise NotFoundException()
                    for key, vals in _query.items():
                        if key not in redirect_uri_query:
                            raise NotFoundException()
                        for val in vals:
                            if redirect_uri_query[key]:
                                if val not in redirect_uri_query[key] and '' not in redirect_uri_query[key]:
                                    raise NotFoundException()
                # found it, so return True
                return True
            except NotFoundException:
                pass

        log.debug("%s Doesn't match any registered uris %s", _redirect_uri, self.redirect_uris)
        return False

    @staticmethod
    def __split_base_query(_redirect_uri):
        (_base, _query) = splitquery(_redirect_uri)
        if _query:
            _query = parse_qs(_query, keep_blank_values=True)
        return _base, _query
