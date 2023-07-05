from flask import Flask, Response
import cv2 

app = Flask(__name__)

camera_url = 'rtsp://192.168.0.102:8080/h264_pcm.sdp'

def video_from_camera():
    # tạo đối tượng VideoCapture để kết nối lấy dữ liệu từ camera
    cap = cv2.VideoCapture(camera_url)
    if not cap.isOpened():
        print("Khong the ket noi den camera")
        return
    else :
        while True :
            # đọc các khung ảnh video từ cap
            ret , frame = cap.read()
            if not ret:
                print("fail to read cap")
                break
            # Ghi video vào file
            print("write file")

            _, img_encoded = cv2.imencode('.png', frame)
            frame = img_encoded.tobytes()

            yield (b'--frame\r\n'
                b'Content-Type: image/png\r\n\r\n' + frame + b'\r\n')
            
    # đóng kết nối đễn camera   
    cap.release()   

@app.route('/video')
def stream_video():
    return Response(video_from_camera(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    app.run()