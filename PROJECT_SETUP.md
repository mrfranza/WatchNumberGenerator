# Watch Number Generator - Project Setup

## Panoramica Progetto

Applicazione GTK4/Python con Adwaita per generare numeri 3D stampabili come quadranti per orologi.

## Stack Tecnologico

- **UI Framework**: GTK4 + libadwaita
- **Linguaggio**: Python 3.11+
- **Generazione 3D**: numpy-stl / trimesh
- **Rendering 2D**: Cairo (integrato con GTK)
- **Formato Export**: STL (Standard Tessellation Language)
- **Build System**: Meson + Ninja (preparazione futura per Flatpak)

## Struttura del Progetto

```
WatchNumberGenerator/
├── src/
│   ├── main.py                 # Entry point applicazione
│   ├── window.py               # Finestra principale GTK
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── controls_panel.py  # Pannello controlli (raggi, font, stili)
│   │   ├── preview_2d.py      # Canvas 2D con Cairo
│   │   └── preview_3d.py      # Preview mesh 3D (opzionale)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── mesh_generator.py  # Generazione mesh STL
│   │   ├── font_handler.py    # Gestione font di sistema
│   │   ├── distortion.py      # Filtri distorsione numeri
│   │   └── exporter.py        # Export ZIP con metadata
│   └── utils/
│       ├── __init__.py
│       └── geometry.py        # Calcoli geometrici
├── data/
│   ├── ui/
│   │   └── window.ui          # Blueprint UI (opzionale)
│   └── icons/
├── tests/
├── meson.build
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Funzionalità Principali

### 1. Input Parametri Base
- **Raggio Esterno**: Diametro massimo quadrante (mm)
- **Raggio Interno**: Delimitatore per dimensione numeri (mm)
- **Stile Numerazione**:
  - Decimale (1-12)
  - Romano (I-XII)
  - Opzione: Tutti i numeri (1-12) o solo cardinali (12, 3, 6, 9)

### 2. Controlli Mesh 3D
- **Profondità Estrusione**: Spessore numeri (mm)
- **Margine Superiore/Inferiore**: Padding tra numeri e raggi (mm)
- **Margine Laterale**: Spaziatura orizzontale

### 3. Filtri Distorsione (con slider)
- **Irregolarità Bordi**: Randomizzazione vertici
- **Ruvidezza Superficie**: Noise procedurale
- **Deformazione Prospettica**: Stretch radiale
- **Erosione**: Effetto consumato/vintage
- **Seed Randomness**: Per risultati riproducibili

### 4. Preview Interattiva 2D
- **Visualizzazione**:
  - Cerchi dei due raggi
  - Posizionamento numeri con dimensioni
  - Quote tecniche (distanze, angoli)
  - Griglia opzionale
- **Interazioni**:
  - Zoom (scroll mouse / pinch)
  - Pan (drag)
  - Reset vista

### 5. Preview 3D (opzionale)
- Rendering semplificato delle mesh generate
- Rotazione modello

### 6. Export
- **Formato Archivio**: ZIP
- **Contenuto**:
  - `numbers/individual/` - STL singoli (1.stl, 2.stl, ...)
  - `numbers/combined.stl` - Mesh unica con tutti i numeri
  - `preview.png` - Screenshot grafico 2D
  - `README.txt` - Metadata progetto:
    ```
    Watch Number Generator Export
    ==============================
    Data: YYYY-MM-DD HH:MM

    Parametri:
    - Raggio Esterno: XXX mm
    - Raggio Interno: YYY mm
    - Stile: Decimale/Romano
    - Numeri: Tutti / Solo Cardinali
    - Profondità: ZZZ mm
    - Filtri Applicati: [lista]

    File Generati:
    - 12 mesh individuali (numbers/individual/)
    - 1 mesh combinata (numbers/combined.stl)
    ```

## Setup Iniziale

### 1. Ambiente Virtuale

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
```

### 2. Dipendenze Python

```bash
pip install --upgrade pip
pip install pygobject PyGObject-stubs
pip install numpy numpy-stl trimesh
pip install pillow  # Per screenshot
```

### 3. Dipendenze Sistema (Fedora/RHEL)

```bash
sudo dnf install gtk4-devel libadwaita-devel python3-gobject cairo-devel
sudo dnf install python3-cairo python3-cairo-devel
```

### 4. Verifica Installazione GTK4

```python
# test_gtk.py
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw
print("GTK4 + Adwaita OK!")
```

## Prossimi Passi con Claude Code

1. **Inizializzare Struttura**:
   - Creare directory e file base
   - Setup `pyproject.toml` e `requirements.txt`

2. **Implementare Window Base**:
   - Finestra principale Adwaita
   - Layout responsive (sidebar + area preview)

3. **Pannello Controlli**:
   - Spin button per raggi
   - Dropdown stile numerazione
   - Switch "Tutti numeri / Solo cardinali"
   - Slider parametri mesh e distorsioni

4. **Canvas 2D Cairo**:
   - Rendering cerchi e numeri
   - Sistema zoom/pan
   - Quote tecniche

5. **Generatore Mesh**:
   - Conversione font TrueType → poligoni
   - Estrusione 3D
   - Applicazione filtri distorsione
   - Export STL

6. **Sistema Export**:
   - Generazione ZIP
   - Screenshot automatico
   - Metadata README

7. **Packaging Flatpak** (fase finale):
   - Manifest `com.example.WatchNumberGenerator.json`
   - Meson build
   - Test sandbox

## Note Tecniche

- **Font Rendering**: Usare `fontconfig` + `freetype` per ottenere outline vettoriali
- **Distorsioni**: Applicare trasformazioni sui vertici prima dell'estrusione
- **Performance**: Generare mesh in thread separato con `GLib.idle_add()` per non bloccare UI
- **Validazione**: Raggio interno deve essere < raggio esterno (con margine minimo)

## Linee Guida UI (Adwaita)

- Usare `AdwPreferencesGroup` per raggruppare controlli
- `AdwHeaderBar` per toolbar
- `AdwToastOverlay` per notifiche
- Rispettare spacing standard (12px, 18px)
- Icone da `icon-library` se disponibili

## Domande Aperte

- [ ] Unità di misura alternative (inch oltre a mm)?
- [ ] Supporto esportazione altri formati (OBJ, 3MF)?
- [ ] Template preimpostati (stili vintage, moderno, ecc.)?
- [ ] Anteprima rendering realistico (con texture)?

## Risorse

- [GTK4 Python Tutorial](https://docs.gtk.org/gtk4/)
- [Libadwaita HIG](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/)
- [numpy-stl docs](https://numpy-stl.readthedocs.io/)
- [Flatpak Builder](https://docs.flatpak.org/en/latest/flatpak-builder.html)
