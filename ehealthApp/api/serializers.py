from rest_framework import serializers
from ehealthApp.models import Profile


class ProfileSerializer(serializers.ModelSerializer):

    username = serializers.SerializerMethodField('get_username')
    class Meta:
        model = Profile
        fields = ['username', 'user', 'image', 'Email', 'Malaria', 'Diarrheal_Diseases', 'Road_Injuries', 'Tuberculosis', 'Cough']

    def get_username(self, authoruser):
        username = str(authoruser.user)
        return username