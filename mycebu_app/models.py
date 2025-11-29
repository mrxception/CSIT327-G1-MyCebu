from django.db import models
import uuid


class Complaint(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField()
    category = models.TextField()
    subcategory = models.TextField(blank=True, null=True)
    subject = models.TextField()
    location = models.TextField()
    description = models.TextField()
    is_anonymous = models.BooleanField(blank=True, null=True)
    name = models.TextField(blank=True, null=True)
    email = models.TextField(blank=True, null=True)
    phone = models.TextField(blank=True, null=True)
    status = models.TextField()
    attachments = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "complaints"


class Ordinance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.TextField()
    pdf_file_path = models.TextField()
    name_or_ordinance = models.TextField()
    author = models.TextField(blank=True, null=True)
    ordinance_number = models.TextField(blank=True, null=True)
    date_of_enactment = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "ordinances"


class ServiceApplication(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField()
    service_type = models.TextField()
    reference_number = models.TextField()
    progress = models.IntegerField(blank=True, null=True)
    step_index = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "service_applications"
