import argparse
import asyncio
import json
import logging
import os
import platform
import ssl


from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack, VideoStreamTrack
from aiortc.contrib.media import MediaPlayer, MediaRelay
from aiortc.rtcrtpsender import RTCRtpSender

from aiortc.mediastreams import MediaStreamError
import cv2
import numpy as np
from av.video.frame import VideoFrame

ROOT = os.path.dirname(__file__)


relay = None
webcam = None
   
# Tạo lớp VideoStreamTrack để lưu trữ khung hình video
class CameraVideoTrack(VideoStreamTrack):
    """
    A video track that reads frames from a camera.
    """
    def __init__(self, device_id=0):
        super().__init__()        
        self.device_id = device_id
        self.cap = cv2.VideoCapture(self.device_id)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    async def recv(self):
        """
        Receive the next :class:`~av.video.frame.VideoFrame`.
        """
        # Read frame from camera
        ret, frame = self.cap.read()
        if not ret:
            raise MediaStreamError

        # Convert frame to VideoFrame
        pts, time_base = await self.next_timestamp()
        video_frame = VideoFrame.from_ndarray(frame, format="bgr24")
        video_frame.pts = pts
        video_frame.time_base = time_base

        return video_frame

    async def stop(self):
        """
        Stop the video track.
        """
        self.cap.release()
        await super().stop()


def force_codec(pc, sender, forced_codec):
    kind = forced_codec.split("/")[0]
    codecs = RTCRtpSender.getCapabilities(kind).codecs
    transceiver = next(t for t in pc.getTransceivers() if t.sender == sender)
    transceiver.setCodecPreferences(
        [codec for codec in codecs if codec.mimeType == forced_codec]
    )

# render index.html
async def index(request):
    content = open(os.path.join(ROOT, "index.html"), "r").read()
    return web.Response(content_type="text/html", text=content)


async def javascript(request):
    content = open(os.path.join(ROOT, "client.js"), "r").read()
    return web.Response(content_type="application/javascript", text=content)


async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    pc = RTCPeerConnection()
    pcs.add(pc)

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print("Connection state is %s" % pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()
            pcs.discard(pc)

    
    video = CameraVideoTrack('rtsp://admin:songnam@123@192.168.1.250/')
    #video = CameraVideoTrack('http://192.168.1.250/')


    if video:
        video_sender = pc.addTrack(video)
        if args.video_codec:
            force_codec(pc, video_sender, args.video_codec)
        elif args.play_without_decoding:
            raise Exception("You must specify the video codec using --video-codec")

    await pc.setRemoteDescription(offer)

    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.Response(
        content_type="application/json",
        text=json.dumps(
            {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
        ),
    )


pcs = set()


async def on_shutdown(app):
    # close peer connections
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WebRTC webcam demo")
    parser.add_argument("--cert-file", help="SSL certificate file (for HTTPS)")
    parser.add_argument("--key-file", help="SSL key file (for HTTPS)")
    parser.add_argument("--play-from", help="Read the media from a file and sent it."),
    parser.add_argument(
        "--play-without-decoding",
        help=(
            "Read the media without decoding it (experimental). "
            "For now it only works with an MPEGTS container with only H.264 video."
        ),
        action="store_true",
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host for HTTP server (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=8081, help="Port for HTTP server (default: 8080)"
    )
    parser.add_argument("--verbose", "-v", action="count")
    parser.add_argument(
        "--audio-codec", help="Force a specific audio codec (e.g. audio/opus)"
    )
    parser.add_argument(
        "--video-codec", help="Force a specific video codec (e.g. video/H264)"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if args.cert_file:
        ssl_context = ssl.SSLContext()
        ssl_context.load_cert_chain(args.cert_file, args.key_file)
    else:
        ssl_context = None

    app = web.Application()
    app.on_shutdown.append(on_shutdown)
    app.router.add_get("/", index)
    app.router.add_get("/client.js", javascript)
    app.router.add_post("/offer", offer)
    web.run_app(app, host=args.host, port=args.port, ssl_context=ssl_context)


# from onvif import ONVIFCamera
# import cv2
# import aiortc

# IP='192.168.0.103'   # Camera IP address
# PORT=8080           # Port
# USER=''         # Username
# PASS=''        # Password

# def create_frame(IP, PORT, USER , PASS):
#     camera = ONVIFCamera(IP, PORT, USER , PASS)

#     media_service = camera.create_media_service()

#     profiles = media_service.GetProfiles()

#     profile = profiles[0]

#     stream_uri = media_service.GetStreamUri({
#         'StreamSetup':{
#             'Stream':'RTP-Unicast',
#             'Transport': {
#                 'Protocol': 'RTSP',
#                 'Tunnel': None
#             }
#         },
#         'ProfileToken': profile.token
#     })

#     print(stream_uri)


#     # Set up the OpenCV video capture object
#     # cap = cv2.VideoCapture(stream_uri.Uri)
#     if len(USER)>0 and len(PASS)>0:
#         uri = stream_uri.Uri[:7]+USER+':'+PASS+'@'+stream_uri.Uri[7:]
#     else:
#         uri = stream_uri.Uri
#     print(uri)
#     cap = cv2.VideoCapture(uri)
#     print('after cap')
#     # Read frames from the video stream and display them
#     while True:
#         ret, frame = cap.read()
#         if not ret:
#             break
#         cv2.imshow('Video Stream', frame)
#         if cv2.waitKey(1) == ord('q'):
#             break

#     # Release the video capture object and close the window
#     cap.release()
#     cv2.destroyAllWindows()

# create_frame(IP, PORT, USER , PASS)