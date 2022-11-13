from django.db import models
import datetime
from model_utils.models import TimeStampedModel

# To reprocess events that didn't make it to the processing queue
class EventOverflow(TimeStampedModel):
    event = models.CharField(max_length=255)