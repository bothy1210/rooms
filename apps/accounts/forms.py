"""Authentication and user-management forms."""
from django import forms
from django.contrib.auth import authenticate, password_validation
from django.db import transaction
from django.db.models import Q

from apps.accounts.models import User
from apps.accounts.permissions import ROLE_DEPT_ADMIN
from apps.core.forms import new_code as _new_code
from apps.core.forms import typed_input as _typed
from apps.core.models import Department, Faculty


class UsernameLoginForm(forms.Form):
    """Login by username + password."""

    username = forms.CharField(
        label="Username",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Username", "autofocus": True}),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Password"}),
    )

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        username = (cleaned.get("username") or "").strip()
        password = cleaned.get("password")
        if username and password:
            self.user = authenticate(self.request, username=username, password=password)
            if self.user is None:
                raise forms.ValidationError("Invalid username or password.")
            if not self.user.is_active:
                raise forms.ValidationError("This account is disabled.")
        return cleaned

    def get_user(self):
        return self.user


class UserForm(forms.ModelForm):
    """Create/edit a user account (central-admin only).

    Department and faculty are typed, not picked. A typed name is matched to an
    existing record by name or code, ignoring case; one that does not exist yet
    is added (a new department needs its faculty, so it knows where it belongs).
    """

    department_name = forms.CharField(label="Department", max_length=150, required=False,
                                      widget=_typed("e.g. Geoinformatics", "department-options"))
    faculty_name = forms.CharField(label="Faculty", max_length=150, required=False,
                                   widget=_typed("e.g. Faculty of Science", "faculty-options"))

    class Meta:
        model = User
        fields = ["username", "full_name", "email", "role", "is_active"]
        widgets = {f: forms.Select(attrs={"class": "form-select"}) if f == "role"
                   else forms.TextInput(attrs={"class": "form-control"})
                   for f in ["username", "full_name", "email", "role"]}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial.setdefault("department_name", getattr(self.instance.department, "name", ""))
            self.initial.setdefault("faculty_name", getattr(self.instance.faculty, "name", ""))
        # Suggestions while typing; any other name is still accepted.
        self.department_options = sorted(set(Department.objects.values_list("name", flat=True)))
        self.faculty_options = list(Faculty.objects.values_list("name", flat=True))
        self._department = self._faculty = None

    def clean(self):
        cleaned = super().clean()
        dept_name = " ".join((cleaned.get("department_name") or "").split())
        fac_name = " ".join((cleaned.get("faculty_name") or "").split())

        faculty = None
        if fac_name:
            faculty = (Faculty.objects.filter(Q(name__iexact=fac_name) | Q(code__iexact=fac_name)).first()
                       or Faculty(name=fac_name))                       # added on save

        department = None
        if dept_name:
            found = Department.objects.filter(Q(name__iexact=dept_name) | Q(code__iexact=dept_name))
            if faculty is not None:
                found = found.filter(faculty=faculty) if faculty.pk else found.none()
            found = list(found.select_related("faculty")[:2])
            if len(found) > 1:
                self.add_error("faculty_name", f"More than one faculty has a department called "
                                               f"\u201c{dept_name}\u201d \u2014 type the faculty too.")
            elif found:
                department = found[0]
                faculty = faculty or department.faculty
            elif faculty is None:
                self.add_error("faculty_name", f"There is no department called \u201c{dept_name}\u201d yet. "
                                               f"Type its faculty and it will be added under it.")
            else:
                department = Department(name=dept_name, faculty=faculty)   # added on save

        self._department, self._faculty = department, faculty
        return cleaned

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        faculty, department = self._faculty, self._department
        if faculty is not None and not faculty.pk:
            faculty.code = _new_code(Faculty, faculty.name)
            faculty.save()
        if department is not None and not department.pk:
            department.faculty = faculty
            department.code = _new_code(Department, department.name, faculty=faculty)
            department.save()
        user.department, user.faculty = department, faculty
        if commit:
            user.save()
        return user


class UserCreateForm(UserForm):
    """Central admin adds a new account with an initial password."""

    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
    )

    class Meta(UserForm.Meta):
        widgets = {
            **UserForm.Meta.widgets,
            "username": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. tmoyo",
                                               "autocomplete": "off"}),
            "full_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Tendai Moyo"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "name@uz.ac.zw"}),
        }

    def clean_username(self):
        # Sign-in ignores case, so "TMoyo" may not be added beside "tmoyo".
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("A user with this username already exists.")
        return username

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "The two passwords do not match.")
        elif p1:
            try:
                password_validation.validate_password(p1, self.instance)
            except forms.ValidationError as exc:
                self.add_error("password1", exc)
        if (cleaned.get("role") == ROLE_DEPT_ADMIN and not (self._department or self._faculty)
                and "faculty_name" not in self.errors):
            self.add_error("department_name", "A departmental administrator needs a department or faculty.")
        return cleaned

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user
