from django.shortcuts import render

# Create your views here.

"""
views.py in src/genui/compounds/extensions/search/

Viewsets of the search package.
"""
from typing import List, Tuple, Callable

from rdkit import Chem
from rdkit import DataStructs
from rdkit.Chem import rdMolDescriptors,MACCSkeys,AllChem

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import GenericViewSet

from django.shortcuts import get_object_or_404

from genui.compounds.extensions.search.initializer import SearchSetInitializer
from genui.compounds.models import Molecule, MolSet
from genui.compounds.extensions.search.serializers import SimilaritySearchParamsSerializer, SimilaritySearchResponseSerializer


class SearchSetViewSet(GenericViewSet):

    queryset = MolSet.objects.all()
    serializer_class = SimilaritySearchParamsSerializer

    fps = {
        "morgan": AllChem.GetMorganFingerprintAsBitVect,
        "atom_pair": rdMolDescriptors.GetHashedAtomPairFingerprintAsBitVect,
        "tt": rdMolDescriptors.GetHashedTopologicalTorsionFingerprintAsBitVect,
        "maccs": MACCSkeys.GenMACCSKeys
    }

    sims = {
        "tanimoto": DataStructs.TanimotoSimilarity,
        "cosine":DataStructs.CosineSimilarity,
        "dice":DataStructs.DiceSimilarity
    }

    def _calc_fp(self, mol, fp: Callable = fps["morgan"], radius: int = 2, n_bits: int = 2048):
        try:
            return fp(mol, radius=radius, nBits=n_bits)
        except TypeError:
            pass
        try:
            return fp(mol, nBits=n_bits)
        except TypeError:
            return fp(mol)

    def _fp_from_smiles(self, smiles: str, fp, radius: int, n_bits: int):
        qmol = Chem.MolFromSmiles(smiles)
        if qmol is None:
            return None
        return self._calc_fp(qmol, fp, radius, n_bits)


    # def _mol_fp_for_hit(self, m: Molecule):
    #     return m.fingerprint  

    @action(detail=True, methods=["post"], url_path="search/similarity")
    def similarity_search(self, request, pk, *args, **kwargs):
        params_ser = SimilaritySearchParamsSerializer(data=request.data)
        params_ser.is_valid(raise_exception=True)
        params = params_ser.validated_data
        
        molset = get_object_or_404(self.get_queryset(), pk=pk)
        mols_qs = molset.molecules.distinct()
        
        # Load request data into variables
        qcan_smi: str = params["canonical_smiles"]
        fp: Callable = self.fps[params["fp_type"]]
        similarity: Callable = self.sims[params["metric"]]
        radius: int = params["radius"]
        n_bits: int = params["n_bits"]

        # Prepare query fingerprint
        qfp = self._fp_from_smiles(qcan_smi, fp, radius, n_bits)
        if qfp is None:
            return Response({"Detail": "Could not build fingerprint for the query molecule."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Calculate similarities
        threshold = params["threshold"]
        scored: List[Tuple[float, Molecule]] = []
        for m in mols_qs.iterator():
            tcan_smi = m.canonicalSMILES
            tfp = self._fp_from_smiles(tcan_smi, fp, radius, n_bits)
            if tfp is None:
                continue
            sim = similarity(qfp, tfp)
            if threshold is None or sim >= threshold:
                scored.append((sim, m))

        # Sort, select top N
        scored.sort(key=lambda t: t[0], reverse=True)
        top_n = params["top_n"]
        top_hits = scored[:top_n]

        # Attach similarity to instances so it follows the serializer
        hits = []
        for rank, (sim, m) in enumerate(top_hits, start=1):
            setattr(m, "similarity", float(sim))
            setattr(m, "rank", rank)
            hits.append(m)
        
        payload = {
            "query": params,
            "hits": hits,
            "total_searched": molset.molecules.distinct().count(),
            "total_returned": len(hits)
        }

        resp_ser = SimilaritySearchResponseSerializer(payload)
        return Response(resp_ser.data, status=status.HTTP_200_OK)
