from django.contrib import admin
from .models import Category, Product, Order, AdminSetting


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'category', 'image')
    list_filter = ('category',)  # Allows filtering products by category


@admin.register(AdminSetting)
class AdminSettingAdmin(admin.ModelAdmin):
    # Define the maximum allowed instances as a class variable for easy modification
    MAX_INSTANCES = 1

    def has_add_permission(self, request):
        """
        Only allow adding new instances if current count is less than MAX_INSTANCES
        """
        current_count = self.model.objects.count()
        if current_count >= self.MAX_INSTANCES:
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        """
        Optional: Prevent deletion if you want to maintain at least one instance
        """
        return True  # or False if you want to prevent deletion
