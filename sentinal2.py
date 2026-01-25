import requests
import json
import xml.etree.ElementTree as ET
import os
import sys
import random
import pandas as pd
import numpy as np
import rasterio
import matplotlib.pyplot as plt
import matplotlib.image
from rasterio.windows import Window
from pathlib import Path
import warnings

warnings.filterwarnings("ignore")

class CopernicusDataCatalog:
    def __init__(self, start_date, end_date, cloud_rate, lat, lon, status_callback=None):
        self.start_date = start_date
        self.end_date = end_date
        self.cloud_rate = cloud_rate
        self.lat = lat
        self.lon = lon
        self.koordinates = f"OData.CSC.Intersects(area=geography'SRID=4326;POINT({self.lon} {self.lat})')"
        self.catalogue_odata_url = "https://catalogue.dataspace.copernicus.eu/odata/v1"

        self.session = requests.Session()
        self.status_callback = status_callback
        self.df = pd.DataFrame()
        self.access_token = None
        self.product_name = "" 

    def send_message(self, message):
        print(message)
        if self.status_callback:
            self.status_callback(message)

    def post_request(self):
        url = (f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products?"
               f"$filter=Collection/Name eq 'SENTINEL-2' "
               f"and contains(Name,'MSIL1C') " 
               f"and {self.koordinates} " 
               f"and Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' and att/OData.CSC.DoubleAttribute/Value le {self.cloud_rate}) "
               f"and ContentDate/Start gt {self.start_date}T00:00:00.000Z "
               f"and ContentDate/Start lt {self.end_date}T00:00:00.000Z"
               f"&$top=10")
        
        try:
            response = requests.get(url)
            if response.status_code != 200:
                self.send_message(f"HATA: Sunucu Hatası {response.status_code}")
                return

            jsondata = response.json()
            self.send_message("İstek başarılı, veriler analiz ediliyor...")
            
            if 'value' in jsondata:
                self.df = pd.DataFrame.from_dict(jsondata['value'])
            
            if not self.df.empty:
                self.send_message(f"{len(self.df)} adet veri bulundu.")
            else:
                self.send_message("Belirtilen kriterlere uygun veri bulunamadı.")
        
        except Exception as e:
            self.send_message(f"Bağlantı Hatası: {str(e)}")

    def tokenization(self):
        username = "zeynepece.ucuncu@std.yeditepe.edu.tr" 
        password = "Z1071ece1071*"
        auth_server_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
        data = {
            "client_id": "cdse-public",
            "grant_type": "password",
            "username": username,
            "password": password,
        }
        try:
            response = requests.post(auth_server_url, data=data, verify=True, allow_redirects=False)
            if response.status_code == 200:
                self.access_token = json.loads(response.text)["access_token"]
                self.send_message("Kimlik doğrulama başarılı.")
            else:
                self.send_message("Kimlik doğrulama başarısız!")
        except Exception as e:
            self.send_message(f"Token Hatası: {e}")

    def _resolve_redirects(self, url):
        response = self.session.get(url, allow_redirects=False)
        while response.status_code in (301, 302, 303, 307):
            url = response.headers["Location"]
            response = self.session.get(url, allow_redirects=False)
        return response

    def access_the_data(self):
        if self.df.empty:
            return

        row_count = len(self.df)
        self.send_message(f"İşlenecek veri sayısı: {row_count}")
        
        for idx in range(row_count):
            try:

                self.product_identifier = self.df.iloc[idx]["Id"]
                raw_name = self.df.iloc[idx]["Name"]
                self.product_name = raw_name if raw_name.endswith('.SAFE') else raw_name + ".SAFE"
                
                self.send_message(f"İşleniyor ({idx+1}/{row_count}): {raw_name}")
                self.session.headers["Authorization"] = f"Bearer {self.access_token}"
  
                xml_filename = f"{self.product_name}_MTD.xml"
                outfile = Path.home() / xml_filename

                if not outfile.exists():
                    url = f"{self.catalogue_odata_url}/Products({self.product_identifier})/Nodes({self.product_name})/Nodes(MTD_MSIL1C.xml)/$value"
                    response = self._resolve_redirects(url)
                    xml_response = self.session.get(response.url, verify=False, allow_redirects=True)
                    if xml_response.status_code != 200:
                        self.send_message("XML indirilemedi, geçiliyor...")
                        continue
                    outfile.write_bytes(xml_response.content)

                tree = ET.parse(str(outfile))
                root = tree.getroot()

              
                band_location = []
                try:
                    base_path = f"{self.product_name}/"
                    band_location.append((base_path + root[0][0][12][0][0][1].text + ".jp2").split("/"))
                    band_location.append((base_path + root[0][0][12][0][0][2].text + ".jp2").split("/"))
                    band_location.append((base_path + root[0][0][12][0][0][3].text + ".jp2").split("/")) 
                except Exception:
                     self.send_message("XML veri yapısı uyumsuz, bu görüntü atlanıyor.")
                     continue

                bands_paths = []
                
                for band_info in band_location:
                   
                    band_filename = band_info[-1] 
                    
                    unique_band_name = band_filename 
                    band_out_path = Path.home() / unique_band_name

                    if band_out_path.exists():
                        self.send_message(f"Önbellekten bulundu: {band_filename}")
                        bands_paths.append(str(band_out_path))
                    else:
                        self.send_message(f"İndiriliyor: {band_filename}...")
                        
                 
                        url_parts = [f"Nodes({part})" for part in band_info[1:]] # İlk parça Product Name, onu atlıyoruz
                        nodes_str = "/".join(url_parts)
                        
                        url = f"{self.catalogue_odata_url}/Products({self.product_identifier})/Nodes({self.product_name})/{nodes_str}/$value"
                        
                        response = self._resolve_redirects(url)
                        band_data = self.session.get(response.url, verify=False, allow_redirects=True, stream=True)
                        
                        if band_data.status_code == 200:
                            with open(band_out_path, 'wb') as f:
                                for chunk in band_data.iter_content(chunk_size=8192):
                                    f.write(chunk)
                            bands_paths.append(str(band_out_path))
                            self.send_message("İndirme tamamlandı.")
                        else:
                            self.send_message(f"Hata: {band_filename} indirilemedi.")

                if len(bands_paths) == 3:
                    final_image_path = self.process_and_save_image(bands_paths, idx)
                    if final_image_path:
                        self.send_message(f"IMAGE_READY:{final_image_path}")
                
            except Exception as e:
 
                exc_type, exc_obj, exc_tb = sys.exc_info()
                print(f"DEBUG ERROR: Line {exc_tb.tb_lineno} - {e}")
                self.send_message(f"Hata oluştu: {str(e)[:50]}...")

    def process_and_save_image(self, bands, idx):
        try:
            xsize, ysize = 1000, 1000
        
            with rasterio.open(bands[0], driver="JP2OpenJPEG") as src:
                width, height = src.width, src.height
                
                if width < xsize or height < ysize:
                    xsize, ysize = width, height
                    xoff, yoff = 0, 0
                else:
                    xmin, xmax = 0, width - xsize
                    ymin, ymax = 0, height - ysize
                    xoff, yoff = random.randint(xmin, xmax), random.randint(ymin, ymax)
                
                window = Window(xoff, yoff, xsize, ysize)


            b2 = rasterio.open(bands[0]).read(1, window=window)
            b3 = rasterio.open(bands[1]).read(1, window=window)
            b4 = rasterio.open(bands[2]).read(1, window=window)

            gain = 2.5
            red_n = np.clip(b4 * gain / 10000, 0, 1)
            green_n = np.clip(b3 * gain / 10000, 0, 1)
            blue_n = np.clip(b2 * gain / 10000, 0, 1)

            rgb = np.dstack((red_n, green_n, blue_n))

            save_path = f"{Path.home()}/Sentinel2_Result_{idx}.jpeg"
            matplotlib.image.imsave(save_path, rgb)
            return save_path

        except Exception as e:
            self.send_message(f"Resim oluşturulamadı: {e}")
            return None
        


        #latitude 41.0082 , longtitude 28.9784