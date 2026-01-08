# 🐛 Bilinen Sorunlar ve Çözümleri

## 1. ❌ Gemini API Hatası (404 Model Not Found)

### Sorun
```
404 models/gemini-1.5-flash is not found for API version v1beta
```

### ✅ Çözüm
Model adı `gemini-1.5-flash-latest` olarak güncellendi.

**Eğer hala sorun yaşıyorsanız**, alternatif modeller:
- `gemini-pro-vision` (eski ama stabil)
- `gemini-1.5-pro-latest` (daha güçlü)

`gemini_node.py` dosyasında satır 22'yi değiştirin:
```python
self.model = genai.GenerativeModel('gemini-pro-vision')
```

---

## 2. 🤸 Robot Takla Atıyor

### Sorun
Robot hareket ederken devrilip takla atıyor.

### ✅ Çözüm
Robot modeli güncellendi:
- Kütle: 5kg → 15kg
- Ağırlık merkezi alçaltıldı
- İnertia değerleri artırıldı
- Tekerleklere inertia eklendi

**Eğer hala devriliyorsa**:
1. Hızı azaltın (`patrol_node.py`):
   ```python
   twist.linear.x = 0.2  # Varsayılan: 0.4
   twist.angular.z = 0.3  # Varsayılan: 0.6
   ```

2. Veya robotu daha ağır yapın (`model.sdf`):
   ```xml
   <mass>20.0</mass>  <!-- 15.0'dan artırın -->
   ```

---

## 3. ⬛ Gazebo Sahnesi Siyah

### Sorun
Gazebo açılıyor ama sahne tamamen siyah, hiçbir şey görünmüyor.

### ✅ Çözüm 1: Render Engine Değiştir
World dosyasında Ogre2 yerine Ogre kullanın.

`corridor.sdf` dosyasında satır 6'yı değiştirin:
```xml
<!-- Eski -->
<plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors"><render_engine>ogre2</render_engine></plugin>

<!-- Yeni -->
<plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors"><render_engine>ogre</render_engine></plugin>
```

### ✅ Çözüm 2: Grafik Sürücüsü
```bash
# OpenGL bilgisini kontrol et
glxinfo | grep "OpenGL version"

# Eğer sorun devam ederse, software rendering kullan
export LIBGL_ALWAYS_SOFTWARE=1
ros2 launch simulation_pkg simulation.launch.py
```

### ✅ Çözüm 3: Gazebo Cache Temizle
```bash
rm -rf ~/.gz/sim/
rm -rf ~/.gz/rendering/
```

### ✅ Çözüm 4: Işık Ekle
Bazen ışık yeterli olmuyor. `corridor.sdf` dosyasına ek ışık ekleyin (satır 10'dan sonra):
```xml
<light type="point" name="extra_light">
  <pose>5 0 5 0 0 0</pose>
  <diffuse>1 1 1 1</diffuse>
  <specular>0.5 0.5 0.5 1</specular>
  <attenuation>
    <range>50</range>
  </attenuation>
</light>
```

---

## 4. 🖼️ Poster Görünmüyor

### Sorun
```
[Err] Unable to find file [model://poster_board/materials/textures/poster.png]
```

### ✅ Çözüm
Launch dosyası güncellendi, `GZ_SIM_RESOURCE_PATH` otomatik ayarlanıyor.

**Manuel kontrol**:
```bash
# Dosyanın varlığını kontrol et
ls -lh ~/itu_robotics_ws/itu_project_ws/src/simulation_pkg/models/poster_board/materials/textures/poster.png

# Yeniden build et
cd ~/itu_robotics_ws/itu_project_ws
colcon build --symlink-install
```

---

## 5. 🐍 Python Version Warning

### Sorun
```
FutureWarning: You are using a Python version (3.10.12) which Google will stop supporting
```

### ✅ Çözüm
Bu sadece bir uyarı, sistem çalışır. Görmezden gelebilirsiniz.

**Kalıcı çözüm** (opsiyonel):
```bash
# Python 3.11+ yükleyin
sudo apt install python3.11 python3.11-venv
```

---

## 6. ⚠️ Qt Wayland Plugin Warning

### Sorun
```
qt.qpa.plugin: Could not find the Qt platform plugin "wayland" in ""
```

### ✅ Çözüm
Bu da sadece bir uyarı, OpenCV penceresi açılır. Görmezden gelebilirsiniz.

**Kalıcı çözüm** (opsiyonel):
```bash
export QT_QPA_PLATFORM=xcb
```

---

## 7. 📡 Topic'ler Yayınlanmıyor

### Sorun
`/camera`, `/scan` veya `/cmd_vel` topic'leri görünmüyor.

### ✅ Çözüm
```bash
# Bridge'in çalıştığını kontrol et
ros2 node list | grep bridge

# Topic'leri listele
ros2 topic list

# Eğer yoksa, bridge'i manuel başlat
ros2 run ros_gz_bridge parameter_bridge /camera@sensor_msgs/msg/Image@gz.msgs.Image
```

---

## 8. 🤖 Robot Hareket Etmiyor

### Sorun
Otonom devriye çalışıyor ama robot hareket etmiyor.

### ✅ Çözüm
```bash
# cmd_vel topic'ini kontrol et
ros2 topic echo /cmd_vel

# Manuel hareket testi
ros2 run teleop_twist_keyboard teleop_twist_keyboard

# Diff drive plugin'in yüklendiğini kontrol et
gz topic -l | grep cmd_vel
```

---

## 9. 🔴 Pano Tespit Edilmiyor

### Sorun
Robot panoyu görmüyor, algılama çalışmıyor.

### ✅ Çözüm
```bash
# Kamera görüntüsünü kontrol et
ros2 topic echo /camera --once

# Algılama durumunu kontrol et
ros2 topic echo /perception/board_status

# OpenCV penceresini kontrol et
# "Robot Gozu" penceresi açık mı? Mavi çerçeve görünüyor mu?
```

**Renk aralığını ayarlayın** (`gemini_node.py` satır 51):
```python
# Mavi için daha geniş aralık
mask = cv2.inRange(hsv, np.array([90, 40, 40]), np.array([150, 255, 255]))
```

---

## 🆘 Hızlı Sorun Giderme Checklist

1. ✅ Build başarılı mı?
   ```bash
   cd ~/itu_robotics_ws/itu_project_ws && colcon build
   ```

2. ✅ Setup sourced mı?
   ```bash
   source ~/itu_robotics_ws/itu_project_ws/install/setup.bash
   ```

3. ✅ 3 terminal de çalışıyor mu?
   - Terminal 1: Gazebo simülasyonu
   - Terminal 2: Perception node
   - Terminal 3: Patrol node

4. ✅ API Key ayarlı mı?
   ```bash
   echo $GOOGLE_API_KEY
   ```

5. ✅ Topic'ler yayınlanıyor mu?
   ```bash
   ros2 topic list
   ```

---

## 📞 Destek

Sorun devam ediyorsa:
1. Terminal çıktılarını kontrol edin
2. `ros2 topic list` ile topic'leri kontrol edin
3. `ros2 node list` ile node'ları kontrol edin
4. Log dosyalarını inceleyin: `~/.ros/log/`

---

**Son Güncelleme**: 7 Ocak 2026, 22:53
**Durum**: Aktif geliştirme - Sorunlar çözülüyor 🔧
