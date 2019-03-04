from django import forms
#from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from ehealthApp.models import Profile, User
from django.db import transaction
from django.forms.utils import ValidationError



question1 = ['Have you ever being diagnosed with an STD ?', 'Have you been diagnosed with sickle cell', 'Are you a recreational drug user']
choices =  ((" ", " "), ("Yes", 'Yes'), ("Yes", 'No'))




class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
    
    @transaction.atomic
    def save(self):
        user = super().save(commit=False)
        user.is_regular = True
        user.save()
        #Profile.objects.create(user=user)
        #student.interests.add(*self.cleaned_data.get('interests'))
        return user


class MedRegisterForm(UserCreationForm):
    email = forms.EmailField()
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
    
    @transaction.atomic
    def save(self):
        user = super().save(commit=False)
        user.is_practitioner = True
        user.save()
        #Profile.objects.create(user=user)
        #student.interests.add(*self.cleaned_data.get('interests'))
        return user

#hjhsjkgjg



class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
             'image',
        ]

class UpdateMyForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            
            'Malaria',
            'Diarrheal_Diseases',
            'Road_Injuries',
            'Tuberculosis',
            'Cough'
        ]

