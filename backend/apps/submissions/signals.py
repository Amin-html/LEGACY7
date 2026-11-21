from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Submission


@receiver(post_delete, sender=Submission)
def delete_file_with_submission(sender, instance, **kwargs):
    """Удалили работу: удаляем и файл с диска, чтобы не копить мусор."""
    if instance.file:
        instance.file.delete(save=False)