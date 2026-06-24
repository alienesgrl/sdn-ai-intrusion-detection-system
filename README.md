# SDN Tabanlı Yapay Zekâ Destekli Saldırı Tespit Sistemi (IDS) Kontrol Paneli

Bu proje; Yazılım Tanımlı Ağlar (SDN - Software Defined Networking) üzerinde makine öğrenmesi modelleri kullanarak anormal ve saldırı niteliğindeki trafik akışlarını gerçek zamanlı tespit eden, PyQt5 tabanlı gelişmiş bir masaüstü kontrol paneli ve simülasyon arayüzüdür. 

Uygulama; **Mininet** ağ emülatörü ile **Ryu SDN Controller** süreçlerini eşzamanlı olarak arka planda yönetir. Ağdan topladığı trafik istatistiklerini makine öğrenmesi modellerinden geçirerek sınıflandırır, sonuçları hem canlı ağ topolojisi üzerinde dinamik animasyonlarla görselleştirir hem de detaylı analitik performans raporları sunar.

---

## 🏗️ Sistem Mimarisi ve Çalışma Prensibi

Proje, üç ana katmanın birleşimiyle çalışır:

1. **Ağ Emülasyon Katmanı (Mininet):** 
   Gerçekçi bir ağ ortamı simüle etmek amacıyla 6 ana switch (`s1-s6`) ve bunlara dağıtılmış 21 host (`h1-h21`) barındıran doğrusal (chain) bir ağ oluşturur. Tüm anahtarlar merkezi kontrolcüye (`c0`) bağlıdır.
   
2. **Kontrol ve Karar Katmanı (Ryu Controller & ML):**
   Ryu denetleyicisi üzerinde koşan gömülü modül (`topo/controller.py`), switch'lerden saniyede bir akış istatistiklerini (Flow Stats) talep eder. Gelen akış verilerinden şu 6 nitelik (feature) çıkarılır:
   * **Flow Duration:** Akışın toplam aktif kalma süresi
   * **Tot Fwd Pkts / TotLen Fwd Pkts:** İletilen toplam paket sayısı ve bayt uzunluğu
   * **Flow Pkts/s / Flow Byts/s:** Saniye başına düşen paket ve bayt hızı
   * **Pkt Size Avg:** Ortalama paket boyutu
   
   Bu nitelikler arayüzden seçilen makine öğrenmesi modeline (XGBoost, Random Forest veya Decision Tree) girdi olarak verilerek sınıflandırma yapılır. Eğer anomali eşiği aşılırsa akış "Saldırı" (`🚨 ATTACK DETECTED`), aşılmazsa "Normal" (`✅ Normal Traffic`) olarak işaretlenir.

3. **Görselleştirme ve Yönetim Katmanı (PyQt5 GUI Dashboard):**
   Kullanıcıya tüm bu karmaşık süreci tek bir ekrandan yönetme imkanı sunar. Süreçlerin (`stdout/stderr`) çıktılarını anlık ayrıştırarak topoloji ekranında görsel paket akış animasyonlarına dönüştürür.

---

## 📂 Dosya ve Dizin Yapısı

```
bitirme/
├── main.py                  # Uygulamayı başlatan ana Python betiği
├── requirements.txt         # Projenin çalışması için gereken Python kütüphaneleri
├── README.md                # Kapsamlı proje dokümantasyonu
│
├── core/                    # Arka plan iş mantığı ve iş parçacıkları (Threads)
│   ├── mininet_manager.py   # Mininet sürecini başlatan, durduran ve CLI komutu gönderen worker
│   ├── model_manager.py     # `models/` dizinindeki eğik modelleri tarayan ve arayüze sunan sınıf
│   ├── ryu_manager.py       # Ryu Controller sürecini başlatan ve kapatan worker
│   └── test_manager.py      # Modelleri otomatik olarak test eden orkestratör worker
│
├── models/                  # Eğitilmiş makine öğrenmesi modelleri
│   ├── sdn_ids_decision_tree_model.pkl
│   ├── sdn_ids_random_forest_model.pkl
│   └── sdn_ids_xgboost_model.pkl
│
├── topo/                    # SDN ve Topoloji Tanımları
│   ├── topo.py              # Mininet topoloji şeması ve ağ bağlantı tanımları
│   └── controller.py        # Trafik analizi yapan ve ML modellerini çalıştıran Ryu controller uygulaması
│
└── ui/                      # Kullanıcı Arayüzü Bileşenleri
    ├── main_window.py       # Ana pencere tasarımı, buton etkileşimleri ve test grafik ekranı
    └── topology_view.py     # QtGraphics tabanlı interaktif ağ topolojisi ve animasyon motoru
```

---

## 🛠️ Sistem Gereksinimleri

* **İşletim Sistemi:** Linux (Ubuntu 20.04 LTS veya 22.04 LTS önerilir) ya da Windows üzerinde **WSL2** (Windows Subsystem for Linux) ortamı.
* **Python Sürümü:** Python 3.8 veya üzeri
* **Gerekli Ağ Araçları:**
  * **Mininet:** Açık kaynaklı ağ emülatörü (`sudo apt-get install mininet`)
  * **Open vSwitch:** Paket yönlendirme anahtarları için daemon (`sudo service openvswitch-switch start`)
  * **Ryu:** SDN denetleyici çatısı (`pip install ryu`)

---

## 🚀 Kurulum ve Hazırlık

### 1. Python Bağımlılıklarının Yüklenmesi
Aşağıdaki komutla arayüz, veri analizi ve makine öğrenmesi için gerekli tüm kütüphaneleri kurun:
```bash
pip install -r requirements.txt
```

### 2. Ağ Servislerinin Doğrulanması
Mininet ve Ryu'nun kurulu olduğunu ve doğru çalıştığını test edin:
```bash
# Mininet Testi
sudo mn --test pingall

# Ryu Testi
ryu-manager --version
```

### 3. Model Dosyalarının Yerleştirilmesi
Eğer kendi eğittiğiniz modeller varsa, bunları `.pkl` veya `.joblib` uzantısıyla `models/` klasörünün içine yerleştirin. Uygulama açılışta bu klasörü otomatik olarak tarayacaktır.

---

## 💻 Uygulamanın Başlatılması

Mininet doğrudan Linux çekirdeğindeki ağ ad alanlarını (Network Namespaces) ve sanal ethernet arayüzlerini kullandığından, uygulamanın **root yetkisiyle** çalıştırılması gerekmektedir:

```bash
sudo -E python3 main.py
```
*(Not: `-E` parametresi, mevcut kullanıcının ortam değişkenlerini (örneğin GUI ekran yönlendirmesi için gerekli olan `DISPLAY` değişkenini) koruyarak sudo yetkisi sağlar).*

### 🖥️ Windows WSL2 Altında Çalıştırma Notları:
Eğer GUI ekranı açılmazsa, WSL terminalinde DISPLAY yönlendirmesini doğrulamak için şu adımları uygulayabilirsiniz:
1. Windows tarafında bir X-Server programı (örn: VcXsrv) başlatın.
2. WSL terminalinizde şu komutla DISPLAY değişkenini export edin:
   ```bash
   export DISPLAY=$(ip route | grep default | awk '{print $3}'):0
   ```
3. Uygulamayı yeniden başlatın.

---

## 🌟 Detaylı Özellik Seti

### 1. Dinamik Ağ Topolojisi & Canlı Animasyonlar
* **Doğrusal Ağ Şeması:** 6 Switch (`s1-s6`) yan yana bağlanarak zincir oluşturur. Her switch'e 3 veya 4 host bağlıdır (toplam 21 host).
* **Canlı Paket Akışı:** Hostlar arasında Ping atıldığında, topoloji üzerinde **yeşil renkli veri paketleri** ilgili yolları izleyerek akar.
* **Saldırı Görselleştirmesi:** Ağda Iperf ile UDP Flood (Saldırı) trafiği simüle edildiğinde, ilgili hostlar ve switchler arası hatlar anında **kırmızı renkli hareketli kesikli çizgilerle (ışın efektiyle)** kaplanır.
* **Kontrolcü İletişimi:** Switchlerden controller'a akış istatistiği sorgusu gittiğinde, controller (`c0`) ile switchler arasında **turkuaz renkli kontrol paketleri** gidip gelir ve controller anlık olarak sarı renkle parlar (flash efekti).

### 2. Çoklu Model Karşılaştırmalı Otomatik Test Modülü
* **Tek Tıkla Kapsamlı Test:** "Tüm Modelleri Test Et" butonuna tıklandığında sistem otomatik test moduna geçer.
* **Rastgele Host Seçimi:** Test başlamadan önce 21 host arasından rastgele bir kaynak (Source) ve hedef (Destination) seçilerek gerçekçi senaryo simüle edilir.
* **Sıralı Model Değerlendirme:**
  1. Seçilen model ile Ryu Controller arka planda başlatılır.
  2. Gerekli hazırlık süresinden sonra 10 saniye boyunca normal trafik (Ping) üretilir ve modelin performansı kaydedilir.
  3. Ardından 10 saniye boyunca Iperf ile UDP Flood saldırı trafiği simüle edilir.
  4. Test verileri tamamlandığında Ryu durdurulur ve bir sonraki modele geçilir.

### 3. Detaylı Metrik Raporlama ve Dışa Aktarma
Otomatik test işlemi bittiğinde ekrana gelen "Test Sonuçları" panelinde şu raporlar sekmeler halinde sunulur:
* **Detaylı Performans Tablosu:** Modellerin Doğruluk (Normal/Saldırı/Genel), Duyarlılık/Recall, F1 Skoru, Yanlış Alarm Oranı (FPR) ve Kaçan Atak Oranı (FNR) değerleri listelenir.
* **Hata Oranları Grafiği (FPR vs FNR):** Modellerin yanlış alarm verme ve atak kaçırma oranları yan yana karşılaştırılır.
* **Performans Metrikleri Grafiği:** Precision, Recall ve F1 skorları görsel bar grafik olarak çizilir.
* **Confusion Matrix Grafiği:** Doğru Pozitif (TP), Doğru Negatif (TN), Yanlış Pozitif (FP) ve Yanlış Negatif (FN) sayıları karşılaştırılır.
* **PNG Olarak Kaydetme:** Arayüzde bulunan dışa aktarma butonu sayesinde tüm bu grafikler tek tıkla yüksek çözünürlüklü görsel (`.png`) olarak diske kaydedilebilir.
