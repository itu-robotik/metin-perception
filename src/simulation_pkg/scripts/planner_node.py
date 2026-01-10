#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Int32
from geometry_msgs.msg import PoseStamped
import json
import os
import time
import math

class PlannerNode(Node):
    def __init__(self):
        super().__init__('planner_node')
        
        # 1. Memory Dosyasi Konumu
        self.memory_file = os.path.expanduser('~/itu_robotics_ws/itu_project_ws/board_memory.json')
        self.memory = self.load_memory()
        
        # 2. Pano Koordinatlari (Gazebo'daki Konumlar)
        # noticeboard_1: x=3, y=-1.9, theta=1.57 (90 deg - Y'ye bakiyor) -> Robot onunde durmak icin y biraz az almali
        # noticeboard_2: x=6, y=1.9, theta=-1.57 (-90 deg - -Y'ye bakiyor) 
        # noticeboard_3: x=9, y=-1.9, theta=1.57
        
        # Robotun duracagi noktalar (Pano merkezinden 1m geride)
        self.board_locations = {
            "1": {"x": 3.0, "y": -1.0, "theta": -1.57}, # Pano (3, -1.9), Robot (3, -1.0), -90 derece donuk
            "2": {"x": 6.0, "y": 1.0, "theta": 1.57},   # Pano (6, 1.9), Robot (6, 1.0), 90 derece donuk
            "3": {"x": 9.0, "y": -1.0, "theta": -1.57}  # Pano (9, -1.9), Robot (9, -1.0), -90 derece donuk
        }
        
        # 3. Yayin ve Abonelikler
        self.goal_pub = self.create_publisher(PoseStamped, '/planner/goal', 10)
        
        self.analysis_sub = self.create_subscription(String, '/perception/poster_analysis', self.analysis_callback, 10)
        self.status_sub = self.create_subscription(String, '/patrol/status', self.patrol_status_callback, 10)
        
        # 4. Durum Degiskenleri
        self.robot_state = "IDLE" # IDLE, MOVING, DOCKING, ANALYZING
        self.current_target_id = None
        self.plan_timer = self.create_timer(5.0, self.planning_loop)
        
        self.get_logger().info("🧠 Planner Node (MEMORY SYSTEM) Başlatıldı!")
        self.get_logger().info(f"📂 Hafiza Dosyasi: {self.memory_file}")

    def load_memory(self):
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r') as f:
                    return json.load(f)
            except:
                self.get_logger().warn("⚠️ Hafıza dosyası bozuk, yenisi oluşturuluyor.")
        
        # Varsayılan Yapı
        return {
            "boards": {
                "1": {"id": 1, "status": "unknown", "last_visit": 0, "visit_count": 0},
                "2": {"id": 2, "status": "unknown", "last_visit": 0, "visit_count": 0},
                "3": {"id": 3, "status": "unknown", "last_visit": 0, "visit_count": 0}
            },
            "history": []
        }

    def save_memory(self):
        with open(self.memory_file, 'w') as f:
            json.dump(self.memory, f, indent=2)
        # self.get_logger().info("💾 Hafıza Kaydedildi.")

    def analysis_callback(self, msg):
        self.get_logger().info(f"📨 Analiz Verisi Alındı: {msg.data[:50]}...")
        try:
            data = json.loads(msg.data)
            board_id = str(data.get("board_id", self.current_target_id))
            
            if board_id in self.memory["boards"]:
                board = self.memory["boards"][board_id]
                
                # Bilgileri Guncelle
                board["title"] = data.get("title", "Unknown")
                board["event_date"] = data.get("event_date", None)
                board["status"] = data.get("status", "unknown")
                board["is_expired"] = data.get("is_expired", False)
                board["last_visit"] = time.time()
                board["visit_count"] += 1
                
                # History'ye ekle
                entry = {
                    "timestamp": time.time(),
                    "board_id": board_id,
                    "analysis": data
                }
                self.memory["history"].append(entry)
                
                self.save_memory()
                self.get_logger().info(f"💾 Pano {board_id} Hafızası Güncellendi! Status: {board['status']}")
                
                # Analiz bitti, robot bosa cikti sayabiliriz (Patrol node IDLE'a donecek)
                self.robot_state = "IDLE"
                self.current_target_id = None 
                
        except json.JSONDecodeError:
            self.get_logger().error("❌ JSON Decode Hatasi!")

    def patrol_status_callback(self, msg):
        # Patrol Node'dan gelen durum bilgisi (bunu patrol node'a ekleyecegiz)
        self.robot_state = msg.data

    def planning_loop(self):
        # Eger robot mesgulse emir verme
        if self.robot_state != "IDLE":
            # self.get_logger().info(f"⏳ Robot meşgul ({self.robot_state}), bekleniyor...")
            return

        target_id = None
        
        # Strateji 1: Sorunlu Panolar (Expired / Unclear) - Öncelikli
        # Ama cok sık gitmemek icin son ziyaretten en az 60sn gecmeli
        now = time.time()
        
        for bid, info in self.memory["boards"].items():
            if info["status"] in ["expired", "unclear", "unknown"]:
                if (now - info["last_visit"]) > 60:
                    target_id = bid
                    self.get_logger().info(f"🚨 ÖNCELİK: Pano {bid} durumu '{info['status']}'. İncelenmeye gidiliyor.")
                    break
        
        # Strateji 2: Round Robin (Sırayla Hepsini Gez)
        if target_id is None:
            # En eski ziyaret edilene git
            oldest_time = float('inf')
            for bid, info in self.memory["boards"].items():
                if info["last_visit"] < oldest_time:
                    oldest_time = info["last_visit"]
                    target_id = bid
            
            self.get_logger().info(f"🔄 DEVRİYE: Pano {target_id} en eski ziyaret. Oraya gidiliyor.")

        if target_id:
            self.send_goal(target_id)

    def send_goal(self, board_id):
        if board_id not in self.board_locations:
            self.get_logger().error(f"❌ Pano {board_id} koordinatları bilinmiyor!")
            return

        target = self.board_locations[board_id]
        
        msg = PoseStamped()
        msg.header.frame_id = "map"
        msg.header.stamp = self.get_clock().now().to_msg()
        
        msg.pose.position.x = float(target["x"])
        msg.pose.position.y = float(target["y"])
        msg.pose.position.z = 0.0
        
        # Theta -> Quaternion
        theta = float(target["theta"])
        msg.pose.orientation.z = math.sin(theta / 2.0)
        msg.pose.orientation.w = math.cos(theta / 2.0)
        
        self.goal_pub.publish(msg)
        self.current_target_id = board_id
        # self.robot_state = "MOVING" # BUG FIX: Patrol Node zaten status update gonderecek.
        # Biz burada direkt MOVING yaparsak ve Patrol hemen yanit vermezse senkron kopabilir.
        # Ama asil sorun patrol node analiz bittikten sonra "IDLE" donmuyorsa burasi kilitli kalir.
        
        self.get_logger().info(f"🚀 HEDEF GÖNDERİLDİ: Pano {board_id} @ [{target['x']}, {target['y']}]")

def main(args=None):
    rclpy.init(args=args)
    node = PlannerNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
