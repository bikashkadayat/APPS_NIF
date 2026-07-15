"""Reports API: request (async), poll status, download, schedule, analytics."""
import threading

from django.conf import settings
from django.http import FileResponse, Http404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.models import AuditLog
from audit.services import log_action
from users.admin_views import IsAdminOrSuperuser
from . import report_service
from .analytics import dashboard_analytics
from .models import ReportRun, ScheduledReport
from .serializers import (
    ReportRequestSerializer, ReportRunSerializer, ScheduledReportSerializer,
)


def _spawn_generation(run_id):
    """Generate a report in a background thread (its own DB connection)."""
    from django.db import connection

    def _work():
        try:
            run = ReportRun.objects.get(pk=run_id)
            report_service.generate_report(run)
        finally:
            connection.close()

    threading.Thread(target=_work, daemon=True).start()


class ReportsViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAdminOrSuperuser]
    serializer_class = ReportRunSerializer

    def get_queryset(self):
        qs = ReportRun.objects.select_related("requested_by").all()
        # Admins see all; the hub shows "my" runs via ?mine=1.
        if self.request.query_params.get("mine"):
            qs = qs.filter(requested_by=self.request.user)
        return qs

    @action(detail=False, methods=["post"], url_path="request")
    def request_report(self, request):
        serializer = ReportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        run = ReportRun.objects.create(
            report_type=serializer.validated_data["report_type"],
            params=serializer.validated_data.get("params") or {},
            requested_by=request.user,
            status=ReportRun.Status.PENDING,
        )
        log_action(request.user, AuditLog.Action.CREATE, instance=run, request=request)

        if getattr(settings, "REPORTS_RUN_SYNC", False):
            report_service.generate_report(run)
            run.refresh_from_db()
        else:
            _spawn_generation(run.id)

        return Response(ReportRunSerializer(run).data, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["get"], url_path="status")
    def report_status(self, request, pk=None):
        run = self.get_object()
        from documents.protected_media import signed_media_url
        file_url = signed_media_url(run.file.name, ttl=600, download=True) if run.file else None
        return Response({"id": str(run.id), "status": run.status, "error": run.error, "file_url": file_url})

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        run = self.get_object()
        if run.status != ReportRun.Status.READY or not run.file:
            return Response({"detail": f"Report is not ready (status: {run.status})."},
                            status=status.HTTP_409_CONFLICT)
        try:
            handle = run.file.open("rb")
        except FileNotFoundError:
            raise Http404("Report file is missing.")
        return FileResponse(handle, as_attachment=True, filename=run.file.name.split("/")[-1])


class ScheduledReportViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminOrSuperuser]
    serializer_class = ScheduledReportSerializer
    queryset = ScheduledReport.objects.all()

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_action(self.request.user, AuditLog.Action.CREATE, instance=instance, request=self.request)

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(self.request.user, AuditLog.Action.UPDATE, instance=instance, request=self.request)

    def perform_destroy(self, instance):
        log_action(self.request.user, AuditLog.Action.DELETE, instance=instance, request=self.request)
        instance.delete()


class AnalyticsView(APIView):
    """GET /api/v1/reports/analytics/?year= - admin dashboard data."""
    permission_classes = [IsAdminOrSuperuser]

    def get(self, request):
        year = request.query_params.get("year")
        return Response(dashboard_analytics(int(year) if year else None))
