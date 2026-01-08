# 🤖 ITU Noticeboard Patrol - Otonom Devriye Sistemi

## 📋 Proje Özeti

Bu proje, İTÜ kampüsünde otonom olarak devriye gezen ve ilan panolarını tespit edip analiz eden bir robot simülasyonudur. Sistem, ROS 2 Humble, Gazebo simülasyonu, OpenCV görüntü işleme ve Google Gemini AI entegrasyonu kullanır.

## ✨ Özellikler

### 🎯 Otonom Navigasyon
- **Lidar Tabanlı Hareket**: 360° lidar ile engel algılama ve güvenli navigasyon
- **Durum Makinesi**: WANDER → APPROACH → ALIGNING → ANALYZING döngüsü
- **Akıllı Davranış**: Pano arama, yaklaşma, hizalama ve geri dönüş

### 👁️ Görüntü İşleme
- **Renk Tabanlı Tespit**: Mavi pano çerçevelerini OpenCV ile algılama
- **Gerçek Zamanlı İşleme**: 30 Hz kamera görüntüsü analizi
- **Görsel Geri Bildirim**: "Robot Gözü" penceresi ile canlı görüntü

### 🧠 Yapay Zeka Analizi
- **Google Gemini 1.5 Flash**: Poster içerik analizi
- **JSON Çıktı**: Başlık, tarih, geçerlilik ve özet bilgileri
- **Servis Tabanlı**: ROS 2 servis çağrısı ile tetikleme

### 🏗️ Simülasyon
- **Gerçekçi Koridor**: Duvarlar, banklar ve ilan panoları
- **Direkli Robot**: Yüksekte kamera, tabanda lidar
- **Diferansiyel Sürüş**: İki tekerlekli hareket sistemi

## 📁 Proje Yapısı

```
itu_project_ws/
├── src/
│   ├── simulation_pkg/          # Simülasyon paketi (C++)
│   │   ├── launch/              # Launch dosyaları
│   │   │   └── simulation.launch.py
│   │   ├── worlds/              # Gazebo dünyaları
│   │   │   └── corridor.sdf
│   │   ├── models/              # Robot ve objeler
│   │   │   ├── my_robot/
│   │   │   │   └── model.sdf
│   │   │   └── poster_board/
│   │   │       └── materials/textures/poster.png
│   │   └── scripts/             # Python scriptleri
│   │       └── patrol_node.py
│   │
│   └── perception_pkg/          # Algılama paketi (Python)
│       └── perception_pkg/
│           └── gemini_node.py
│
├── CALISTIRMA_REHBERI.md       # Detaylı kullanım kılavuzu
├── basla.sh                     # Hızlı başlatma scripti
└── README.md                    # Bu dosya
```

## 🚀 Hızlı Başlangıç

### 1. Gereksinimler

```bash
# ROS 2 Humble ve Gazebo
sudo apt update
sudo apt install ros-humble-desktop ros-humble-ros-gz ros-humble-teleop-twist-keyboard

# Python kütüphaneleri
sudo apt install python3-pip
pip3 install google-generativeai opencv-python "numpy<2"
```

### 2. API Key Ayarlama

`~/.bashrc` dosyasına ekleyin:

```bash
export GOOGLE_API_KEY='YOUR_API_KEY_HERE'
export GZ_SIM_RESOURCE_PATH=$GZ_SIM_RESOURCE_PATH:$HOME/itu_robotics_ws/itu_project_ws/src/simulation_pkg/models
```

Sonra:
```bash
source ~/.bashrc
```

### 3. Derleme

```bash
cd ~/itu_robotics_ws/itu_project_ws
colcon build --symlink-install
source install/setup.bash
```

### 4. Çalıştırma

**Kolay Yol** - Interaktif script:
```bash
./basla.sh
```

**Manuel Yol** - 3 ayrı terminal:

**Terminal 1** (Simülasyon):
```bash
source ~/itu_robotics_ws/itu_project_ws/install/setup.bash
ros2 launch simulation_pkg simulation.launch.py
```

**Terminal 2** (Algılama):
```bash
source ~/itu_robotics_ws/itu_project_ws/install/setup.bash
ros2 run perception_pkg gemini_node
```

**Terminal 3** (Otonom Devriye):
```bash
source ~/itu_robotics_ws/itu_project_ws/install/setup.bash
ros2 run simulation_pkg patrol_node.py
```

## 🎮 Sistem Davranışı

1. **🔍 WANDER (Gezinme)**: Robot koridorda dolaşır, mavi pano arar
2. **🎯 APPROACH (Yaklaşma)**: Pano tespit edilince görsel takip ile yaklaşır
3. **📐 ALIGNING (Hizalama)**: Lidar ile panoya paralel hizalanır (±2cm tolerans)
4. **🧠 ANALYZING (Analiz)**: Gemini AI posteri analiz eder, JSON döner
5. **🔄 Geri Dönüş**: Analiz sonrası geri gider ve tekrar gezinmeye başlar

## 📡 ROS 2 Topic'ler

| Topic | Tip | Açıklama |
|-------|-----|----------|
| `/camera` | `sensor_msgs/Image` | Kamera görüntüsü (640x480, 30Hz) |
| `/scan` | `sensor_msgs/LaserScan` | Lidar verileri (360°, 10Hz) |
| `/cmd_vel` | `geometry_msgs/Twist` | Robot hareket komutları |
| `/perception/board_status` | `std_msgs/Float32MultiArray` | Pano tespit durumu [found, cx, area] |
| `/poster_analysis` | `std_msgs/String` | AI analiz sonuçları (JSON) |

## 🛠️ Servisler

| Servis | Tip | Açıklama |
|--------|-----|----------|
| `analyze_poster` | `std_srvs/Trigger` | Poster analizi tetikleme |

## 🔧 Parametreler

### Patrol Node
- `STOP_DISTANCE`: 1.3m (panoya yaklaşma mesafesi)
- `ALIGN_TOLERANCE`: 0.02m (hizalama toleransı)
- Kontrol döngüsü: 10Hz

### Perception Node
- Mavi renk aralığı: HSV [100,50,50] - [140,255,255]
- Minimum pano alanı: 500 piksel
- Kamera çözünürlüğü: 640x480

## 📊 Teknik Detaylar

### Robot Özellikleri
- **Boyutlar**: 0.4m x 0.3m x 1.0m (L x W x H)
- **Ağırlık**: 5 kg
- **Tekerlek Çapı**: 0.05m (5cm)
- **Tekerlek Aralığı**: 0.34m
- **Kamera Yüksekliği**: ~0.95m
- **Lidar Yüksekliği**: 0.15m

### Sensörler
- **Kamera**: 640x480, 30Hz, 1.1 rad FOV
- **Lidar**: GPU Lidar, 360 sample, 0.2-10m menzil

## 🐛 Sorun Giderme

### Gazebo açılmıyor
```bash
export GZ_SIM_RESOURCE_PATH=$GZ_SIM_RESOURCE_PATH:$HOME/itu_robotics_ws/itu_project_ws/src/simulation_pkg/models
```

### API Key hatası
```bash
export GOOGLE_API_KEY='YOUR_KEY'
```

### Poster görünmüyor
Dosya yolunu kontrol edin:
```bash
ls ~/itu_robotics_ws/itu_project_ws/src/simulation_pkg/models/poster_board/materials/textures/poster.png
```

### Robot hareket etmiyor
1. Tüm 3 terminal'in çalıştığından emin olun
2. Topic'leri kontrol edin: `ros2 topic list`
3. Mesajları kontrol edin: `ros2 topic echo /cmd_vel`

## 📚 Ek Kaynaklar

- [ROS 2 Humble Dokümantasyonu](https://docs.ros.org/en/humble/)
- [Gazebo Sim Dokümantasyonu](https://gazebosim.org/docs)
- [Google Gemini API](https://ai.google.dev/docs)

## 👥 Geliştirici Notları

### Yeni Poster Ekleme
1. PNG formatında poster oluştur
2. `models/poster_board/materials/textures/` klasörüne kopyala
3. `corridor.sdf` dosyasında texture path'i güncelle

### Parametreleri Değiştirme
- Hız ayarları: `patrol_node.py` içinde `twist.linear.x` ve `twist.angular.z`
- Renk tespiti: `gemini_node.py` içinde `cv2.inRange()` parametreleri
- Robot boyutları: `models/my_robot/model.sdf`

## 📝 Lisans

Bu proje eğitim amaçlı geliştirilmiştir.

## 🎓 İletişim

İTÜ Robotik Projesi
- Workspace: `~/itu_robotics_ws/itu_project_ws/`

---

**Son Güncelleme**: 7 Ocak 2026
**ROS 2 Sürümü**: Humble
**Gazebo Sürümü**: Harmonic (gz-sim)

🚀 **Başarılar!**
