from django.db import models
import uuid


class User(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.TextField(unique=True)
    first_name = models.TextField()
    middle_name = models.TextField(blank=True, null=True)
    last_name = models.TextField()
    age = models.IntegerField(blank=True, null=True)
    birthdate = models.DateField(blank=True, null=True)
    contact_number = models.TextField(blank=True, null=True)
    gender = models.TextField(blank=True, null=True)
    marital_status = models.TextField(blank=True, null=True)
    religion = models.TextField(blank=True, null=True)
    birthplace = models.TextField(blank=True, null=True)
    purok = models.TextField(blank=True, null=True)
    city = models.TextField(blank=True, null=True)
    avatar_url = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "users"


class Profile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.TextField(unique=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "profiles"
