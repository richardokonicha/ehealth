from django.shortcuts import render, redirect
from .models import Profile
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import ProfileUpdateForm, UpdateMyForm
from django.contrib.auth import (authenticate, login, logout, update_session_auth_hash )
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.views.generic import View
from .forms import UserRegisterForm, MedRegisterForm
from django.views.generic import CreateView, ListView, UpdateView
from django_tables2 import RequestConfig
from .table import ProfileTable
from .filter import UserFilter
from .models import User


def value_count():
    '''This function counts the number of user that selected Yes to a Category and returns a dictionary'''
    users= User.objects.all()
    Malaria_number, Diarrheal_number, Road_number, Tuberculosis_number, Cough_number = 0,0,0,0,0
    for i in users:
        if i.profile.Malaria=='Yes':
            Malaria_number += 1
        if i.profile.Diarrheal_Diseases=='Yes':
            Diarrheal_number += 1
        if i.profile.Road_Injuries=='Yes':
            Road_number += 1
        if i.profile.Tuberculosis=='Yes':
            Tuberculosis_number += 1
        if i.profile.Cough=='Yes':
            Cough_number += 1
    value = {
        'Malaria': Malaria_number, 
        'Diarrheal_Diseases': Diarrheal_number, 
        'Road_Injuries': Road_number,
        'Tuberculosis': Tuberculosis_number,
        'Cough': Cough_number
    }
    return value

value = value_count()
#User = get_user_model()

@login_required
def ehealth_home(request):
    profile = request.user.profile
    if request.user.is_regular==True:
        tmp = 'ehealthApp/base.html'
    else:
        tmp = 'ehealthApp/baseMed.html'
    context = {
        'profile': profile,
        'tmp': tmp,
        'value': value
    }
    return render(request, 'ehealthApp/home.html', context)


def ehealth_about(request):
    if request.user.is_anonymous==True:
        print('jumpp')
        tmp = 'ehealthApp/base.html'
        return render(request, 'ehealthApp/about.html', { 'tmp': tmp })

    else:
        if request.user.is_practitioner==True:
            tmp = 'ehealthApp/baseMed.html'
        else:
            tmp = 'ehealthApp/base.html'
        profile = request.user.profile
    return render(request, 'ehealthApp/about.html', 
    { 'tmp': tmp,
      'profile': profile,
      'value': value })


@login_required
def ehealth_tables(request):
    user_list = Profile.objects.all()
    user_filter = UserFilter(request.GET, queryset=user_list)

    return render(request, 'ehealthApp/tables.html', 
    {  
    'filter': user_filter, 
    'value': value} )



def ehealth_tables2(request):
    #RequestConfig(request).configure(tables)
    table = ProfileTable(Profile.objects.all())
    return render(request, 'ehealthApp/tables2.html',  { 'table': table, 'value': value } )



#This is the register view for normal Users
class Ehealth_register(CreateView):
    model = User
    form_class = UserRegisterForm
    template_name = 'ehealthApp/register.html'

    def get_context_data(self, **kwargs):
        kwargs['user_type'] = 'regular'
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        user = form.save()
        username=form.cleaned_data['username']
        login(self.request, user)
        messages.success(self.request, f"Your account have been created, you have been logged in as {username}! Please setup your Profile")
        return redirect('ehealth_profile')

#This is the register view for Medical Pactitioners
class Ehealth_registerMed(CreateView):
    model = User
    form_class = MedRegisterForm
    template_name = 'ehealthApp/registerMed.html'

    def get_context_data(self, **kwargs):
        kwargs['user_type'] = 'practitioner'
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        user = form.save()
        username=form.cleaned_data['username']
        login(self.request, user)
        messages.success(self.request, f"You are now a registered medical pactitioner, you have been logged in as {username}! Please Examine users Profiles and diagnose")
        return redirect('ehealth_home')


@login_required
def ehealth_profile(request):
    '''Regular User profile view'''
    if request.method == 'POST':
        updatemyform = UpdateMyForm(request.POST, request.FILES, instance=request.user.profile)
        profile_update = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if profile_update.is_valid() and updatemyform.is_valid():
            profile_update.save()
            updatemyform.save()
            messages.success(request, f'Account has been Updated')
            return redirect('ehealth_profile')
    else:
        profile_update = ProfileUpdateForm(instance=request.user.profile)
        updatemyform = UpdateMyForm(instance=request.user.profile)
        
    context = {
        'profile_update': profile_update,
        'updatemyform': updatemyform
    }
    return render(request, 'ehealthApp/profile.html', context)



def get_data(request, *args, **kwargs):
    '''pass data to the chart'''
    value_list = list(value.values())
    lables_list = list(value.keys())
    data = {
        "value": value_list,
        "labels": lables_list, 
    }
    return JsonResponse(data) # http response


    