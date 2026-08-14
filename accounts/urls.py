from django.urls import path
from .views import *

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('onboarding/', OnboardingView.as_view(), name='onboarding'),
    path('agreements/', AgreementView.as_view(), name='agreements'),
    path('settings/notifications/', NotificationSettingView.as_view(), name='notification-settings'),
]