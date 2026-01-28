# Uydu Verisi Görselleştirme Aracı
Bu proje, Copernicus Data Space Ecosystem API'sini kullanarak uydu görüntülerini istenen özelliklere uyan görüntülere erişebileceği bir masaüstü uygulamasıdır. Kullanıcıların belirlediği koordinat (enlem/boylam), tarih aralığı ve bulutluluk oranına göre filtreleme yapar ve elde edilen görüntüleri işleyerek arayüzde sunar.

## Teknolojiler 
Proje tamamen Python dili kullanılarak geliştirilmiştir. Kullanılan temel kütüphaneler şunlardır:
  Arayüz (GUI): PyQt5
  API Entegrasyonu: Requests (Copernicus OData)
  Görüntü İşleme: Rasterio, NumPy

## Kurulum
Projeyi çalıştırmak için aşağıdaki Python kütüphanelerinin yüklü olması gerekmektedir:

pip install PyQt5 requests pandas numpy rasterio matplotlib 


## Dosya Yapısı
Projede `gui.py` ve `sentinal2.py` diye iki ana dosya var. Bunların ne işe yaradığını kısaca yazarsan, kodun mimarisini bildiğini gösterirsin.

* gui.py: Kullanıcı arayüzünü (PyQt5) oluşturur ve görselleştirme işlemlerini yönetir. QThread ile performans koruması sağlar.
* sentinal2.py : Copernicus API ile haberleşir, verileri indirir .

##  Özellikler
* Asenkron sistem mimarisi: `QThread` kullanarak arayüz donmadan veri indirme işlemi.
* Akıllı Önbellekleme : Daha önce indirilen bantları tekrar indirmeyerek hız kazandırır.
* RGB Dönüşümü: Ham uydu bantlarını işleyerek gerçek renkli görüntü oluşturur.
