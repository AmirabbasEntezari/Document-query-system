from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q
from django.conf import settings
from .models import Document, Tag
from .serializers import (
    DocumentSerializer,
    TagSerializer,
    DocumentSearchSerializer,
    QuestionSerializer
)
from .services import DocumentSearchService, QAService


# ایجاد instance های singleton برای سرویس‌ها
_search_service = None
_qa_service = None


def get_search_service():
    """دریافت instance سرویس جستجو (singleton)"""
    global _search_service
    if _search_service is None:
        _search_service = DocumentSearchService()
    return _search_service


def get_qa_service():
    """دریافت instance سرویس Q&A (singleton)"""
    global _qa_service
    if _qa_service is None:
        _qa_service = QAService()
    return _qa_service


class DocumentListCreateView(generics.ListCreateAPIView):
    """نمایش لیست و ایجاد سند جدید"""
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user if self.request.user.is_authenticated else None)


class DocumentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """نمایش، ویرایش و حذف یک سند"""
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer


class TagListView(generics.ListAPIView):
    """لیست تمام برچسب‌ها"""
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class DocumentSearchView(APIView):
    """جستجوی معنایی و ساده در اسناد"""
    
    def post(self, request):
        serializer = DocumentSearchSerializer(data=request.data)
        if serializer.is_valid():
            query = serializer.validated_data['query']
            limit = serializer.validated_data['limit']
            
            try:
                # استفاده از جستجوی معنایی
                search_service = get_search_service()
                documents = search_service.search_similar(query, limit=limit)
                
                doc_serializer = DocumentSerializer(documents, many=True)
                return Response({
                    'query': query,
                    'results': doc_serializer.data,
                    'count': len(documents),
                    'search_type': 'semantic' if search_service.embedding_model else 'simple'
                })
            except Exception as e:
                # Fallback به جستجوی ساده در صورت خطا
                documents = Document.objects.filter(
                    Q(title__icontains=query) | Q(content__icontains=query)
                )[:limit]
                
                doc_serializer = DocumentSerializer(documents, many=True)
                return Response({
                    'query': query,
                    'results': doc_serializer.data,
                    'count': documents.count(),
                    'search_type': 'simple',
                    'warning': f'Semantic search failed: {str(e)}'
                })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AskQuestionView(APIView):
    """پرسش و پاسخ با استفاده از LLM"""
    
    def post(self, request):
        serializer = QuestionSerializer(data=request.data)
        if serializer.is_valid():
            question = serializer.validated_data['question']
            document_ids = serializer.validated_data.get('document_ids', [])
            
            try:
                # استفاده از سرویس Q&A
                qa_service = get_qa_service()
                answer, relevant_docs = qa_service.answer_question(question, document_ids)
                
                return Response({
                    'question': question,
                    'answer': answer,
                    'relevant_documents': DocumentSerializer(relevant_docs, many=True).data,
                    'documents_count': len(relevant_docs),
                    'llm_used': qa_service.llm is not None
                })
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                print(f"Error in AskQuestionView: {error_details}")
                return Response({
                    'error': str(e),
                    'details': error_details if settings.DEBUG else None
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

