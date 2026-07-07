import requests
from bs4 import BeautifulSoup
import re
import os
import json
import time
from dotenv import load_dotenv
from urllib.parse import urljoin
from typing import List, Dict, Any, Optional

load_dotenv()

# ==================== SCRAPER GO AFRICA ====================
class AfricaOnlineScraper:
    """Scraper pour Go Africa Online avec pagination"""
    
    def __init__(self):
        self.base_url = "https://www.goafricaonline.com/bj/annuaire-resultat"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
        }
    
    def search_businesses(self, limit: int = 20, max_pages: int = 100, start_page: int = 1, **kwargs) -> List[Dict[str, Any]]:
        """
        Scrape les entreprises depuis Go Africa Online avec pagination
        
        Args:
            limit: Nombre maximum d'entreprises à scraper
            max_pages: Nombre maximum de pages à parcourir
            start_page: Page de départ (pour la pagination intelligente)
        """
        all_prospects = []
        page = start_page  # ← Correction : pas de virgule !
        
        print(f"🔍 Scraping Go Africa Online (max {max_pages} pages, depuis page {start_page})...")
        
        while len(all_prospects) < limit and page <= max_pages:
            try:
                print(f"📄 Page {page}...")
                
                params = {
                    "type": "company",
                    "where": "country-BJ",
                    "p": page
                }
                
                response = requests.get(
                    self.base_url, 
                    headers=self.headers, 
                    params=params, 
                    timeout=15
                )
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                prospects_page = self._parse_page(soup)
                
                if not prospects_page:
                    print(f"📭 Plus d'entreprises à la page {page}")
                    break
                
                remaining = limit - len(all_prospects)
                all_prospects.extend(prospects_page[:remaining])
                
                print(f"   ✅ {len(prospects_page)} entreprises trouvées, total: {len(all_prospects)}")
                
                if not self._has_next_page(soup):
                    print(f"📭 Plus de pages disponibles")
                    break
                
                page += 1
                time.sleep(0.5)
                
            except Exception as e:
                print(f"❌ Erreur page {page}: {e}")
                break
        
        print(f"✅ Go Africa: {len(all_prospects)} prospects extraits sur {page - start_page} pages")
        return all_prospects
    
    def _parse_page(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        prospects = []
        articles = soup.find_all('article', {'data-role': 'company'})
        
        for article in articles:
            prospect = self._parse_article(article)
            if prospect:
                prospects.append(prospect)
        
        return prospects
    
    def _parse_article(self, article) -> Dict[str, Any]:
        try:
            from app.services.normaliseur import normalize
            
            name_tag = article.find('a', class_='stretched-link')
            name = name_tag.get_text(strip=True) if name_tag else None
            
            sector_tag = article.find('div', class_='text-14 text-brand-blue mb-4')
            sector = sector_tag.get_text(strip=True) if sector_tag else None
            
            address = ""
            address_tag = article.find('address', class_='text-14 text-gray-700 flex-1')
            if address_tag:
                address = re.sub(r'\s+', ' ', address_tag.get_text(strip=True))
            
            city = "À déterminer"
            if address:
                cities = ['Cotonou', 'Porto-Novo', 'Parakou', 'Abomey-Calavi', 'Ouidah', 'Bohicon', 'Abomey']
                for c in cities:
                    if c in address:
                        city = c
                        break
            
            tel_tag = article.find('a', href=lambda href: href and href.startswith('tel:'))
            phone = None
            if tel_tag:
                phone = tel_tag['href'].replace('tel:', '').strip()
                phone = re.sub(r'[\s+]', '', phone)
                
                if phone.startswith('+229'):
                    phone = phone[4:]
                elif phone.startswith('229'):
                    phone = phone[3:]
                
                if len(phone) > 8:
                    phone = phone[-8:]
            
            description = ""
            desc_elem = article.find('div', class_='text-gray-700 text-14')
            if desc_elem:
                desc_text = desc_elem.get_text(strip=True)
                if len(desc_text) > 20:
                    description = desc_text
            
            source_url = None
            if name_tag and name_tag.get('href'):
                source_url = f"https://www.goafricaonline.com{name_tag['href']}"
            
            if name and phone and len(phone) >= 8:
                normalized_phone = normalize(phone)
                if normalized_phone and normalized_phone != "À déterminer":
                    return {
                        'name': name[:100],
                        'phone': normalized_phone,
                        'sector': sector[:100] if sector else "À déterminer",
                        'city': city[:100],
                        'address': address[:500] if address else "",
                        'description': description[:500] if description else "",
                        'source': 'go_africa_online',
                        'source_url': source_url
                    }
            
            return None
            
        except Exception as e:
            print(f"⚠️ Erreur parsing: {e}")
            return None
    
    def _has_next_page(self, soup: BeautifulSoup) -> bool:
        next_link = soup.find('a', {'rel': 'next'})
        if next_link:
            return True
        
        pagination = soup.find('ul', class_='pagination')
        if pagination:
            items = pagination.find_all('li')
            for item in items:
                if item.get('class') and 'active' in item.get('class'):
                    next_item = item.find_next_sibling('li')
                    if next_item and not next_item.get('class'):
                        return True
        
        return False


# ==================== SCRAPER SHOWROOM AFRICA ====================
class ShowroomScraper:
    """Scraper pour Showroom Africa"""
    
    def __init__(self, country_code: str = "bj"):
        self.country_code = country_code
        self.base_url = f"https://www.showroomafrica.com/{country_code}"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "fr-FR,fr;q=0.9",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def search_businesses(self, limit: int = 20, start_page: int = 1, max_pages: Optional[int] = None, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Scrape les entreprises depuis Showroom Africa
        
        Args:
            limit: Nombre maximum d'entreprises
            start_page: Page de départ (pour la pagination intelligente)
            max_pages: Nombre maximum de pages par sous-catégorie
            category: Catégorie spécifique
        """
        all_prospects = []
        
        print(f"🔍 Scraping Showroom Africa ({self.country_code.upper()}) depuis page {start_page}")
        
        subcats = self._get_all_subcategory_urls()
        if not subcats:
            print("❌ Aucune catégorie trouvée")
            return []
        
        print(f"📊 {len(subcats)} sous-catégories trouvées")

        for subcat in subcats:
            secteur = subcat["secteur"]
            sous_secteur = subcat["sous_secteur"]
            
            # Filtrer les catégories non pertinentes
            excluded = ["administration", "communication", "comptabilité"]
            if any(kw in secteur.lower() or kw in sous_secteur.lower() for kw in excluded):
                print(f"⏭Skip: {secteur} › {sous_secteur}")
                continue
                
            if len(all_prospects) >= limit:
                break
            
            url = subcat["url"]
            
            if category and category.lower() not in secteur.lower() and category.lower() not in sous_secteur.lower():
                continue
            
            print(f"  📂 {secteur} › {sous_secteur}")
            
            page_num = start_page  # ← Démarrer à la page demandée
            current_url = url
            
            while current_url and len(all_prospects) < limit:
                print(f"    📄 Page {page_num}...", end=" ", flush=True)
                time.sleep(1.5)
                
                companies, next_url = self._scrape_listing_page(
                    current_url, secteur, sous_secteur
                )
                
                print(f"{len(companies)} entreprises")
                
                remaining = limit - len(all_prospects)
                all_prospects.extend(companies[:remaining])
                
                if max_pages and page_num >= max_pages:
                    break
                if not next_url or next_url == current_url:
                    break
                
                current_url = next_url
                page_num += 1
        
        print(f"✅ Showroom Africa: {len(all_prospects)} prospects extraits")
        return all_prospects
    
    def _get_all_subcategory_urls(self) -> List[Dict[str, str]]:
        soup = self._get_soup(f"{self.base_url}/categorie")
        if not soup:
            return []
        
        subcats = []
        current_sector = ""
        
        for tag in soup.select("h3, ul li a"):
            if tag.name == "h3":
                current_sector = self._clean(tag.get_text())
            elif tag.name == "a" and tag.get("href", "").startswith("https://"):
                href = tag["href"]
                label = self._clean(tag.get_text())
                if href != self.base_url and "/categorie" not in href:
                    subcats.append({
                        "secteur": current_sector,
                        "sous_secteur": label,
                        "url": href,
                    })
        
        return subcats
    
    def _scrape_listing_page(self, url: str, secteur: str, sous_secteur: str) -> tuple:
        soup = self._get_soup(url)
        if not soup:
            return [], None
        
        companies = []
        cards = self._find_company_cards(soup)
        seen = set()
        
        for card in cards:
            nom_tag = card.select_one("h3 a")
            if not nom_tag:
                continue
            
            nom = self._clean(nom_tag.get_text())
            if not nom or nom in seen:
                continue
            
            seen.add(nom)
            data = self._parse_company_card(card, secteur, sous_secteur)
            if data.get("nom"):
                prospect = {
                    "name": data["nom"],
                    "phone": data["telephone"] or "À déterminer",
                    "sector": data["secteur"],
                    "city": data["ville"] or "À déterminer",
                    "address": data["adresse"],
                    "description": data["description"],
                    "source": f"showroom_africa_{self.country_code}",
                    "source_url": None
                }
                companies.append(prospect)
        
        next_url = None
        next_link = soup.find("a", string=re.compile(r"suivant|next|›|»", re.I))
        if next_link and next_link.get("href"):
            next_url = urljoin(url, next_link["href"])
        
        return companies, next_url
    
    def _find_company_cards(self, soup: BeautifulSoup) -> List:
        cards = []
        
        for tag in ["article", "section", "div"]:
            candidates = soup.find_all(tag)
            for c in candidates:
                if c.find("h3") and c.find("h3").find("a"):
                    if len(c.find_all("h3")) == 1:
                        cards.append(c)
            if cards:
                break
        
        if not cards:
            for h3 in soup.select("h3 a[href]"):
                parent = h3.find_parent(["article", "section", "div", "li"])
                if parent:
                    cards.append(parent)
        
        return cards
    
    def _parse_company_card(self, card, secteur: str, sous_secteur: str) -> Dict[str, Any]:
        nom = self._clean(card.select_one("h3 a").get_text()) if card.select_one("h3 a") else ""
        
        adresse = ""
        ville = ""
        telephone = ""
        description = ""
        
        items = card.select("li")
        for li in items:
            text = self._clean(li.get_text())
            if re.search(r"\(\+\d+\)", text) or li.select("strong"):
                nums = re.findall(r"[\d\s]{8,15}", text)
                telephone = " / ".join(n.strip() for n in nums if n.strip())
            elif text:
                adresse = text
        
        desc_tag = card.select_one("p:not(:has(li))")
        if not desc_tag:
            for p in card.select("p"):
                t = self._clean(p.get_text())
                if t and not re.search(r"\(\+\d+\)", t) and len(t) > 40:
                    description = t
                    break
        else:
            description = self._clean(desc_tag.get_text())
        
        if "," in adresse:
            parts = adresse.rsplit(",", 1)
            adresse = self._clean(parts[0])
            ville = self._clean(parts[1])
        
        return {
            "nom": nom,
            "ville": ville,
            "adresse": adresse,
            "secteur": secteur,
            "sous_secteur": sous_secteur,
            "telephone": telephone,
            "description": description,
        }
    
    def _get_soup(self, url: str) -> Optional[BeautifulSoup]:
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as e:
            print(f"⚠️ Erreur: {e}")
            return None
    
    def _clean(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip() if text else ""


# ==================== SERVICE UNIFIÉ ====================
class ScraperService:
    """Service de scraping unifié avec pagination intelligente"""
    
    def __init__(self):
        self.africa_scraper = AfricaOnlineScraper() 
        self.showroom_scraper = ShowroomScraper(country_code="bj")
    
    def collect_prospects(self, source: str = "africa", page: int = 1, **kwargs) -> List[Dict[str, Any]]:
        """
        Collecte des prospects avec pagination intelligente
        
        Args:
            source: "africa", "showroom", ou "all"
            page: Page de départ (pour continuer là où on s'était arrêté)
            limit: Nombre maximum de prospects
            max_pages: Nombre maximum de pages à scraper
        """
        all_prospects = []
        
        limit = kwargs.get('limit', 20)
        max_pages = kwargs.get('max_pages', 5)
        query = kwargs.get('query', 'entreprises Bénin')
        category = kwargs.get('category')
        country = kwargs.get('country', 'bj')
        
        # Go Africa
        if source in ["africa", "all"]:
            try:
                print(f"🔍 Scraping Go Africa (depuis page {page}, max {max_pages} pages)...")
                africa_results = self.africa_scraper.search_businesses(
                    limit=limit,
                    start_page=page,
                    max_pages=max_pages
                )
                all_prospects.extend(africa_results)
                print(f"✅ Go Africa: {len(africa_results)} prospects")
            except Exception as e:
                print(f"❌ Erreur sur africa: {e}")
        
        # Showroom Africa
        if source in ["showroom", "all"]:
            try:
                print(f"🔍 Scraping Showroom Africa ({country}) depuis page {page}...")
                scraper = ShowroomScraper(country_code=country)
                results = scraper.search_businesses(
                    limit=limit,
                    start_page=page,
                    max_pages=max_pages,
                    category=category
                )
                all_prospects.extend(results)
                print(f"✅ Showroom Africa: {len(results)} prospects")
            except Exception as e:
                print(f"❌ Erreur Showroom: {e}")
        
        print(f"📊 TOTAL: {len(all_prospects)} prospects collectés")
        return all_prospects