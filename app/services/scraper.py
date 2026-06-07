import requests
from bs4 import BeautifulSoup
from googlesearch import search
from typing import List, Dict, Any
import time
import re
from app.schemas.prospects import ItemCreate

class GoogleScraper:
    """Scraper pour Google Search"""
    
    def __init__(self, api_key: str = None, cse_id: str = None):
        self.api_key = api_key
        self.cse_id = cse_id
        self.use_api = api_key and cse_id
    
    def search_businesses(self, query: str, num_results: int = 20) -> List[Dict[str, Any]]:
        """Recherche des entreprises sur Google"""
        businesses = []
        
        if self.use_api:
            businesses = self._search_with_api(query, num_results)
        else:
            businesses = self._search_with_scraping(query, num_results)
        
        return businesses
    
    def _search_with_api(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """Recherche via Google Custom Search API"""
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': self.api_key,
            'cx': self.cse_id,
            'q': query,
            'num': min(num_results, 10)  # API limit
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            businesses = []
            for item in data.get('items', []):
                business = {
                    'name': self._extract_business_name(item.get('title', '')),
                    'sector': self._extract_sector(item.get('snippet', '')),
                    'city': self._extract_city(item.get('snippet', '')),
                    'phone': self._extract_phone(item.get('snippet', '')),
                    'description': item.get('snippet', ''),
                    'source': 'google_api'
                }
                if business['name'] and business['phone']:
                    businesses.append(business)
            
            return businesses
            
        except Exception as e:
            print(f"Erreur API Google: {str(e)}")
            return []
    
    def _search_with_scraping(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """Recherche par scraping (moins fiable mais sans API)"""
        businesses = []
        
        try:
            for url in search(query, num_results=num_results, stop=num_results):
                business = self._scrape_page(url)
                if business and business.get('phone'):
                    businesses.append(business)
                time.sleep(1)  # Éviter le rate limiting
            
            return businesses
            
        except Exception as e:
            print(f"Erreur scraping Google: {str(e)}")
            return []
    
    def _scrape_page(self, url: str) -> Dict[str, Any]:
        """Scrape une page individuelle"""
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extraction basique
            title = soup.find('title')
            name = title.text.strip() if title else ""
            
            # Extraction téléphone (pattern simple)
            text = soup.get_text()
            phone = self._extract_phone(text)
            
            return {
                'name': name[:100],
                'sector': '',
                'city': '',
                'phone': phone,
                'description': text[:500],
                'source': url
            }
            
        except Exception:
            return None
    
    def _extract_business_name(self, text: str) -> str:
        """Extrait le nom de l'entreprise du texte"""
        # Patterns simples pour extraire le nom
        patterns = [
            r'([A-Z][A-Za-z\s]+)(?:SARL|SA|EURL|SAS|CI)',
            r'^([A-Za-z\s]+)(?:\s+-\s+|$)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        
        return text.split('-')[0].strip()[:100]
    
    def _extract_phone(self, text: str) -> str:
        """Extrait un numéro de téléphone du texte"""
        patterns = [
            r'\+(?:229)\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{2}',
            r'0\d{2}\s?\d{2}\s?\d{2}\s?\d{2}',
            r'\d{8}'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        
        return ""
    
    def _extract_sector(self, text: str) -> str:
        """Extrait le secteur d'activité"""
        sectors = ['commerce', 'pharmacie', 'restaurant', 'hôtel', 'boutique', 'service']
        text_lower = text.lower()
        
        for sector in sectors:
            if sector in text_lower:
                return sector.capitalize()
        
        return ""
    
    def _extract_city(self, text: str) -> str:
        """Extrait la ville"""
        cities = ['Cotonou', 'Porto-Novo', 'Parakou', 'Abomey-Calavi', 'Ouidah']
        
        for city in cities:
            if city.lower() in text.lower():
                return city
        
        return ""

def scrape_go_africa():
    """
    Scrape les entreprises depuis Go Africa Online (Bénin)
    
    """
    prospects = []
    try:
        # L'URL qui fonctionne (basée sur ton HTML)
        url = "https://www.goafricaonline.com/bj/annuaire-resultat?type=company&where=country-BJ"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'fr-FR,fr;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Méthode 1 : Chercher les articles avec data-company-id (c'est fiable)
        articles = soup.find_all('article', attrs={'data-company-id': True})
        
        for article in articles:
            try:
                # 1. Extraire le nom de l'entreprise
                name_elem = article.find('h2')
                if name_elem:
                    link = name_elem.find('a')
                    name = link.get_text(strip=True) if link else name_elem.get_text(strip=True)
                else:
                    name = ""
                
                # 2. Extraire le téléphone
                phone_links = article.find_all('a', href=lambda x: x and 'tel:' in x)
                phone = ""
                for phone_link in phone_links:
                    phone_href = phone_link.get('href', '')
                    if 'tel:' in phone_href:
                        phone = phone_href.replace('tel:', '').strip()
                        break
                
                # 3. Extraire le secteur
                sector_elem = article.find('div', class_=re.compile(r'text-brand-blue'))
                sector = sector_elem.get_text(strip=True) if sector_elem else ""
                
                # 4. Extraire la ville/adresse
                address_elem = article.find('address')
                city = address_elem.get_text(strip=True) if address_elem else "Cotonou"
                # Nettoyer la ville (prendre la dernière ligne souvent)
                if city:
                    city_lines = city.split('\n')
                    city = city_lines[-1].strip() if city_lines else "Cotonou"
                
                # Nettoyer le téléphone
                if phone and name:
                    # Nettoyer le numéro (garder uniquement chiffres)
                    digits_only = re.sub(r'[^\d]', '', phone)
                    # Extraire les 8 derniers chiffres (numéro béninois)
                    if len(digits_only) >= 8:
                        # Prendre les 8 derniers chiffres
                        local_number = digits_only[-8:]
                        formatted_phone = f"+229 01 {local_number[0:2]} {local_number[2:4]} {local_number[4:6]} {local_number[6:8]}"
                        
                        prospects.append({
                            'name': name[:100],
                            'phone': formatted_phone,
                            'sector': sector[:100],
                            'city': city[:100],
                            'description': "",
                            'source': 'go_africa'
                        })
                        
            except Exception as e:
                print(f"Erreur sur un article: {e}")
                continue
        
        print(f"Scraping terminé : {len(prospects)} prospects trouvés")
        return prospects
        
    except Exception as e:
        print(f" Erreur scraping: {e}")
        return []

class ScraperService:
    """Service de scraping unifié"""
    
    def __init__(self, google_api_key: str = None, google_cse_id: str = None):
        self.google_scraper = GoogleScraper(google_api_key, google_cse_id)
        self.africa_scraper = scrape_go_africa()
    
    def collect_prospects(self, source: str = "all", **kwargs) -> List[Dict[str, Any]]:
        """Collecte des prospects depuis différentes sources"""
        all_prospects = []
        
        if source in ["google", "all"]:
            google_query = kwargs.get('query', 'entreprises Benin commerce')
            google_results = self.google_scraper.search_businesses(google_query, kwargs.get('limit', 20))
            all_prospects.extend(google_results)
        
        if source in ["africa", "all"]:
            africa_results = self.africa_scraper.search_businesses(
                country=kwargs.get('country', 'benin'),
                category=kwargs.get('category')
            )
            all_prospects.extend(africa_results)
        
        return all_prospects