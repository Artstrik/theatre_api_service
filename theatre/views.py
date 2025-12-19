from datetime import datetime

from django.db.models import F, Count
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiExample
)
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from theatre.models import (
    Genre,
    Actor,
    TheatreHall,
    Play,
    Performance,
    Reservation
)
from theatre.permissions import IsAdminOrIfAuthenticatedReadOnly

from theatre.serializers import (
    GenreSerializer,
    ActorSerializer,
    TheatreHallSerializer,
    PlaySerializer,
    PerformanceSerializer,
    PerformanceListSerializer,
    PlayDetailSerializer,
    PerformanceDetailSerializer,
    PlayListSerializer,
    ReservationSerializer,
    ReservationListSerializer,
    PlayImageSerializer,
)


class GenreViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    @extend_schema(
        description="Get list of all genres. "
                    "No authentication required for viewing.",
        summary="Get list of all genres.",
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        description="Create a new genre. Admin permission required.",
        summary="Create a new genre.",
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


class ActorViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    @extend_schema(
        description="Get list of all actors. "
                    "No authentication required for viewing.",
        summary="List all actors"
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        description="Create a new actor. Admin permission required.",
        summary="Create actor"
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


class TheatreHallViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    queryset = TheatreHall.objects.all()
    serializer_class = TheatreHallSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    @extend_schema(
        description="Get list of all theatre halls with their capacity. "
                    "No authentication required for viewing.",
        summary="List all theatre halls"
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        description="Create a new theatre hall. Admin permission required.",
        summary="Create theatre hall"
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


class PlayViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Play.objects.prefetch_related("genres", "actors")
    serializer_class = PlaySerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    @staticmethod
    def _params_to_ints(qs):
        """Converts a list of string IDs to a list of integers"""
        return [int(str_id) for str_id in qs.split(",")]

    def get_queryset(self):
        """Retrieve the plays with filters"""
        title = self.request.query_params.get("title")
        genres = self.request.query_params.get("genres")
        actors = self.request.query_params.get("actors")

        queryset = self.queryset

        if title:
            queryset = queryset.filter(title__icontains=title)

        if genres:
            genres_ids = self._params_to_ints(genres)
            queryset = queryset.filter(genres__id__in=genres_ids)

        if actors:
            actors_ids = self._params_to_ints(actors)
            queryset = queryset.filter(actors__id__in=actors_ids)

        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return PlayListSerializer

        if self.action == "retrieve":
            return PlayDetailSerializer

        if self.action == "upload_image":
            return PlayImageSerializer

        return PlaySerializer

    @action(
        methods=["POST"],
        detail=True,
        url_path="upload-image",
        permission_classes=[IsAdminUser],
    )
    def upload_image(self, request, pk=None):
        """Endpoint for uploading image to specific play"""
        play = self.get_object()
        serializer = self.get_serializer(play, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        description="""Get list of plays with optional filtering.

            You can filter plays by:
            - **title**: Filter by play title (case-insensitive partial match)
            - **genres**: Filter by genre IDs (comma-separated list)
            - **actors**: Filter by actor IDs (comma-separated list)

            **Note**: All filters can be used separately or combined.
            """,
        summary="List plays with filtering",
        parameters=[
            OpenApiParameter(
                name="title",
                description="Filter by play title "
                            "(partial match, case-insensitive)",
                type=OpenApiTypes.STR,
                required=False,
                examples=[
                    OpenApiExample(
                        "Search for play containing 'hamlet'",
                        value="hamlet",
                    ),
                ],
            ),
            OpenApiParameter(
                name="genres",
                description="Filter play by genre IDs. "
                            "Provide a comma-separated list of genre IDs",
                type=OpenApiTypes.STR,
                required=False,
                examples=[
                    OpenApiExample(
                        "Plays in Tragedy (ID: 1) and Drama (ID: 2) genres",
                        value="1,2",
                    ),
                ],
            ),
            OpenApiParameter(
                name="actors",
                description="Filter plays by actor IDs. "
                            "Provide a comma-separated list of actor IDs",
                type=OpenApiTypes.STR,
                required=False,
                examples=[
                    OpenApiExample(
                        "Plays featuring actors with IDs 1 and 2",
                        value="1,2"
                    ),
                ],
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        description="Get detailed information about a specific play "
                    "including all genres and actors.",
        summary="Get play details"
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        description="Create a new play. Admin permission required.",
        summary="Create play"
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


class PerformanceViewSet(viewsets.ModelViewSet):
    queryset = (
        Performance.objects.all()
        .select_related("play", "theatre_hall")
        .annotate(
            tickets_available=(
                F("theatre_hall__rows") * F("theatre_hall__seats_in_row")
                - Count("tickets")
            )
        )
    )
    serializer_class = PerformanceSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_queryset(self):
        date = self.request.query_params.get("date")
        play_id_str = self.request.query_params.get("play")

        queryset = self.queryset

        if date:
            date = datetime.strptime(date, "%Y-%m-%d").date()
            queryset = queryset.filter(show_time__date=date)

        if play_id_str:
            queryset = queryset.filter(play_id=int(play_id_str))

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return PerformanceListSerializer

        if self.action == "retrieve":
            return PerformanceDetailSerializer

        return PerformanceSerializer

    @extend_schema(
        description="""Get a list of all performances
            with optional filtering.

            You can filter performances by:
            - **date**: Filter by specific date (format: YYYY-MM-DD)
            - **play**: Filter by play ID

            **Note**: Filters can be used separately or combined.
            Each performance includes information about available tickets.
            """,
        summary="List performances with filtering",
        parameters=[
            OpenApiParameter(
                name="date",
                description="Filter by specific date (format: YYYY-MM-DD)",
                type=OpenApiTypes.DATE,
                required=False,
                examples=[
                    OpenApiExample(
                        "Performance on January 15, 2024",
                        value="2024-01-15"
                    ),
                ],
            ),
            OpenApiParameter(
                name="play",
                description="Filter performances by specific play ID",
                type=OpenApiTypes.INT,
                required=False,
                examples=[
                    OpenApiExample("Performance for play with ID: 1", value=1),
                ],
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        description="Get detailed information about a specific performance "
                    "including taken seats and theatre hall details.",
        summary="Get performance details"
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        description="Create a new performance. Admin permission required.",
        summary="Create performance"
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        description="Update a performance. Admin permission required.",
        summary="Update performance"
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        description="Partially update a performance. "
                    "Admin permission required.",
        summary="Partial update performance"
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        description="Delete a performance. Admin permission required.",
        summary="Delete performance"
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class ReservationPagination(PageNumberPagination):
    page_size = 10
    max_page_size = 100


class ReservationViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    queryset = Reservation.objects.prefetch_related(
        "tickets__performance__play",
        "tickets__performance__theatre_hall"
    )
    serializer_class = ReservationSerializer
    pagination_class = ReservationPagination
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Reservation.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return ReservationListSerializer

        return ReservationSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(
        description="Get list of user's reservations."
                    " Authentication required.",
        summary="List user reservations"
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        description="Create a new reservation with tickets. "
                    "Authentication required.",
        summary="Create reservation"
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
