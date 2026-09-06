from common import context


class RequestContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        context.set_request_context(request)
        try:
            response = self.get_response(request)
        finally:
            # The bearer-token authenticator leases a pooled connection while it
            # builds the UserPrincipal (lazy permission/scope queries). Release it
            # as soon as the response is produced, before the connection is reused.
            auth_session = getattr(request, "auth_session", None)
            if auth_session is not None:
                auth_session.close()
        return response