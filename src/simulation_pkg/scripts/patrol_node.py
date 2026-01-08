#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist
from std_msgs.msg import Float32MultiArray
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
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.client = self.create_client(Trigger, 'analyze_poster')
        
        # Robot Durumu
        self.robot_x = 0.0
        self.robot_y = 0.0
        self.robot_yaw = 0.0
        self.odom_received = False
        
        self.lidar_ranges = []
        self.board_found = False 
        
        # HAFIZA (Memory)
        self.target_locked = False
        self.dock_x = 0.0 
        self.dock_y = 0.0
        self.poster_x = 0.0 
        self.poster_y = 0.0
        
        self.state = "INITIAL_SCAN" 
        self.action_start_time = None
        self.scan_stage = 0
        
        # Son 1.0 metreyi yavaş gitmek için
        self.is_final_approach = False

        self.timer = self.create_timer(0.1, self.control_loop)
        self.get_logger().info("🤖 Otonom Devriye v9.0 (PERPENDICULAR DOCKING) Hazir!")

    def odom_callback(self, msg):
        self.robot_x = msg.pose.pose.position.x
        self.robot_y = msg.pose.pose.position.y
        orientation = msg.pose.pose.orientation
        self.robot_yaw = euler_from_quaternion(orientation.x, orientation.y, orientation.z, orientation.w)
        self.odom_received = True

    def lidar_callback(self, msg): 
        self.lidar_ranges = msg.ranges
    
    def vision_callback(self, msg): 
        if self.target_locked: return 
        
        if len(msg.data) >= 5: # [found, cx, dist, yaw_err, marker_yaw]
            found = (msg.data[0] > 0.5)
            if found and self.odom_received:
                self.board_found = True
                dist = msg.data[2]
                yaw_err = msg.data[3]
                marker_yaw = msg.data[4] # Marker yüzeyinin kameraya göre açısı
                
                if dist < 4.0: 
                    # 1. Posterin Global Konumu (Mevcut Yöntem)
                    # Robotun o anki baktığı yöne (robot_yaw) göre değil, 
                    # Marker'ın kamerada göründüğü açıya (robot_yaw - yaw_err) göre hesaplanmalı.
                    # NOT: Simülasyon kamerasında X ekseni sağ, Z ileri olduğu için dönüşümler:
                    # yaw_err: Merkeze göre sapma.
                    global_angle_to_poster = self.robot_yaw - yaw_err
                    
                    px = self.robot_x + (dist * math.cos(global_angle_to_poster))
                    py = self.robot_y + (dist * math.sin(global_angle_to_poster))
                    
                    self.poster_x = px
                    self.poster_y = py
                    
                    # 2. DOCKING NOKTASI (Dik Yaklaşım için)
                    # Posterin Yüzey Normalini Bulmamız Lazım.
                    # marker_yaw: Marker yüzeyinin kameraya göre açısı.
                    # Eğer marker_yaw ~0 ise tam karşıdan bakıyoruz.
                    # Posterin Global Açısı (Yüzeyinin baktığı yön)
                    # poster_face_angle = global_angle_to_poster - marker_yaw + PI
                    # Basit Trigonometri: Robot -> Poster vektörü + Marker dönüşü
                    
                    # Daha basit yaklaşım:
                    # Dock noktası, Poster'den "Poster Yüzey Normali" yönünde 0.9m uzakta olmalı.
                    # Posterin normali roughly = (Robot - Poster) açısı - marker_yaw ?
                    
                    # Robotun Postere Bakış Açısı (Global) = global_angle_to_poster
                    # Posterin Robota Bakış Açısı (Global) = global_angle_to_poster + PI
                    # Ama marker döndüyse (marker_yaw kadar), posterin normali de dönmüştür.
                    
                    # Posterin Normal Vektör Açısı (Global)
                    poster_normal_angle = global_angle_to_poster + math.pi + marker_yaw
                    
                    # Docking Point: Posterden Normal Vektör yönünde 0.9m git
                    self.dock_x = px + (0.9 * math.cos(poster_normal_angle))
                    self.dock_y = py + (0.9 * math.sin(poster_normal_angle))
                    
                    self.target_locked = True
                    self.get_logger().info(f"📍 HEDEF: [{px:.2f}, {py:.2f}] | YÜZEY AÇISI: {marker_yaw:.2f} | DOCK: [{self.dock_x:.2f}, {self.dock_y:.2f}]")

    def get_lidar_avg(self, angle_idx, width=10):
        if not self.lidar_ranges: 
            return 9.9
        total, count = 0, 0
        slen = len(self.lidar_ranges)
        for i in range(angle_idx - width, angle_idx + width):
            val = self.lidar_ranges[i % slen]
            if 0.1 < val < 10.0: 
                total += val
                count += 1
        return (total / count) if count > 0 else 9.9
    
    def stop_robot(self):
        twist = Twist()
        self.cmd_pub.publish(twist)

    def control_loop(self):
        if not self.odom_received: return
        twist = Twist()
        lidar_len = len(self.lidar_ranges)
        mid_idx = lidar_len // 2 if lidar_len > 0 else 0
        front = self.get_lidar_avg(mid_idx)

        # Durum Makinesi
        if self.state == "ANALYZING": 
            return 
        
        elif self.state == "INITIAL_SCAN":
            if self.target_locked:
                self.stop_robot()
                self.state = "NAVIGATE_TO_DOCK"
                self.get_logger().info("🚀 Dik Konumlandırma Başlıyor...")
                return

            if self.action_start_time is None:
                self.action_start_time = self.get_clock().now()
                self.scan_stage = 0

            elapsed = (self.get_clock().now() - self.action_start_time).nanoseconds / 1e9
            
            if self.scan_stage == 0: 
                twist.angular.z = 0.5
                if elapsed > 2.0: 
                    self.scan_stage = 1
                    self.action_start_time = self.get_clock().now()
            elif self.scan_stage == 1: 
                twist.angular.z = -0.5
                if elapsed > 4.0: 
                    self.stop_robot()
                    self.state = "WANDER"
                    self.get_logger().info("❌ Bulunamadı. Gezintiye çıkılıyor...")
            self.cmd_pub.publish(twist)

        elif self.state == "WANDER":
            if self.target_locked:
                self.stop_robot()
                self.state = "NAVIGATE_TO_DOCK"
                self.get_logger().info("🚀 Seyir Halinde Tespit Edildi!")
                return
            
            # Engelden Kaçış
            if front < 1.0: 
                twist.linear.x = 0.0
                twist.angular.z = 0.6
            else: 
                twist.linear.x = 0.4
                twist.angular.z = 0.0
            self.cmd_pub.publish(twist)

        elif self.state == "NAVIGATE_TO_DOCK":
            # Docking Noktasına Git
            dx = self.dock_x - self.robot_x
            dy = self.dock_y - self.robot_y
            dist = math.sqrt(dx*dx + dy*dy)
            target_angle = math.atan2(dy, dx)
            angle_diff = target_angle - self.robot_yaw
            while angle_diff > math.pi: angle_diff -= 2*math.pi
            while angle_diff < -math.pi: angle_diff += 2*math.pi
            
            self.get_logger().debug(f"NAVDOCK: Dist={dist:.2f}m")
            
            # VARIŞ (0.10m tolerans - Hassas)
            if dist < 0.10: 
                self.stop_robot()
                self.state = "ALIGN_TO_POSTER"
                self.get_logger().info("🏁 Dik Konuma Varıldı. Postere Dönülüyor...")
                return
            
            # HAREKET
            if abs(angle_diff) > 0.3: # Önce dön
                twist.linear.x = 0.0
                twist.angular.z = 0.6 if angle_diff > 0 else -0.6
            else:
                # Hem dön hem git
                twist.linear.x = min(0.35, dist * 0.5)
                twist.linear.x = max(0.1, twist.linear.x)
                twist.angular.z = angle_diff * 2.0
            self.cmd_pub.publish(twist)

        elif self.state == "ALIGN_TO_POSTER":
            # Postere Dön
            dx = self.poster_x - self.robot_x
            dy = self.poster_y - self.robot_y
            target_angle = math.atan2(dy, dx)
            angle_diff = target_angle - self.robot_yaw
            while angle_diff > math.pi: angle_diff -= 2*math.pi
            while angle_diff < -math.pi: angle_diff += 2*math.pi
            
            if abs(angle_diff) < 0.02: # Hassas Hizalama (<1 derece)
                self.stop_robot()
                self.state = "ANALYZING"
                self.get_logger().info("📸 Mükemmel Açı Yakalandı. Analiz Başlıyor...")
                time.sleep(1.0) # Kameranın oturması için bekle
                self.client.call_async(Trigger.Request())
                return
            
            twist.angular.z = 0.3 if angle_diff > 0 else -0.3
            self.cmd_pub.publish(twist)

def main(args=None):
    rclpy.init(args=args)
    node = PatrolNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
