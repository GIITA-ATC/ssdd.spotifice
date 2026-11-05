#!/usr/bin/env python3

import logging
import signal
import sys
import threading
import uuid
from contextlib import contextmanager
from time import sleep

import Ice
from Ice import identityToString as id2str

from gst_player import GstPlayer

Ice.loadSlice(f'-I{Ice.getSliceDir()} spotifice_v1.ice')
import Spotifice  # type: ignore # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MediaRender")


class PlaybackHistory(list):
    """Loaded tracks, most recent last. The last one may be the loaded track."""

    def push(self, track):
        if not self or self[-1].id != track.id:
            self.append(track)
            self.show()

    def previous(self, loaded_track):
        tracks = self
        if tracks and loaded_track and tracks[-1].id == loaded_track.id:
            tracks = tracks[:-1]

        return tracks[-1] if tracks else None

    def back_to(self, track):
        size = len(self)
        while self[-1].id != track.id:
            self.pop()

        if len(self) != size:
            self.show()

    def clear(self):
        if not self:
            return

        super().clear()
        self.show()

    def show(self):
        "The whole history, numbered, every time it changes"
        tracks = [f"  {position}. {track.title}" for position, track in enumerate(self, start=1)]
        logger.info(("History:\n" + "\n".join(tracks)) if tracks else "History: empty")


class MediaRenderI(Spotifice.MediaRender):
    def __init__(self, player):
        self.player = player
        self.provider = None
        self.current_track = None
        self.repeat = False
        self.playback_state = Spotifice.PlaybackState.STOPPED
        self.history = PlaybackHistory()

    def ensure_player_stopped(self):
        if self.player.is_playing():
            raise Spotifice.PlayerError(reason="Already playing")

    def ensure_provider_bound(self):
        if not self.provider:
            raise Spotifice.BadReference(reason="No MediaProvider bound")

    # --- RenderConnectivity ---
    def bind_media_provider(self, media_provider, current=None):
        try:
            proxy = media_provider.ice_timeout(500)
            proxy.ice_ping()
        except Ice.ConnectionRefusedException as e:
            raise Spotifice.BadReference(reason=f"MediaProvider not reachable: {e}")

        self.provider = media_provider
        self.history.clear()
        logger.info(f"Bound to MediaProvider '{id2str(media_provider.ice_getIdentity())}'")

    def unbind_media_provider(self, current=None):
        try:
            self.stop(current)
        except Spotifice.PlayerError as e:
            logger.error(f"Unbinding despite stop failure: {e.reason}")

        self.provider = None
        self.history.clear()
        logger.info("Unbound MediaProvider")

    # --- ContentManager ---
    def load_track(self, track_id, current=None, *, with_history=True):
        self.ensure_provider_bound()

        try:
            with self.keep_playing_state(current):
                self.current_track = self.provider.get_track_info(track_id)

            logger.info(f"Current track set to: {self.current_track.title}")

        except Spotifice.TrackError as e:
            logger.error(f"Error setting track: {e.reason}")
            raise

        if with_history:
            self.history.push(self.current_track)

    def get_current_track(self, current=None):
        return self.current_track

    # --- PlaybackController ---
    @contextmanager
    def keep_playing_state(self, current):
        playing = self.player.is_playing()
        is_paused = self.player.get_state() == 'PAUSED'
        if playing:
            self.stop(current)
        try:
            yield
        finally:
            if playing:
                self.start_playing(current.id)

            if is_paused:
                self.pause(current)

    def play(self, current=None):
        assert current, "remote invocation required"

        if self.playback_state == Spotifice.PlaybackState.PAUSED:
            if not self.player.resume():
                raise Spotifice.PlayerError(reason="Failed to confirm resume")

            logger.info("Resumed")
            self.playback_state = Spotifice.PlaybackState.PLAYING

        else:  # state is STOPPED
            self.start_playing(current.id)

    def start_playing(self, render_id):
        self.ensure_provider_bound()

        if not self.current_track:
            raise Spotifice.TrackError(reason="No track loaded")

        self.ensure_player_stopped()

        try:
            self.provider.open_stream(render_id, self.current_track.id)
        except Spotifice.BadIdentity as e:
            logger.error(f"Error starting stream: {e.reason}")
            raise Spotifice.StreamError(reason="Strean setup failed")

        self.player.play(self.chunk_reader(render_id), self.on_track_exhausted(render_id))
        if not self.player.confirm_play_starts():
            raise Spotifice.PlayerError(reason="Failed to confirm playback")

        self.playback_state = Spotifice.PlaybackState.PLAYING

    def chunk_reader(self, render_id):
        provider = self.provider

        def read_chunk(chunk_size):
            try:
                return provider.get_chunk(render_id, chunk_size)
            except Spotifice.IOError as e:
                logger.error(f"Playback of track '{e.item}' aborted: {e.reason}")
            except Ice.Exception as e:
                logger.critical(e)

        return read_chunk

    def on_track_exhausted(self, render_id):
        provider = self.provider

        def close_stream():
            logger.info(f"Track exhausted: '{self.current_track.title}'")
            try:
                provider.close_stream(render_id)
            except Spotifice.StreamError as e:
                logger.error(f"Error closing stream: {e.reason}")

            self.playback_state = Spotifice.PlaybackState.STOPPED
            if self.repeat:
                logger.info("Repeating track")
                self.start_playing(render_id)

        return close_stream

    def stop(self, current=None):
        if self.provider and current:
            self.provider.close_stream(current.id)

        if not self.player.stop():
            raise Spotifice.PlayerError(reason="Failed to confirm stop")

        logger.info("Stopped")
        self.playback_state = Spotifice.PlaybackState.STOPPED

    def pause(self, current=None):
        if self.playback_state == Spotifice.PlaybackState.STOPPED:
            raise Spotifice.PlayerError(reason="Cannot pause when stopped")

        if self.playback_state == Spotifice.PlaybackState.PLAYING:
            if not self.player.pause():
                raise Spotifice.PlayerError(reason="Failed to confirm pause")

            logger.info("Paused")
            self.playback_state = Spotifice.PlaybackState.PAUSED
            return

        # playback_state is PAUSED, do nothing

    def get_status(self, current=None):
        return Spotifice.PlaybackStatus(
            state=self.playback_state,
            current_track=self.current_track,
            is_repeating=self.repeat
        )

    def previous(self, current=None):
        track = self.history.previous(self.current_track)
        if not track:
            logger.info("No previous track")
            return

        self.load_track(track.id, current, with_history=False)
        self.history.back_to(track)

    def set_repeat(self, enabled, current=None):
        self.repeat = enabled
        logger.info(f"Repeat mode set to: {self.repeat}")


def shutdown_on_interrupt(ic):
    def shutdown(*_):
        ic.shutdown()

    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGINT,  shutdown)
        signal.signal(signal.SIGTERM, shutdown)


def main(ic, player):
    shutdown_on_interrupt(ic)

    servant = MediaRenderI(player)

    properties = ic.getProperties()
    identity = properties.getPropertyWithDefault(
        'Spotifice.MediaRender.Identity',  str(uuid.uuid1()))

    adapter = ic.createObjectAdapter('Spotifice.MediaRenderAdapter')
    proxy = adapter.add(servant, ic.stringToIdentity(identity))
    logger.info(f"MediaRender: {proxy}")

    adapter.activate()
    while not ic.isShutdown():
        sleep(0.5)

    logger.info("Server shutdown.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: media_render.py --Ice.Config=<config-file>")

    with Ice.initialize(sys.argv) as communicator, GstPlayer() as player:
        main(communicator, player)
