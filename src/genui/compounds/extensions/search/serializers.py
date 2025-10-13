"""
serializers.py in src/genui/compounds/extensions/Searchimport

"""
from rest_framework import serializers
from genui.compounds.serializers import MoleculeSerializer, ActivitySerializer
from genui.compounds.models import Molecule
from rdkit import Chem



# ---------------------------
# Query / Params
# ---------------------------

class SimilaritySearchParamsSerializer(serializers.Serializer):

    FP_CHOICES = (
        ("morgan", "Morgan (ECFP-like)"),
        ("maccs", "MACCS Keys"),
        ("atom_pair", "Atom Pair"),
        ("tt", "Topological Torsion"),
    )
    METRIC_CHOICES = (
        ("tanimoto", "Tanimoto"),
        ("dice", "Dice"),
        ("cosine", "Cosine"),
    )

    smiles = serializers.CharField(required=True, allow_blank=False, trim_whitespace=True)
    canonical_smiles = serializers.CharField(read_only=True)

    top_n = serializers.IntegerField(min_value=1, max_value=1000, required=False, default=25)
    threshold = serializers.FloatField(min_value=0.0, max_value=1.0, required=False, allow_null=True, default=None)

    fp_type = serializers.ChoiceField(choices=FP_CHOICES, required=False, default="morgan")
    radius = serializers.IntegerField(min_value=1, max_value=6, required=False, default=2)
    n_bits = serializers.IntegerField(min_value=256, max_value=8192, required=False, default=2048)
    metric = serializers.ChoiceField(choices=METRIC_CHOICES, required=False, default="tanimoto")

    return_fields = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        default=list,
        help_text="Optional list of molecule fields to retain in each hit (server may ignore)."
    )
    
    def validate(self, attrs):
        smiles = attrs.get("smiles", "").strip()
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            raise serializers.ValidationError({"smiles": "Invalid SMILES string."})
        attrs["canonical_smiles"] = Chem.MolToSmiles(mol)

        # If a non-morgan fp is selected, ignore radius
        if attrs["fp_type"] != "morgan":
            attrs["radius"] = None

        # If threshold is set, ensure it's within the (0-1) interval
        thr = attrs.get("threshold")
        if thr is not None and not (0.0 <= thr <= 1.0):
            raise serializers.ValidationError({"threshold": "Threshold must be between 0.0 and 1.0."})

        return attrs


class SimilarityHitSerializer(MoleculeSerializer):
    """
    Extends your existing MoleculeSerializer to include similarity metadata.
    The view should attach `.similarity` and optionally `.rank` to instances
    (e.g., annotate queryset or wrap rows as objects/dicts).
    """
    similarity = serializers.FloatField(read_only=True)
    rank = serializers.IntegerField(read_only=True, required=False)

    class Meta():
        model = Molecule
        fields = MoleculeSerializer.Meta.fields + ("similarity", "rank")


class SimilaritySearchResponseSerializer(serializers.Serializer):
    """
    Response payload for a similarity search.
    """
    query = SimilaritySearchParamsSerializer(read_only=True)

    hits = SimilarityHitSerializer(many=True, read_only=True)

    total_searched = serializers.IntegerField(read_only=True, required=False)
    total_returned = serializers.IntegerField(read_only=True, required=False)
