# Generated manually to handle JSONB to TEXT[] conversion
from django.db import migrations, models
import django.contrib.postgres.fields


def convert_skills_to_array(apps, schema_editor):
    """Convert skills from JSONB to TEXT[] format"""
    from django.db import connection
    
    with connection.cursor() as cursor:
        # Add a temporary column
        cursor.execute('ALTER TABLE user_settings ADD COLUMN skills_temp TEXT[]')
        
        # Convert JSONB data to TEXT array
        # Handle both array format and non-array format
        cursor.execute("""
            UPDATE user_settings 
            SET skills_temp = CASE 
                WHEN jsonb_typeof(skills) = 'array' THEN 
                    ARRAY(SELECT jsonb_array_elements_text(skills))
                ELSE 
                    ARRAY[skills::text]
            END
        """)
        
        # Drop the old column
        cursor.execute('ALTER TABLE user_settings DROP COLUMN skills')
        
        # Rename the temp column
        cursor.execute('ALTER TABLE user_settings RENAME COLUMN skills_temp TO skills')
        
        # Set NOT NULL constraint
        cursor.execute('ALTER TABLE user_settings ALTER COLUMN skills SET NOT NULL')


def reverse_convert_skills_to_jsonb(apps, schema_editor):
    """Reverse: Convert skills from TEXT[] back to JSONB"""
    from django.db import connection
    
    with connection.cursor() as cursor:
        # Add a temporary column
        cursor.execute('ALTER TABLE user_settings ADD COLUMN skills_temp JSONB')
        
        # Convert TEXT array to JSONB
        cursor.execute("""
            UPDATE user_settings 
            SET skills_temp = to_jsonb(skills)
        """)
        
        # Drop the old column
        cursor.execute('ALTER TABLE user_settings DROP COLUMN skills')
        
        # Rename the temp column
        cursor.execute('ALTER TABLE user_settings RENAME COLUMN skills_temp TO skills')
        
        # Set NOT NULL constraint
        cursor.execute('ALTER TABLE user_settings ALTER COLUMN skills SET NOT NULL')


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0002_usersettings"),
    ]

    operations = [
        # First convert the data
        migrations.RunPython(
            convert_skills_to_array,
            reverse_convert_skills_to_jsonb
        ),
        
        # Then update the enum choices for other fields
        migrations.AlterField(
            model_name="usersettings",
            name="preferred_pace",
            field=models.CharField(
                choices=[
                    ("Very Detailed", "非常详细"),
                    ("Detailed", "详细"),
                    ("Moderate", "适中"),
                    ("Fast", "快速"),
                    ("Ultra Fast", "超快"),
                ],
                default="Moderate",
                max_length=20,
                verbose_name="偏好学习节奏",
            ),
        ),
        migrations.AlterField(
            model_name="usersettings",
            name="preferred_style",
            field=models.CharField(
                choices=[
                    ("Visual", "视觉型"),
                    ("Text", "文本型"),
                    ("Practical", "实践型"),
                ],
                default="Practical",
                max_length=20,
                verbose_name="偏好学习风格",
            ),
        ),
    ]
