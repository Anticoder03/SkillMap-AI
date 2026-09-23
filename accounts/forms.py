"""Forms for authentication and profile management."""
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import UserProfile


class RegistrationForm(UserCreationForm):
    """User registration with email and optional first/last name."""

    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "password1", "password2"]

    def clean_email(self) -> str:
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            "education_level",
            "degree",
            "college",
            "graduation_year",
            "experience_level",
            "bio",
            "location",
        ]
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 4}),
        }

    def clean_graduation_year(self) -> int | None:
        year = self.cleaned_data.get("graduation_year")
        if year and year < 1950:
            raise forms.ValidationError("Enter a valid graduation year.")
        if year and year > 2099:
            raise forms.ValidationError("Enter a valid graduation year.")
        return year