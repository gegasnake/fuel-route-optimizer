from django.urls import path

from routing.views import RouteOptimizeView

urlpatterns = [
    path("optimize/", RouteOptimizeView.as_view(), name="route-optimize"),
]
