from rest_framework import serializers
from .models import Document, Tag


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']


class DocumentSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all(),
        source='tags',
        write_only=True,
        required=False
    )
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = Document
        fields = [
            'id', 'title', 'content', 'created_at', 'updated_at',
            'tags', 'tag_ids', 'created_by', 'created_by_username'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']


class DocumentSearchSerializer(serializers.Serializer):
    query = serializers.CharField(required=True, help_text='متن جستجو')
    limit = serializers.IntegerField(default=5, min_value=1, max_value=20)


class QuestionSerializer(serializers.Serializer):
    question = serializers.CharField(required=True, help_text='پرسش کاربر')
    document_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text='لیست ID اسناد برای جستجو (اختیاری)'
    )

