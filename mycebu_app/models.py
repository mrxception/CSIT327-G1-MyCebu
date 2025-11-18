from django.db import models
from django.utils import timezone
import uuid
import json
import logging
from supabase import create_client
from django.conf import settings

logger = logging.getLogger(__name__)

STATUS_CHOICES = [
    ("in_progress", "In Progress"),
    ("submitted", "Submitted"),
    ("in_review", "In Review"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
    ("cancelled", "Cancelled"),
]

class UserProfile(models.Model):
    supabase_id = models.UUIDField(primary_key=True, editable=False)
    email = models.EmailField(max_length=254, unique=True)
    first_name = models.CharField(max_length=120, blank=True, null=True)
    middle_name = models.CharField(max_length=120, blank=True, null=True)
    last_name = models.CharField(max_length=120, blank=True, null=True)
    display_name = models.CharField(max_length=200, blank=True, null=True)
    avatar_url = models.URLField(blank=True, null=True)
    contact_number = models.CharField(max_length=32, blank=True, null=True)
    birthdate = models.DateField(blank=True, null=True)
    age = models.PositiveSmallIntegerField(blank=True, null=True)

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name or (self.email or str(self.supabase_id))


class Permit(models.Model):
    id = models.CharField(max_length=100, primary_key=True) 
    title = models.CharField(max_length=240)
    subtitle = models.CharField(max_length=400, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    requirements = models.JSONField(default=list, blank=True)  
    steps = models.JSONField(default=list, blank=True)      
    additional_info = models.TextField(blank=True, null=True)
    downloadable = models.JSONField(default=dict, blank=True) 

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


_supabase_client = None
def _get_supabase_client():
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _supabase_client

class Application(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="applications")
    permit = models.ForeignKey(Permit, on_delete=models.PROTECT, related_name="applications")
    progress = models.PositiveSmallIntegerField(default=0)  
    step_index = models.PositiveSmallIntegerField(default=0) 
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="in_progress")
    requirements_data = models.JSONField(default=dict, blank=True) 

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["status"]),
            models.Index(fields=["permit"]),
        ]
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.permit_id_display} — {self.user.email}"

    @property
    def permit_id_display(self):
        return self.permit.id if self.permit else "unknown"

    def advance_to(self, next_index: int):
        total_steps = len(self.permit.steps) if self.permit and self.permit.steps else 1
        self.step_index = max(0, min(next_index, max(0, total_steps - 1)))
        self.progress = int((self.step_index / max(total_steps, 1)) * 100)
        return self

    def to_supabase_payload(self) -> dict:
        return {
            "id": str(self.id),
            "user_id": str(self.user.supabase_id) if self.user and self.user.supabase_id else None,
            "permit_id": self.permit.id if self.permit else None,
            "progress": int(self.progress or 0),
            "step_index": int(self.step_index or 0),
            "status": self.status or "in_progress",
            "requirements_data": self.requirements_data or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def save(self, *args, **kwargs):
        """
        Save locally, then upsert to Supabase 'applications' table.
        """
        super().save(*args, **kwargs)
        try:
            supabase = _get_supabase_client()
            payload = self.to_supabase_payload()
            res = supabase.table("applications").upsert(payload).execute()
            if getattr(res, "data", None):
                pass
        except Exception as e:
            logger.error(f"mycebu_app.models.Application.save: Supabase sync failed: {e}")

    def delete(self, *args, **kwargs):
        try:
            supabase = _get_supabase_client()
            supabase.table("applications").delete().eq("id", str(self.id)).execute()
        except Exception as e:
            logger.error(f"mycebu_app.models.Application.delete: Supabase delete failed: {e}")
        super().delete(*args, **kwargs)

    @classmethod
    def create_from_supabase_row(cls, row: dict):
        """
        Build or update a local Application from a Supabase row (best-effort).
        Expects row to have keys: id, user_id, permit_id, progress, step_index, status, requirements_data.
        """
        try:
            user = None
            if row.get("user_id"):
                try:
                    user = UserProfile.objects.filter(supabase_id=row.get("user_id")).first()
                except Exception:
                    user = None
            permit = None
            if row.get("permit_id"):
                permit = Permit.objects.filter(id=row.get("permit_id")).first()
            obj, created = cls.objects.update_or_create(
                id=uuid.UUID(row.get("id")),
                defaults={
                    "user": user,
                    "permit": permit,
                    "progress": row.get("progress") or 0,
                    "step_index": row.get("step_index") or 0,
                    "status": row.get("status") or "in_progress",
                    "requirements_data": row.get("requirements_data") or {},
                }
            )
            return obj
        except Exception as e:
            logger.error(f"mycebu_app.models.Application.create_from_supabase_row: {e}")
            return None
