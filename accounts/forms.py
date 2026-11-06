from django import forms
from django.contrib.auth import get_user_model
from .models import UserProfile
User = get_user_model()

class EmailLoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "you@gmail.com", "autocomplete": "email"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "current-password"}))

class AdminCreateUserForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "form-control"}))
    first_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    phone = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    role = forms.ChoiceField(choices=UserProfile.Role.choices, widget=forms.Select(attrs={"class": "form-select"}))
    password1 = forms.CharField(min_length=8, label="Temporary Gromaster password", widget=forms.PasswordInput(attrs={"class": "form-control"}))
    password2 = forms.CharField(min_length=8, label="Confirm password", widget=forms.PasswordInput(attrs={"class": "form-control"}))

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        data = super().clean()
        if data.get("password1") and data.get("password2") and data["password1"] != data["password2"]:
            self.add_error("password2", "Passwords do not match.")
        return data
