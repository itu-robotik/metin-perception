#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String, Float32MultiArray
from cv_bridge import CvBridge
import cv2
import numpy as np
import google.generativeai as genai
import os
from std_srvs.srv import Trigger

class PerceptionNode(Node):
    def __init__(self):
        super().__init__('perception_node')
        
        # Abonelikler ve Yayımcılar
        self.subscription = self.create_subscription(Image, '/camera', self.img_cb, 10)
        self.detect_pub = self.create_publisher(Float32MultiArray, '/perception/board_status', 10)
        self.analysis_pub = self.create_publisher(String, '/perception/poster_analysis', 10)
        self.debug_pub = self.create_publisher(Image, '/perception/debug_image', 10)
        
        # Servis
        self.srv = self.create_service(Trigger, 'analyze_poster', self.analyze_poster_callback)
        
        self.bridge = CvBridge()
        self.latest_img = None
        
        # Tracking
        self.last_cx = 0.0
        self.last_distance = 0.0
        self.last_yaw_err = 0.0
        self.last_marker_yaw = 0.0
        self.locked = False
        self.frames_without_target = 0
        
        # ArUco Setup
        # OpenCV 4.7+
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        self.aruco_params = cv2.aruco.DetectorParameters()
        self.detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.aruco_params)
        
        # Gemini Setup
        api_key = os.environ.get("GOOGLE_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            # API Key Kontrolü (Güvenli Loglama)
            masked_key = api_key[:5] + "..." + api_key[-3:]
            self.get_logger().info(f"🔑 API Key Yüklendi: {masked_key}")
            
            # En Stabil Model (2.5 yerine 1.5-flash kullanıyoruz)
            try:
                self.model = genai.GenerativeModel('gemini-2.5-flash')
                self.get_logger().info("✅ Gemini API Bağlandı (gemini-1.5-flash)!")
            except:
                self.model = genai.GenerativeModel('gemini-pro')
                self.get_logger().warn("⚠️ Flash Bulunamadı, gemini-pro kullanılıyor.")
        else:
            self.get_logger().error("❌ GOOGLE_API_KEY bulunamadı!")

    def img_cb(self, msg):
        try:
            cv_img = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            self.latest_img = cv_img.copy()
            
            debug_img = cv_img.copy()
            height, width, _ = cv_img.shape
            img_center_x = width // 2
            
            # ArUco Tespiti
            gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
            corners, ids, rejected = self.detector.detectMarkers(gray)
            
            found = 0.0
            cx = 0.0
            area = 0.0
            alignment_error = 0.0
            needs_forward = 0.0 # Bu artık marker_yaw olacak
            
            if ids is not None:
                poster_indices = np.where(ids == 0)[0]
                if len(poster_indices) > 0:
                    idx = poster_indices[0]
                    corners_params = corners[idx] 
                    
                    # Pose Estimation
                    camera_matrix = np.array([[554.25, 0, 320.0], [0, 554.25, 240.0], [0, 0, 1.0]], dtype=np.float32)
                    dist_coeffs = np.zeros((4,1))
                    marker_size = 0.2
                    obj_points = np.array([
                        [-marker_size/2, marker_size/2, 0],
                        [marker_size/2, marker_size/2, 0],
                        [marker_size/2, -marker_size/2, 0],
                        [-marker_size/2, -marker_size/2, 0]
                    ], dtype=np.float32)
                    
                    success, rvec, tvec = cv2.solvePnP(obj_points, corners_params[0], camera_matrix, dist_coeffs)
                    
                    if success:
                        distance = tvec[2][0]
                        yaw_err = np.arctan2(tvec[0][0], tvec[2][0])
                        
                        # Marker Yaw (Orientation)
                        rmat, _ = cv2.Rodrigues(rvec)
                        normal_vec = np.dot(rmat, np.array([0, 0, 1]).T)
                        marker_yaw = np.arctan2(normal_vec[0], normal_vec[2])

                        # Hafıza Güncelle
                        self.last_cx = float(np.mean(corners_params[0][:, 0]))
                        self.last_distance = float(distance)
                        self.last_yaw_err = float(yaw_err)
                        self.last_marker_yaw = float(marker_yaw)
                        self.frames_without_target = 0
                        self.locked = True
                        
                        # Çizim
                        cv2.drawFrameAxes(debug_img, camera_matrix, dist_coeffs, rvec, tvec, 0.1)
                        cv2.putText(debug_img, f"DIST: {distance:.2f}m", (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        
                        found = 1.0
                        cx = self.last_cx
                        area = self.last_distance
                        alignment_error = self.last_yaw_err
                        needs_forward = self.last_marker_yaw

            # Hafıza Modu
            if found == 0.0 and self.locked:
                self.frames_without_target += 1
                if self.frames_without_target < 20: 
                    found = 1.0
                    cx = self.last_cx
                    area = self.last_distance
                    alignment_error = self.last_yaw_err
                    needs_forward = self.last_marker_yaw
                    cv2.putText(debug_img, "MEMORY MODE", (320, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
                else:
                    self.locked = False

            cv2.putText(debug_img, f"Lock:{self.locked} Err:{alignment_error:.2f}", (10, 470), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.imshow("Robot Gozu (Perception)", debug_img)
            cv2.waitKey(1)

            # [found, cx, distance, yaw_error, marker_yaw]
            self.detect_pub.publish(Float32MultiArray(data=[found, cx, area, alignment_error, needs_forward]))
            try:
                self.debug_pub.publish(self.bridge.cv2_to_imgmsg(debug_img, "bgr8"))
            except: pass
            
        except Exception as e:
            self.get_logger().error(f"ImgCB Hatasi: {e}")

    def analyze_poster_callback(self, request, response):
        self.get_logger().info("📸 Poster Analizi İsteği Alındı!")
        
        if self.latest_img is None:
            response.success = False
            response.message = "Görüntü yok!"
            return response
            
        img_path = "/tmp/poster_capture.jpg"
        cv2.imwrite(img_path, self.latest_img)
        
        # Resmi Gemini'ye okunabilir formatta ver (PIL Image olarak)
        try:
            import PIL.Image
            pil_img = PIL.Image.open(img_path)
            
            prompt = """
            Analyze this noticeboard image from our robotics simulation.
            Extract all event titles, dates, and times visible on the poster.
            Provide the output in a clean list format.
            If the image is blurry or empty, describe exactly what you see.
            """
            
            self.get_logger().info("🤖 Gemini 2.5 Flash Modeli Cevaplıyor...")
            # Modeli tekrar tanımla (her çağrıda taze olsun) veya self.model kullan
            model = genai.GenerativeModel('gemini-2.5-flash')
            result = model.generate_content([prompt, pil_img])
            
            analysis_text = result.text
            
            # TERMİNALE BAS (Renkli)
            print("\n" + "█"*60)
            print("█" + " "*18 + "GEMINI 2.5 FLASH ANALIZ" + " "*19 + "█")
            print("█"*60)
            print(analysis_text)
            print("█"*60 + "\n")
            
            self.analysis_pub.publish(String(data=analysis_text))
            response.success = True
            response.message = "Analiz basarili."
            
        except Exception as e:
            self.get_logger().error(f"Hata: {str(e)}")
            print(f"\n❌ GEMINI HATASI: {str(e)}\nFallback 'gemini-pro' deneniyor...")
            try:
                model = genai.GenerativeModel('gemini-pro')
                result = model.generate_content([prompt, pil_img])
                print("\n✅ FALLBACK SONUCU:\n" + result.text + "\n")
                response.success = True
                response.message = "Fallback basarili."
            except Exception as e2:
                response.success = False
                response.message = f"Kritik Hata: {str(e2)}"
        
        return response

def main(args=None):
    rclpy.init(args=args)
    node = PerceptionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
