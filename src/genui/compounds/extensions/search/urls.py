"""
urls.py in src/genui/compounds/extensions/search/

"""
from django.urls import path, include
from rest_framework import routers
from . import views

router = routers.DefaultRouter()
router.register(r'sets', views.SearchSetViewSet)

urlpatterns = [
    path('', include(router.urls)),
]