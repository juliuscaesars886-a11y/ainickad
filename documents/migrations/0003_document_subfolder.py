# Generated migration for adding subfolder field to Document model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0002_template'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='subfolder',
            field=models.CharField(
                choices=[
                    ('engagement', 'Engagement & Onboarding'),
                    ('incorporation', 'Incorporation & Formation'),
                    ('annual-returns', 'Annual Returns'),
                    ('statutory-returns', 'Other Statutory Returns'),
                    ('board-meetings', 'Board Meetings'),
                    ('shareholder-meetings', 'Shareholder Meetings'),
                    ('corporate-governance', 'Corporate Governance'),
                    ('fee-notes', 'Fee Notes'),
                    ('correspondence', 'Correspondence'),
                    ('sealed', 'Sealed Documents'),
                    ('register', 'Register'),
                    ('resolutions', 'Resolutions'),
                    ('other', 'Other'),
                ],
                db_index=True,
                default='other',
                help_text='Subfolder within company for document organization',
                max_length=50,
            ),
        ),
        migrations.AddIndex(
            model_name='document',
            index=models.Index(fields=['company', 'category', 'subfolder'], name='documents_company_cat_subfolder_idx'),
        ),
        migrations.AddIndex(
            model_name='document',
            index=models.Index(fields=['company', 'subfolder'], name='documents_company_subfolder_idx'),
        ),
    ]
