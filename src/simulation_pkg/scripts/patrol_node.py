#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist, PoseStamped
from std_msgs.msg import Float32MultiArray, String
from std_srvs.srv import Trigger
import time
import math
import numpy as np

# Euler dönüşümü
def euler_from_quaternion(x, y, z, w):
    t3 = +2.0 * (w * z + x * y)
    t4 = +1.0 - 2.0 * (y * y + z * z)
    return math.atan2(t3, t4)
    
class PatrolNode(Node):
    def __init__(self):
        super().__init__('patrol_node') 
        self.lidar_sub = self.create_subscription(LaserScan, '/scan', self.lidar_callback, 10)
        self.vision_sub = self.create_subscription(Float32MultiArray, '/perception/board_status', self.vision_callback, 10)
        self.odom_sub = self.create_subscription(Odometry, '/odom', self.odom_callback, 10)
        self.goal_sub = self.create_subscription(PoseStamped, '/planner/goal', self.goal_callback, 10)
        
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.status_pub = self.create_publisher(String, '/patrol/status', 10)
        
        self.client = self.create_client(Trigger, 'analyze_poster')
        
        self.analysis_sub = self.create_subscription(String, '/perception/poster_analysis', self.analysis_done_callback, 10)
        # Robot Durumu
        self.robot_x = 0.0
        self.robot_y = 0.0
        self.robot_yaw = 0.0
        self.odom_received = False
        
        self.lidar_ranges = []
        self.board_found = False 
        
        # Hedef Bilgisi (Planner'dan gelen)
        self.has_global_goal = False
        self.global_goal_x = 0.0
        self.global_goal_y = 0.0
        self.global_goal_theta = 0.0
        
        # DOCKING / LOKAL HEDEF
        self.target_locked = False
        self.dock_x = 0.0 
        self.dock_y = 0.0
        self.poster_x = 0.0 
        self.poster_y = 0.0
        
        self.state = "IDLE" 
        self.timer = self.create_timer(0.1, self.control_loop)
        
        # Durum bildirimi icin ekstra timer
        self.status_timer = self.create_timer(1.0, self.publish_status)
        
        # Re-docking Prevention
        self.last_analysis_pos_x = -999.0
        self.last_analysis_pos_y = -999.0
        
        # Navigation Hysteresis
        self.turning_in_place = False
        
        self.get_logger().info("🤖 Otonom Devriye v10.0 (PLANNER INTEGRATED) Hazir!")

    def analysis_done_callback(self, msg):
        self.get_logger().info("✅ Analiz Tamamlandı Mesajı Alındı. Durum IDLE yapılıyor.")
        self.state = "IDLE"
        self.target_locked = False 
        
        # Son analiz yapilan pozisyonu kaydet (Re-docking engellemek icin)
        self.last_analysis_pos_x = self.robot_x
        self.last_analysis_pos_y = self.robot_y
        
    def publish_status(self):
        self.status_pub.publish(String(data=self.state))

    def odom_callback(self, msg):
        self.robot_x = msg.pose.pose.position.x
        self.robot_y = msg.pose.pose.position.y
        orientation = msg.pose.pose.orientation
        self.robot_yaw = euler_from_quaternion(orientation.x, orientation.y, orientation.z, orientation.w)
        self.odom_received = True

    def lidar_callback(self, msg): 
        self.lidar_ranges = msg.ranges
        self.scan_info = {
            'min': msg.angle_min,
            'max': msg.angle_max,
            'inc': msg.angle_increment
        }
    
    def goal_callback(self, msg):
        self.global_goal_x = msg.pose.position.x
        self.global_goal_y = msg.pose.position.y
        
        orientation = msg.pose.orientation
        self.global_goal_theta = euler_from_quaternion(orientation.x, orientation.y, orientation.z, orientation.w)
        
        self.has_global_goal = True
        self.target_locked = False # Yeni hedef, eski kilitleri unut
        self.state = "TRAVELING"
        self.get_logger().info(f"📨 Yeni Hedef Alındı: [{self.global_goal_x:.2f}, {self.global_goal_y:.2f}]")

    # Kamerasel ve Poster Sabitleri (Varsayilan A1 Pano: 59.4cm x 84.1cm)
    POSTER_WIDTH = 0.60 
    POSTER_HEIGHT = 0.85
    CAMERA_FX = 554.25
    CAMERA_CX = 320.0
    FRAME_WIDTH = 640
    FRAME_HEIGHT = 480
    
    def calculate_optimal_distance(self):
        # Yatay FOV (Radyan)
        # tan(fov_h / 2) = (W/2) / fx
        fov_h_half = math.atan((self.FRAME_WIDTH / 2.0) / self.CAMERA_FX)
        
        # Dikey FOV (Radyan) - Kare piksel varsayimi ile fx=fy
        fov_v_half = math.atan((self.FRAME_HEIGHT / 2.0) / self.CAMERA_FX)
        
        # Yatayda sigmasi icin gereken mesafe
        # distance = (ObjectSize / 2) / tan(fov / 2)
        dist_h = (self.POSTER_WIDTH / 2.0) / math.tan(fov_h_half)
        
        # Dikeyde sigmasi icin gereken mesafe
        dist_v = (self.POSTER_HEIGHT / 2.0) / math.tan(fov_v_half)
        
        # Hangisi daha buyukse onu al ki ikisi de sigsin
        optimal_dist = max(dist_h, dist_v)
        
        # Biraz marj payi (Orn: %10 daha geride dur)
        optimal_dist *= 1.1
        
        return optimal_dist

    def vision_callback(self, msg): 
        # Sadece TRAVELING bitip docking asamasina gectigimizde vizyonu kullanalim
        # VEYA TRAVELING sirasinda hedef panoya yaklastigimizda
        # VEYA NAVIGATE_TO_DOCK modundaysak surekli guncelleyelim
        if self.state not in ["TRAVELING", "SCANNING", "NAVIGATE_TO_DOCK"]: 
            return 
            
        if self.target_locked and self.state == "TRAVELING": return 
        
        # COOLDOWN KONTROLU (Eger NAVIGATE_TO_DOCK degilsek)
        if self.state != "NAVIGATE_TO_DOCK":
            dist_from_last = math.sqrt((self.robot_x - self.last_analysis_pos_x)**2 + (self.robot_y - self.last_analysis_pos_y)**2)
            if dist_from_last < 2.0:
                return

        if len(msg.data) >= 7: 
            found = (msg.data[0] > 0.5)
            # data indices: [found, cx, distance, yaw_err, marker_yaw, poster_cx_offset, poster_width_px]
            
            if found:
                self.board_found = True
                dist = msg.data[2]
                self.latest_visual_dist = dist # Save for control loop
                yaw_err = msg.data[3]
                marker_yaw = msg.data[4]
                self.visual_cx_offset = msg.data[5] # -1.0 to 1.0
                self.visual_poster_width = msg.data[6]
                
                # --- STATE TRANSITION TO DOCKING ---
                # Eger henuz docking modunda degilsek ve pano yakinimizdaysa
                if self.state in ["TRAVELING", "SCANNING"] and dist < 4.0:
                    # ArUco ile kaba yaklasma konumu hesapla (Transition icin)
                    global_angle_to_poster = self.robot_yaw - yaw_err
                    px = self.robot_x + (dist * math.cos(global_angle_to_poster))
                    py = self.robot_y + (dist * math.sin(global_angle_to_poster))
                    
                    self.poster_x = px
                    self.poster_y = py
                    
                    # Lock Target
                    self.target_locked = True
                    self.state = "NAVIGATE_TO_DOCK"
                    self.get_logger().info("📍 GÖRSEL KİLİTLENME! Visual Servoing Moduna Geçiliyor...")

    def stop_robot(self):
        twist = Twist()
        self.cmd_pub.publish(twist)

    def navigate_to(self, tx, ty, final_yaw=None, tolerance=0.1): 
        # Standart navigasyon (TRAVELING vb icin kalsin)
        # ... (Bu fonksiyon degismiyor, kodun geri kalaninda kullanilabilir)
        # ANCAK VISUAL SERVOING ICIN YENI MANTIK ASAGIDA CONTROL_LOOP ICINDE
        
        # Kod tekrari olmamasi icin burayi oldugu gibi birakiyoruz
        # Ama NAVIGATE_TO_DOCK artik burayi kullanmayacak.
        return self._navigate_impl(tx, ty, final_yaw, tolerance)

    def _navigate_impl(self, tx, ty, final_yaw, tolerance):
        # Eski navigate_to mantiginin kopyasi (Helper)
        twist = Twist()
        dx = tx - self.robot_x
        dy = ty - self.robot_y
        dist = math.sqrt(dx*dx + dy*dy)
        target_angle = math.atan2(dy, dx)
        angle_diff = target_angle - self.robot_yaw
        while angle_diff > math.pi: angle_diff -= 2*math.pi
        while angle_diff < -math.pi: angle_diff += 2*math.pi
        
        if dist < tolerance:
            if final_yaw is not None:
                yaw_diff = final_yaw - self.robot_yaw
                while yaw_diff > math.pi: yaw_diff -= 2*math.pi
                while yaw_diff < -math.pi: yaw_diff += 2*math.pi
                if abs(yaw_diff) < 0.1: return True, twist
                else:
                    twist.angular.z = 0.3 if yaw_diff > 0 else -0.3
                    return False, twist
            return True, twist
            
        turn_start_threshold = 0.5
        turn_stop_threshold = 0.2
        
        if not self.turning_in_place:
            if abs(angle_diff) > turn_start_threshold: self.turning_in_place = True
        else:
            if abs(angle_diff) < turn_stop_threshold: self.turning_in_place = False
            
        if self.turning_in_place:
            twist.linear.x = 0.0
            twist.angular.z = 0.4 if angle_diff > 0 else -0.4
        else:
            # Engel Kontrolu (Basit)
            safe = True
            if self.lidar_ranges:
                mid = len(self.lidar_ranges)//2
                checks = self.lidar_ranges[mid-10:mid+10]
                valid = [r for r in checks if 0.1<r<10]
                if valid and min(valid) < 0.35: safe = False
            
            if safe:
                speed = 0.35 if dist > 1.0 else 0.2
                if dist < 0.5: speed = 0.1
                twist.linear.x = speed
            else: twist.linear.x = 0.0
            
            ang_spd = max(min(angle_diff * 0.5, 0.5), -0.5)
            twist.angular.z = ang_spd
            
        return False, twist

    def control_loop(self):
        if not self.odom_received: return
        
        if self.state == "IDLE":
            self.stop_robot()
        
        elif self.state == "TRAVELING":
            if not self.has_global_goal:
                self.state = "IDLE"
                return
            arrived, twist = self._navigate_impl(self.global_goal_x, self.global_goal_y, None, 0.5)
            if arrived:
                self.get_logger().info("🏁 Global hedefe yaklaşıldı. Tarama yapılıyor...")
                self.stop_robot()
                self.state = "SCANNING"
                self.scan_start_time = time.time()
            else:
                self.cmd_pub.publish(twist)
                
        elif self.state == "SCANNING":
            if self.target_locked:
                self.state = "NAVIGATE_TO_DOCK"
                return
            
            angle_diff = self.global_goal_theta - self.robot_yaw
            while angle_diff > math.pi: angle_diff -= 2*math.pi
            while angle_diff < -math.pi: angle_diff += 2*math.pi
            
            twist = Twist()
            if abs(angle_diff) > 0.1:
                twist.angular.z = 0.5 if angle_diff > 0 else -0.5
                self.cmd_pub.publish(twist)
                self.scan_start_time = time.time()
            else:
                self.stop_robot()
                if (time.time() - self.scan_start_time) > 3.0:
                     if not self.target_locked:
                        self.get_logger().warn("⚠️ Pano gorulmedi. IDLE.")
                        self.state = "IDLE"
        
        elif self.state == "NAVIGATE_TO_DOCK":
            # --- VISUAL SERVOING CONTROLLER ---
            # Gorsel verilere gore hareket et
            # Hedef: 
            # 1. cx_offset -> 0 (Ortala)
            # 2. poster_width -> Hedef Genislik (Yakinlas) veya Distance -> 0.8m
            
            twist = Twist()
            
            # Guvenlik saati: Eger cok uzun sure kilitli kalirsa (kilitlenirse)
            # Simdilik es gecelim, basite odaklanalim
            
            # Veri var mi?
            if not hasattr(self, 'visual_cx_offset'):
                self.stop_robot()
                return

            # 1. AÇISAL KONTROL (P-Controller)
            K_ang = 0.8 
            err_ang = self.visual_cx_offset
            ang_z = -K_ang * err_ang
            ang_z = max(min(ang_z, 0.4), -0.4)
            if abs(err_ang) < 0.05: ang_z = 0.0

            # 2. DOĞRUSAL KONTROL (Pano Genisligi Bazli - Frame Icinde Tutma)
            # Hedef: Pano genisligi ekrani kaplamasin (Kenarlar gorunsun)
            # 640px genislik var. Hedefimiz 450px olsun (~%70 doluluk)
            target_width = 450.0 
            current_width = 0.0
            
            if hasattr(self, 'visual_poster_width') and self.visual_poster_width > 10:
                current_width = self.visual_poster_width
            
            # Eger width verisi yoksa veya cok kucukse (algilama bozuksa), ArUco mesafesine guvenelim
            dist_control_active = False
            
            if current_width > 10:
                err_width = target_width - current_width
                # Eger width < target -> Yaklas (Pozitif err)
                # Eger width > target -> Uzaklas (Negatif err)
                
                K_lin = 0.0015 # Pixel hatasini hiza cevir
                lin_x = K_lin * err_width
                
                # Cok yaklastiysak (Width > 550) sert dur/geri git
                if current_width > 550:
                    lin_x = -0.1
            else:
                # Fallback: ArUco Dist
                distance_to_target = 99.0
                if hasattr(self, 'latest_visual_dist'): distance_to_target = self.latest_visual_dist
                elif self.lidar_ranges: 
                    mid = len(self.lidar_ranges)//2
                    valid = [r for r in self.lidar_ranges[mid-5:mid+5] if 0.1<r<5.0]
                    if valid: distance_to_target = min(valid)
                
                # Hedef mesafe 1.2m (Daha guvenli, cerceve sigsin)
                lin_x = 0.2 * (distance_to_target - 1.2)
                self.get_logger().info(f"VS FALLBACK: Dist={distance_to_target:.2f}")

            # Hiz limitleri (Yavas yaklasim)
            lin_x = max(min(lin_x, 0.25), -0.1) 
            
            # KOMBINASYON
            twist.angular.z = float(ang_z)
            twist.linear.x = float(lin_x)
            
            self.get_logger().info(f"VS: Off={err_ang:.2f} Width={current_width:.0f} LinX={lin_x:.2f}")
            
            # BITIS KOSULU: Pixeller hedefteyse ve ortaladiysak
            # Width hatasi < 20px ve Angle hatasi < 0.05
            is_aligned_visual = (current_width > 10 and abs(lin_x) < 0.02 and abs(err_ang) < 0.05 and current_width > 400)
            is_aligned_dist = (current_width <= 10 and abs(lin_x) < 0.02 and abs(err_ang) < 0.1)
            
            if is_aligned_visual or is_aligned_dist:
                self.get_logger().info("🎯 Visual Docking Başarılı. Analiz Başlıyor...")
                self.stop_robot()
                self.state = "ANALYZING"
                time.sleep(1.0)
                self.client.call_async(Trigger.Request())
            else:
                self.cmd_pub.publish(twist)

        elif self.state == "ANALYZING":
            pass 

def main(args=None):
    rclpy.init(args=args)
    node = PatrolNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
