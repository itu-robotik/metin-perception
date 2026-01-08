# 🔧 Poster Yükleme Sorunu - Çözüldü!

## ✅ Yapılan Düzeltmeler

### 1. Launch Dosyası Güncellendi
`launch/simulation.launch.py` dosyasına `GZ_SIM_RESOURCE_PATH` environment variable ayarı eklendi. Artık Gazebo, install klasöründeki modelleri otomatik olarak bulacak.

### 2. Model Yapısı Tamamlandı
`poster_board` modeli için gerekli dosyalar oluşturuldu:
- ✅ `model.config` - Gazebo model yapılandırması
- ✅ `model.sdf` - Model tanımı
- ✅ `materials/textures/poster.png` - Poster görseli

### 3. Symlink Kurulumu
Build sistemi, poster dosyasını `install/` klasörüne otomatik olarak symlink ile bağladı.

## 📂 Poster Klasör Yapısı

```
models/poster_board/
├── model.config
├── model.sdf
└── materials/
    └── textures/
        ├── poster.png       ← Mevcut poster (ITU Workshop)
        ├── poster.jpeg      ← Yedek (silebilirsiniz)
        └── README.md        ← Poster ekleme rehberi
```

## 🖼️ Yeni Poster Ekleme

### Adım 1: Poster Dosyasını Hazırlayın
- Format: PNG, JPG veya JPEG
- Oran: Dikey/Portrait (örn: 800x1000 piksel)
- Dosya adı: `poster.png` (önemli!)

### Adım 2: Dosyayı Kopyalayın
```bash
cp /path/to/your/poster.png ~/itu_robotics_ws/itu_project_ws/src/simulation_pkg/models/poster_board/materials/textures/poster.png
```

### Adım 3: Simülasyonu Yeniden Başlatın
```bash
# Mevcut simülasyonu durdurun (Ctrl+C)
# Tekrar başlatın:
source ~/itu_robotics_ws/itu_project_ws/install/setup.bash
ros2 launch simulation_pkg simulation.launch.py
```

**Not**: Symlink kullanıldığı için yeniden build gerekmez!

## 🧪 Test Etme

### 1. Poster Dosyasını Kontrol Edin
```bash
ls -lh ~/itu_robotics_ws/itu_project_ws/src/simulation_pkg/models/poster_board/materials/textures/poster.png
```

Çıktı:
```
-rw-r--r-- 1 user user 565K Jan 7 22:42 poster.png
```

### 2. Install Klasöründeki Symlink'i Kontrol Edin
```bash
ls -lh ~/itu_robotics_ws/itu_project_ws/install/simulation_pkg/share/simulation_pkg/models/poster_board/materials/textures/
```

Çıktı:
```
lrwxrwxrwx 1 user user 111 Jan 7 22:42 poster.png -> /home/user/itu_robotics_ws/itu_project_ws/src/simulation_pkg/models/poster_board/materials/textures/poster.png
```

### 3. Gazebo'da Görüntüleyin
Simülasyonu başlattığınızda, koridorda mavi çerçeveli pano üzerinde posterinizi görmelisiniz.

## ⚠️ Sorun Giderme

### Hala "Unable to find file" Hatası Alıyorsanız

**1. Environment Variable'ı Kontrol Edin:**
```bash
echo $GZ_SIM_RESOURCE_PATH
```

Çıktıda şunları görmelisiniz:
```
/home/user/itu_robotics_ws/itu_project_ws/install/simulation_pkg/share/simulation_pkg/models:...
```

**2. Yeniden Build Edin:**
```bash
cd ~/itu_robotics_ws/itu_project_ws
colcon build --symlink-install
```

**3. Setup Script'i Source Edin:**
```bash
source ~/itu_robotics_ws/itu_project_ws/install/setup.bash
```

**4. Terminal'i Yeniden Başlatın:**
Bazen environment variable'lar yenilenmez. Yeni bir terminal açın ve tekrar deneyin.

### Poster Görünmüyor Ama Hata Yok

**1. Poster Formatını Kontrol Edin:**
- PNG formatı önerilir
- Dosya bozuk olabilir, başka bir görsel deneyin

**2. Dosya İzinlerini Kontrol Edin:**
```bash
chmod 644 ~/itu_robotics_ws/itu_project_ws/src/simulation_pkg/models/poster_board/materials/textures/poster.png
```

**3. Gazebo Cache'ini Temizleyin:**
```bash
rm -rf ~/.gz/sim/
```

## 📝 Teknik Detaylar

### Launch Dosyasında Yapılan Değişiklik

```python
# GZ_SIM_RESOURCE_PATH'i otomatik ayarla
models_path = os.path.join(pkg_share, 'models')
gz_resource_path = SetEnvironmentVariable(
    name='GZ_SIM_RESOURCE_PATH',
    value=models_path + ':' + os.environ.get('GZ_SIM_RESOURCE_PATH', '')
)
```

Bu sayede Gazebo, `model://poster_board/materials/textures/poster.png` URI'sini çözümleyebilir.

### Model URI Çözümleme

Gazebo şu sırayla arama yapar:
1. `GZ_SIM_RESOURCE_PATH` içindeki klasörler
2. `~/.gz/models/`
3. Sistem model klasörleri

Bizim durumumuzda:
```
model://poster_board/materials/textures/poster.png
↓
$GZ_SIM_RESOURCE_PATH/poster_board/materials/textures/poster.png
↓
~/itu_robotics_ws/itu_project_ws/install/simulation_pkg/share/simulation_pkg/models/poster_board/materials/textures/poster.png
```

## ✅ Sonuç

Artık sistem tamamen çalışır durumda! Poster dosyası Gazebo tarafından bulunacak ve pano üzerinde görüntülenecektir.

**Önemli**: Her yeni poster eklediğinizde sadece simülasyonu yeniden başlatmanız yeterli, build gerekmez!

---

**Güncelleme**: 7 Ocak 2026, 22:48
**Durum**: ✅ Çözüldü
