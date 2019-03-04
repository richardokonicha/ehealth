
from .models import Profile
import django_filters

from .models import User
import django_filters

class UserFilter(django_filters.FilterSet):
    class Meta:
        model = Profile
        fields = [
            'Malaria',
            'Diarrheal_Diseases',
            'Road_Injuries',
            'Tuberculosis',
            'Cough'
         ]
