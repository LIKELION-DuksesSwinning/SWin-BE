from django.urls import path
from .views import LoginView, OnboardingView

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('onboarding/', OnboardingView.as_view(), name='onboarding'),
]