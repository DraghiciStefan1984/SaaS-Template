import json

from django.conf import settings
from rest_framework import serializers


def validate_json_payload_size(value):
    payload_size = len(json.dumps(value, default=str).encode("utf-8"))
    if payload_size > settings.MAX_JSON_PAYLOAD_BYTES:
        raise serializers.ValidationError(
            f"JSON payload exceeds {settings.MAX_JSON_PAYLOAD_BYTES} bytes."
        )
    return value


def validate_json_object(value):
    validate_json_payload_size(value)
    if not isinstance(value, dict):
        raise serializers.ValidationError("Expected a JSON object.")
    return value
