import requests
from bs4 import BeautifulSoup
import re
import os
import json
import time
from dotenv import load_dotenv
from urllib.parse import urljoin
from .normaliseur import extract_phone_from_text
from typing import List, Dict, Any, Optional
import requests


load_dotenv()

        
# SCRAPER GO AFRICA
class AfricaOnlineScraper:
    """Scraper pour Go Africa Online avec pagination"""
    
    def __init__(self):
        self.base_url = "https://www.goafricaonline.com/bj/annuaire-resultat"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
        }
    
    def search_businesses(self, limit: int = 20, max_pages: int = 100, **kwargs) -> List[Dict[str, Any]]:
        """
        Scrape les entreprises depuis Go Africa Online avec pagination
        
        Args:
            limit: Nombre maximum d'entreprises à scraper
            max_pages: Nombre maximum de pages à parcourir (défaut: 5)
        """
        all_prospects = []
        page = 1
        total_extracted = 0
        
        print(f"🔍 Scraping Go Africa Online (max {max_pages} pages)...")
        
        while len(all_prospects) < limit and page <= max_pages:
            try:
                print(f"📄 Page {page}...")
                
                # Paramètres de la page
                params = {
                    "type": "company",
                    "where": "country-BJ",
                    "p": page  # ← Pagination
                }
                
                response = requests.get(
                    self.base_url, 
                    headers=self.headers, 
                    params=params, 
                    timeout=15
                )
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extraire les entreprises de la page
                prospects_page = self._parse_page(soup)
                
                if not prospects_page:
                    print(f"Plus d'entreprises à la page {page}")
                    break
                
                # Ajouter les prospects
                remaining = limit - len(all_prospects)
                all_prospects.extend(prospects_page[:remaining])
                
                print(f" {len(prospects_page)} entreprises trouvées, total: {len(all_prospects)}")
                
                # Vérifier s'il y a une page suivante
                if not self._has_next_page(soup):
                    print(f" Plus de pages disponibles")
                    break
                
                page += 1
                
                # Petite pause pour éviter le rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                print(f"Erreur page {page}: {e}")
                break
        
        print(f"Go Africa: {len(all_prospects)} prospects extraits sur {page} pages")
        return all_prospects
    
    def _parse_page(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Parse une page et extrait les entreprises"""
        prospects = []
        articles = soup.find_all('article', {'data-role': 'company'})
        
        for article in articles:
            prospect = self._parse_article(article)
            if prospect:
                prospects.append(prospect)
        
        return prospects
    
    def _parse_article(self, article) -> Dict[str, Any]:
        """Parse un article d'entreprise"""
        try:
            # Nom
            name_tag = article.find('a', class_='stretched-link')
            name = name_tag.get_text(strip=True) if name_tag else None
            
            # Secteur
            sector_tag = article.find('div', class_='text-14 text-brand-blue mb-4')
            sector = sector_tag.get_text(strip=True) if sector_tag else None
            
            # Adresse
            address = ""
            address_tag = article.find('address', class_='text-14 text-gray-700 flex-1')
            if address_tag:
                address = re.sub(r'\s+', ' ', address_tag.get_text(strip=True))
            
            # Ville
            city = "À déterminer"
            if address:
                cities = ['Cotonou', 'Porto-Novo', 'Parakou', 'Abomey-Calavi', 'Ouidah', 'Bohicon', 'Abomey']
                for c in cities:
                    if c in address:
                        city = c
                        break
            
            # Téléphone
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
            
            # Description
            description = ""
            desc_elem = article.find('div', class_='text-gray-700 text-14')
            if desc_elem:
                desc_text = desc_elem.get_text(strip=True)
                if len(desc_text) > 20:
                    description = desc_text
            
            # URL source
            source_url = None
            if name_tag and name_tag.get('href'):
                source_url = f"https://www.goafricaonline.com{name_tag['href']}"
            
            if name and phone and len(phone) >= 8:
                from app.services.normaliseur import normalize
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
            print(f" Erreur parsing: {e}")
            return None
    
    def _has_next_page(self, soup: BeautifulSoup) -> bool:
        """Vérifie s'il y a une page suivante"""
        # Chercher le lien "Next" dans la pagination
        next_link = soup.find('a', {'rel': 'next'})
        if next_link:
            return True
        
        # Alternative: chercher le dernier lien de pagination
        pagination = soup.find('ul', class_='pagination')
        if pagination:
            # Vérifier si le dernier élément n'est pas "disabled"
            items = pagination.find_all('li')
            for item in items:
                if item.get('class') and 'active' in item.get('class'):
                    # La page active, vérifier s'il y a un "Next"
                    next_item = item.find_next_sibling('li')
                    if next_item and not next_item.get('class'):
                        return True
        
        return False

#SCRAPER SHOWROOM AFRICA

class ShowroomScraper:
    """
    Scraper pour Showroom Africa
    Pays supportés : bj (Bénin), tg (Togo), ci (Côte d'Ivoire), sn (Sénégal), cm (Cameroun)
    """
    
    def __init__(self, country_code: str = "bj"):
        self.country_code = country_code
        self.base_url = f"https://www.showroomafrica.com/{country_code}"
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "fr-FR,fr;q=0.9",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def search_businesses(
        self,
        limit: int = 20,
        max_pages: Optional[int] = None,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape les entreprises depuis Showroom Africa
        
        Args:
            limit: Nombre maximum d'entreprises
            max_pages: Nombre maximum de pages par sous-catégorie
            category: Catégorie spécifique (ex: "restaurants", "hotels")
        """
        all_prospects = []
        
        print(f"🔍 Scraping Showroom Africa ({self.country_code.upper()})")
        
        # Récupérer les catégories
        subcats = self._get_all_subcategory_urls()
        if not subcats:
            print("Aucune catégorie trouvée")
            return []
        
        print(f"{len(subcats)} sous-catégories trouvées")
        
        for subcat in subcats:
            if len(all_prospects) >= limit:
                break
            
            secteur = subcat["secteur"]
            sous_secteur = subcat["sous_secteur"]
            url = subcat["url"]
            
            # Filtrer par catégorie si spécifiée
            if category and category.lower() not in secteur.lower() and category.lower() not in sous_secteur.lower():
                continue
            
            print(f"  📂 {secteur} › {sous_secteur}")
            
            page_num = 1
            current_url = url
            
            while current_url and len(all_prospects) < limit:
                print(f"    📄 Page {page_num}...", end=" ", flush=True)
                time.sleep(1.5)  # Délai pour respecter le site
                
                companies, next_url = self._scrape_listing_page(
                    current_url, secteur, sous_secteur
                )
                
                print(f"{len(companies)} entreprises")
                
                # Ajouter les entreprises
                remaining = limit - len(all_prospects)
                all_prospects.extend(companies[:remaining])
                
                # Pagination
                if max_pages and page_num >= max_pages:
                    break
                if not next_url or next_url == current_url:
                    break
                
                current_url = next_url
                page_num += 1
        
        print(f"✅ Showroom Africa: {len(all_prospects)} prospects extraits")
        return all_prospects
    
    def _get_all_subcategory_urls(self) -> List[Dict[str, str]]:
        """Récupère toutes les sous-catégories"""
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
    
    def _scrape_listing_page(
        self,
        url: str,
        secteur: str,
        sous_secteur: str
    ) -> tuple[List[Dict[str, Any]], Optional[str]]:
        """Scrape une page de liste"""
        soup = self._get_soup(url)
        if not soup:
            return [], None
        
        companies = []
        
        # Trouver les cartes d'entreprises
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
                # Transformer au format attendu par ton système
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
        
        # Pagination
        next_url = None
        next_link = soup.find("a", string=re.compile(r"suivant|next|›|»", re.I))
        if next_link and next_link.get("href"):
            next_url = urljoin(url, next_link["href"])
        
        return companies, next_url
    
    def _find_company_cards(self, soup: BeautifulSoup) -> List:
        """Trouve les cartes d'entreprises dans la page"""
        cards = []
        
        # Méthode 1 : blocs section/article
        for tag in ["article", "section", "div"]:
            candidates = soup.find_all(tag)
            for c in candidates:
                if c.find("h3") and c.find("h3").find("a"):
                    if len(c.find_all("h3")) == 1:
                        cards.append(c)
            if cards:
                break
        
        # Méthode 2 (fallback)
        if not cards:
            for h3 in soup.select("h3 a[href]"):
                parent = h3.find_parent(["article", "section", "div", "li"])
                if parent:
                    cards.append(parent)
        
        return cards
    
    def _parse_company_card(self, card, secteur: str, sous_secteur: str) -> Dict[str, Any]:
        """Parse une carte d'entreprise"""
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
        
        # Description
        desc_tag = card.select_one("p:not(:has(li))")
        if not desc_tag:
            for p in card.select("p"):
                t = self._clean(p.get_text())
                if t and not re.search(r"\(\+\d+\)", t) and len(t) > 40:
                    description = t
                    break
        else:
            description = self._clean(desc_tag.get_text())
        
        # Extraire la ville depuis l'adresse
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
        """Télécharge une page et retourne le BeautifulSoup"""
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as e:
            print(f"    ⚠️ Erreur: {e}")
            return None
    
    def _clean(self, text: str) -> str:
        """Nettoie le texte"""
        return re.sub(r"\s+", " ", text).strip() if text else ""

# ==================== SERVICE UNIFIÉ ====================

class ScraperService:
    """Service de scraping unifié"""
    
    def __init__(self):
        self.africa_scraper = AfricaOnlineScraper() 
        self.showroom_scraper = ShowroomScraper(country_code="bj")

    def collect_prospects(self, source: str = "africa", **kwargs) -> List[Dict[str, Any]]:
        """Collecte des prospects de'une source GoAfricaOnine pour une première version"""
        all_prospects = []
        
        limit = kwargs.get('limit', 20)
        query = kwargs.get('query', 'entreprises Bénin')
        max_pages = kwargs.get('max_pages', 5)
        category = kwargs.get('category')
        country = kwargs.get('country', 'bj')
        
        if source in ["africa","all"]:
            try:
                print(f"Scraping Go Africa (max {max_pages} pages)...")
                africa_results = self.africa_scraper.search_businesses(
                    limit=limit,
                    max_pages=max_pages
                )
                all_prospects.extend(africa_results)
                print(f"Go Africa: {len(africa_results)} prospects")
            except Exception as e:
                print(f" Erreur sur africa: {e}")
    
        if source in ["showroom","all"]:
            try:
                # Créer un scraper pour le pays demandé
                scraper = ShowroomScraper(country_code=country)
                prospects = scraper.search_businesses(
                    limit=limit,
                    max_pages=max_pages,
                    category=category
                )
                all_prospects.extend(prospects)
                print(f"Showroom Africa ({country}): {len(prospects)} prospects")
            except Exception as e:
                print(f"Erreur Showroom: {e}")
        print(f"TOTAL: {len(all_prospects)} prospects collectés")
        return all_prospects