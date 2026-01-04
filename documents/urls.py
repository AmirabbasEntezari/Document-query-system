from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    path('documents/', views.DocumentListCreateView.as_view(), name='document-list'),
    path('documents/<int:pk>/', views.DocumentDetailView.as_view(), name='document-detail'),
    path('documents/search/', views.DocumentSearchView.as_view(), name='document-search'),
    path('documents/ask/', views.AskQuestionView.as_view(), name='ask-question'),
    path('tags/', views.TagListView.as_view(), name='tag-list'),
]

