import json
import logging
import time
from django.http import StreamingHttpResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required

logger = logging.getLogger(__name__)


class SSEStreamView(View):
    def get(self, request):
        channel = request.GET.get("channel", "dashboard")

        def event_stream():
            yield f"retry: 30000\n\n"
            yield f"data: {json.dumps({'type': 'connected', 'channel': channel})}\n\n"

            while True:
                time.sleep(30)
                yield f": heartbeat\n\n"

        response = StreamingHttpResponse(
            event_stream(),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["Connection"] = "keep-alive"
        response["X-Accel-Buffering"] = "no"
        return response
