from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import LogSheet, DutyStatusChange
from .serializers import LogSheetSerializer, DutyStatusChangeSerializer
from .services.log_generator import LogGenerator
from route_planner.models import Trip

# Create your views here.

class LogSheetViewSet(viewsets.ModelViewSet):
    serializer_class = LogSheetSerializer
    permission_classes = [IsAuthenticated]
    queryset = LogSheet.objects.all()  # Add this line
    
    def get_queryset(self):
        """
        This view should return a list of all the log sheets
        for trips belonging to the currently authenticated user.
        """
        user = self.request.user
        return LogSheet.objects.filter(trip__user=user)
    
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
            trip = get_object_or_404(Trip, id=trip_id, user=request.user)
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
    serializer_class = DutyStatusChangeSerializer
    permission_classes = [IsAuthenticated]
    queryset = DutyStatusChange.objects.all()  # Add this line too
    
    def get_queryset(self):
        """
        This view should return a list of all duty status changes
        for log sheets belonging to the currently authenticated user.
        """
        user = self.request.user
        return DutyStatusChange.objects.filter(log_sheet__trip__user=user)

    def perform_create(self, serializer):
        """
        Validate that the log_sheet belongs to the current user.
        """
        log_sheet = serializer.validated_data['log_sheet']
        if log_sheet.trip.user != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not have permission to modify this log sheet.")
        serializer.save()