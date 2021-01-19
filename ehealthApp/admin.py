from django.contrib import admin
import csv
import datetime
from django.http import HttpResponse
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Profile

# Now, The ADMIN WILL BE ABLE TO GET THE PATIENT DATA IN THE CSV FILE
def export_to_csv(modeladmin, request, queryset):
    opts = modeladmin.model._meta
    content_disposition = f'attachment; filename={opts.verbose_name}.csv'
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = content_disposition
    writer = csv.writer(response)

    fields = [field for field in opts.get_fields() if not field.many_to_many\
    and not field.one_to_many]
    # Write a first row with header information
    writer.writerow([field.verbose_name for field in fields])
    # Write data rows
    for obj in queryset:
        data_row = []
        for field in fields:
            value = getattr(obj, field.name)
            if isinstance(value, datetime.datetime):
                value = value.strftime('%d/%m/%Y')
            data_row.append(value)
        writer.writerow(data_row)
    return response
export_to_csv.short_description = 'Export to CSV'

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display=['user','image','Email','Malaria','Cough','Road_Injuries','Tuberculosis']
    list_filter=['Malaria','Cough','Road_Injuries','Tuberculosis']
    actions=[export_to_csv]
