#!/bin/bash

# ITU Noticeboard Patrol - Hızlı Başlatma Scripti
# Bu script tüm sistemi otomatik olarak başlatır

echo "🚀 ITU Noticeboard Patrol Sistemi Başlatılıyor..."
echo ""

# Renk kodları
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Workspace'i source et
source ~/itu_robotics_ws/itu_project_ws/install/setup.bash

# Secrets dosyasını yükle (varsa)
if [ -f ~/itu_robotics_ws/itu_project_ws/secrets.env ]; then
    source ~/itu_robotics_ws/itu_project_ws/secrets.env
fi

# Environment variables kontrol
if [ -z "$GOOGLE_API_KEY" ]; then
    echo -e "${YELLOW}⚠️  UYARI: GOOGLE_API_KEY ayarlanmamış!${NC}"
    echo "Lütfen ~/.bashrc dosyasında GOOGLE_API_KEY'i ayarlayın."
    echo ""
fi

echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ITU Noticeboard Patrol - Otonom Devriye Sistemi${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo ""
echo "Sistemi başlatmak için 4 terminal açmanız gerekiyor:"
echo ""
echo -e "${YELLOW}Terminal 1 - Simülasyon:${NC}"
echo "  source ~/itu_robotics_ws/itu_project_ws/install/setup.bash"
echo "  ros2 launch simulation_pkg simulation.launch.py"
echo ""
echo -e "${YELLOW}Terminal 2 - Algılama & AI:${NC}"
echo "  source ~/itu_robotics_ws/itu_project_ws/install/setup.bash"
echo "  ros2 run perception_pkg gemini_node"
echo ""
echo -e "${YELLOW}Terminal 3 - Otonom Devriye (Navigation):${NC}"
echo "  source ~/itu_robotics_ws/itu_project_ws/install/setup.bash"
echo "  ros2 run simulation_pkg patrol_node.py"
echo ""
echo -e "${YELLOW}Terminal 4 - Planlayıcı (Planner):${NC}"
echo "  source ~/itu_robotics_ws/itu_project_ws/install/setup.bash"
echo "  ros2 run simulation_pkg planner_node.py"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo ""
echo "📚 Detaylı bilgi için: ~/itu_robotics_ws/itu_project_ws/CALISTIRMA_REHBERI.md"
echo ""

# Otomatik Build
echo -e "${YELLOW}🔨 Proje build ediliyor (Otomatik)...${NC}"
cd ~/itu_robotics_ws/itu_project_ws
colcon build --symlink-install
source install/setup.bash
echo -e "${GREEN}✅ Build tamamlandı!${NC}"
echo ""

# Log Dosyası ve Seviyesi
LOG_FILE=~/itu_robotics_ws/itu_project_ws/debug_log.txt
echo "Loglar buraya kaydediliyor: $LOG_FILE"
echo "----------------------------------------" >> $LOG_FILE
echo "Başlangıç: $(date)" >> $LOG_FILE

# Kullanıcıya seçenek sun
echo "Ne yapmak istersiniz?"
echo "1) Simülasyonu başlat (Terminal 1)"
echo "2) Algılama sistemini başlat (Terminal 2)"
echo "3) Otonom devriyeyi başlat (Terminal 3)"
echo "4) Planlayıcıyı başlat (Terminal 4)"
echo "5) Çıkış"
echo ""
read -p "Seçiminiz (1-5): " choice

case $choice in
    1)
        echo -e "${GREEN}🎮 Simülasyon başlatılıyor...${NC}"
        # Simülasyon loglarını temiz tutalım
        ros2 launch simulation_pkg simulation.launch.py 2>&1 | tee -a $LOG_FILE
        ;;
    2)
        echo -e "${GREEN}👁️  Algılama sistemi başlatılıyor...${NC}"
        # Sadece perception_node için debug aç
        ros2 run perception_pkg gemini_node --ros-args --log-level perception_node:=DEBUG 2>&1 | tee -a $LOG_FILE
        ;;
    3)
        echo -e "${GREEN}🤖 Otonom devriye başlatılıyor...${NC}"
        # Sadece patrol_node için debug aç
        ros2 run simulation_pkg patrol_node.py --ros-args --log-level patrol_node:=DEBUG 2>&1 | tee -a $LOG_FILE
        ;;
    4)
        echo -e "${GREEN}🧠 Planlayıcı başlatılıyor...${NC}"
        ros2 run simulation_pkg planner_node.py --ros-args --log-level planner_node:=DEBUG 2>&1 | tee -a $LOG_FILE
        ;;
    5)
        echo "Çıkılıyor..."
        exit 0
        ;;
    *)
        echo "Geçersiz seçim!"
        exit 1
        ;;
esac
