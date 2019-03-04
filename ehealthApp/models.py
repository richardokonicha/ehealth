from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser




class User(AbstractUser):
    is_regular = models.BooleanField(default=False)
    is_practitioner = models.BooleanField(default=False)



#this is wher ei
class Post(models.Model):
    title = models.CharField(max_length=20)
    content = models.TextField()
    date_posted = models.DateTimeField(default=timezone.now)
    author = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.title


class Profile(models.Model):
    choices = (("Yes", 'Yes'), ("No", 'No'))
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(default='default.jpg', upload_to='profile_pics')
    Email = models.EmailField(default='none@email.com')
    Malaria = models.CharField(max_length=255, choices=choices )
    Diarrheal_Diseases = models.CharField(max_length=255,choices=choices)
    Road_Injuries = models.CharField(max_length=255, choices=choices)
    Tuberculosis = models.CharField(max_length=255, choices=choices)
    Cough = models.CharField(max_length=255, choices=choices)
    def __str__(self):
        return f'{self.user.username} Profile'
        

