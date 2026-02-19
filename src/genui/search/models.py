from django.db import models

# Create your models here.

"""
models.py in src/genui/search/
"""

from django.db import models
from genui.compounds.models import Molecule, MolSet


class SearchMolecule(Molecule):
    pass

class SearchMolSet(MolSet):
    pass
