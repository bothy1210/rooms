"""Booking request and venue-search forms."""
from django import forms

from apps.bookings.models import Booking, Purpose


class BookingRequestForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ["room", "requester_name", "requester_dept", "purpose",
                  "date", "start_time", "end_time", "attendance", "equipment_note"]
        widgets = {
            "room": forms.Select(attrs={"class": "form-select"}),
            "requester_name": forms.TextInput(attrs={"class": "form-control"}),
            "requester_dept": forms.TextInput(attrs={"class": "form-control"}),
            "purpose": forms.Select(attrs={"class": "form-select"}),
            "date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "start_time": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "end_time": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "attendance": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "equipment_note": forms.TextInput(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("start_time"), cleaned.get("end_time")
        if start and end and start >= end:
            raise forms.ValidationError("End time must be after start time.")
        return cleaned


class VenueSearchForm(forms.Form):
    attendance = forms.IntegerField(
        min_value=1, label="Expected attendance",
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "e.g. 180"}),
    )
    purpose = forms.ChoiceField(choices=Purpose.choices, widget=forms.Select(attrs={"class": "form-select"}))
    date = forms.DateField(required=False, widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}))
    start_time = forms.TimeField(required=False, widget=forms.TimeInput(attrs={"class": "form-control", "type": "time"}))
    end_time = forms.TimeField(required=False, widget=forms.TimeInput(attrs={"class": "form-control", "type": "time"}))

    def clean(self):
        """The time window is optional, but a half or backwards one would
        silently search nothing."""
        cleaned = super().clean()
        date, start, end = cleaned.get("date"), cleaned.get("start_time"), cleaned.get("end_time")
        if start and end and start >= end:
            self.add_error("end_time", "End time must be after start time.")
        if (start or end) and not (start and end and date):
            raise forms.ValidationError("To search a time window, give the date, start and end time.")
        return cleaned
