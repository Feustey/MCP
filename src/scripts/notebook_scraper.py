import asyncio
import json
import os
import time
from typing import Dict, List
from datetime import datetime
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup

class NotebookScraper:
    def __init__(self, notebook_url: str):
        load_dotenv()
        self.notebook_url = notebook_url
        self.output_dir = "output"
        self.email = os.getenv("GMAIL_EMAIL")
        self.password = os.getenv("GMAIL_PASSWORD")
        
        if not self.email or not self.password:
            raise ValueError("Les identifiants Gmail sont manquants dans le fichier .env")
        
        # Configuration de Chrome en mode headless
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 20)

    def fetch_content(self) -> str:
        """Récupère le contenu HTML de la page du notebook avec authentification."""
        try:
            # Accéder à la page de connexion Google
            print("Accès à la page de connexion...")
            self.driver.get("https://accounts.google.com/signin")
            
            # Attendre et remplir l'email
            print("Saisie de l'email...")
            email_input = self.wait.until(
                EC.presence_of_element_located((By.NAME, "identifier"))
            )
            email_input.send_keys(self.email)
            email_input.submit()
            
            # Attendre et remplir le mot de passe
            print("Saisie du mot de passe...")
            password_input = self.wait.until(
                EC.presence_of_element_located((By.NAME, "password"))
            )
            password_input.send_keys(self.password)
            password_input.submit()
            
            # Attendre que la redirection soit terminée
            time.sleep(5)
            
            # Accéder au notebook
            print("Accès au notebook...")
            self.driver.get(self.notebook_url)
            
            # Attendre que le contenu soit chargé
            self.wait.until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Récupérer le contenu HTML
            return self.driver.page_source
            
        except TimeoutException as e:
            print(f"Timeout lors de l'attente d'un élément: {str(e)}")
            raise
        except Exception as e:
            print(f"Erreur lors de la récupération du contenu: {str(e)}")
            raise
        finally:
            self.driver.quit()

    def parse_content(self, html_content: str) -> Dict:
        """Parse le contenu HTML et extrait les informations pertinentes."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extraction du contenu
        notebook_data = {
            "title": self._extract_title(soup),
            "sections": self._extract_sections(soup),
            "metadata": {
                "scraped_at": datetime.now().isoformat(),
                "source_url": self.notebook_url
            }
        }
        
        return notebook_data

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extrait le titre du notebook."""
        # Recherche plus spécifique pour le titre
        title_element = soup.find("div", {"class": "notebook-title"}) or \
                       soup.find("h1", {"class": "title"}) or \
                       soup.find("h1")
        return title_element.text.strip() if title_element else "Untitled Notebook"

    def _extract_sections(self, soup: BeautifulSoup) -> List[Dict]:
        """Extrait les sections du notebook."""
        sections = []
        
        # Recherche plus spécifique pour les sections
        section_elements = soup.find_all(["div", "section"], {"class": ["note-section", "content-section"]})
        
        for element in section_elements:
            title = element.find(["h2", "h3", "h4"])
            content = element.find(["div", "p"], {"class": ["note-content", "section-content"]})
            
            if title or content:
                sections.append({
                    "title": title.text.strip() if title else "Sans titre",
                    "content": content.text.strip() if content else "",
                    "level": int(title.name[1]) if title and title.name.startswith('h') else 1
                })
        
        return sections

    def save_as_json(self, data: Dict, filename: str = "notebook.json"):
        """Sauvegarde les données au format JSON."""
        os.makedirs(self.output_dir, exist_ok=True)
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return filepath

    def save_as_markdown(self, data: Dict, filename: str = "notebook.md"):
        """Convertit et sauvegarde les données au format Markdown."""
        os.makedirs(self.output_dir, exist_ok=True)
        filepath = os.path.join(self.output_dir, filename)
        
        markdown_content = f"# {data['title']}\n\n"
        markdown_content += f"*Scraped from: {data['metadata']['source_url']}*\n\n"
        markdown_content += f"*Last updated: {data['metadata']['scraped_at']}*\n\n"
        
        for section in data['sections']:
            level = '#' * (section['level'])
            markdown_content += f"{level} {section['title']}\n\n"
            markdown_content += f"{section['content']}\n\n"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        return filepath

def main():
    notebook_url = "https://notebooklm.google.com/notebook/6cfbfe60-3b64-4522-a867-229f55dd73b0"
    scraper = NotebookScraper(notebook_url)
    
    try:
        print("Récupération du contenu du notebook...")
        html_content = scraper.fetch_content()
        
        print("Analyse du contenu...")
        notebook_data = scraper.parse_content(html_content)
        
        print("Sauvegarde au format JSON...")
        json_path = scraper.save_as_json(notebook_data)
        print(f"Fichier JSON sauvegardé: {json_path}")
        
        print("Sauvegarde au format Markdown...")
        md_path = scraper.save_as_markdown(notebook_data)
        print(f"Fichier Markdown sauvegardé: {md_path}")
        
    except Exception as e:
        print(f"Erreur: {str(e)}")

if __name__ == "__main__":
    main() 