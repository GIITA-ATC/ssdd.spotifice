#!/usr/bin/env python3

import sys
from time import sleep

import Ice

Ice.loadSlice(f'-I{Ice.getSliceDir()} spotifice_v1.ice')
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


def print_status(render, step):
    status = render.get_status()
    title = status.current_track.title if status.current_track else None
    print(f"{step:<30} {status.state}, {title}, repeat={status.is_repeating}")


def main(ic):
    provider = get_proxy(ic, 'Spotifice.MediaProvider.Proxy', Spotifice.MediaProviderPrx)
    render = get_proxy(ic, 'Spotifice.MediaRender.Proxy', Spotifice.MediaRenderPrx)

    tracks = provider.get_all_tracks()
    track1, track2 = tracks[0].id, tracks[1].id

    render.bind_media_provider(provider)
    render.load_track(track1)
    print_status(render, "load_track(track1)")

    render.play()                    # PLAYING, track1
    print_status(render, "play()")
    sleep(5)

    render.load_track(track2)        # PLAYING, track2
    print_status(render, "load_track(track2)")
    sleep(5)

    render.pause()                   # PAUSED, track2
    print_status(render, "pause()")
    sleep(2)

    render.previous()                # PAUSED, track1
    print_status(render, "previous()")
    sleep(2)

    render.play()                    # PLAYING, track1
    print_status(render, "play()")
    sleep(5)

    render.set_repeat(enabled=True)  # track1 will repeat when it ends
    print_status(render, "set_repeat(enabled=True)")

    render.stop()                    # STOPPED, track1
    print_status(render, "stop()")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit("Usage: media_control.py --Ice.Config=<config-file>")

    with Ice.initialize(sys.argv) as communicator:
        main(communicator)
