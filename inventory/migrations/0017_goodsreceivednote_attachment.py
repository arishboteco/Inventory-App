from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0016_indent_department_fk"),
    ]

    operations = [
        migrations.AddField(
            model_name="goodsreceivednote",
            name="attachment",
            field=models.FileField(blank=True, null=True, upload_to="grn_attachments/"),
        ),
    ]
