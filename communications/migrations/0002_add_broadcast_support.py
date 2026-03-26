# Generated migration for broadcast message support

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('communications', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='is_broadcast',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AlterField(
            model_name='message',
            name='recipient',
            field=models.ForeignKey(
                blank=True,
                db_index=True,
                null=True,
                on_delete=models.deletion.CASCADE,
                related_name='received_messages',
                to='authentication.userprofile'
            ),
        ),
        migrations.AlterField(
            model_name='message',
            name='subject',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddIndex(
            model_name='message',
            index=models.Index(fields=['is_broadcast', 'sent_at'], name='messages_is_broa_idx'),
        ),
    ]
