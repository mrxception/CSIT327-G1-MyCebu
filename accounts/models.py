from django.db import models
import uuid


class User(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)  # FIXED: Use EmailField for better validation (was TextField)
    first_name = models.CharField(max_length=150)  # FIXED: Use CharField (TextField is for long text)
    middle_name = models.CharField(max_length=150, blank=True, null=True)
    last_name = models.CharField(max_length=150)
    age = models.IntegerField(blank=True, null=True)
    birthdate = models.DateField(blank=True, null=True)
    contact_number = models.CharField(max_length=20, blank=True, null=True)
    gender = models.CharField(max_length=50, blank=True, null=True)
    marital_status = models.CharField(max_length=50, blank=True, null=True)
    religion = models.CharField(max_length=100, blank=True, null=True)
    birthplace = models.CharField(max_length=200, blank=True, null=True)
    purok = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    avatar_url = models.URLField(blank=True, null=True)  # FIXED: URLField for avatars
    created_at = models.DateTimeField(auto_now_add=True)  # FIXED: auto_now_add for consistency
    role = models.CharField(max_length=50, default='user')  # FIXED: CharField

    class Meta:
        db_table = "users"

# If Profile is unused, delete it to clean up