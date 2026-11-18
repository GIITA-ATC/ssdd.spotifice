from media_render import Spotifice
from metadata import identify

from .icetest import pool_condition
from .test_render import MEDIA, TestRender

TRACK_1S = identify(MEDIA / '1s.mp3')
TRACK_2S = identify(MEDIA / '2s.mp3')
TRACK_4S = identify(MEDIA / '4s.mp3')

THREE = 'test-playlist-three'  # 1s, 2s, 4s
SHORT = 'test-playlist-short'  # 1s, 1s
TWO = 'test-playlist-unknown'  # 2s, 1s (unknown track skipped)


class RenderV2TestCase(TestRender):
    def setUp(self):
        super().setUp()
        self.bind()

    def assert_current(self, track_id, playing):
        self.assertEqual(self.sut.get_current_track().id, track_id)
        self.assertEqual(self.player.is_playing(), playing)

    def wait_until(self, condition):
        self.assertTrue(pool_condition(condition, ntries=12, interval_secs=0.5))


class LoadPlaylistTests(RenderV2TestCase):
    def test_load_playlist_unbound_provider(self):
        self.sut.unbind_media_provider()

        with self.assertRaises(Spotifice.BadReference):
            self.sut.load_playlist(THREE)

    def test_load_playlist_wrong_id(self):
        with self.assertRaises(Spotifice.PlaylistError) as cm:
            self.sut.load_playlist('bad-playlist-id')

        self.assertEqual(cm.exception.item, 'bad-playlist-id')

    def test_load_playlist_loads_first_track_stopped(self):
        self.sut.load_playlist(THREE)
        self.assert_current(TRACK_1S, playing=False)

    def test_load_playlist_keeps_playing(self):
        self.sut.load_track(TRACK_4S)
        self.sut.play()

        self.sut.load_playlist(THREE)
        self.assert_current(TRACK_1S, playing=True)

    def test_load_track_cancels_playlist(self):
        self.sut.load_playlist(THREE)
        self.sut.load_track(TRACK_4S)

        self.sut.next()
        self.assert_current(TRACK_4S, playing=False)


    def test_unbind_discards_playlist(self):
        self.sut.load_playlist(THREE)
        self.sut.unbind_media_provider()
        self.bind()

        self.sut.next()
        self.assert_current(TRACK_1S, playing=False)

    def test_bind_discards_playlist(self):
        self.sut.load_playlist(THREE)
        self.bind()

        self.sut.next()
        self.assert_current(TRACK_1S, playing=False)


class NextPreviousTests(RenderV2TestCase):
    def test_next_without_playlist_does_nothing(self):
        self.sut.load_track(TRACK_4S)
        self.sut.next()
        self.assert_current(TRACK_4S, playing=False)

    def test_previous_without_playlist_does_nothing(self):
        self.sut.load_track(TRACK_4S)
        self.sut.previous()
        self.assert_current(TRACK_4S, playing=False)

    def test_next_keeps_stopped(self):
        self.sut.load_playlist(THREE)
        self.sut.next()
        self.assert_current(TRACK_2S, playing=False)

    def test_next_keeps_playing(self):
        self.sut.load_playlist(THREE)
        self.sut.play()
        self.sut.next()
        self.assert_current(TRACK_2S, playing=True)

    def test_previous_keeps_state(self):
        self.sut.load_playlist(THREE)
        self.sut.next()
        self.sut.play()
        self.sut.previous()
        self.assert_current(TRACK_1S, playing=True)

    def test_previous_on_first_track_does_nothing(self):
        self.sut.load_playlist(THREE)
        self.sut.previous()
        self.assert_current(TRACK_1S, playing=False)

    def test_next_on_last_track_does_nothing(self):
        self.sut.load_playlist(THREE)
        self.sut.next()
        self.sut.next()
        self.sut.next()
        self.assert_current(TRACK_4S, playing=False)

    def test_next_on_last_track_with_repeat_wraps(self):
        self.sut.load_playlist(THREE)
        self.sut.set_repeat(True)
        self.sut.next()
        self.sut.next()
        self.sut.next()
        self.assert_current(TRACK_1S, playing=False)

    def test_statement_example(self):
        self.sut.load_playlist(THREE)
        self.sut.play()
        self.assert_current(TRACK_1S, playing=True)
        self.sut.next()
        self.assert_current(TRACK_2S, playing=True)
        self.sut.stop()
        self.assert_current(TRACK_2S, playing=False)
        self.sut.previous()
        self.assert_current(TRACK_1S, playing=False)
        self.sut.play()
        self.assert_current(TRACK_1S, playing=True)
        self.sut.set_repeat(enabled=True)
        self.sut.next()
        self.assert_current(TRACK_2S, playing=True)


class TrackEndTests(RenderV2TestCase):
    def test_single_track_stops_at_end(self):
        self.sut.load_track(TRACK_1S)
        self.sut.set_repeat(True)
        self.sut.play()

        self.wait_until(lambda: not self.player.is_playing())
        self.assert_current(TRACK_1S, playing=False)

    def test_playlist_advances_at_track_end(self):
        self.sut.load_playlist(THREE)
        self.sut.play()

        self.wait_until(lambda: self.sut.get_current_track().id == TRACK_2S)
        self.assert_current(TRACK_2S, playing=True)

    def test_playlist_stops_at_end_without_repeat(self):
        self.sut.load_playlist(SHORT)
        self.sut.next()
        self.sut.play()

        self.wait_until(lambda: not self.player.is_playing())
        self.assert_current(TRACK_1S, playing=False)

    def test_playlist_restarts_at_end_with_repeat(self):
        self.sut.load_playlist(TWO)
        self.sut.next()
        self.sut.set_repeat(True)
        self.sut.play()

        self.wait_until(lambda: self.sut.get_current_track().id == TRACK_2S)
        self.assert_current(TRACK_2S, playing=True)
