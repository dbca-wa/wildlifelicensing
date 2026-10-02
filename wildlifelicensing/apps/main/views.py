import mimetypes
import os

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import CharField, Q, Value
from django.db.models.functions import Concat
from django.http import (
    FileResponse,
    Http404,
    HttpResponse,
    HttpResponseForbidden,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic.base import TemplateView, View
from ledger_api_client.ledger_models import EmailUserRO as EmailUser

from wildlifelicensing.apps.main.file_validation import (
    is_internal_uploader,
    validate_request_files,
)
from wildlifelicensing.apps.main.forms import (
    AddressForm,
    CommunicationsLogEntryForm,
    ProfileForm,
)
from wildlifelicensing.apps.main.helpers import is_assessor, is_customer, is_officer
from wildlifelicensing.apps.main.mixins import (
    CustomerRequiredMixin,
    OfficerRequiredMixin,
)
from wildlifelicensing.apps.main.models import (
    CommunicationsLogEntry,
    Document,
    Profile,
    WildlifeLicence,
)
from wildlifelicensing.apps.main.pdf import (
    bulk_licence_renewal_pdf_bytes,
    create_licence_renewal_pdf_bytes,
)
from wildlifelicensing.apps.main.serializers import (
    CommunicationsLogEntrySerializer,
    DocumentSerializer,
    ProfileSerializer,
    WildlifeLicensingJSONEncoder,
)


class SearchCustomersView(OfficerRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        search_term = request.GET.get("q", "")

        # Allow for search of first name, last name and concatenation of both
        users = EmailUser.objects.annotate(
            search_term=Concat(
                "first_name",
                Value(" "),
                "last_name",
                Value(" "),
                "legal_first_name",
                Value(" "),
                "legal_last_name",
                Value(" "),
                "email",
                output_field=CharField(),
            )
        )

        # Filter out users with no name or legal name as otherwise
        # an invoice can be created with no name which is not a valid invoice
        users = (
            users.filter(search_term__icontains=search_term)
            .filter(
                Q(
                    first_name__isnull=False,
                    first_name__gt="",
                    last_name__isnull=False,
                    last_name__gt="",
                )
                | Q(
                    legal_first_name__isnull=False,
                    legal_first_name__gt="",
                    legal_last_name__isnull=False,
                    legal_last_name__gt="",
                )
            )
            .values(
                "id",
                "email",
                "first_name",
                "last_name",
                "legal_first_name",
                "legal_last_name",
                "dob",
            )[:10]
        )

        data_transform = []

        for person in users:
            # Format the date of birth
            if person["dob"]:
                person["dob"] = person["dob"].strftime("%d/%m/%Y")
            dob_text = ""
            if person["dob"]:
                dob_text = f", DOB: {person['dob']}"

            text = f"{person['first_name']} {person['last_name']} (email: {person['email']}{dob_text})"
            if not person["first_name"] and not person["last_name"]:
                text = f"{person['legal_first_name']} {person['legal_last_name']} (email: {person['email']}{dob_text})"
            data_transform.append(
                {
                    "id": person["id"],
                    "text": text,
                }
            )

        return JsonResponse(
            data_transform, safe=False, encoder=WildlifeLicensingJSONEncoder
        )


class ListProfilesView(CustomerRequiredMixin, TemplateView):
    template_name = "wl/list_profiles.html"
    login_url = "/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["data"] = ProfileSerializer(
            Profile.objects.filter(user=self.request.user), many=True
        ).data

        return context


class CreateProfilesView(CustomerRequiredMixin, TemplateView):
    template_name = "wl/create_profile.html"
    login_url = "/"

    def get(self, request, *args, **kwargs):
        return render(
            request,
            self.template_name,
            {
                "profile_form": ProfileForm(user=request.user),
                "address_form": AddressForm(user=request.user),
            },
        )

    def post(self, request, *args, **kwargs):
        if request.user.pk != int(request.POST["user"]):
            return HttpResponse("Unauthorized", status=401)

        profile_form = ProfileForm(request.POST)
        address_form = AddressForm(request.POST)

        if profile_form.is_valid() and address_form.is_valid():
            profile = profile_form.save(commit=False)
            profile.postal_address = address_form.save()
            profile.save()
        else:
            return render(
                request,
                self.template_name,
                {"profile_form": profile_form, "address_form": address_form},
            )

        messages.success(request, "The profile '%s' was created." % profile.name)

        return redirect("wl_main:list_profiles")


class DeleteProfileView(CustomerRequiredMixin, TemplateView):
    template_name = "wl/list_profiles.html"
    login_url = "/"

    def get(self, request, *args, **kwargs):
        profile = get_object_or_404(Profile, pk=args[0])
        profile.delete()
        messages.success(request, "The profile '%s' was deleted." % profile.name)
        return redirect("wl_main:list_profiles")


class EditProfilesView(CustomerRequiredMixin, TemplateView):
    template_name = "wl/edit_profile.html"
    login_url = "/"

    def get(self, request, *args, **kwargs):
        profile = get_object_or_404(Profile, pk=args[0])

        if profile.user != request.user:
            return HttpResponse("Unauthorized", status=401)

        return render(
            request,
            self.template_name,
            {
                "profile_form": ProfileForm(instance=profile),
                "address_form": AddressForm(instance=profile.postal_address),
            },
        )

    def post(self, request, *args, **kwargs):
        profile = get_object_or_404(Profile, pk=args[0])

        if profile.user != request.user or request.user.pk != int(request.POST["user"]):
            return HttpResponse("Unauthorized", status=401)
        profile_form = ProfileForm(request.POST, instance=profile)
        address_form = AddressForm(request.POST, instance=profile.postal_address)

        if profile_form.is_valid() and address_form.is_valid():
            profile = profile_form.save()
            profile.postal_address = address_form.save()
            profile.save()
        else:
            return render(
                request,
                self.template_name,
                {"profile_form": profile_form, "address_form": address_form},
            )

        messages.success(request, "The profile '%s' was updated." % profile.name)

        return redirect("wl_main:list_profiles")


class ListDocumentView(CustomerRequiredMixin, TemplateView):
    template_name = "wl/list_documents.html"
    login_url = "/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["data"] = DocumentSerializer(
            self.request.user.documents.all(), many=True
        ).data

        return context


class LicenceRenewalPDFView(OfficerRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        licence = get_object_or_404(WildlifeLicence, pk=self.args[0])

        filename = f"{licence.licence_number}-{licence.licence_sequence}-renewal.pdf"

        response = HttpResponse(content_type="application/pdf")

        response.write(
            create_licence_renewal_pdf_bytes(
                filename, licence, request.build_absolute_uri(reverse("home"))
            )
        )

        licence.renewal_sent = True
        licence.save()

        return response


class BulkLicenceRenewalPDFView(OfficerRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        query = request.POST.get("query")
        licences = []
        if query:
            licences = WildlifeLicence.objects.filter(query)
        response = HttpResponse(content_type="application/pdf")
        response.write(
            bulk_licence_renewal_pdf_bytes(
                licences, request.build_absolute_uri(reverse("home"))
            )
        )

        if licences:
            licences.update(renewal_sent=True)

        return response


class CommunicationsLogListView(OfficerRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        q = Q(staff=args[0]) | Q(customer=args[0])

        data = CommunicationsLogEntrySerializer(
            CommunicationsLogEntry.objects.filter(q).order_by("created"), many=True
        ).data

        return JsonResponse(
            {"data": data}, safe=False, encoder=WildlifeLicensingJSONEncoder
        )


class AddCommunicationsLogEntryView(OfficerRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            validate_request_files(request)
        except ValidationError as e:
            return JsonResponse(
                {
                    "errors": [
                        {
                            "status": "422",
                            "title": "Data not valid",
                            "detail": {"attachment": e.messages},
                        }
                    ]
                },
                status=422,
            )

        customer = get_object_or_404(EmailUser, pk=args[0])

        form = CommunicationsLogEntryForm(data=request.POST, files=request.FILES)

        if form.is_valid():
            communications_log_entry = form.save(commit=False)

            communications_log_entry.customer = customer
            communications_log_entry.staff = request.user
            communications_log_entry.save()
            if request.FILES and "attachment" in request.FILES:
                document = Document(file=request.FILES["attachment"])
                document.save(is_internal=is_internal_uploader(request))
                communications_log_entry.documents.add(document)

            return JsonResponse("ok", safe=False, encoder=WildlifeLicensingJSONEncoder)
        else:
            return JsonResponse(
                {
                    "errors": [
                        {
                            "status": "422",
                            "title": "Data not valid",
                            "detail": form.errors,
                        }
                    ]
                },
                safe=False,
                encoder=WildlifeLicensingJSONEncoder,
                status_code=422,
            )


def _resolve_under(root, relative_path):
    root = os.path.realpath(root)
    try:
        candidate = os.path.realpath(os.path.join(root, relative_path))
        if os.path.commonpath([root, candidate]) != root:
            return None
    except ValueError:
        return None
    return candidate if os.path.isfile(candidate) else None


def _user_owns_document(user, relative_path):
    return (
        Document.objects.filter(file=relative_path)
        .filter(
            Q(application__applicant=user)
            | Q(application__proxy_applicant=user)
            | Q(hard_copy__applicant=user)
            | Q(hard_copy__proxy_applicant=user)
            | Q(licence_document__holder=user)
            | Q(cover_letter_document__holder=user)
            | Q(communicationslogentry__customer=user)
        )
        .exists()
    )


def getPrivateFile(request):
    # 1. Authentication check
    if not request.user.is_authenticated:
        return HttpResponseForbidden()

    # 2. Extract the relative path from the leading URL prefix
    path = request.path
    relative_path = None
    for prefix in [settings.PRIVATE_MEDIA_URL, settings.MEDIA_URL]:
        if path.startswith(prefix):
            relative_path = path[len(prefix) :].lstrip("/")
            break

    if not relative_path:
        raise Http404()

    # 3. Resolve the file: PRIVATE_MEDIA_ROOT first, legacy MEDIA_ROOT as fallback
    full_path = _resolve_under(settings.PRIVATE_MEDIA_ROOT, relative_path) or (
        _resolve_under(settings.MEDIA_ROOT, relative_path)
    )
    if not full_path:
        raise Http404()

    # 4. Authorization check
    user = request.user
    if is_officer(user) or is_assessor(user) or user.is_staff or user.is_superuser:
        pass
    elif is_customer(user):
        if not _user_owns_document(user, relative_path):
            return HttpResponseForbidden()
    else:
        return HttpResponseForbidden()

    # 5. Serve the file
    extension = relative_path.split(".")[-1].lower() if "." in relative_path else ""
    if extension in ["msg", "eml"]:
        content_type = "application/vnd.ms-outlook"
    else:
        content_type = (
            mimetypes.guess_type(full_path)[0] or "application/octet-stream"
        )

    original_filename = (
        Document.objects.filter(file=relative_path)
        .values_list("original_filename", flat=True)
        .first()
    )
    response = FileResponse(
        open(full_path, "rb"),
        content_type=content_type,
        filename=original_filename or None,
    )
    response["X-Content-Type-Options"] = "nosniff"
    return response


def getLedgerIdentificationFile(request, emailuser_id):
    allow_access = False
    # Add permission rules
    # allow_access = True
    ####
    try:
        user = EmailUser.objects.get(id=emailuser_id)
    except EmailUser.DoesNotExist:
        messages.error(request, "Unable to find the document")
    try:
        if (
            request.user == user
            or request.user.is_staff is True
            or request.user.is_superuser is True
        ):
            allow_access = True
        user_id = user.identification2
        id_path = user_id.upload.path

        extension = ""

        if id_path[-5:-4] == ".":
            extension = id_path[-4:]
        if id_path[-4:-3] == ".":
            extension = id_path[-3:]

        # if request.user.is_superuser:
        if allow_access is True:
            full_file_path = id_path
            if os.path.isfile(full_file_path) is True:
                # extension = file_name_path[-3:]
                the_file = open(full_file_path, "rb")
                the_data = the_file.read()
                the_file.close()
                if extension == "msg":
                    return HttpResponse(
                        the_data, content_type="application/vnd.ms-outlook"
                    )
                if extension == "eml":
                    return HttpResponse(
                        the_data, content_type="application/vnd.ms-outlook"
                    )
                return HttpResponse(
                    the_data, content_type=mimetypes.types_map["." + str(extension)]
                )
        else:
            messages.error(request, "Unable to find the document")
            return redirect("wl_home")
    except Exception as e:
        messages.error(request, "Unable to find the document: " + str(e))
        return redirect("wl_home")


def getLedgerSeniorCardFile(request, emailuser_id):
    allow_access = False
    # Add permission rules
    # allow_access = True
    ####
    try:
        user = EmailUser.objects.get(id=emailuser_id)
    except EmailUser.DoesNotExist:
        messages.error(request, "Unable to find the document")
    try:
        if (
            request.user == user
            or request.user.is_staff is True
            or request.user.is_superuser is True
        ):
            allow_access = True
        user_senior_card = user.senior_card2
        senior_card_path = user_senior_card.upload.path

        extension = ""

        if senior_card_path[-5:-4] == ".":
            extension = senior_card_path[-4:]
        if senior_card_path[-4:-3] == ".":
            extension = senior_card_path[-3:]

        if allow_access is True:
            full_file_path = senior_card_path
            if os.path.isfile(full_file_path) is True:
                # extension = file_name_path[-3:]
                the_file = open(full_file_path, "rb")
                the_data = the_file.read()
                the_file.close()
                if extension == "msg":
                    return HttpResponse(
                        the_data, content_type="application/vnd.ms-outlook"
                    )
                if extension == "eml":
                    return HttpResponse(
                        the_data, content_type="application/vnd.ms-outlook"
                    )

                return HttpResponse(
                    the_data, content_type=mimetypes.types_map["." + str(extension)]
                )
        else:
            messages.error(request, "Unable to find the document")
            return redirect("wl_home")
    except Exception as e:
        messages.error(request, "Unable to find the document: " + str(e))
        return redirect("wl_home")
