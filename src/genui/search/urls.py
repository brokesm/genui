"""
urls.py in src/genui/search/

"""
from django.urls import path, include
from rest_framework import routers
from . import views

router = routers.DefaultRouter()
router.register(r'occurrence', views.InchiKeyOccurrenceSearchViewSet,basename='occurrence_inchikey_search')
router.register(r'projects', views.InchiKeyProjectsSearchViewSet,basename='projects_inchikey_search')
router.register(r'sets', views.SimSearchMolsetViewSet,basename='molsets_sim_search')
router.register(r'sets', views.SubsSearchMolsetViewSet,basename='molsets_sub_search')
router.register(r'sets', views.SmartsSearchMolsetViewSet,basename='molsets_smarts_search')
router.register(r'projects', views.SimSearchProjectViewSet, basename='projects_sim_search')
router.register(r'projects', views.SubsSearchProjectViewSet, basename='projects_sub_search')
router.register(r'projects', views.SmartsSearchProjectViewSet, basename='projects_smarts_search')

router.register(r'sets',views.PropertyFilterViewSet, basename='molsets_property_filters')

urlpatterns = [
    path('', include(router.urls))
]