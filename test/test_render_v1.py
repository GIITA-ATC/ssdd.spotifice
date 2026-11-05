import time

from media_render import Spotifice
from metadata import identify

from .icetest import pool_condition
from .test_render import MEDIA, TestRender

TRACK_1S = identify(MEDIA / '1s.mp3')
TRACK_2S = identify(MEDIA / '2s.mp3')
TRACK_4S = identify(MEDIA / '4s.mp3')


State = Spotifice.PlaybackState


class RenderV1TestCase(TestRender):

    def setUp(self):
        super().setUp()
        self.bind()

    def play_track(self, track_id):
        self.sut.load_track(track_id)
        self.sut.play()

    def assert_status(self, state, track_id):
        status = self.sut.get_status()
        self.assertEqual(status.state, state)
        self.assertEqual(status.current_track.id, track_id)

    def wait_until_stopped(self):
        stopped = pool_condition(
            lambda: self.sut.get_status().state == State.STOPPED,
            ntries=10, interval_secs=0.5)
        self.assertTrue(stopped, "Didn't stop after track end")


class PlaybackStatusTests(RenderV1TestCase):

    def test_get_status_default(self):
        status = self.sut.get_status()
        self.assertIsNone(status.current_track)
        self.assertFalse(status.is_repeating)
        self.assertEqual(status.state, State.STOPPED)

    def test_state_playing_confirmed(self):
        self.play_track(TRACK_4S)
        self.assert_status(State.PLAYING, TRACK_4S)

    def test_state_stopped(self):
        self.play_track(TRACK_4S)
        self.sut.stop()
        self.assert_status(State.STOPPED, TRACK_4S)

    def test_state_is_stopped_when_exhausted_track(self):
        self.play_track(TRACK_1S)
        self.wait_until_stopped()
        self.assert_status(State.STOPPED, TRACK_1S)

    def test_pause_and_resume(self):
        self.play_track(TRACK_4S)

        self.sut.pause()
        self.assert_status(State.PAUSED, TRACK_4S)

        self.sut.play()  # resume
        self.assert_status(State.PLAYING, TRACK_4S)

    def test_pause_without_track(self):
        with self.assertRaises(Spotifice.PlayerError) as cm:
            self.sut.pause()

        self.assertEqual(cm.exception.reason, "Cannot pause when stopped")

    def test_pause_is_idempotent(self):
        self.play_track(TRACK_4S)
        self.sut.pause()
        self.sut.pause()
        self.assert_status(State.PAUSED, TRACK_4S)

    def test_stop_while_paused(self):
        self.play_track(TRACK_4S)
        self.sut.pause()
        self.sut.stop()
        self.assert_status(State.STOPPED, TRACK_4S)


class LoadTrackTests(RenderV1TestCase):

    def setUp(self):
        super().setUp()
        self.sut.load_track(TRACK_4S)

    def test_load_track_dont_play_if_stopped(self):
        self.sut.load_track(TRACK_2S)
        self.assert_status(State.STOPPED, TRACK_2S)

    def test_load_track_plays_if_playing(self):
        self.sut.play()
        self.sut.load_track(TRACK_2S)
        self.assert_status(State.PLAYING, TRACK_2S)

    def test_load_track_keeps_paused(self):
        self.sut.play()
        self.sut.pause()
        self.sut.load_track(TRACK_2S)
        self.assert_status(State.PAUSED, TRACK_2S)

    def test_stop_then_play(self):
        self.sut.play()
        self.sut.load_track(TRACK_2S)

        self.sut.stop()
        self.assert_status(State.STOPPED, TRACK_2S)

        self.sut.play()
        self.assert_status(State.PLAYING, TRACK_2S)


class RepeatTests(RenderV1TestCase):

    def test_repeat_off_by_default(self):
        self.assertFalse(self.sut.get_status().is_repeating)

    def test_set_repeat_on(self):
        self.sut.set_repeat(True)
        self.assertTrue(self.sut.get_status().is_repeating)

    def test_set_repeat_off(self):
        self.sut.set_repeat(True)
        self.sut.set_repeat(False)
        self.assertFalse(self.sut.get_status().is_repeating)

    def test_repeat_plays_same_track(self):
        self.sut.load_track(TRACK_2S)
        self.sut.set_repeat(True)
        self.sut.play()

        time.sleep(2.5)  # wait for track to end and repeat
        self.assert_status(State.PLAYING, TRACK_2S)


class HistoryTests(RenderV1TestCase):

    def setUp(self):
        super().setUp()
        self.sut.load_track(TRACK_4S)

    def test_load_previous(self):
        self.sut.load_track(TRACK_2S)
        self.sut.previous()
        self.assert_status(State.STOPPED, TRACK_4S)

    def test_previous_without_history(self):
        self.sut.previous()
        self.assert_status(State.STOPPED, TRACK_4S)

    def test_previous_while_playing(self):
        self.sut.play()
        self.sut.load_track(TRACK_2S)
        self.sut.previous()
        self.assert_status(State.PLAYING, TRACK_4S)

    def test_previous_while_paused(self):
        self.sut.play()
        self.sut.pause()
        self.sut.load_track(TRACK_2S)
        self.sut.previous()
        self.assert_status(State.PAUSED, TRACK_4S)

    def test_previous_twice(self):
        self.sut.load_track(TRACK_2S)
        self.sut.load_track(TRACK_1S)
        self.sut.previous()
        self.assert_status(State.STOPPED, TRACK_2S)
        self.sut.previous()
        self.assert_status(State.STOPPED, TRACK_4S)

    def test_previous_discards_current_track(self):
        self.sut.load_track(TRACK_2S)
        self.sut.previous()
        self.sut.previous()
        self.assert_status(State.STOPPED, TRACK_4S)

    def test_reloading_current_track_is_not_stacked(self):
        self.sut.load_track(TRACK_2S)
        self.sut.load_track(TRACK_2S)
        self.sut.previous()
        self.assert_status(State.STOPPED, TRACK_4S)

    def test_load_after_previous(self):
        self.sut.load_track(TRACK_2S)
        self.sut.previous()
        self.sut.load_track(TRACK_1S)
        self.sut.previous()
        self.assert_status(State.STOPPED, TRACK_4S)

    def test_finished_track_is_stacked(self):
        self.sut.load_track(TRACK_1S)
        self.sut.play()
        self.wait_until_stopped()
        self.sut.load_track(TRACK_2S)
        self.sut.previous()
        self.assert_status(State.STOPPED, TRACK_1S)

    def test_bind_clears_history(self):
        self.sut.load_track(TRACK_2S)
        self.bind()
        self.sut.previous()
        self.assert_status(State.STOPPED, TRACK_2S)

    def test_unbind_clears_history(self):
        self.sut.load_track(TRACK_2S)
        self.sut.unbind_media_provider()
        self.bind()
        self.sut.previous()
        self.assert_status(State.STOPPED, TRACK_2S)
