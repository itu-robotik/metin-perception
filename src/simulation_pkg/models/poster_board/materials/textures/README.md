# 📸 Poster Klasörü

Bu klasör, simülasyonda görünecek poster görsellerini içerir.

## 📁 Klasör Yapısı

```
poster_board/
├── model.config          # Gazebo model yapılandırması
├── model.sdf            # Model tanımı (mavi çerçeve + poster)
└── materials/
    └── textures/
        └── poster.png   # POSTER RESMİNİZİ BURAYA KOYUN
```

## 🖼️ Poster Ekleme

### Yöntem 1: Mevcut Posteri Değiştirme
Kendi poster görselinizi bu klasöre `poster.png` adıyla kopyalayın:

```bash
cp /yol/to/poster_resminiz.png ~/itu_robotics_ws/itu_project_ws/src/simulation_pkg/models/poster_board/materials/textures/poster.png
```

### Yöntem 2: Direkt Kopyalama
```bash
cd ~/itu_robotics_ws/itu_project_ws/src/simulation_pkg/models/poster_board/materials/textures/
# Eski posteri yedekle (opsiyonel)
mv poster.png poster_backup.png
# Yeni posteri kopyala
cp /path/to/your/poster.png ./poster.png
```

## 📐 Önerilen Poster Özellikleri

- **Format**: PNG (şeffaflık destekli)
- **Oran**: Dikey/Portrait (örn: 3:4 veya 2:3)
- **Çözünürlük**: En az 800x1000 piksel
- **Boyut**: Maksimum 2MB (simülasyon performansı için)

## 🔄 Değişiklikleri Uygulama

Poster değiştirdikten sonra:

1. **Yeniden build edin** (symlink kullanıldığı için genelde gerekmez):
   ```bash
   cd ~/itu_robotics_ws/itu_project_ws
   colcon build --symlink-install
   ```

2. **Simülasyonu yeniden başlatın**:
   - Mevcut simülasyonu kapatın (Ctrl+C)
   - Tekrar başlatın:
     ```bash
     source install/setup.bash
     ros2 launch simulation_pkg simulation.launch.py
     ```

## 🎨 Örnek Poster İçeriği

Poster'da şunlar olabilir:
- Etkinlik başlığı
- Tarih bilgisi (Gemini AI analiz edecek)
- Detaylı açıklama
- QR kod
- Görseller
- İletişim bilgileri

## ⚠️ Önemli Notlar

1. **Dosya adı**: Mutlaka `poster.png` olmalı
2. **Konum**: Bu klasörde (`materials/textures/`) olmalı
3. **Format**: PNG, JPG veya JPEG desteklenir (PNG önerilir)
4. **Symlink**: Build sonrası `install/` klasörüne otomatik kopyalanır

## 🧪 Test Etme

Poster'ın doğru yüklendiğini kontrol etmek için:

```bash
# Dosyanın varlığını kontrol et
ls -lh ~/itu_robotics_ws/itu_project_ws/src/simulation_pkg/models/poster_board/materials/textures/poster.png

# Simülasyonda görüntüle
ros2 launch simulation_pkg simulation.launch.py
```

Gazebo'da pano üzerinde posterinizi görmelisiniz!

## 📝 Mevcut Poster

Şu anda sistemde **ITU Robotics Workshop** posteri bulunmaktadır:
- Başlık: "ITU Robotics Workshop"
- Tarih: 2025-12-15
- İçerik: Robotik workshop duyurusu

Bu posteri kendi posterinizle değiştirebilirsiniz.

---

**Not**: Poster değiştirildikten sonra Gemini AI yeni içeriği otomatik olarak analiz edecektir.
