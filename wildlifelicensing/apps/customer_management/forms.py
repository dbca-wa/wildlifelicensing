from django import forms


class CustomerSearchForm(forms.Form):
    search = forms.CharField()
