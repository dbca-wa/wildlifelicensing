# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-08-15 06:41
from __future__ import unicode_literals

from django.conf import settings
import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


def update_applicant(apps, schema_editor):
    Application = apps.get_model('wl_applications', 'Application')
    for application in Application.objects.all():
        application.applicant = application.applicant_profile.user
        application.save()


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('wl_applications', '0005_assessment_date_last_reminded'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='applicant',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='applicant', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='application',
            name='applicant_profile',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='accounts.Profile'),
        ),
        migrations.AlterField(
            model_name='application',
            name='customer_status',
            field=models.CharField(choices=[('temp', 'Temporary'), ('draft', 'Draft'), ('under_review', 'Under Review'), ('id_required', 'Identification Required'), ('returns_required', 'Returns Completion Required'), ('amendment_required', 'Amendment Required'), ('id_and_amendment_required', 'Identification/Amendments Required'), ('id_and_returns_required', 'Identification/Returns Required'), ('returns_and_amendment_required', 'Returns/Amendments Required'), ('id_and_returns_and_amendment_required', 'Identification/Returns/Amendments Required'), ('approved', 'Approved'), ('declined', 'Declined')], default='temp', max_length=40, verbose_name='Customer Status'),
        ),
        migrations.AlterField(
            model_name='application',
            name='data',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='application',
            name='licence_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='wl_main.WildlifeLicenceType'),
        ),
        migrations.AlterField(
            model_name='application',
            name='processing_status',
            field=models.CharField(choices=[('temp', 'Temporary'), ('draft', 'Draft'), ('new', 'New'), ('renewal', 'Renewal'), ('ready_for_action', 'Ready for Action'), ('awaiting_applicant_response', 'Awaiting Applicant Response'), ('awaiting_assessor_response', 'Awaiting Assessor Response'), ('awaiting_responses', 'Awaiting Responses'), ('ready_for_conditions', 'Ready for Conditions'), ('ready_to_issue', 'Ready to Issue'), ('issued', 'Issued'), ('declined', 'Declined')], default='temp', max_length=30, verbose_name='Processing Status'),
        ),
        migrations.RunPython(update_applicant),
    ]
