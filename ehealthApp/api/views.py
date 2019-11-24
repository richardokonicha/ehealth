from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view


from ehealthApp.api.serializers import ProfileSerializer
from ehealthApp.models import Profile, User
@api_view(['GET', ])
def api_profile_view(request, slug):
    try:
        profile = Profile.objects.get(user_id=slug)
    except Profile.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    if request.method == "GET":
        serializer = ProfileSerializer(profile)
        return Response(serializer.data)


@api_view(["PUT, "])
def api_update_profile_view(request, slug):
    try:
        profile = Profile.objects.get(user_id=slug)
    except Profile.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    if request.method == "PUT":
        serializer = ProfileSerializer(profile, data=request.data)
        data = {}
        if serializer.is_valid():
            serializer.save()
            data['success'] = "update successful"
            return Response(serializer.data)
        return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)


@api_view(["DELETE", ])
def api_delete_profile_view(request, slug):
    try:
        profile = Profile.objects.get(user_id=slug)
    except Profile.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    if request.method == "DELETE":
        operation = profile.delete()
        data = {}
        if operation:
            data["success"] = "delete successful"
        else:
            data["failure"] = "delete was unsuccessful"
        return Response(data=data)

@api_view(["POST"])
def api_create_profile_view(request):
    user = User.objects.get(pk=5)
    profile = Profile()

    if request.method == "POST":
        serializer = ProfileSerializer(profile, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.data, status=status.HTTP_400_BAD_REQUEST)

