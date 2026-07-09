# resources.py
from import_export import resources
from .models import MCQ

class CSVDataResource(resources.ModelResource):
    class Meta:
        model = MCQ