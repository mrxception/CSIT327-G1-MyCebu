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


class Official(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.TextField()
    position = models.TextField()
    office = models.TextField(blank=True, null=True)
    district = models.TextField(blank=True, null=True)
    email = models.TextField(blank=True, null=True)
    phone = models.TextField(blank=True, null=True)
    initials = models.TextField(blank=True, null=True)
    photo = models.TextField(blank=True, null=True) 
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "directory_officials"


class Department(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.TextField()
    head = models.TextField(blank=True, null=True)
    contact_details = models.JSONField(blank=True, null=True) 
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "directory_departments"


class EmergencyContact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service = models.TextField()
    numbers = models.JSONField(blank=True, null=True) 
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "directory_emergency"

class Service(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service_id = models.TextField(unique=True)      
    icon = models.TextField()                    
    title = models.TextField()
    description = models.TextField()
    color = models.TextField()                       

    requirements = models.JSONField(default=list, blank=True)
    steps = models.JSONField(default=list, blank=True)
    step_details = models.JSONField(default=list, blank=True, null=True)  
    additional_info = models.JSONField(blank=True, null=True)
    forms = models.JSONField(default=list, blank=True)
    forms_download = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "services"
        verbose_name_plural = "services"

    def __str__(self):
        return self.title
    
class ChatHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField() # Links to your Custom User ID
    user_message = models.TextField()
    bot_response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chat_history"
        ordering = ['-created_at']