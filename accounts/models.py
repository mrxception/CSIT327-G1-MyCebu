from django.db import models
from django.utils import timezone
import uuid
import json
import logging
from supabase import create_client
from django.conf import settings

logger = logging.getLogger(__name__)

GENDER_CHOICES = [
    ("male", "Male"),
    ("female", "Female"),
    ("other", "Other"),
    ("unspecified", "Unspecified"),
]

MARITAL_STATUS_CHOICES = [
    ("single", "Single"),
    ("married", "Married"),
    ("widowed", "Widowed"),
    ("separated", "Separated"),
    ("divorced", "Divorced"),
    ("unspecified", "Unspecified"),
]


# create a supabase client for model-level sync
_supabase_client = None
def _get_supabase_client():
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _supabase_client

class Account(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    supabase_id = models.UUIDField(null=True, blank=True, unique=True)
    email = models.EmailField(max_length=254, unique=True)
    first_name = models.CharField(max_length=120, blank=True)
    middle_name = models.CharField(max_length=120, blank=True)
    last_name = models.CharField(max_length=120, blank=True)
    display_name = models.CharField(max_length=200, blank=True)
    avatar_url = models.URLField(blank=True)
    contact_number = models.CharField(max_length=32, blank=True)
    birthdate = models.DateField(null=True, blank=True)
    age = models.PositiveSmallIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=16, choices=GENDER_CHOICES, default="unspecified")
    marital_status = models.CharField(max_length=16, choices=MARITAL_STATUS_CHOICES, default="unspecified")
    city = models.CharField(max_length=200, blank=True)
    purok = models.CharField(max_length=200, blank=True)
    verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["supabase_id"]),
        ]

    def __str__(self):
        return self.display_name or self.email or str(self.id)

    @property
    def full_name(self):
        parts = [self.first_name, self.middle_name, self.last_name]
        return " ".join([p for p in parts if p]).strip()

    @property
    def initials(self):
        name = self.display_name or self.full_name or self.email.split("@")[0]
        initials = "".join([p[0].upper() for p in name.split()[:2] if p])
        return initials or "US"

    def avatar_or_placeholder(self, size=100):
        if self.avatar_url:
            return self.avatar_url
        return f"https://placehold.co/{size}x{size}/E2E8F0/4A5568?text={self.initials}"

    def update_from_supabase_payload(self, payload: dict):
        changed = False
        mapping = {
            "email": "email",
            "first_name": "first_name",
            "middle_name": "middle_name",
            "last_name": "last_name",
            "display_name": "display_name",
            "avatar_url": "avatar_url",
            "contact_number": "contact_number",
            "birthdate": "birthdate",
        }
        for src, dest in mapping.items():
            if src in payload and payload[src] is not None:
                val = payload[src]
                if getattr(self, dest) != val:
                    setattr(self, dest, val)
                    changed = True
        if changed:
            self.save(update_fields=["first_name", "middle_name", "last_name", "display_name", "avatar_url", "contact_number", "birthdate", "updated_at"])
        return changed

    def to_supabase_payload(self) -> dict:
        """Return a dict suitable for Supabase 'users' table upsert"""
        payload = {
            "id": str(self.supabase_id) if self.supabase_id else None,
            "email": self.email,
            "first_name": self.first_name or None,
            "middle_name": self.middle_name or None,
            "last_name": self.last_name or None,
            "display_name": self.display_name or None,
            "avatar_url": self.avatar_url or None,
            "contact_number": self.contact_number or None,
            "birthdate": self.birthdate.isoformat() if self.birthdate else None,
            "age": int(self.age) if self.age is not None else None,
            "gender": self.gender or None,
            "marital_status": self.marital_status or None,
            "city": self.city or None,
            "purok": self.purok or None,
            "verified": bool(self.verified),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        return payload

    def save(self, *args, **kwargs):
        """
        Save locally, then upsert to Supabase 'users' table.
        If Supabase returns an id, persist it to supabase_id.
        """
        super().save(*args, **kwargs)

        try:
            supabase = _get_supabase_client()
            payload = self.to_supabase_payload()
            # remove id if None to let Supabase generate it
            if payload.get("id") is None:
                payload.pop("id", None)
            res = supabase.table("users").upsert(payload, on_conflict="email").execute()
            if getattr(res, "data", None):
                row = res.data[0]
                # update supabase_id from returned row if available
                if row.get("id"):
                    try:
                        self.supabase_id = uuid.UUID(row.get("id"))
                        super().save(update_fields=["supabase_id"])
                    except Exception:
                        # keep existing supabase_id if conversion fails
                        logger.debug("accounts.models.save: could not convert supabase id to UUID")
        except Exception as e:
            logger.error(f"accounts.models.save: Supabase sync failed: {e}")

    def delete(self, *args, **kwargs):
        """
        Delete locally and attempt to delete from Supabase (best-effort).
        """
        try:
            supabase = _get_supabase_client()
            if self.supabase_id:
                supabase.table("users").delete().eq("id", str(self.supabase_id)).execute()
        except Exception as e:
            logger.error(f"accounts.models.delete: Supabase delete failed: {e}")
        super().delete(*args, **kwargs)

    @classmethod
    def get_or_create_from_supabase(cls, email: str):
        """
        Lookup user row in Supabase users table and create or update local Account.
        """
        try:
            supabase = _get_supabase_client()
            res = supabase.table("users").select("*").eq("email", email).execute()
            if getattr(res, "data", None):
                row = res.data[0]
                sup_id = row.get("id")
                obj, created = cls.objects.get_or_create(email=email, defaults={
                    "supabase_id": sup_id,
                    "first_name": row.get("first_name") or "",
                    "middle_name": row.get("middle_name") or "",
                    "last_name": row.get("last_name") or "",
                    "display_name": row.get("display_name") or "",
                    "avatar_url": row.get("avatar_url") or "",
                })
                if not created:
                    # attempt to update fields if changed
                    updated = False
                    for attr in ("first_name","middle_name","last_name","display_name","avatar_url"):
                        if getattr(obj, attr) != (row.get(attr) or ""):
                            setattr(obj, attr, row.get(attr) or "")
                            updated = True
                    if updated:
                        obj.save()
                return obj
        except Exception as e:
            logger.error(f"accounts.models.get_or_create_from_supabase: {e}")
        return None
