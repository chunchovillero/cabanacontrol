from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections
from PIL import Image
from rest_framework.exceptions import ValidationError

from apps.properties.models import PropertyPhoto
from apps.properties.services import save_property, upload_photo
from tests.test_properties import DATA


@pytest.mark.django_db(transaction=True)
def test_concurrent_code_creation_is_rejected_by_database(identities):
    def attempt(_):
        close_old_connections()
        try:
            save_property(actor=identities["owner"], tenant=identities["tenant_a"], data=DATA)
            return True
        except ValidationError:
            return False
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        result = list(executor.map(attempt, range(2)))
    assert result.count(True) == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_uploads_respect_photo_limit(identities, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.PROPERTY_PHOTO_MAX_COUNT = 1
    property = save_property(actor=identities["owner"], tenant=identities["tenant_a"], data=DATA)
    stream = BytesIO()
    Image.new("RGB", (10, 10), "green").save(stream, "PNG")

    def attempt(_):
        close_old_connections()
        try:
            file = SimpleUploadedFile("test.png", stream.getvalue(), content_type="image/png")
            upload_photo(
                actor=identities["owner"],
                tenant=identities["tenant_a"],
                property=property,
                upload=file,
                alt="Ficticia",
                order=0,
            )
            return True
        except ValidationError:
            return False
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        result = list(executor.map(attempt, range(2)))
    assert result.count(True) == 1
    assert PropertyPhoto.objects.filter(property=property, active=True).count() == 1
