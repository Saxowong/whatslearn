### api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views import (
    RegisterView,
    LoginView,
    DictionaryItemViewSet,
    StudentWordViewSet,
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

router = DefaultRouter()
router.register(r"dictionary", DictionaryItemViewSet, basename="dictionary")
router.register(r"library", StudentWordViewSet, basename="studentword")

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("", include(router.urls)),
]
