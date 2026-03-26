# Migration to rename employees to staff
import django.core.validators
import django.db.models.deletion
import uuid
from decimal import Decimal
from django.db import migrations, models


def rename_table_if_exists(apps, schema_editor):
    """Rename employees table to staff if it exists"""
    with schema_editor.connection.cursor() as cursor:
        # Check if employees table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='employees';
        """)
        if cursor.fetchone():
            # Table exists, rename it
            cursor.execute("ALTER TABLE employees RENAME TO staff;")
            cursor.execute("ALTER TABLE staff RENAME COLUMN employee_number TO staff_number;")
            
            # Drop old constraint and indexes
            cursor.execute("ALTER TABLE staff DROP CONSTRAINT IF EXISTS unique_employee_number;")
            cursor.execute("DROP INDEX IF EXISTS employees_employe_68f2c7_idx;")
            cursor.execute("DROP INDEX IF EXISTS employees_company_f82024_idx;")
            cursor.execute("DROP INDEX IF EXISTS employees_email_f66e96_idx;")
            
            # Add new constraint and indexes
            cursor.execute("ALTER TABLE staff ADD CONSTRAINT unique_staff_number UNIQUE (staff_number);")
            cursor.execute("CREATE INDEX staff_staff_n_68f2c7_idx ON staff (staff_number);")
            cursor.execute("CREATE INDEX staff_company_f82024_idx ON staff (company_id, employment_status);")
            cursor.execute("CREATE INDEX staff_email_f66e96_idx ON staff (email);")


class Migration(migrations.Migration):

    initial = True
    
    # This replaces the employees app
    replaces = [('employees', '0001_initial')]

    dependencies = [
        ('authentication', '0001_initial'),
        ('companies', '0001_initial'),
    ]

    operations = [
        # Create the model (for fresh installs)
        migrations.CreateModel(
            name='Staff',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('staff_number', models.CharField(db_index=True, max_length=50, unique=True)),
                ('first_name', models.CharField(max_length=100)),
                ('last_name', models.CharField(max_length=100)),
                ('email', models.EmailField(max_length=254)),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('job_title', models.CharField(max_length=100)),
                ('department', models.CharField(blank=True, max_length=100)),
                ('employment_status', models.CharField(choices=[('active', 'Active'), ('on_leave', 'On Leave'), ('suspended', 'Suspended'), ('terminated', 'Terminated')], db_index=True, default='active', max_length=20)),
                ('hire_date', models.DateField()),
                ('termination_date', models.DateField(blank=True, null=True)),
                ('salary', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('emergency_contact_name', models.CharField(blank=True, max_length=100)),
                ('emergency_contact_phone', models.CharField(blank=True, max_length=20)),
                ('address', models.TextField(blank=True)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='staff_members', to='companies.company')),
                ('user', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='staff', to='authentication.userprofile')),
            ],
            options={
                'db_table': 'staff',
                'ordering': ['last_name', 'first_name'],
                'indexes': [models.Index(fields=['staff_number'], name='staff_staff_n_68f2c7_idx'), models.Index(fields=['company', 'employment_status'], name='staff_company_f82024_idx'), models.Index(fields=['email'], name='staff_email_f66e96_idx')],
            },
        ),
        migrations.AddConstraint(
            model_name='staff',
            constraint=models.UniqueConstraint(fields=('staff_number',), name='unique_staff_number'),
        ),
        # Rename existing table if it exists (for migrations from employees)
        migrations.RunPython(rename_table_if_exists, migrations.RunPython.noop),
    ]
