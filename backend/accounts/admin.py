from django.contrib import admin

from accounts.models import ClientOrg, User

admin.site.register(ClientOrg)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["email", "full_name", "role", "client_org", "is_active"]
    list_filter = ["role"]
    exclude = ["password"]
