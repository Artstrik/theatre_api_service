import tempfile
import os
from datetime import datetime

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from theatre.models import Play, Performance, TheatreHall, Genre, Actor, Reservation, Ticket
from theatre.serializers import PlayDetailSerializer, PlayListSerializer

PLAY_URL = reverse("theatre:play-list")
PERFORMANCE_URL = reverse("theatre:performance-list")


def sample_play(**params):
    defaults = {
        "title": "Sample play",
        "description": "Sample description",
    }
    defaults.update(params)

    return Play.objects.create(**defaults)


def sample_genre(**params):
    defaults = {
        "name": "Drama",
    }
    defaults.update(params)

    return Genre.objects.create(**defaults)


def sample_actor(**params):
    defaults = {"first_name": "George", "last_name": "Clooney"}
    defaults.update(params)

    return Actor.objects.create(**defaults)


def sample_theatre_hall(**params):
    defaults = {
        "name": "Main Hall",
        "rows": 10,
        "seats_in_row": 15,
    }
    defaults.update(params)

    return TheatreHall.objects.create(**defaults)


def sample_performance(**params):
    theatre_hall = sample_theatre_hall()
    play = sample_play()

    defaults = {
        "show_time": datetime(2022, 6, 2, 14, 0, 0),
        "play": play,
        "theatre_hall": theatre_hall,
    }
    defaults.update(params)

    return Performance.objects.create(**defaults)


def image_upload_url(play_id):
    """Return URL for play image upload"""
    return reverse("theatre:play-upload-image", args=[play_id])


def detail_url(play_id):
    return reverse("theatre:play-detail", args=[play_id])


class PlayImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.play = sample_play()
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.performance = sample_performance(play=self.play)

    def tearDown(self):
        if self.play.image:
            self.play.image.delete()

    def test_upload_image_to_play(self):
        """Test uploading an image to play"""
        url = image_upload_url(self.play.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
        self.play.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.play.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image"""
        url = image_upload_url(self.play.id)
        res = self.client.post(url, {"image": "not image"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_image_to_play_list(self):
        url = PLAY_URL
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(
                url,
                {
                    "title": "Title",
                    "description": "Description",
                    "genres": [1],
                    "actors": [1],
                    "image": ntf,
                },
                format="multipart",
            )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        play = Play.objects.get(title="Title")
        self.assertFalse(play.image)

    def test_image_url_is_shown_on_play_detail(self):
        url = image_upload_url(self.play.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(detail_url(self.play.id))

        self.assertIn("image", res.data)

    def test_image_url_is_shown_on_play_list(self):
        url = image_upload_url(self.play.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(PLAY_URL)

        self.assertIn("image", res.data["results"][0].keys())

    def test_image_url_is_shown_on_performance_list(self):
        url = image_upload_url(self.play.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(PERFORMANCE_URL)

        self.assertIn("play_image", res.data["results"][0].keys())


class UnauthorizedTests(TestCase):
    """Test unauthenticated API access"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required_for_play_list(self):
        res = self.client.get(PLAY_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_auth_required_for_play_detail(self):
        play = sample_play()
        url = detail_url(play.id)

        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_auth_required_for_create_play(self):
        payload = {
            "title": "Test Play",
            "description": "Test Description",
        }

        res = self.client.post(PLAY_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedTheatreApi(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="testemail@example.com", password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_plays_list(self):
        sample_play()

        res = self.client.get(PLAY_URL)

        plays = Play.objects.all()
        serializer = PlayListSerializer(plays, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Порівнюємо лише дані з результатами пагінації
        self.assertEqual(res.data["results"], serializer.data)
        self.assertEqual(res.data["count"], 1)

    def test_play_detail(self):
        play = sample_play()
        play.genres.add(sample_genre())
        play.actors.add(sample_actor())

        url = detail_url(play.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        serializer = PlayDetailSerializer(play)
        self.assertEqual(res.data, serializer.data)

    def test_plays_ordered_by_title(self):
        sample_play(title="Gamma Play")
        sample_play(title="Beta Play")
        sample_play(title="Alpha Play")

        res = self.client.get(PLAY_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Get data from pagination (PageSize = 2, so first page has 2 items)
        data = res.data["results"]

        # Check that first page has 2 items (Alpha and Beta)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["title"], "Alpha Play")
        self.assertEqual(data[1]["title"], "Beta Play")

        # Get second page for the third item
        res_page2 = self.client.get(PLAY_URL, {"page": 2})
        data_page2 = res_page2.data["results"]

        # Check that second page has 1 item (Gamma)
        self.assertEqual(len(data_page2), 1)
        self.assertEqual(data_page2[0]["title"], "Gamma Play")

    def test_retrieve_nonexistent_play(self):
        url = detail_url(9999)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_play_forbidden(self):
        payload = {
            "title": "Test Play",
            "description": "Test Description",
        }
        res = self.client.post(PLAY_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_plays_by_title(self):
        play1 = sample_play(title="Hamlet")
        play2 = sample_play(title="Romeo and Juliet")
        play3 = sample_play(title="Hamlet 2")

        res = self.client.get(PLAY_URL, {"title": "hamlet"})

        serializer1 = PlayListSerializer(play1)
        serializer2 = PlayListSerializer(play2)
        serializer3 = PlayListSerializer(play3)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Перетворюємо ReturnDict на dict для порівняння
        play1_data = dict(serializer1.data)
        play2_data = dict(serializer2.data)
        play3_data = dict(serializer3.data)

        results = res.data["results"]
        self.assertIn(play1_data, results)
        self.assertNotIn(play2_data, results)
        self.assertIn(play3_data, results)

    def test_filter_plays_by_genres(self):
        play1 = sample_play(title="Play 1")
        play2 = sample_play(title="Play 2")
        play3 = sample_play(title="Play 3")

        genre1 = sample_genre(name="Tragedy")
        genre2 = sample_genre(name="Comedy")

        play1.genres.add(genre1)
        play2.genres.add(genre2)
        play3.genres.add(genre1, genre2)

        res = self.client.get(PLAY_URL, {"genres": f"{genre1.id}"})

        serializer1 = PlayListSerializer(play1)
        serializer2 = PlayListSerializer(play2)
        serializer3 = PlayListSerializer(play3)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        play1_data = dict(serializer1.data)
        play2_data = dict(serializer2.data)
        play3_data = dict(serializer3.data)

        results = res.data["results"]
        self.assertIn(play1_data, results)
        self.assertNotIn(play2_data, results)
        self.assertIn(play3_data, results)

    def test_filter_plays_by_multiple_genres(self):
        play1 = sample_play(title="Play 1")
        play2 = sample_play(title="Play 2")
        play3 = sample_play(title="Play 3")

        genre1 = sample_genre(name="Tragedy")
        genre2 = sample_genre(name="Comedy")
        genre3 = sample_genre(name="Drama")

        play1.genres.add(genre1)
        play2.genres.add(genre2)
        play3.genres.add(genre3)

        res = self.client.get(PLAY_URL, {"genres": f"{genre1.id},{genre2.id}"})

        serializer1 = PlayListSerializer(play1)
        serializer2 = PlayListSerializer(play2)
        serializer3 = PlayListSerializer(play3)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        play1_data = dict(serializer1.data)
        play2_data = dict(serializer2.data)
        play3_data = dict(serializer3.data)

        results = res.data["results"]
        self.assertIn(play1_data, results)
        self.assertIn(play2_data, results)
        self.assertNotIn(play3_data, results)

    def test_filter_plays_by_actors(self):
        play1 = sample_play(title="Play 1")
        play2 = sample_play(title="Play 2")
        play3 = sample_play(title="Play 3")

        actor1 = sample_actor(first_name="John", last_name="Gielgud")
        actor2 = sample_actor(first_name="Laurence", last_name="Olivier")

        play1.actors.add(actor1)
        play2.actors.add(actor2)
        play3.actors.add(actor1, actor2)

        res = self.client.get(PLAY_URL, {"actors": f"{actor1.id}"})

        serializer1 = PlayListSerializer(play1)
        serializer2 = PlayListSerializer(play2)
        serializer3 = PlayListSerializer(play3)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        play1_data = dict(serializer1.data)
        play2_data = dict(serializer2.data)
        play3_data = dict(serializer3.data)

        results = res.data["results"]
        self.assertIn(play1_data, results)
        self.assertNotIn(play2_data, results)
        self.assertIn(play3_data, results)

    def test_filter_plays_by_multiple_actors(self):
        play1 = sample_play(title="Play 1")
        play2 = sample_play(title="Play 2")
        play3 = sample_play(title="Play 3")

        actor1 = sample_actor(first_name="John", last_name="Gielgud")
        actor2 = sample_actor(first_name="Laurence", last_name="Olivier")
        actor3 = sample_actor(first_name="Marlon", last_name="Brando")

        play1.actors.add(actor1)
        play2.actors.add(actor2)
        play3.actors.add(actor3)

        res = self.client.get(PLAY_URL, {"actors": f"{actor1.id},{actor2.id}"})

        serializer1 = PlayListSerializer(play1)
        serializer2 = PlayListSerializer(play2)
        serializer3 = PlayListSerializer(play3)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        play1_data = dict(serializer1.data)
        play2_data = dict(serializer2.data)
        play3_data = dict(serializer3.data)

        results = res.data["results"]
        self.assertIn(play1_data, results)
        self.assertIn(play2_data, results)
        self.assertNotIn(play3_data, results)

    def test_filter_plays_by_title_and_genre(self):
        play1 = sample_play(title="Hamlet Tragedy")
        play2 = sample_play(title="Hamlet Comedy")
        play3 = sample_play(title="Macbeth Tragedy")

        genre1 = sample_genre(name="Tragedy")
        genre2 = sample_genre(name="Comedy")

        play1.genres.add(genre1)
        play2.genres.add(genre2)
        play3.genres.add(genre1)

        res = self.client.get(PLAY_URL, {"title": "hamlet", "genres": f"{genre1.id}"})

        serializer1 = PlayListSerializer(play1)
        serializer2 = PlayListSerializer(play2)
        serializer3 = PlayListSerializer(play3)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        play1_data = dict(serializer1.data)
        play2_data = dict(serializer2.data)
        play3_data = dict(serializer3.data)

        results = res.data["results"]
        self.assertIn(play1_data, results)
        self.assertNotIn(play2_data, results)
        self.assertNotIn(play3_data, results)

    def test_filter_plays_by_all_parameters(self):
        play1 = sample_play(title="Great Play")
        play2 = sample_play(title="Great Drama")
        play3 = sample_play(title="Another Great Play")

        genre1 = sample_genre(name="Tragedy")
        actor1 = sample_actor(first_name="John", last_name="Doe")

        play1.genres.add(genre1)
        play1.actors.add(actor1)

        play2.genres.add(genre1)

        play3.actors.add(actor1)

        res = self.client.get(
            PLAY_URL,
            {"title": "play", "genres": f"{genre1.id}", "actors": f"{actor1.id}"},
        )

        serializer1 = PlayListSerializer(play1)
        serializer2 = PlayListSerializer(play2)
        serializer3 = PlayListSerializer(play3)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        play1_data = dict(serializer1.data)
        play2_data = dict(serializer2.data)
        play3_data = dict(serializer3.data)

        results = res.data["results"]
        self.assertIn(play1_data, results)
        self.assertNotIn(play2_data, results)
        self.assertNotIn(play3_data, results)

    def test_partial_update_play_forbidden(self):
        play = sample_play()
        url = detail_url(play.id)

        payload = {"title": "Updated Title"}
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_full_update_play_forbidden(self):
        play = sample_play()
        url = detail_url(play.id)

        payload = {
            "title": "Updated Play",
            "description": "Updated Description",
        }
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_play_forbidden(self):
        play = sample_play()
        url = detail_url(play.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Play.objects.filter(id=play.id).exists())


class AdminTheatreApi(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            email="admin@example.com", password="adminpass"
        )
        self.client.force_authenticate(self.user)

    def test_create_play(self):
        genre = sample_genre()
        actor = sample_actor()
        payload = {
            "title": "New Play",
            "description": "New Description",
            "genres": [genre.id],
            "actors": [actor.id],
        }
        res = self.client.post(PLAY_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        play = Play.objects.get(id=res.data["id"])

        self.assertEqual(play.title, payload["title"])
        self.assertEqual(play.description, payload["description"])
        self.assertIn(genre, play.genres.all())
        self.assertIn(actor, play.actors.all())

    def test_create_play_with_multiple_genres_and_actors(self):
        genre1 = sample_genre(name="Tragedy")
        genre2 = sample_genre(name="Drama")
        actor1 = sample_actor(first_name="Actor", last_name="One")
        actor2 = sample_actor(first_name="Actor", last_name="Two")
        payload = {
            "title": "Complex Play",
            "description": "Complex Description",
            "genres": [genre1.id, genre2.id],
            "actors": [actor1.id, actor2.id],
        }
        res = self.client.post(PLAY_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        play = Play.objects.get(id=res.data["id"])

        self.assertEqual(play.genres.count(), 2)
        self.assertEqual(play.actors.count(), 2)
        self.assertIn(genre1, play.genres.all())
        self.assertIn(genre2, play.genres.all())
        self.assertIn(actor1, play.actors.all())
        self.assertIn(actor2, play.actors.all())

    def test_create_play_with_empty_genres_and_actors(self):
        payload = {
            "title": "Simple Play",
            "description": "Simple Description",
            "genres": [],
            "actors": [],
        }
        res = self.client.post(PLAY_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("genres", res.data)
        self.assertIn("actors", res.data)

    def test_create_play_invalid_data(self):
        payload = {
            "title": "",
            "description": "Description",
        }
        res = self.client.post(PLAY_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_play_missing_required_fields(self):
        payload = {
            "title": "Test Play",
        }
        res = self.client.post(PLAY_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
