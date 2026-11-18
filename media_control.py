#!/usr/bin/env python3

import sys
from time import sleep

import Ice

Ice.loadSlice(f'-I{Ice.getSliceDir()} spotifice_v2.ice')
import Spotifice  # type: ignore # noqa: E402


def get_proxy(ic, property, cls):
    proxy = ic.propertyToProxy(property)

    for _ in range(5):
        try:
            proxy.ice_ping()
            break
        except Ice.ConnectionRefusedException:
            sleep(0.5)

    object = cls.checkedCast(proxy)
    if object is None:
        raise RuntimeError(f'Invalid proxy for {property}')

    return object


def print_current(render, step):
    track = render.get_current_track()
    title = track.title if track else None
    print(f"{step:<34} {title}")


def main(ic):
    provider = get_proxy(ic, 'Spotifice.MediaProvider.Proxy', Spotifice.MediaProviderPrx)
    render = get_proxy(ic, 'Spotifice.MediaRender.Proxy', Spotifice.MediaRenderPrx)

    playlists = provider.get_all_playlists()
    if not playlists:
        print("No playlists found.")
        return

    for p in playlists:
        print(f"- {p.name} ({p.id}): {len(p.track_ids)} tracks")

    playlist = provider.get_playlist(playlists[0].id)

    render.bind_media_provider(provider)
    render.load_playlist(playlist.id)      # stopped, track1
    print_current(render, "load_playlist(playlist.id)")

    render.play()                          # playing, track1
    print_current(render, "play()")
    sleep(5)

    render.next()                          # playing, track2
    print_current(render, "next()")
    sleep(5)

    render.stop()                          # stopped, track2
    print_current(render, "stop()")
    sleep(2)

    render.previous()                      # stopped, track1
    print_current(render, "previous()")

    render.play()                          # playing, track1
    print_current(render, "play()")
    sleep(5)

    render.set_repeat(enabled=True)        # the playlist will repeat when it ends
    render.next()                          # playing, track2
    print_current(render, "set_repeat(enabled=True), next()")

    # the playlist keeps playing...


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit("Usage: media_control.py --Ice.Config=<config-file>")

    with Ice.initialize(sys.argv) as communicator:
        main(communicator)
