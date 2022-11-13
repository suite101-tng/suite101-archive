from django.contrib.staticfiles.storage import CachedFilesMixin
from django.core.files.storage import get_storage_class
from storages.backends.s3boto import S3BotoStorage
from require.storage import OptimizedFilesMixin


class CachedS3BotoStorage(S3BotoStorage):
    """
    S3 storage backend that saves the files locally, too.
    """
    def __init__(self, *args, **kwargs):
        super(CachedS3BotoStorage, self).__init__(*args, **kwargs)
        self.local_storage = get_storage_class(
            "compressor.storage.CompressorFileStorage")()

    def save(self, name, content):
        """ https://github.com/jezdez/django_compressor/issues/404 """
        non_gzipped_file_content = content.file
        name = super(CachedS3BotoStorage, self).save(name, content)
        content.file = non_gzipped_file_content
        self.local_storage._save(name, content)
        return name

# S3 storage with r.js optimization and MD5 fingerprinting.
class OptimizedCachedS3BotoStorage(OptimizedFilesMixin, CachedFilesMixin, CachedS3BotoStorage):
    pass
