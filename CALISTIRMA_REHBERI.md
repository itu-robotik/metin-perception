# ITU Noticeboard Patrol - Çalıştırma Rehberi

## Sistem Gereksinimleri

✅ ROS 2 Humble
✅ Gazebo (gz-sim)
✅ Python 3
✅ OpenCV
✅ Google Generative AI (Gemini)

## Kurulum Tamamlandı! ✨

Tüm dosyalar başarıyla oluşturuldu:
- ✅ Robot modeli (direkli kamera sistemi)
- ✅ Simülasyon dünyası (koridor + pano)
- ✅ Otonom devriye kodu
- ✅ Görüntü işleme ve AI analiz sistemi
- ✅ Launch dosyaları

## Çalıştırma Adımları

### Terminal 1: Simülasyon Başlatma
```bash
source ~/itu_robotics_ws/itu_project_ws/install/setup.bash
ros2 launch simulation_pkg simulation.launch.py
```

Bu terminal:
- Gazebo simülasyonunu başlatır
- Robotu spawn eder
- ROS 2 - Gazebo bridge'i çalıştırır

### Terminal 2: Algılama ve AI Sistemi
```bash
source ~/itu_robotics_ws/itu_project_ws/install/setup.bash
ros2 run perception_pkg gemini_node
```

Bu terminal:
- Kamera görüntüsünü işler
- Mavi panoları tespit eder
- Gemini AI ile poster analizi yapar
- "Robot Gozu" penceresi açar (görüntü gösterir)

### Terminal 3: Otonom Devriye Sistemi
```bash
source ~/itu_robotics_ws/itu_project_ws/install/setup.bash
ros2 run simulation_pkg patrol_node.py
```

Bu terminal:
- Robotun otonom hareketini kontrol eder
- Pano arama, yaklaşma, hizalama ve analiz durumlarını yönetir

## Sistem Davranışı

1. **WANDER (Gezinme)**: Robot koridorda dolaşır, pano arar
2. **APPROACH (Yaklaşma)**: Mavi pano tespit edilince yaklaşır
3. **ALIGNING (Hizalama)**: Lidar ile panoya paralel hizalanır
4. **ANALYZING (Analiz)**: Gemini AI posteri analiz eder
5. **Geri Dönüş**: Analiz sonrası geri gider ve tekrar gezinmeye başlar

## Önemli Topic'ler

- `/camera` - Kamera görüntüsü
- `/scan` - Lidar verileri
- `/cmd_vel` - Robot hareket komutları
- `/perception/board_status` - Pano tespit durumu
- `/poster_analysis` - AI analiz sonuçları

## Servisler

- `analyze_poster` - Poster analizi tetikleme servisi

## Sorun Giderme

### Gazebo açılmıyorsa:
```bash
export GZ_SIM_RESOURCE_PATH=$GZ_SIM_RESOURCE_PATH:$HOME/itu_robotics_ws/itu_project_ws/src/simulation_pkg/models
```

### API Key hatası alıyorsanız:
```bash
export GOOGLE_API_KEY='YOUR_API_KEY_HERE'
```

### Poster görünmüyorsa:
Poster dosyasının doğru konumda olduğundan emin olun:
`~/itu_robotics_ws/itu_project_ws/src/simulation_pkg/models/poster_board/materials/textures/poster.png`

## Manuel Kontrol (Opsiyonel)

Otonom sistemi kapatıp manuel kontrol için:
```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

## Sistem Özellikleri

🤖 **Otonom Navigasyon**: Lidar tabanlı engel algılama
👁️ **Görüntü İşleme**: OpenCV ile mavi pano tespiti
🧠 **AI Analiz**: Google Gemini ile poster içerik analizi
📐 **Hassas Hizalama**: Lidar ile paralel hizalama
🔄 **Durum Makinesi**: Akıllı davranış kontrolü

## Geliştirme Notları

- Robot yüksekliği: ~1m (kamera tepede)
- Lidar: 360 derece, 10Hz
- Kamera: 640x480, 30Hz
- Hizalama toleransı: 2cm
- Durma mesafesi: 1.3m

---

**Proje Konumu**: `~/itu_robotics_ws/itu_project_ws/`

Başarılar! 🚀
