# Quick Start Guide

## Setup (Prima volta)

### 1. Installa dipendenze di sistema

**Fedora/RHEL:**
```bash
sudo dnf install gtk4-devel libadwaita-devel python3-gobject
sudo dnf install cairo-devel python3-cairo python3-cairo-devel
```

**Ubuntu/Debian:**
```bash
sudo apt install libgtk-4-dev libadwaita-1-dev python3-gi
sudo apt install libcairo2-dev python3-cairo
```

### 2. Crea ambiente virtuale Python

```bash
python3 -m venv venv
source venv/bin/activate  # Su Linux/Mac
# oppure
venv\Scripts\activate  # Su Windows
```

### 3. Installa dipendenze Python

```bash
pip install -r requirements.txt
```

## Avvia l'applicazione

### Metodo 1: Script
```bash
./run.sh
```

### Metodo 2: Manuale
```bash
cd src
python main.py
```

## Utilizzo Base

1. **Imposta dimensioni**
   - Raggio esterno: diametro massimo del quadrante
   - Raggio interno: delimita l'area per i numeri (deve essere almeno 5mm più piccolo)

2. **Scegli stile**
   - Sistema numerico: Decimale (1-12) o Romano (I-XII)
   - Set: Tutti i numeri o solo cardinali (12, 3, 6, 9)

3. **Seleziona font**
   - Clicca sul pulsante font per scegliere il carattere
   - Font più grassetti funzionano meglio per la stampa 3D

4. **Parametri mesh**
   - Profondità estrusione: spessore dei numeri (consigliato: 2-3mm)
   - Margini: spaziatura dai bordi (consigliato: 1mm)

5. **Filtri distorsione (opzionale)**
   - Attiva l'interruttore per abilitare
   - Regola gli slider per effetti artistici:
     - Edge Irregularity: bordi organici
     - Surface Roughness: texture superficiale
     - Perspective Stretch: deformazione radiale
     - Erosion: effetto vintage/consumato

6. **Preview**
   - Zoom: rotella del mouse
   - Pan: trascina con il mouse
   - I numeri sono visualizzati nelle loro posizioni finali

7. **Export**
   - Clicca "Export STL Files"
   - Scegli dove salvare il file ZIP
   - Il file contiene:
     - `numbers/individual/*.stl` - File separati
     - `numbers/combined.stl` - Mesh unica
     - `README.txt` - Parametri e info
     - `preview.png` - Screenshot layout

## Consigli per la Stampa 3D

### Impostazioni Consigliate
- **Layer Height**: 0.1-0.2mm (più basso = dettaglio migliore)
- **Infill**: 20-30%
- **Supporti**: Potrebbero servire per font complessi
- **Orientamento**: Numeri rivolti verso l'alto

### Materiali
- **PLA**: Facile, buon dettaglio
- **PETG**: Più resistente
- **Resin**: Miglior dettaglio per numeri piccoli

## Risoluzione Problemi

### L'app non si avvia
- Verifica che tutte le dipendenze di sistema siano installate
- Assicurati che l'ambiente virtuale sia attivato
- Controlla errori con: `python src/main.py 2>&1 | less`

### Preview vuota
- Controlla che raggio interno < raggio esterno - 5mm
- Prova a resettare i valori predefiniti

### Export non funziona
- Verifica di avere permessi di scrittura nella cartella di destinazione
- Assicurati che ci sia spazio su disco

## Prossimi Passi

Vedi [PROJECT_SETUP.md](PROJECT_SETUP.md) per:
- Dettagli architetturali
- Piano di sviluppo
- Preparazione Flatpak
