"""
Wraps wger's own urls.py without modifying it, so that our gym app's
API routes survive container recreation even if wger.urls.py itself
gets overwritten by an image update.
"""
from django.urls import include, path

from wger.urls import urlpatterns as _wger_urlpatterns

urlpatterns = _wger_urlpatterns + [
    path('api/v2/gym/', include('wger.gym.urls_api')),
]
