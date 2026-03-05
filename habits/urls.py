from django.urls import path
from .views import (
    HabitListCreateView, HabitRetrieveUpdateDestroyView,
    HabitTrackingListCreateView, DeleteAccountView,
    DeleteAllDataView, HabitProgressView, HabitSearchView,
    HabitStatsView, HabitListView, CategoryListView,
    HabitCompletionStatsView, HabitConsistencyStatsView
)


urlpatterns = [
    path("list/", HabitListView.as_view(), name="habit-list"),
    path('habits/', HabitListCreateView.as_view(), name='habit-list-create'),
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path('habits/<int:pk>/', HabitRetrieveUpdateDestroyView.as_view(), name='habit-retrieve-update-destroy'),
    path('habits/trackings/', HabitTrackingListCreateView.as_view(), name='habit-tracking-list-create'),
    path("habit-progress/", HabitProgressView.as_view(), name="habit-progress"),
    path("delete-account/", DeleteAccountView.as_view(), name="delete-account"),
    path("delete-all-data/", DeleteAllDataView.as_view(), name="delete-all-data"),
    path("search-habits/", HabitSearchView.as_view(), name="search-habits"),
    path("stats/<int:habit_id>/", HabitStatsView.as_view(), name="habit-stats"),
    path("stats/", HabitCompletionStatsView.as_view(), name="habit-stats"),
    path("consistency-stats/", HabitConsistencyStatsView.as_view(), name="habit-consistency-stats"),
]