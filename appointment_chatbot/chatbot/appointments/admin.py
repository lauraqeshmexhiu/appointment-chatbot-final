from django.contrib import admin
from .models import Appointment
from .models import Doctor , DoctorAvailability


admin.site.register(Appointment)
admin.site.register(Doctor)
admin.site.register(DoctorAvailability)
# Register your models here.
