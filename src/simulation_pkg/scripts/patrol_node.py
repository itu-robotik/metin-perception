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
        
        self.get_logger().info("🤖 Otonom Devriye v10.0 (PLANNER INTEGRATED) Hazir!")

    def analysis_done_callback(self, msg):
        self.get_logger().info("✅ Analiz Tamamlandı Mesajı Alındı. Durum IDLE yapılıyor.")
        self.state = "IDLE"
        self.target_locked = False # Yeni hedef arayabilir artik vizyon
        
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
    
    def goal_callback(self, msg):
        self.global_goal_x = msg.pose.position.x
        self.global_goal_y = msg.pose.position.y
        
        orientation = msg.pose.orientation
        self.global_goal_theta = euler_from_quaternion(orientation.x, orientation.y, orientation.z, orientation.w)
        
        self.has_global_goal = True
        self.target_locked = False # Yeni hedef, eski kilitleri unut
        self.state = "TRAVELING"
        self.get_logger().info(f"📨 Yeni Hedef Alındı: [{self.global_goal_x:.2f}, {self.global_goal_y:.2f}]")

    def vision_callback(self, msg): 
        # Sadece TRAVELING bitip docking asamasina gectigimizde vizyonu kullanalim
        # VEYA TRAVELING sirasinda hedef panoya yaklastigimizda
        if self.state not in ["TRAVELING", "SCANNING"]: 
            return 
            
        # Hedef panoya yakin miyiz? (3m menzil)
        if self.has_global_goal:
            dist_to_goal = math.sqrt((self.global_goal_x - self.robot_x)**2 + (self.global_goal_y - self.robot_y)**2)
            if dist_to_goal > 3.0: 
                return # Henuz uzagiz, vizyonu dikkate alma

        if self.target_locked: return 
        
        if len(msg.data) >= 5: 
            found = (msg.data[0] > 0.5)
            if found and self.odom_received:
                self.board_found = True
                dist = msg.data[2]
                yaw_err = msg.data[3]
                marker_yaw = msg.data[4]
                
                if dist < 4.0: 
                    global_angle_to_poster = self.robot_yaw - yaw_err
                    px = self.robot_x + (dist * math.cos(global_angle_to_poster))
                    py = self.robot_y + (dist * math.sin(global_angle_to_poster))
                    
                    self.poster_x = px
                    self.poster_y = py
                    
                    # DOCKING HESABI
                    poster_normal_angle = global_angle_to_poster + math.pi + marker_yaw
                    self.dock_x = px + (0.9 * math.cos(poster_normal_angle))
                    self.dock_y = py + (0.9 * math.sin(poster_normal_angle))
                    
                    self.target_locked = True
                    self.state = "NAVIGATE_TO_DOCK" # Hemen dockinga gec
                    self.get_logger().info(f"📍 PANO BULUNDU! Docking basliyor... Dist: {dist:.2f}m")

    def stop_robot(self):
        twist = Twist()
        self.cmd_pub.publish(twist)

    def navigate_to(self, tx, ty, final_yaw=None, tolerance=0.5):
        twist = Twist()
        dx = tx - self.robot_x
        dy = ty - self.robot_y
        dist = math.sqrt(dx*dx + dy*dy)
        target_angle = math.atan2(dy, dx)
        angle_diff = target_angle - self.robot_yaw
        
        # Aci normalizasyonu
        while angle_diff > math.pi: angle_diff -= 2*math.pi
        while angle_diff < -math.pi: angle_diff += 2*math.pi
        
        if dist < tolerance:
            # Hedefe vardik
            return True, twist
        
        # Basit P-Kontrol
        if abs(angle_diff) > 0.4:
            twist.linear.x = 0.0
            twist.angular.z = 0.6 if angle_diff > 0 else -0.6
        else:
            twist.linear.x = 0.4
            twist.angular.z = angle_diff * 1.5
            
        return False, twist

    def control_loop(self):
        if not self.odom_received: return
        
        if self.state == "IDLE":
            self.stop_robot()
        
        elif self.state == "TRAVELING":
            if not self.has_global_goal:
                self.state = "IDLE"
                return
            
            arrived, twist = self.navigate_to(self.global_goal_x, self.global_goal_y, self.global_goal_theta, tolerance=0.8)
            
            if arrived:
                self.get_logger().info("🏁 Global hedefe yaklaşıldı. Tarama yapılıyor...")
                self.stop_robot()
                self.state = "SCANNING"
                self.scan_start_time = time.time()
            else:
                self.cmd_pub.publish(twist)
                
        elif self.state == "SCANNING":
            # Hedefe geldik ama vizyon locklanmadiysa, biraz donup bakalim
            if self.target_locked:
                self.state = "NAVIGATE_TO_DOCK"
                return
                
            elapsed = time.time() - self.scan_start_time
            twist = Twist()
            
            if elapsed < 2.0: # Sağa dön
                twist.angular.z = 0.4
            elif elapsed < 6.0: # Sola dön
                twist.angular.z = -0.4
            else:
                # Bulamazsak da yapacak bir sey yok, IDLE olup yeni emir bekle
                self.state = "IDLE" 
                self.stop_robot()
                self.get_logger().warn("⚠️ Pano bulunamadı veya kilitlenilemedi.")
            
            self.cmd_pub.publish(twist)

        elif self.state == "NAVIGATE_TO_DOCK":
            arrived, twist = self.navigate_to(self.dock_x, self.dock_y, tolerance=0.10)
            
            # Docking icin daha hassas ve yavas olalim
            twist.linear.x = min(0.2, twist.linear.x) 
            
            if arrived:
                self.stop_robot()
                self.state = "ALIGN_TO_POSTER"
                self.get_logger().info("🏁 Dock Noktasına Varıldı.")
            else:
                self.cmd_pub.publish(twist)

        elif self.state == "ALIGN_TO_POSTER":
            # Postere Dön (Zaten navigasyon fonksiyonu mantigi ama sadece donus)
            dx = self.poster_x - self.robot_x
            dy = self.poster_y - self.robot_y
            target_angle = math.atan2(dy, dx)
            angle_diff = target_angle - self.robot_yaw
            while angle_diff > math.pi: angle_diff -= 2*math.pi
            while angle_diff < -math.pi: angle_diff += 2*math.pi
            
            twist = Twist()
            if abs(angle_diff) < 0.02:
                self.stop_robot()
                self.state = "ANALYZING"
                self.get_logger().info("📸 Analiz Başlıyor...")
                time.sleep(1.0)
                self.client.call_async(Trigger.Request())
            else:
                twist.angular.z = 0.3 if angle_diff > 0 else -0.3
                self.cmd_pub.publish(twist)
                
        elif self.state == "ANALYZING":
            # Callback (analysis_done_callback) gelene kadar bekle
            pass 

def main(args=None):
    rclpy.init(args=args)
    node = PatrolNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
