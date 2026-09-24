"""Sign in with a username instead of an R-number.

A rename, not a new column: existing accounts keep the identifier they had
(their R-number becomes their username) and their passwords.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(model_name="user", old_name="r_number", new_name="username"),
        migrations.AlterField(
            model_name="user",
            name="username",
            field=models.CharField(
                help_text="The name this person signs in with, e.g. tmoyo. Matched without regard to case.",
                max_length=150, unique=True, verbose_name="Username",
            ),
        ),
        migrations.AlterModelOptions(name="user", options={"ordering": ["username"]}),
    ]
