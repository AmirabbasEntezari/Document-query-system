from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Tag(models.Model):
    """مدل برای برچسب‌های اسناد"""
    name = models.CharField(max_length=100, unique=True, verbose_name='نام برچسب')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')

    class Meta:
        verbose_name = 'برچسب'
        verbose_name_plural = 'برچسب‌ها'
        ordering = ['name']

    def __str__(self):
        return self.name


class Document(models.Model):
    """مدل برای اسناد متنی"""
    title = models.CharField(max_length=255, verbose_name='عنوان')
    content = models.TextField(verbose_name='متن کامل')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')
    tags = models.ManyToManyField(Tag, blank=True, verbose_name='برچسب‌ها')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='ایجاد کننده'
    )
    
    # برای ذخیره embedding در آینده
    embedding = models.TextField(blank=True, null=True, verbose_name='Embedding')

    class Meta:
        verbose_name = 'سند'
        verbose_name_plural = 'اسناد'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

