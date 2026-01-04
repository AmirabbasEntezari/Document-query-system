"""
Management command برای ساخت مجدد index جستجوی معنایی
"""
from django.core.management.base import BaseCommand
from documents.services import DocumentSearchService


class Command(BaseCommand):
    help = 'ساخت مجدد index جستجوی معنایی برای تمام اسناد'

    def handle(self, *args, **options):
        self.stdout.write('شروع ساخت مجدد index...')
        
        try:
            search_service = DocumentSearchService()
            search_service.rebuild_index()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Index با موفقیت ساخته شد. {len(search_service.document_ids)} سند index شدند.'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ خطا در ساخت index: {e}')
            )

