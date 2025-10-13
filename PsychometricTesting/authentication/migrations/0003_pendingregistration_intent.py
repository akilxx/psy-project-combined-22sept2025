from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0002_user_stripe_customer_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pendingregistration',
            name='otp_code',
            field=models.CharField(max_length=4),
        ),
        migrations.AddField(
            model_name='pendingregistration',
            name='intent',
            field=models.CharField(
                choices=[('register', 'Register'), ('login', 'Login')],
                default='register',
                help_text='Indicates whether the pending OTP is for registration or login.',
                max_length=20,
            ),
        ),
    ]
