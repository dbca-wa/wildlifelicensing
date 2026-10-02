from django import forms

from wildlifelicensing.apps.main.file_validation import validate_uploaded_file
from wildlifelicensing.apps.main.forms import CommunicationsLogEntryForm
from wildlifelicensing.apps.returns.models import ReturnAmendmentRequest, ReturnLogEntry


class NilReturnForm(forms.Form):
    comments = forms.CharField(
        label="Nil Return Comments",
        help_text="Please provide the reasons why you're not providing return data. ",
        widget=forms.Textarea(attrs={"cols": 40, "rows": 2}),
    )


class UploadSpreadsheetForm(forms.Form):
    spreadsheet_file = forms.FileField(
        label="Upload Excel Spreadsheet",
        help_text="Upload Excel spreadsheet of returns in xlsx format",
    )

    def __init__(self, *args, is_internal: bool = False, **kwargs):
        self.is_internal = is_internal
        super().__init__(*args, **kwargs)

    def clean_spreadsheet_file(self):
        spreadsheet = self.cleaned_data["spreadsheet_file"]
        validate_uploaded_file(spreadsheet, is_internal=self.is_internal)
        return spreadsheet


class ReturnsLogEntryForm(CommunicationsLogEntryForm):
    class Meta:
        model = ReturnLogEntry
        fields = ["to", "fromm", "type", "subject", "text", "attachment"]


class ReturnAmendmentRequestForm(forms.ModelForm):
    class Meta:
        model = ReturnAmendmentRequest
        fields = ["ret", "officer", "reason"]
        widgets = {"ret": forms.HiddenInput(), "officer": forms.HiddenInput()}

    def __init__(self, *args, **kwargs):
        ret = kwargs.pop("ret", None)
        officer = kwargs.pop("officer", None)

        super().__init__(*args, **kwargs)

        if ret is not None:
            self.fields["ret"].initial = ret

        if officer is not None:
            self.fields["officer"].initial = officer
