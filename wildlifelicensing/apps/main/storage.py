from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateFileSystemStorage(FileSystemStorage):
    def __init__(self):
        super().__init__(
            location=settings.PRIVATE_MEDIA_ROOT,
            base_url=settings.PRIVATE_MEDIA_URL,
        )


private_storage = PrivateFileSystemStorage()
