# payment/forms.py


from django import forms
from .models import Payment

class PaymentReadOnlyForm(forms.ModelForm):
    """
    A read-only ModelForm for Payment objects.
    The fields are displayed but cannot be changed.
    """

    class Meta:
        model = Payment
        fields = '__all__'  # or list them explicitly if needed
        # Provide basic widgets or override them to look read-only
        widgets = {
            'user': forms.TextInput(attrs={'readonly': 'readonly'}),
            'test': forms.TextInput(attrs={'readonly': 'readonly'}),
            'test_result': forms.TextInput(attrs={'readonly': 'readonly'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Alternatively, disable fields so they can't be edited
        readonly_field_names = ['user', 'test', 'test_result',
                                'amount', 'currency',
                                'stripe_payment_intent_id', 'payment_method',
                                'status', 'refund_status', 'refund_id',
                                'refund_reason', 'error_details', 'refund_error_details',
                                'created_at']

        for field_name in readonly_field_names:
            if field_name in self.fields:
                # Disable the form widget entirely
                self.fields[field_name].disabled = True
                # Optionally add a 'readonly' attribute for good measure
                self.fields[field_name].widget.attrs['readonly'] = True