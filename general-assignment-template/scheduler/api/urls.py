from django.urls import path
from .views import ReviewView, DueCardsView

urlpatterns = [
    path("reviews", ReviewView.as_view(), name="review"),
    path("users/<uuid:user_id>/due-cards", DueCardsView.as_view(), name="due-cards"),
]