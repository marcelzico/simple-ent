from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db import models

class MultiFieldAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        
        try:
            # Try to find user by username, email, or IM ID
            user = UserModel.objects.get(
                models.Q(username__iexact=username) | 
                models.Q(email__iexact=username) |
                models.Q(im_id__iexact=username)
            )
        except UserModel.DoesNotExist:
            # Run the default password hasher once to reduce timing difference
            UserModel().set_password(password)
            return None
        except UserModel.MultipleObjectsReturned:
            # This shouldn't happen because of unique constraints
            return None
        
        if user.check_password(password) and self.user_can_authenticate(user):
            return user