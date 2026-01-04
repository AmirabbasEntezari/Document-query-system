"""
سرویس‌های اصلی برای جستجو و پرسش و پاسخ
"""
from typing import List, Tuple, Optional
from django.conf import settings
from django.db.models import Q
from .models import Document
import os
import json
import pickle


class DocumentSearchService:
    """سرویس جستجوی معنایی در اسناد"""
    
    def __init__(self):
        self.embedding_model = None
        self.index = None
        self.document_ids = []  # نگهداری mapping بین index و document IDs
        self.index_path = 'documents_index.faiss'
        self.mapping_path = 'documents_mapping.pkl'
        self._initialize_embeddings()
        self._load_or_rebuild_index()
    
    def _initialize_embeddings(self):
        """راه‌اندازی مدل embedding"""
        try:
            from sentence_transformers import SentenceTransformer
            
            # بارگذاری مدل embedding
            model_name = settings.EMBEDDING_MODEL
            print(f"Loading embedding model: {model_name}")
            self.embedding_model = SentenceTransformer(model_name)
            print("Embedding model loaded successfully")
        except ImportError:
            print("Warning: sentence-transformers not installed. Semantic search will be disabled.")
            self.embedding_model = None
        except Exception as e:
            print(f"Warning: Could not load embedding model: {e}")
            self.embedding_model = None
    
    def _load_or_rebuild_index(self):
        """بارگذاری یا ساخت مجدد index"""
        try:
            import faiss
            import numpy as np
            
            if not self.embedding_model:
                return
            
            # بارگذاری index و mapping اگر وجود داشته باشد
            if os.path.exists(self.index_path) and os.path.exists(self.mapping_path):
                try:
                    self.index = faiss.read_index(self.index_path)
                    with open(self.mapping_path, 'rb') as f:
                        self.document_ids = pickle.load(f)
                    print(f"Loaded index with {len(self.document_ids)} documents")
                    return
                except Exception as e:
                    print(f"Error loading index: {e}. Rebuilding...")
            
            # ساخت index جدید
            dimension = self.embedding_model.get_sentence_embedding_dimension()
            self.index = faiss.IndexFlatL2(dimension)
            self.document_ids = []
            print("Created new FAISS index")
            
            # ساخت index برای تمام اسناد موجود
            self.rebuild_index()
            
        except ImportError:
            print("Warning: faiss not installed. Semantic search will be disabled.")
            self.index = None
        except Exception as e:
            print(f"Warning: Could not initialize FAISS index: {e}")
            self.index = None
    
    def rebuild_index(self):
        """ساخت مجدد index برای تمام اسناد"""
        if not self.embedding_model or not self.index:
            return
        
        try:
            import faiss
            import numpy as np
            
            documents = Document.objects.all()
            if not documents.exists():
                return
            
            print(f"Rebuilding index for {documents.count()} documents...")
            
            # پاک کردن index قبلی
            dimension = self.embedding_model.get_sentence_embedding_dimension()
            self.index = faiss.IndexFlatL2(dimension)
            self.document_ids = []
            
            # ایجاد embeddings برای تمام اسناد
            texts = []
            doc_ids = []
            
            for doc in documents:
                # ترکیب عنوان و محتوا برای embedding
                text = f"{doc.title}\n{doc.content}"
                texts.append(text)
                doc_ids.append(doc.id)
            
            if texts:
                # ایجاد embeddings
                embeddings = self.embedding_model.encode(texts, show_progress_bar=True)
                embeddings = np.array(embeddings).astype('float32')
                
                # اضافه کردن به index
                self.index.add(embeddings)
                self.document_ids = doc_ids
                
                # ذخیره index و mapping
                self._save_index()
                print(f"Index rebuilt successfully with {len(self.document_ids)} documents")
        
        except Exception as e:
            print(f"Error rebuilding index: {e}")
    
    def _save_index(self):
        """ذخیره index و mapping"""
        try:
            import faiss
            
            if self.index and self.document_ids:
                faiss.write_index(self.index, self.index_path)
                with open(self.mapping_path, 'wb') as f:
                    pickle.dump(self.document_ids, f)
        except Exception as e:
            print(f"Error saving index: {e}")
    
    def search_similar(self, query: str, limit: int = 5) -> List[Document]:
        """جستجوی اسناد مشابه با استفاده از embedding"""
        if not self.embedding_model or not self.index:
            # Fallback به جستجوی ساده
            return list(Document.objects.filter(
                Q(title__icontains=query) | Q(content__icontains=query)
            )[:limit])
        
        try:
            import numpy as np
            
            # ایجاد embedding برای query
            query_embedding = self.embedding_model.encode([query])
            query_embedding = np.array(query_embedding).astype('float32')
            
            # جستجو در index
            k = min(limit, len(self.document_ids))
            if k == 0:
                return []
            
            distances, indices = self.index.search(query_embedding, k)
            
            # تبدیل indices به document IDs
            found_doc_ids = [self.document_ids[idx] for idx in indices[0] if idx < len(self.document_ids)]
            
            # دریافت اسناد از دیتابیس
            documents = Document.objects.filter(id__in=found_doc_ids)
            
            # مرتب‌سازی بر اساس ترتیب یافت شده
            doc_dict = {doc.id: doc for doc in documents}
            ordered_docs = [doc_dict[doc_id] for doc_id in found_doc_ids if doc_id in doc_dict]
            
            return ordered_docs
        
        except Exception as e:
            print(f"Error in semantic search: {e}")
            # Fallback به جستجوی ساده
            return list(Document.objects.filter(
                Q(title__icontains=query) | Q(content__icontains=query)
            )[:limit])


class QAService:
    """سرویس پرسش و پاسخ با استفاده از LangChain و LLM"""
    
    def __init__(self):
        self.llm = None
        self.search_service = DocumentSearchService()
        self._initialize_llm()
    
    def _initialize_llm(self):
        """راه‌اندازی مدل زبانی"""
        try:
            # تلاش برای استفاده از Ollama (رایگان و محلی)
            try:
                from langchain_community.llms import Ollama
                self.llm = Ollama(model="llama2")
                print("Using Ollama LLM")
                return
            except Exception as e:
                print(f"Ollama not available: {e}")
            
            # تلاش برای استفاده از HuggingFace (رایگان)
            try:
                from langchain_community.llms import HuggingFacePipeline
                from transformers import pipeline
                
                # استفاده از یک مدل کوچک و رایگان
                pipe = pipeline(
                    "text-generation",
                    model="gpt2",  # مدل رایگان و کوچک
                    max_length=500,
                    temperature=0.7
                )
                self.llm = HuggingFacePipeline(pipeline=pipe)
                print("Using HuggingFace LLM")
                return
            except Exception as e:
                print(f"HuggingFace not available: {e}")
            
            # اگر هیچ LLM در دسترس نبود
            self.llm = None
            print("Warning: No LLM available. QA will use simple text matching.")
            
        except ImportError:
            print("Warning: LangChain not properly installed. QA will use simple text matching.")
            self.llm = None
        except Exception as e:
            print(f"Warning: Could not initialize LLM: {e}")
            self.llm = None
    
    def answer_question(self, question: str, document_ids: List[int] = None) -> Tuple[str, List[Document]]:
        """
        پاسخ به پرسش کاربر بر اساس اسناد
        
        Args:
            question: پرسش کاربر
            document_ids: لیست ID اسناد برای جستجو (اختیاری)
        
        Returns:
            Tuple شامل پاسخ و لیست اسناد مرتبط
        """
        # جستجوی اسناد مرتبط
        if document_ids:
            relevant_docs = Document.objects.filter(id__in=document_ids)
            # تبدیل QuerySet به list برای یکنواختی
            relevant_docs_list = list(relevant_docs)
        else:
            relevant_docs_list = self.search_service.search_similar(question, limit=5)
        
        if not relevant_docs_list:
            return "متأسفانه هیچ سند مرتبطی پیدا نشد.", []
        
        # آماده‌سازی context از اسناد (استفاده از محتوای کامل)
        context_parts = []
        for doc in relevant_docs_list:
            # استفاده از محتوای کامل یا حداقل 1000 کاراکتر
            content = doc.content[:2000] if len(doc.content) > 2000 else doc.content
            context_parts.append(f"=== سند: {doc.title} ===\n{content}")
        
        context = "\n\n".join(context_parts)
        
        if self.llm:
            # استفاده از LLM برای تولید پاسخ
            prompt = f"""شما یک دستیار هوشمند هستید که بر اساس اسناد ارائه شده به پرسش‌های کاربران پاسخ می‌دهید.

اسناد مرتبط:
{context}

پرسش کاربر: {question}

لطفاً بر اساس اطلاعات موجود در اسناد بالا، به پرسش کاربر پاسخ دقیق و مفصل دهید. اگر پاسخ در اسناد موجود نیست، صادقانه بگویید که اطلاعات کافی در دسترس نیست.

پاسخ:"""
            
            try:
                # استفاده از LangChain برای تولید پاسخ
                if hasattr(self.llm, '__call__'):
                    answer = self.llm(prompt)
                else:
                    # برای مدل‌های مختلف
                    answer = self.llm.invoke(prompt) if hasattr(self.llm, 'invoke') else str(self.llm(prompt))
                
                # پاکسازی پاسخ
                answer = answer.strip()
                if not answer:
                    raise ValueError("Empty response from LLM")
                
                return answer, relevant_docs_list
            except Exception as e:
                print(f"Error generating answer with LLM: {e}")
                # Fallback به پاسخ ساده
                answer = self._simple_answer(question, relevant_docs_list)
                return answer, relevant_docs_list
        else:
            # پاسخ ساده بدون LLM
            answer = self._simple_answer(question, relevant_docs_list)
            return answer, relevant_docs_list
    
    def _simple_answer(self, question: str, documents: List[Document]) -> str:
        """پاسخ ساده بدون استفاده از LLM"""
        if not documents:
            return "متأسفانه هیچ سند مرتبطی با پرسش شما پیدا نشد. لطفاً پرسش خود را تغییر دهید یا از کلمات کلیدی دیگری استفاده کنید."
        
        # ساخت پاسخ بر اساس محتوای اسناد
        answer_parts = [f"بر اساس جستجو، {len(documents)} سند مرتبط پیدا شد:\n"]
        
        for i, doc in enumerate(documents[:3], 1):  # فقط 3 سند اول
            # استخراج جملات مرتبط از محتوا
            content_preview = doc.content[:300] + "..." if len(doc.content) > 300 else doc.content
            answer_parts.append(f"{i}. {doc.title}:\n{content_preview}\n")
        
        if len(documents) > 3:
            answer_parts.append(f"\nو {len(documents) - 3} سند مرتبط دیگر نیز پیدا شد.")
        
        answer_parts.append("\nبرای اطلاعات بیشتر، لطفاً به اسناد کامل مراجعه کنید.")
        
        return "\n".join(answer_parts)

