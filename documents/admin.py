from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.contrib.admin.views.decorators import staff_member_required
from .models import Document, Tag
from .views import get_qa_service


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']
    list_filter = ['created_at']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'created_at', 'updated_at', 'created_by']
    search_fields = ['title', 'content']
    list_filter = ['created_at', 'tags']
    filter_horizontal = ['tags']
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    
    change_list_template = 'admin/documents/document_change_list.html'
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('title', 'content')
        }),
        ('برچسب‌ها', {
            'fields': ('tags',)
        }),
        ('اطلاعات زمانی', {
            'fields': ('created_at', 'updated_at', 'created_by')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """تنظیم خودکار created_by هنگام ایجاد سند جدید"""
        if not change:  # اگر سند جدید است
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_urls(self):
        """افزودن URL های سفارشی به admin"""
        urls = super().get_urls()
        custom_urls = [
            path('ask-question/', self.admin_site.admin_view(self.ask_question_view), name='documents_document_ask_question'),
        ]
        return custom_urls + urls
    
    @method_decorator(staff_member_required)
    def ask_question_view(self, request):
        """نمایش صفحه پرسش و پاسخ در ادمین"""
        context = {
            'title': 'پرسش از اسناد',
            'opts': self.model._meta,
            'has_view_permission': True,
            'site_header': admin.site.site_header,
            'site_title': admin.site.site_title,
        }
        
        if request.method == 'POST':
            question = request.POST.get('question', '').strip()
            document_ids = request.POST.getlist('document_ids')
            
            if question:
                try:
                    qa_service = get_qa_service()
                    doc_ids = [int(id) for id in document_ids] if document_ids else None
                    answer, relevant_docs = qa_service.answer_question(question, doc_ids)
                    
                    context.update({
                        'question': question,
                        'answer': answer,
                        'relevant_docs': relevant_docs,
                        'llm_used': qa_service.llm is not None,
                        'success': True
                    })
                except Exception as e:
                    context.update({
                        'error': str(e),
                        'question': question
                    })
            else:
                context['error'] = 'لطفاً پرسش خود را وارد کنید.'
        
        # لیست تمام اسناد برای انتخاب
        context['all_documents'] = Document.objects.all()[:50]  # محدود به 50 سند
        
        return render(request, 'admin/documents/ask_question.html', context)

