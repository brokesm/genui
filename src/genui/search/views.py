from django.shortcuts import render

# Create your views here.

"""
views.py in src/genui/search/

Viewsets of the search package.
"""

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import GenericViewSet

from django_rdkit.models import *
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models.functions import JSONObject

from genui.compounds.models import Molecule, MolSet
from genui.projects.models import Project

from genui.search.serializers import (
    SimilaritySearchParamsSerializer, 
    SimilaritySearchResponseSerializer, 
    SubstructureSearchParamsSerializer,
    SubstructureSearchResponseSerializer,
    SmartsSearchParamsSerializer,
    SmartsSearchResponseSerializer,
    PropertyFilterSerializer,
    PropertyFiltersResponseSerializer,
    BaseSearchParamsSerializer,
    BaseSearchResponseSerializer,
    InchiKeySearchParamsSerializer,
    InchiKeySearchResponseSerializer
    )


class BaseSearch(GenericViewSet):
    queryset = Molecule.objects.all()
    serializer_class = BaseSearchParamsSerializer
    response_serializer_class = BaseSearchResponseSerializer

    def get_molset_ids(self, request, ids):
        raise NotImplementedError
    
    def build_queryset(self, molset_ids, params):
        raise NotImplementedError
    
    def do_search(self, request):
        
        params_ser = self.serializer_class(data=request.data)
        params_ser.is_valid(raise_exception=True)
        params = params_ser.validated_data
        top_n = params["top_n"]
        ids = params["ids"]

        molset_ids = self.get_molset_ids(request,ids)
        if isinstance(molset_ids, Response):
            return molset_ids
        
        qs = self.build_queryset(molset_ids,params)
        hits = qs[:top_n]

        total_searched = (
            self.get_queryset()
            .filter(Q(providers__id__in=molset_ids) & Q(providers__project__owner=request.user))
            .distinct()
            .count()
        )

        resp = {
            "query": params,
            "hits": hits,
            "total_searched": total_searched,
            "total_returned": len(hits),
        }

        resp_ser = self.response_serializer_class(resp, context={"request": request})
        return Response(resp_ser.data, status=status.HTTP_200_OK)
    

class SearchMolset(BaseSearch):

    def get_molset_ids(self, request, ids):
        qs = MolSet.objects.filter(project__owner=request.user, pk__in=ids)
        molset_ids = list(qs.values_list("id",flat=True))
        missing = [id for id in ids if id not in molset_ids]
        if missing:
            return Response({"error":f"Some MolSet IDs {missing} not found"}, status=status.HTTP_404_NOT_FOUND)
        return molset_ids
    

class SearchProject(BaseSearch):

    def get_molset_ids(self, request, ids):
        qs = MolSet.objects.filter(project__owner=request.user, project__id__in=ids)
        molset_ids = list(qs.values_list("id",flat=True))
        project_ids = list(Project.objects.filter(id__in=ids).values_list("id",flat=True))
        missing = [id for id in ids if id not in project_ids]
        if missing:
            return Response({"error":f"Some Project IDs {missing} not found"}, status=status.HTTP_404_NOT_FOUND)
        return molset_ids
    

class SimilaritySearch(BaseSearch):

    serializer_class = SimilaritySearchParamsSerializer
    response_serializer_class = SimilaritySearchResponseSerializer

    fingerprints = {
        "maccsFP": MACCS_FP,
        "morganFP": MORGANBV_FP
    }

    sims = {
        "tanimoto":TANIMOTO_SML,
        "dice":DICE_SML
    }

    def build_queryset(self, molset_ids, params):
        smiles = params["canonical"]
        fp_type = params["fp_type"]
        metric = params["metric"]
        threshold = params["threshold"]

        fp_fn = self.fingerprints[fp_type]
        sim_fn = self.sims[metric]
        value = fp_fn(Value(smiles))

        qs = (
            self.get_queryset()
            .annotate(similarity=sim_fn(f"entity__{fp_type}", value))
            .order_by("-similarity")
            .filter(similarity__gte=threshold)
            .annotate(project_ids=ArrayAgg("providers__project__id",distinct=True))
            .filter(providers__id__in=molset_ids)
            .distinct()
        )

        return qs
    

class SubstructureSearch(BaseSearch):
    serializer_class = SubstructureSearchParamsSerializer
    response_serializer_class = SubstructureSearchResponseSerializer

    def build_queryset(self, molset_ids, params):
        smiles = params["canonical"]

        qs = (
            self.get_queryset()
            .annotate(project_ids=ArrayAgg("providers__project__id",distinct=True))
            .filter(Q(providers__id__in=molset_ids) & Q(entity__rdMol__hassubstruct=smiles))
            .order_by(NUMHEAVYATOMS("entity__rdMol"))
            .distinct()
        )

        return qs
    

class SmartsSearch(BaseSearch):
    serializer_class = SmartsSearchParamsSerializer
    response_serializer_class = SmartsSearchResponseSerializer

    def build_queryset(self, molset_ids, params):
        smarts = params["canonical"]

        qs = (
            self.get_queryset()
            .annotate(project_ids=ArrayAgg("providers__project__id",distinct=True))
            .filter(Q(providers__id__in=molset_ids) & Q(entity__rdMol__hassubstruct=QMOL(Value(smarts))))
            .order_by(NUMHEAVYATOMS("entity__rdMol"))
            .distinct()
        )

        return qs

class InchiKeySearch(GenericViewSet):
    queryset = Project.objects.all()
    serializer_class = InchiKeySearchParamsSerializer
    response_serializer_class = InchiKeySearchResponseSerializer
    
    def build_queryset(self, params):
        inchi_key = params["input"]

        qs = (
            self.get_queryset()
            .filter(molset__molecules__entity__inchiKey=inchi_key)
            .annotate(
                providers=ArrayAgg(
                    JSONObject(
                        id=F("molset__id"),
                        name=F("molset__name"),
                    ),
                    filter=Q(molset__molecules__entity__inchiKey=inchi_key),
                    distinct=True,
                )
            )
        )

        return qs
    
    def do_search(self,request):
        params_ser = self.serializer_class(data=request.data)
        params_ser.is_valid(raise_exception=True)
        params = params_ser.validated_data

        qs = self.build_queryset(params)

        resp = {
            "query":params,
            "occurrence":qs
        }

        print(qs[0])

        resp_ser = self.response_serializer_class(resp)
        return Response(resp_ser.data, status=status.HTTP_200_OK)


class SimSearchMolsetViewSet(SearchMolset, SimilaritySearch):

    @action(detail=False, methods=["post"], url_path="similarity")
    def molset_similarity_search(self, request, *args, **kwargs):
        response = self.do_search(request)
        return response
        
    
class SubsSearchMolsetViewSet(SearchMolset, SubstructureSearch):

    @action(detail=False, methods=["post"], url_path="substructure")
    def molset_substructure_search(self, request, *args, **kwargs):
        response = self.do_search(request)
        return response

    
class SmartsSearchMolsetViewSet(SearchMolset, SmartsSearch):

    @action(detail=False, methods=["post"], url_path="smarts")
    def molset_smarts_search(self, request, *args, **kwargs):
        response = self.do_search(request)
        return response
    

class InchiKeySearchViewSet(InchiKeySearch):

    @action(detail=False, methods=["post"], url_path="inchikey")
    def molset_inchikey_search(self, request, *args, **kwargs):
        response = self.do_search(request)
        return response


class SimSearchProjectViewSet(SearchProject, SimilaritySearch):

    @action(detail=False, methods=["post"], url_path="similarity")
    def project_similarity_search(self, request, *args, **kwargs):
        response = self.do_search(request)
        return response
    

class SubsSearchProjectViewSet(SearchProject, SubstructureSearch):

    @action(detail=False, methods=["post"], url_path="substructure")
    def project_substructure_search(self, request, *args, **kwargs):
        response = self.do_search(request)
        return response


class SmartsSearchProjectViewSet(SearchProject, SmartsSearch):

    @action(detail=False, methods=["post"], url_path="smarts")
    def project_smarts_search(self, request, *args, **kwargs):
        response = self.do_search(request)
        return response
    
    
class PropertyFilterViewSet(SearchMolset):

    serializer_class = PropertyFilterSerializer
    response_serializer_class = PropertyFiltersResponseSerializer

    def build_queryset(self, molset_ids, params):
        property = params["property"]
        relation = params["relation"]
        value = params["value"]

        qs = (
            self.get_queryset()
            .select_related("entity")
            .prefetch_related("activities")
            .filter(Q(providers__id__in=molset_ids) & Q(**{f"entity__rdMol__{property}__{relation}":value}))
            .distinct()
        )

        return qs
    
    @action(detail=False, methods=["post"], url_path="filter")
    def molset_property_filters(self, request, *args, **kwargs):
        response = self.do_search(request)
        return response
    