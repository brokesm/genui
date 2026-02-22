"""
urls.py in src/genui/search/

"""
from django.urls import path, include
from rest_framework import routers
from . import views

router = routers.DefaultRouter()
router.register(r'', views.InchiKeySearchViewSet,basename='inchikey_search')
router.register(r'set', views.SimSearchMolsetViewSet,basename='molset_sim_search')
router.register(r'set', views.SubsSearchMolsetViewSet,basename='molset_sub_search')
router.register(r'set', views.SmartsSearchMolsetViewSet,basename='molset_smarts_search')
router.register(r'project', views.SimSearchProjectViewSet, basename='project_sim_search')
router.register(r'project', views.SubsSearchProjectViewSet, basename='project_sub_search')
router.register(r'project', views.SmartsSearchProjectViewSet, basename='project_smarts_search')

router.register(r'set',views.PropertyFilterViewSet, basename='molset_property_filters')

urlpatterns = [
    path('', include(router.urls))
]