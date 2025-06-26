# Generated manually to add user foreign key to StudySession

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('learning_plans', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='studysession',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='study_sessions',
                to=settings.AUTH_USER_MODEL,
                verbose_name='用户'
            ),
        ),
        migrations.AlterModelOptions(
            name='studysession',
            options={
                'verbose_name': '学习会话',
                'verbose_name_plural': '学习会话'
            },
        ),
        migrations.AlterField(
            model_name='studysession',
            name='session_id',
            field=models.UUIDField(
                primary_key=True,
                default=None,
                editable=False,
                verbose_name='会话ID'
            ),
        ),
    ]
