

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("play", "0020_mbtiquiz_mbtiquizpersonal_mbtiquizquestion_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="resultplaysomespec",
            old_name="chatto_coundel",
            new_name="chatto_counsel",
        ),
        migrations.RenameField(
            model_name="resultplaysomespec",
            old_name="chatto_coundel_tips",
            new_name="chatto_counsel_tips",
        ),
    ]
