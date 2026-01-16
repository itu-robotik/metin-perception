# Robot Navigasyon Stratejileri: Bilinen vs. Bilinmeyen Ortamlar

Bu belge, hedef konumların (ör. posterler) önceden bilinip bilinmediğine veya robotun bunları keşfetmesi gerekip gerekmediğine bağlı olarak otonom robot navigasyonu yaklaşımlarını özetlemektedir.

## 1. Bilinen Konumlar (Harita Tabanlı Navigasyon)
**Senaryo:** Ortamın bir haritasına sahipsiniz (veya önce bir tane oluşturursunuz) ve posterlerin tam olarak nerede olduğunu (x, y koordinatları) biliyorsunuz.

### Yaklaşım:
1.  **Haritalama (SLAM):** İlk olarak, global bir harita oluşturmak için robotu manuel olarak sürün (`slam_toolbox` veya `cartographer` kullanarak). Bu haritayı kaydedin.
2.  **Konumlandırma (AMCL):** Otonom çalışırken robot, tam olarak nerede olduğunu anlamak için kaydedilen haritayı ve LiDAR verilerini kullanır.
3.  **Navigasyon (Nav2):** Robota belirli koordinatlar (yol noktaları) gönderirsiniz. Robot, statik engellerden (duvarlar) ve dinamik engellerden (insanlar) kaçınarak bir yol planlamak için haritayı kullanır.

### Artıları:
*   **Verimli:** En kısa yolu kullanır.
*   **Güvenilir:** Robot tam olarak nereye gittiğini bilir.
*   **Ölçeklenebilir:** Sadece bir listeye koordinat ekleyerek daha fazla hedef eklemek kolaydır.

### Eksileri:
*   **Kurulum Süresi:** Önce alanın haritalandırılmasını gerektirir.
*   **Oynaklık:** Bir poster hareket ederse, koordinat listesini güncellemeniz gerekir.

### ROS 2'de Uygulama:
*   Navigasyon yığını için `nav2_bringup` kullanın.
*   Her posterin belirli [(x, y, theta)](file:///home/metin/itu_robotics_ws/itu_project_ws/src/simulation_pkg/scripts/patrol_node.py#287-293) değerini saklamak için bir JSON dosyası (mevcut "belleğiniz" gibi) kullanın.

---

## 2. Bilinmeyen Konumlar (Keşif Tabanlı)
**Senaryo:** Robotu tamamen yeni bir binaya koyuyorsunuz. Haritası yok ve posterlerin nerede olduğunu bilmiyor.

### Yaklaşım:
1.  **Sınır (Frontier) Keşfi:** Robot, yerel haritasındaki "sınırları" (bilinen boş alan ile bilinmeyen alan arasındaki sınırlar) tanımlar ve yeni alanları ortaya çıkarmak için bunlara doğru hareket eder.
2.  **Bilgisayarlı Görme (Nesne Algılama):** Keşif sırasında robotun kamerası sürekli olarak ilgi çekici nesneleri (ArUco işaretleri, belirli poster şekilleri) tarar.
3.  **Görsel Servolama (Visual Servoing):** Bir hedef tespit edildiğinde, robot keşfini kesintiye uğratır, "Kenetlenme Modu"na geçer, hedefe yaklaşır, analiz eder ve keşfe devam etmeden önce o alanı dahili haritasında "ziyaret edildi" olarak işaretler.

### Artıları:
*   **Esnek:** Önceden kurulum yapmadan herhangi bir ortamda çalışır.
*   **Dinamik:** Posterler günlük olarak taşınsa bile onları bulabilir.

### Eksileri:
*   **Yavaş:** Robot bir şey bulana kadar etrafta dolaşır.
*   **Karmaşık:** Daha gelişmiş mantık gerektirir (Keşif Düğümü + Algılama Düğümü).

### ROS 2'de Uygulama:
*   `explore_lite` kullanın veya basit bir "Duvar Takipçisi" / "Rastgele Yürüyüş" algoritması yazın.
*   Mevcut `patrol_node`'unuz bunun basitleştirilmiş bir versiyonudur: kaba koordinatlara gider ancak son yaklaşım için görüşe güvenir.

## 3. Hibrit Yaklaşım (Topolojik + Görsel)
**Senaryo:** Posterlerin *yaklaşık* alanlarını (ör. "Koridor A'nın sonu", "Lobi") biliyorsunuz, ancak tam santimetrik konumunu bilmiyorsunuz.

### Yaklaşım:
1.  **Topolojik Grafik:** Ana alanları bir grafikteki düğümler olarak tanımlayın (ör. Koridor_1, Koridor_2).
2.  **Görsel Yönelim (Visual Homing):** Robot "Koridor_1"e gider. Oraya vardığında döner/tarar. Bir işaret görürse kenetlenir. Görmezse bir sonraki düğüme geçer.
3.  **Bu sizin mevcut sisteminiz.** Koordinat tahminlerini (`planner_node`) verirsiniz ve `patrol_node`, tam noktayı bulmak ve kenetlenmek için görüşü (`gemini_node`) kullanır.

## Bu Proje İçin Öneri
Bu bir geliştirme/öğrenme projesi olduğu için:

1.  **Hibrit (Mevcut) ile Devam Edin:** `planner_node`'un yaklaşık koordinatlar göndermesini sağlayın. Bu, yapı ve otonomi arasındaki en iyi dengedir.
    *   *İyileştirme:* Robot bir noktaya gider ve hiçbir şey bulamazsa, vazgeçmeden önce bir "sürünen arama" (1 metre ileri git, tekrar dön) gerçekleştirmesini sağlayın.
2.  **Gelecek Yükseltmesi (Nav2):** Profesyonel hale getirmek istiyorsanız `Nav2` uygulayın.
    *   Dünyayı haritalayın.
    *   Robotu panoya göndermek için `NavigateToPose` eylemini kullanın.
    *   Kamerayı sadece son 50 cm'lik "ince ayar" için kullanın.
