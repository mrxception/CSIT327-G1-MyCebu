from django.db import models
from django.utils import timezone
import uuid

class PasswordResetOTP(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(db_index=True)
    otp = models.CharField(max_length=32)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    expires_at = models.DateTimeField()
    consumed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def is_valid(self):
        now = timezone.now()
        return (not self.consumed) and (self.expires_at > now)

    def consume(self):
        self.consumed = True
        self.save(update_fields=["consumed"])
