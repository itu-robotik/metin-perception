#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String, Float32MultiArray
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from cv_bridge import CvBridge
import cv2
import numpy as np
import google.generativeai as genai
import os
import threading
import json
import datetime
from std_srvs.srv import Trigger

class PerceptionNode(Node):
    def __init__(self):
        super().__init__('perception_node')
        
        # Thread Lock ve UI Buffer
        self.lock = threading.Lock()
        self.visual_img = None 
        
        # Callback Group
        self.cb_group = ReentrantCallbackGroup()

        # Abonelikler ve Yayımcılar
        self.subscription = self.create_subscription(Image, '/camera', self.img_cb, 10, callback_group=self.cb_group)
        self.detect_pub = self.create_publisher(Float32MultiArray, '/perception/board_status', 10, callback_group=self.cb_group)
        self.analysis_pub = self.create_publisher(String, '/perception/poster_analysis', 10, callback_group=self.cb_group)
        self.debug_pub = self.create_publisher(Image, '/perception/debug_image', 10, callback_group=self.cb_group)
        
        # Servis
        self.srv = self.create_service(Trigger, 'analyze_poster', self.analyze_poster_callback, callback_group=self.cb_group)
        
        self.bridge = CvBridge()
        self.latest_img = None
        self.latest_board_id = -1
        
        # Tracking
        self.last_cx = 0.0
        self.last_distance = 0.0
        self.last_yaw_err = 0.0
        self.last_marker_yaw = 0.0
        self.locked = False
        self.frames_without_target = 0
        
        # Seçilen Model İsmi
        self.selected_model_name = None
        self.is_analyzing = False
        
        # ArUco Setup
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        self.aruco_params = cv2.aruco.DetectorParameters()
        self.detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.aruco_params)
        
        # Gemini Setup ve OTOMATİK MODEL SEÇİMİ
        api_key = os.environ.get("GOOGLE_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            masked_key = api_key[:5] + "..." + api_key[-3:]
            self.get_logger().info(f"🔑 API Key Yüklendi: {masked_key}")
            
            try:
                self.get_logger().info("🔍 Uygun Modeller Listeleniyor...")
                found_models = []
                for m in genai.list_models():
                    if 'generateContent' in m.supported_generation_methods:
                        found_models.append(m.name)
                
                self.get_logger().info(f"📋 Bulunan Modeller: {found_models}")
                
                # En iyisini seç: İçinde 'gemini' geçen, tercihen 'flash' veya 'pro'
                target_model = None
                
                # 1. Öncelik: Gemini Flash
                for m in found_models:
                    if 'gemini' in m and 'flash' in m:
                        target_model = m
                        break
                
                # 2. Öncelik: Gemini Pro
                if not target_model:
                    for m in found_models:
                        if 'gemini' in m and 'pro' in m:
                            target_model = m
                            break
                            
                # 3. Öncelik: Herhangi bir Gemini
                if not target_model:
                     for m in found_models:
                        if 'gemini' in m:
                            target_model = m
                            break
                
                if target_model:
                    self.selected_model_name = target_model
                    self.get_logger().info(f"✅ OTOMATIK SEÇİLEN MODEL: {self.selected_model_name}")
                    
                    # Test Bağlantısı
                    model = genai.GenerativeModel(self.selected_model_name)
                    resp = model.generate_content("Ping")
                    self.get_logger().info(f"🟢 BAĞLANTI OK: {resp.text}")
                else:
                    self.get_logger().error("❌ Hiçbir uygun Gemini modeli bulunamadı!")
            except Exception as e:
                self.get_logger().error(f"❌ MODEL SEÇİM HATASI: {str(e)}")
        else:
            self.get_logger().error("❌ GOOGLE_API_KEY bulunamadı!")

    def img_cb(self, msg):
        try:
            cv_img = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            self.latest_img = cv_img.copy()
            
            debug_img = cv_img.copy()
            gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
            corners, ids, rejected = self.detector.detectMarkers(gray)
            
            found = 0.0
            cx = 0.0
            area = 0.0
            alignment_error = 0.0
            needs_forward = 0.0 
            
            if ids is not None:
                # Sadece ID 0 degil, herhangi bir marker'i takip etsin
                # Ancak poster_indices mantigini koruyalim, simdilik ilk ID'yi alalim
                if len(ids) > 0:
                    # En buyuk alana sahip olani sec (daha yakin olandir)
                    # Basitlik icin ilkini aliyoruz
                    idx = 0 
                    self.latest_board_id = int(ids[idx][0]) # ID'yi kaydet
                    
                    corners_params = corners[idx] 
                    
                    camera_matrix = np.array([[554.25, 0, 320.0], [0, 554.25, 240.0], [0, 0, 1.0]], dtype=np.float32)
                    dist_coeffs = np.zeros((4,1))
                    marker_size = 0.2
                    obj_points = np.array([
                        [-marker_size/2, marker_size/2, 0], [marker_size/2, marker_size/2, 0],
                        [marker_size/2, -marker_size/2, 0], [-marker_size/2, -marker_size/2, 0]
                    ], dtype=np.float32)
                    
                    success, rvec, tvec = cv2.solvePnP(obj_points, corners_params[0], camera_matrix, dist_coeffs)
                    
                    if success:
                        distance = tvec[2][0]
                        yaw_err = np.arctan2(tvec[0][0], tvec[2][0])
                        
                        rmat, _ = cv2.Rodrigues(rvec)
                        normal_vec = np.dot(rmat, np.array([0, 0, 1]).T)
                        marker_yaw = np.arctan2(normal_vec[0], normal_vec[2])

                        self.last_cx = float(np.mean(corners_params[0][:, 0]))
                        self.last_distance = float(distance)
                        self.last_yaw_err = float(yaw_err)
                        self.last_marker_yaw = float(marker_yaw)
                        self.frames_without_target = 0
                        self.locked = True
                        
                        cv2.drawFrameAxes(debug_img, camera_matrix, dist_coeffs, rvec, tvec, 0.1)
                        cv2.putText(debug_img, f"ID: {self.latest_board_id} DIST: {distance:.2f}m", (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        
                        found = 1.0
                        cx = self.last_cx
                        area = self.last_distance
                        alignment_error = self.last_yaw_err
                        needs_forward = self.last_marker_yaw

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

            if self.is_analyzing:
                cv2.putText(debug_img, "YAPAY ZEKA DUSUNUYOR...", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            cv2.putText(debug_img, f"Lock:{self.locked} Err:{alignment_error:.2f}", (10, 470), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Gorseli UI thread icin kaydet
            with self.lock:
                self.visual_img = debug_img.copy()

            self.detect_pub.publish(Float32MultiArray(data=[found, cx, area, alignment_error, needs_forward]))
            try:
                self.debug_pub.publish(self.bridge.cv2_to_imgmsg(debug_img, "bgr8"))
            except: pass
            
        except Exception as e:
            self.get_logger().error(f"ImgCB Hatasi: {e}")

    def analyze_poster_callback(self, request, response):
        self.get_logger().info("📸 Poster Analizi İsteği Alındı!")
        self.is_analyzing = True
        
        if self.latest_img is None:
            response.success = False
            response.message = "Görüntü yok!"
            self.is_analyzing = False
            return response
            
        if not self.selected_model_name:
            response.success = False
            response.message = "Uygun Model Bulunamadı!"
            self.is_analyzing = False
            return response

        # OPTIMIZASYON: Resmi Küçült (Hızlandırmak için)
        resized_img = cv2.resize(self.latest_img, (640, 480))
        img_path = "/tmp/poster_capture.jpg"
        cv2.imwrite(img_path, resized_img, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        self.get_logger().info(f"📸 Resim Kaydedildi: {img_path} (640x480)")
        
        try:
            import PIL.Image
            pil_img = PIL.Image.open(img_path)
            
            today_date = datetime.date.today().strftime("%Y-%m-%d")
            
            prompt = f"""
            You are a smart robot assistant patrolling a university campus.
            Analyze this noticeboard image and extract event details.
            
            Current Date: {today_date}
            
            Return ONLY a valid JSON object. Do not use Markdown code blocks.
            Use exactly this schema:
            {{
              "title": "Event Title",
              "event_date": "YYYY-MM-DD",
              "status": "ok | expired | unclear",
              "is_expired": boolean,
              "summary": "Short summary of the poster"
            }}
            
            Rules:
            1. If the event date is in the past relative to {today_date}, set "status": "expired" and "is_expired": true.
            2. If the event date is today or future, set "status": "ok" and "is_expired": false.
            3. If no date is found, set "status": "unclear", "event_date": null, "is_expired": false.
            4. Convert text dates to YYYY-MM-DD format.
            5. "summary" should be brief (max 1 sentence).
            """
            
            self.get_logger().info(f"🤖 {self.selected_model_name} Modeli Cevaplıyor...")
            model = genai.GenerativeModel(self.selected_model_name)
            result = model.generate_content([prompt, pil_img])
            
            raw_text = result.text.strip()
            
            # Markdown temizleme (eger model ```json ... ``` gonderirse)
            if raw_text.startswith("```"):
                raw_text = raw_text.strip("`")
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:]
            
            raw_text = raw_text.strip()
            
            self.get_logger().info("\n" + "█"*60)
            self.get_logger().info(f"   {self.selected_model_name.upper()} RAW RESULT")
            self.get_logger().info("█"*60)
            self.get_logger().info(f"\n{raw_text}\n")
            self.get_logger().info("█"*60)

            # JSON Parsing ve Zenginlestirme
            try:
                data = json.loads(raw_text)
                
                # API Contract gereksinimlerini ekle
                data["board_id"] = self.latest_board_id if self.latest_board_id != -1 else 0
                data["is_duplicate"] = False # Perception node statelesstir, bunu Planner yonetir.
                data["gemini_raw_id"] = "generated-by-gemini"
                
                final_json = json.dumps(data)
                
                self.get_logger().info(f"✅ Gecerli JSON Olusturuldu: {final_json}")
                self.analysis_pub.publish(String(data=final_json))
                response.success = True
                response.message = "Analiz basarili ve JSON ayristirildi."
                
            except json.JSONDecodeError:
                self.get_logger().error("❌ JSON Parse Hatasi!")
                # Fallback: String olarak gonder ama contract'a uymaz :( 
                # Yine de bos bir JSON yapisi gonderelim ki sistem cokmesin
                fallback_data = {
                    "board_id": self.latest_board_id,
                    "title": "Parse Error",
                    "event_date": None,
                    "status": "unclear",
                    "is_expired": False,
                    "is_duplicate": False,
                    "summary": f"Raw output could not be parsed: {raw_text[:50]}..."
                }
                self.analysis_pub.publish(String(data=json.dumps(fallback_data)))
                response.success = False
                response.message = "Model valid JSON donmedi."
            
        except Exception as e:
            self.get_logger().error(f"Hata: {str(e)}")
            response.success = False
            response.message = f"Hata: {str(e)}"
            
            # Gelin genel hatada da bir JSON donelim ki sistem kilitlenmesin
            error_data = {
                "board_id": self.latest_board_id,
                "title": "System Error",
                "event_date": None,
                "status": "unclear",
                "is_expired": False,
                "is_duplicate": False,
                "summary": f"System error occurred: {str(e)}"
            }
            self.analysis_pub.publish(String(data=json.dumps(error_data)))
        
        self.is_analyzing = False
        return response

def main(args=None):
    rclpy.init(args=args)
    node = PerceptionNode()
    
    # Executor'u arka planda calistir (MultiThreaded)
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    
    # Spin thread'i baslat
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()
    
    # Ana thread sadece GUI guncellesin
    print("🖥️  GUI Ana Thread'de başlatıldı...")
    try:
        while rclpy.ok():
            with node.lock:
                if node.visual_img is not None:
                    cv2.imshow("Robot Gozu (Perception)", node.visual_img)
            
            key = cv2.waitKey(20) # 20ms bekle (50fps)
            if key == ord('q'):
                break
                
            # Thread yasiyor mu kontrol et
            if not spin_thread.is_alive():
                break
                
    except KeyboardInterrupt:
        pass
        
    node.destroy_node()
    rclpy.shutdown()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
