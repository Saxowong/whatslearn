### api/views.py
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from user.models import Profile
from .serializers import (
    ProfileSerializer,
    DictionaryItemSerializer,
    StudentWordSerializer,
    DictionarySearchResponseSerializer,
)
from dictionary.models import DictionaryItem, StudentWord
from django.utils import timezone
from django.db.models import Q
import re


# Authentication Views
class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ProfileSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(username=username, password=password)
        if user:
            profile = user.profile
            profile.last_login_at = timezone.now()
            profile.save()
            refresh = RefreshToken.for_user(user)
            student_words = StudentWord.objects.filter(student=profile)
            student_words_serializer = StudentWordSerializer(
                student_words, many=True, context={"request": request}
            )
            return Response(
                {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                    "user": ProfileSerializer(
                        profile, context={"request": request}
                    ).data,
                    "word_list": student_words_serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            {"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED
        )


# Dictionary and StudentWord ViewSets
class DictionaryItemViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DictionaryItem.objects.all()
    serializer_class = DictionaryItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["get"])
    def search(self, request):
        query = request.query_params.get("q", "").strip()
        results = []
        match_algorithm = None
        student_word_count = 0
        pending_revise_count = 0

        # Get the current user's profile and count their words
        try:
            profile = request.user.profile
            student_word_count = StudentWord.objects.filter(student=profile).count()
            pending_revise_count = StudentWord.objects.filter(
                student=profile, revise_at__isnull=False, revise_at__lte=timezone.now()
            ).count()
        except Profile.DoesNotExist:
            student_word_count = 0
            pending_revise_count = 0

        if query:
            # Remove punctuation and split into words
            clean_query = re.sub(r"[^\w\s]", "", query)
            words = [word.strip() for word in clean_query.split() if word.strip()]
            input_words = [(word, word.lower()) for word in words if word.strip()]

            if input_words:
                if len(words) == 1:
                    # Single-word query
                    original_word = input_words[0][0]
                    lowercase_word = input_words[0][1]
                    # Try exact match
                    exact_match = DictionaryItem.objects.filter(
                        word__iexact=lowercase_word,
                        word__regex=r"^\w+$",
                    ).first()
                    if exact_match:
                        match_algorithm = "exact match"
                        db_results = DictionaryItem.objects.filter(
                            word__gte=exact_match.word,
                            word__regex=r"^\w+$",
                        ).order_by("word")[:10]
                    else:
                        match_algorithm = "similar words"
                        search_prefix = (
                            lowercase_word[:4]
                            if len(lowercase_word) >= 4
                            else lowercase_word
                        )
                        db_results = DictionaryItem.objects.filter(
                            word__istartswith=search_prefix,
                            word__regex=r"^\w+$",
                        ).order_by("word")[:10]
                        if len(db_results) < 5 and len(search_prefix) > 2:
                            shorter_prefix = lowercase_word[:3]
                            more_results = DictionaryItem.objects.filter(
                                word__istartswith=shorter_prefix,
                                word__regex=r"^\w+$",
                            ).order_by("word")[:10]
                            combined_results = list(db_results) + [
                                r for r in more_results if r not in db_results
                            ]
                            db_results = combined_results[:10]

                    for i, result in enumerate(db_results):
                        is_owned_by_student = (
                            StudentWord.objects.filter(
                                student=profile, word=result.word
                            ).exists()
                            if request.user.is_authenticated
                            else False
                        )
                        results.append(
                            {
                                "input_word": (
                                    original_word if i == 0 and exact_match else None
                                ),
                                "db_word": result.word,
                                "meaning": result.meaning,
                                "is_owned_by_student": is_owned_by_student,
                            }
                        )
                else:
                    # Sentence query: Exact matches in input order
                    query_filter = Q()
                    for _, lowercase_word in input_words:
                        query_filter |= Q(word__iexact=lowercase_word)
                    db_results = DictionaryItem.objects.filter(
                        query_filter, word__regex=r"^\w+$"
                    ).distinct()
                    result_dict = {result.word.lower(): result for result in db_results}
                    seen = set()
                    for original_word, lowercase_word in input_words:
                        if lowercase_word not in seen and lowercase_word in result_dict:
                            entry = result_dict[lowercase_word]
                            is_owned_by_student = (
                                StudentWord.objects.filter(
                                    student=profile, word=entry.word
                                ).exists()
                                if request.user.is_authenticated
                                else False
                            )
                            results.append(
                                {
                                    "input_word": original_word,
                                    "db_word": entry.word,
                                    "meaning": entry.meaning,
                                    "is_owned_by_student": is_owned_by_student,
                                }
                            )
                            seen.add(lowercase_word)

        response_data = {
            "query": query,
            "results": DictionarySearchResponseSerializer(results, many=True).data,
            "match_algorithm": match_algorithm,
            "student_word_count": student_word_count,
            "pending_revise_count": pending_revise_count,
        }
        return Response(response_data, status=status.HTTP_200_OK)


class StudentWordViewSet(viewsets.ModelViewSet):
    serializer_class = StudentWordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StudentWord.objects.filter(student=self.request.user.profile)

    def perform_create(self, serializer):
        serializer.save(student=self.request.user.profile)

    @action(detail=True, methods=["put"])
    def revise(self, request, pk=None):
        try:
            word_entry = self.get_queryset().get(pk=pk)
            serializer = self.get_serializer(
                word_entry, data=request.data, partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except StudentWord.DoesNotExist:
            return Response(
                {"error": "Word not found"}, status=status.HTTP_404_NOT_FOUND
            )
