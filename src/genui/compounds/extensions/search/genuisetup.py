"""
genuisetup.py in src/genui/compounds/extensions/search/

"""

PARENT = 'genui.compounds'

def setup(*args, **kwargs):
    from . import models
    from genui.utils.init import createGroup
    createGroup(
        "GenUI_Users",
        [
            models.SearchMolecule,
            models.SearchMolSet
        ]
    )