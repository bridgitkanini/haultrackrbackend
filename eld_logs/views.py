from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import LogSheet, DutyStatusChange
from .serializers import LogSheetSerializer, DutyStatusChangeSerializer
from .services.log_generator import LogGenerator
from route_planner.models import Trip

# Create your views here.

class LogSheetViewSet(viewsets.ModelViewSet):
    queryset = LogSheet.objects.all()
    serializer_class = LogSheetSerializer
    
    def get_queryset(self):
        queryset = LogSheet.objects.all()
        trip_id = self.request.query_params.get('trip_id', None)
        if trip_id is not None:
            queryset = queryset.filter(trip__id=trip_id)
        return queryset
    
    @action(detail=False, methods=['post'])
    def generate_logs(self, request):
        """
        Generate log sheets for a trip
        """
        trip_id = request.data.get('trip_id')
        if not trip_id:
            return Response(
                {'error': 'trip_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            trip = get_object_or_404(Trip, id=trip_id)
            generator = LogGenerator(trip)
            log_sheets = generator.generate_logs()
            
            serializer = self.get_serializer(log_sheets, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def grid(self, request, pk=None):
        """
        Generate visual grid representation of the log sheet
        """
        try:
            log_sheet = self.get_object()
            generator = LogGenerator(log_sheet.trip)
            grid_image = generator.generate_grid(log_sheet)
            
            return Response({
                'grid_image': grid_image,
                'content_type': 'image/png'
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class DutyStatusChangeViewSet(viewsets.ModelViewSet):
    queryset = DutyStatusChange.objects.all()
    serializer_class = DutyStatusChangeSerializer
    
    def get_queryset(self):
        queryset = DutyStatusChange.objects.all()
        log_sheet_id = self.request.query_params.get('log_sheet_id', None)
        if log_sheet_id is not None:
            queryset = queryset.filter(log_sheet__id=log_sheet_id)
        return queryset