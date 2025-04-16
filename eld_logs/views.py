from django.shortcuts import render
from rest_framework import viewsets
from .models import LogSheet
from .serializers import LogSheetSerializer

# Create your views here.

class LogSheetViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LogSheet.objects.all()
    serializer_class = LogSheetSerializer
    
    def get_queryset(self):
        queryset = LogSheet.objects.all()
        trip_id = self.request.query_params.get('trip_id', None)
        if trip_id is not None:
            queryset = queryset.filter(trip__id=trip_id)
        return queryset

