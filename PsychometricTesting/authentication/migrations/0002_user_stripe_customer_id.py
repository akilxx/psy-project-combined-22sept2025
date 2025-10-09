from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='stripe_customer_id',
            field=models.CharField(
                blank=True,
                help_text='Stripe customer identifier used for subscription billing.',
                max_length=255,
                null=True,
                unique=True,
            ),
        ),
    ]
