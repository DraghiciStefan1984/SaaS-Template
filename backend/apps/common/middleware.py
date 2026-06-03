from uuid import uuid4

REQUEST_ID_HEADER = "HTTP_X_REQUEST_ID"
CORRELATION_ID_HEADER = "HTTP_X_CORRELATION_ID"
RESPONSE_HEADER = "X-Request-ID"
MAX_REQUEST_ID_LENGTH = 120


class RequestIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = self.get_request_id(request)
        request.request_id = request_id
        response = self.get_response(request)
        response[RESPONSE_HEADER] = request_id
        return response

    def get_request_id(self, request):
        raw_request_id = (
            request.META.get(REQUEST_ID_HEADER)
            or request.META.get(CORRELATION_ID_HEADER)
            or uuid4().hex
        )
        request_id = "".join(
            character for character in raw_request_id if character.isalnum() or character in "-_"
        )
        return (request_id or uuid4().hex)[:MAX_REQUEST_ID_LENGTH]
