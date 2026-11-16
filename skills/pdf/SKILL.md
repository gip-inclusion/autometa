---
name: pdf
description: Lire un PDF (texte, tableaux, pages scannées), en produire un (rapport, export) ou réassembler ses pages (fusionner, extraire, réordonner, pivoter). À utiliser dès qu'une demande porte sur un fichier .pdf ou demande d'en produire un.
---

# PDF

Trois bibliothèques Python, présentes en production : `pdfplumber` pour lire, `pypdfium2` pour rendre et réassembler des pages, `reportlab` pour produire. Rien d'autre n'est installé (ni `pypdf`, ni `pdftotext`, ni `qpdf`, ni moteur OCR) et rien ne s'installe.

## Lire

```python
import pdfplumber

with pdfplumber.open(chemin) as pdf:  # password="…" pour un PDF protégé
    for page in pdf.pages:
        texte = page.extract_text()
        tableaux = page.extract_tables()
```

- `extract_tables()` ne voit que les tableaux tracés avec des filets. Sans filets : `page.extract_tables({"vertical_strategy": "text", "horizontal_strategy": "text"})`, puis retirer les lignes vides.
- Sur un long document, lire d'abord quelques pages (`pdf.pages[:3]`) pour en repérer la structure.

## Voir une page

Une page scannée rend un texte vide ou illisible : c'est une image. La rendre en PNG, puis lire l'image.

```python
import os

import pypdfium2 as pdfium

# dossier : le dossier de travail de la conversation, /tmp/$AUTOMETA_CONVERSATION_ID
os.makedirs(dossier, exist_ok=True)
pdfium.PdfDocument(chemin)[0].render(scale=2).to_pil().save(f"{dossier}/page-1.png")
```

Même méthode pour un graphique, une mise en page, ou pour vérifier un PDF produit. Sur un long document scanné, demander à l'utilisateur quelles pages lire.

## Réassembler

```python
import pypdfium2 as pdfium

sortie = pdfium.PdfDocument.new()
sortie.import_pages(pdfium.PdfDocument(chemin), [2, 0])  # pages 3 puis 1 ; sans liste, toutes
sortie[0].set_rotation(90)
sortie.save(destination)
```

Pour fusionner, un `import_pages` par fichier source.

## Produire

`reportlab.platypus` : `SimpleDocTemplate`, `Paragraph`, `Table`, `Image`, `PageBreak`. Les polices de base affichent les accents, `€`, `œ` et les espaces insécables. Un graphique s'enregistre en PNG avec matplotlib, puis s'insère avec `Image`.

Le fichier remis à l'utilisateur va à la racine de `/app/data/interactive/` (servi à `/interactive/`). Vérifier son rendu (« Voir une page ») avant d'en donner le lien.

## Hors de portée

Remplir un formulaire PDF, chiffrer ou signer un document, faire de l'OCR en masse : rien en production ne le permet. Le dire à l'utilisateur.
