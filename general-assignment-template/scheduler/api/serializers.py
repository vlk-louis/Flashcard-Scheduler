from rest_framework import serializers

class ReviewInSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    card_id = serializers.UUIDField()
    rating = serializers.IntegerField(min_value=0, max_value=2)
    idempotency_key = serializers.CharField(max_length=64)

class DueQuerySerializer(serializers.Serializer):
    until = serializers.DateTimeField()  # ISO-8601