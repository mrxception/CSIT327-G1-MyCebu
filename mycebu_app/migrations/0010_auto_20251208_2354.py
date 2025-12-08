from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [('mycebu_app', '0001_initial')]  # Your last migration

    operations = [
        migrations.RunSQL(
            "ALTER TABLE users DROP CONSTRAINT IF EXISTS users_id_fkey;",
            reverse_sql="SELECT 1;"  # Irreversible, but fine
        ),
    ]