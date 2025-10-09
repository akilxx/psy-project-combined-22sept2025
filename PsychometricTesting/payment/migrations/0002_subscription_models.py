from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('testing', '0001_initial'),
        ('authentication', '0001_initial'),
        ('payment', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SubscriptionPlan',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=120)),
                ('slug', models.SlugField(unique=True)),
                ('description', models.TextField(blank=True)),
                ('price', models.DecimalField(decimal_places=2, max_digits=8)),
                ('currency', models.CharField(default='usd', max_length=3)),
                ('billing_interval', models.CharField(choices=[('monthly', 'Monthly')], default='monthly', help_text='Billing frequency for the plan. Only monthly is currently supported.', max_length=32)),
                ('monthly_allowance', models.PositiveIntegerField(default=0, help_text='Number of tests granted per billing cycle when not unlimited.')),
                ('unlimited_tests', models.BooleanField(default=False, help_text='When true the subscriber may take unlimited tests without consuming allowance.')),
                ('stripe_product_id', models.CharField(blank=True, max_length=255)),
                ('stripe_price_id', models.CharField(blank=True, max_length=255)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('allowed_tests', models.ManyToManyField(blank=True, help_text='Optional whitelist of tests the plan grants access to.', related_name='subscription_plans', to='testing.psychometrictest')),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='UserSubscription',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('active', 'Active'), ('incomplete', 'Incomplete'), ('incomplete_expired', 'Incomplete Expired'), ('trialing', 'Trialing'), ('past_due', 'Past Due'), ('canceled', 'Canceled'), ('unpaid', 'Unpaid')], default='incomplete', max_length=32)),
                ('stripe_subscription_id', models.CharField(blank=True, max_length=255, null=True, unique=True)),
                ('stripe_customer_id', models.CharField(blank=True, max_length=255, null=True)),
                ('current_period_start', models.DateTimeField(blank=True, null=True)),
                ('current_period_end', models.DateTimeField(blank=True, null=True)),
                ('cancel_at_period_end', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ended_at', models.DateTimeField(blank=True, null=True)),
                ('plan', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='subscriptions', to='payment.subscriptionplan')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subscriptions', to='authentication.user')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='TestAllowanceLedger',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('entry_type', models.CharField(choices=[('accrual', 'Accrual'), ('consumption', 'Consumption'), ('adjustment', 'Adjustment')], max_length=32)),
                ('quantity', models.IntegerField(help_text='Positive for accrual, negative for consumption.')),
                ('note', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('effective_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('subscription', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ledger_entries', to='payment.usersubscription')),
                ('test', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='testing.psychometrictest')),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='usersubscription',
            index=models.Index(fields=['status'], name='payment_use_status_83d88c_idx'),
        ),
        migrations.AddIndex(
            model_name='usersubscription',
            index=models.Index(fields=['user', 'is_active'], name='payment_use_user_id_b03989_idx'),
        ),
    ]
