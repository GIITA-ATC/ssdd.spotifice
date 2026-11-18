from datetime import datetime

from media_provider import Spotifice
from metadata import identify

from .test_provider import MEDIA, TestProvider

TRACK_1S = identify(MEDIA / '1s.mp3')
TRACK_2S = identify(MEDIA / '2s.mp3')
TRACK_4S = identify(MEDIA / '4s.mp3')


class PlaylistManagerTests(TestProvider):
    def test_get_all_playlists(self):
        playlists = self.sut.get_all_playlists()

        ids = sorted(p.id for p in playlists)
        self.assertEqual(ids, ['test-playlist-short', 'test-playlist-three',
                               'test-playlist-unknown'])

    def test_broken_playlist_file_is_skipped(self):
        ids = [p.id for p in self.sut.get_all_playlists()]
        self.assertNotIn('broken', ids)

    def test_get_playlist(self):
        playlist = self.sut.get_playlist('test-playlist-three')

        self.assertEqual(playlist.name, 'Three tracks')
        self.assertEqual(playlist.owner, 'UCLM ESI')
        self.assertEqual(playlist.track_ids, [TRACK_1S, TRACK_2S, TRACK_4S])

    def test_created_at_is_a_timestamp(self):
        playlist = self.sut.get_playlist('test-playlist-three')

        expected = int(datetime(2025, 9, 29).timestamp())
        self.assertEqual(playlist.created_at, expected)

    def test_unknown_tracks_are_skipped(self):
        playlist = self.sut.get_playlist('test-playlist-unknown')
        self.assertEqual(playlist.track_ids, [TRACK_2S, TRACK_1S])

    def test_get_playlist_wrong_id(self):
        with self.assertRaises(Spotifice.PlaylistError) as cm:
            self.sut.get_playlist('bad-playlist-id')

        self.assertEqual(cm.exception.item, 'bad-playlist-id')
        self.assertEqual(cm.exception.reason, 'Playlist not found')
