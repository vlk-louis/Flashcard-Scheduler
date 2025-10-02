# from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Custom User model that extends the default Django User model.
    This can be used to add additional fields or methods in the future.
    """

    pass


###############################################################################
## TODO: Modify the following
