from django.contrib import admin
from .models import Requirements, Bid

class BidInline(admin.TabularInline):
    model = Bid
    extra = 0
    ordering = ('-id',)
    max_num = 5  # Limit to 5 latest shown

    fields = ('user', 'rate')
    readonly_fields = ('user', 'rate')


@admin.register(Requirements)
class RequirementsAdmin(admin.ModelAdmin):
    list_display = ('id', 'loading_point', 'unloading_point', 'truck_type', 'qty', 'product')
    inlines = [BidInline]



@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'req', 'rate', 'get_loading_point', 'get_unloading_point')
    search_fields = ('user__username', 'req__loading_point', 'req__unloading_point')
    list_filter = ('rate', 'req__truck_type')
    ordering = ('id',)
    list_display_links =('rate',)

    def get_loading_point(self, obj):
        return obj.req.loading_point
    get_loading_point.short_description = 'Loading Point'

    def get_unloading_point(self, obj):
        return obj.req.unloading_point
    get_unloading_point.short_description = 'Unloading Point'
