import os
from core.models import Applications, Projects, UserRequest, ProjectUsers
from django.conf import settings
from django.shortcuts import render
from jinja2 import Environment
from django.http.response import Http404, HttpResponseForbidden
from rest_framework import viewsets, status, mixins, permissions
from rest_framework_swagger.views import get_swagger_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from email.mime.text import MIMEText
from core.serializers import ProjectsSerializer, ProjectSerializer, ApplicationSerializer, ProjectUsersSerializer, UserRequestSerializer, UserDetailsSerializer
from core.client.daco import DacoClient
import smtplib

schema_view = get_swagger_view(title='Enrol API')
SMTP_SERVER = smtplib.SMTP(settings.SMTP_URL, 25)


class CreateListRetrieveUpdateViewSet(mixins.CreateModelMixin,
                                      mixins.ListModelMixin,
                                      mixins.RetrieveModelMixin,
                                      mixins.UpdateModelMixin,
                                      viewsets.GenericViewSet):
    """
    A viewset that provides `retrieve`, `create`, 'update', and `list` actions.

    To use it, override the class and set the `.queryset` and
    `.serializer_class` attributes.

    Also allows you to set different serializers for the various methods:

    serializers = {
        'default': serializers.Default,
        'list':    serializers.List,
        'detail':  serializers.Details,
        # etc.
    }
    """
    serializers = {
        'default': None,
    }

    def get_serializer_class(self):
        return self.serializers.get(self.action, self.serializers['default'])


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permissions that allow admin or owner
    permission to object on all HTTP verbs except PUT/PATCH
    which is only for admins
    """

    def has_object_permission(self, request, view, obj):
        # If superuser allow
        if request.user.is_superuser:
            return True

        # If repuest is PUT/PATCH require admin
        if request.method in ("PUT", "PATCH") and not request.user.is_superuser:
            return False

        # Instance must have an attribute named `user`.
        return obj.user == request.user


class ProjectsViewSet(CreateListRetrieveUpdateViewSet):
    """
    Handles the Projects entity for the API
    """
    serializers = {
        'default': ProjectSerializer,
        'list':  ProjectsSerializer,
    }
    authentication_classes = (SessionAuthentication, )
    permission_classes = (IsAuthenticated, IsOwnerOrAdmin)

    def get_queryset(self):
        """
        Return all if user is admin, else return only owned
        """
        user = self.request.user

        if user.is_superuser:
            return Projects.objects.all()

        return Projects.objects.filter(user=user)


class ApplicationsViewSet(CreateListRetrieveUpdateViewSet):
    """
    Handles the Projects entity for the API
    """
    serializers = {
        'default': ApplicationSerializer,
    }
    authentication_classes = (SessionAuthentication, )
    permission_classes = (IsAuthenticated, IsOwnerOrAdmin)

    def get_queryset(self):
        """
        Return all if user is admin, else return only owned
        """
        user = self.request.user

        if user.is_superuser:
            return Applications.objects.all()

        return Applications.objects.filter(user=user)


@api_view(['GET'])
@authentication_classes((SessionAuthentication, ))
@permission_classes((IsAuthenticated, ))
def daco(request):
    if request.user.is_authenticated():
        email = request.user.email
        daco = DacoClient(base_url=settings.ICGC_BASE_URL,
                          client_key=settings.ICGC_CLIENT_KEY,
                          client_secret=settings.ICGC_CLIENT_SECRET,
                          token=settings.ICGC_TOKEN,
                          token_secret=settings.ICGC_TOKEN_SECRET)

        response = daco.get_daco_status(email)
        return Response(response)
    else:
        return HttpResponseForbidden()


@api_view(['GET'])
@authentication_classes((SessionAuthentication, ))
@permission_classes((IsAuthenticated, ))
def dacoAccess(request, email):
    if request.user.is_authenticated():
        dacoClient = DacoClient(base_url=settings.ICGC_BASE_URL,
                                client_key=settings.ICGC_CLIENT_KEY,
                                client_secret=settings.ICGC_CLIENT_SECRET,
                                token=settings.ICGC_TOKEN,
                                token_secret=settings.ICGC_TOKEN_SECRET)
        response = dacoClient.get_daco_status(email)
        return Response(response, status=status.HTTP_200_OK)
    else:
        return HttpResponseForbidden()


@api_view(['GET'])
@authentication_classes((SessionAuthentication, ))
@permission_classes((IsAuthenticated, ))
def SocialViewSet(request):
    user = request.user
    response = user.socialaccount_set.get(provider='google').extra_data
    return Response(response, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes((SessionAuthentication, ))
@permission_classes((IsAuthenticated, ))
def ProjectsUsersByIdViewSet(request, id):
    try:
        serializer = ProjectUsersSerializer(ProjectUsers.objects.get(pk=id))
        return Response(serializer.data, status=status.HTTP_200_OK)
    except ProjectUsers.DoesNotExist:
        raise Http404("No Users matches the given query.")


class ProjectUsersViewSet(APIView):
    """
    Responsible for handling the creation and retrieval of users in projects
    get - lists users that the current logged in user can see
    post - save a new user to a project
    put - update a user in a project
    """
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        if request.user.is_superuser:
            serializer = ProjectUsersSerializer(
                ProjectUsers.objects.all(), many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            user = request.user
            serializer = ProjectUsersSerializer(
                ProjectUsers.objects.filter(user=user), many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ProjectUsersSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            response = {"id": serializer.data.get('id')}
            return Response(response, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        if request.user.is_superuser:
            users = ProjectUsers.objects.get(pk=request.data.get('id'))
            serializer = ProjectUsersSerializer(
                users, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                response = {"id": serializer.data.get('id')}
                return Response(response, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return HttpResponseForbidden()


@api_view(['GET'])
@authentication_classes((SessionAuthentication, ))
@permission_classes((IsAuthenticated, ))
def ProjectsUsersByProjectViewSet(request, project):
    try:
        serializer = ProjectUsersSerializer(
            ProjectUsers.objects.filter(project=project), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except ProjectUsers.DoesNotExist:
        raise Http404("No Project User matches the given query.")


@api_view(['GET'])
@authentication_classes((SessionAuthentication, ))
@permission_classes((IsAuthenticated, ))
def UserRequestConfirmation(request, id):
    user = request.user
    email = request.user.email
    if user.is_authenticated():
        userRequest = UserRequestSerializer(
            UserRequest.objects.get(pk=id)).data

        if userRequest['email'] == email:
            return Response({
                'confirm': True,
                'user': userRequest
            }, status=status.HTTP_200_OK)

        return Response({'confirm': False}, status=status.HTTP_403_FORBIDDEN)


@api_view(['POST'])
@authentication_classes((SessionAuthentication, ))
@permission_classes((IsAuthenticated, ))
def UserRequestViewSet(request):
    if request.method == 'POST':
        response = {
            'success': True,
            'message': 'Emails were sent out'
        }
        for data in request.data:
            serializer = UserRequestSerializer(data=data)
            project = ProjectSerializer(
                Projects.objects.get(pk=data['project'])).data
            if serializer.is_valid():
                serializer.save()
                msg = MIMEText(
                    Environment().from_string(open(os.path.join(settings.BASE_DIR, 'enrol/template.html')).read()).render(
                        id=serializer.data['id'],
                        name=project['project_name'],
                        pi=project['pi']
                    ), "html"
                )
                msg['Subject'] = 'Collaboratory - Enrollment to project ' + \
                    project['project_name']
                msg['To'] = data['email']
                msg['From'] = 'test@cancercollaboratory.org'
                SMTP_SERVER.send_message(msg)
                continue
            else:
                SMTP_SERVER.quit()
                response = {
                    'success': False,
                    'message': 'Something went wrong'
                }
        return Response(response, status=status.HTTP_200_OK)
    else:
        SMTP_SERVER.quit()
        return HttpResponseForbidden()
