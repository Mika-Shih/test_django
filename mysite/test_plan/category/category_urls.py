from django.urls import path
from . import category_views

urlpatterns = [
    path('get_categories/', category_views.get_categories),
    path('update_item_category/', category_views.update_item_category),
    path('delete_item_category/', category_views.delete_item_category),   
    path('update_plan_category/', category_views.update_plan_category),
    path('delete_plan_category/', category_views.delete_plan_category),
]
