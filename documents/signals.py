"""
Signal handlers برای به‌روزرسانی خودکار index
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Document
from .services import DocumentSearchService


@receiver(post_save, sender=Document)
def update_document_index(sender, instance, **kwargs):
    """به‌روزرسانی index پس از ذخیره سند"""
    try:
        # استفاده از async یا background task برای جلوگیری از کند شدن ذخیره
        # برای حال حاضر، فقط در صورت وجود index، rebuild می‌کنیم
        from .services import DocumentSearchService
        search_service = DocumentSearchService()
        # فقط rebuild می‌کنیم اگر index وجود داشته باشد
        if search_service.index is not None and search_service.embedding_model is not None:
            # برای بهینه‌تر بودن، می‌توانیم فقط سند جدید را اضافه کنیم
            # اما برای سادگی، rebuild کامل انجام می‌دهیم
            # استفاده از try-except برای جلوگیری از خطا در ذخیره
            try:
                search_service.rebuild_index()
            except Exception as rebuild_error:
                # خطا را لاگ می‌کنیم اما اجازه می‌دهیم سند ذخیره شود
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Error rebuilding index: {rebuild_error}")
    except Exception as e:
        # خطا را لاگ می‌کنیم اما اجازه می‌دهیم سند ذخیره شود
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error updating index after document save: {e}")


@receiver(post_delete, sender=Document)
def remove_document_from_index(sender, instance, **kwargs):
    """حذف سند از index پس از حذف"""
    try:
        from .services import DocumentSearchService
        search_service = DocumentSearchService()
        if search_service.index is not None and search_service.embedding_model is not None:
            try:
                search_service.rebuild_index()
            except Exception as rebuild_error:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Error rebuilding index after delete: {rebuild_error}")
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error updating index after document delete: {e}")

