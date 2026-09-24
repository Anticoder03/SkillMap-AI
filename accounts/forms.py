"""Forms for authentication and profile management."""
from django import forms
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm
from django.contrib.auth.models import User

from .models import UserProfile


class StyledFormMixin:
    """Apply the app's ``input-field`` look (class + hints) to every widget.

    Any subclass form gets consistent styling without repeating the loop.
    Override :attr:`placeholders` / :attr:`autocompletes` to set hints.
    """

    placeholders: dict[str, str] = {}
    autocompletes: dict[str, str] = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.setdefault("class", "input-field")
            if placeholder := self.placeholders.get(name):
                field.widget.attrs.setdefault("placeholder", placeholder)
            if autocomplete := self.autocompletes.get(name):
                field.widget.attrs.setdefault("autocomplete", autocomplete)


class RegistrationForm(StyledFormMixin, UserCreationForm):
    """User registration with email and optional first/last name."""

    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "password1", "password2"]

    placeholders = {
        "username": "yourusername",
        "email": "you@example.com",
        "first_name": "Ada",
        "last_name": "Lovelace",
        "password1": "••••••••",
        "password2": "••••••••",
    }

    autocompletes = {
        "username": "username",
        "email": "email",
        "first_name": "given-name",
        "last_name": "family-name",
        "password1": "new-password",
        "password2": "new-password",
    }

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


class UserForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]

    placeholders = {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email": "you@example.com",
    }

    autocompletes = {
        "first_name": "given-name",
        "last_name": "family-name",
        "email": "email",
    }


class UserProfileForm(StyledFormMixin, forms.ModelForm):
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

    placeholders = {
        "degree": "e.g. B.Tech in Computer Science",
        "college": "e.g. Delhi Technological University",
        "location": "e.g. New Delhi, India",
        "bio": "A short paragraph about what drives you…",
    }

    def clean_graduation_year(self) -> int | None:
        year = self.cleaned_data.get("graduation_year")
        if year and year < 1950:
            raise forms.ValidationError("Enter a valid graduation year.")
        if year and year > 2099:
            raise forms.ValidationError("Enter a valid graduation year.")
        return year


class StyledPasswordChangeForm(StyledFormMixin, PasswordChangeForm):
    placeholders = {
        "old_password": "Current password",
        "new_password1": "New password",
        "new_password2": "Repeat new password",
    }

    autocompletes = {
        "old_password": "current-password",
        "new_password1": "new-password",
        "new_password2": "new-password",
    }