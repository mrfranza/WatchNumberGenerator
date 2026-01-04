# Refactoring Plan - Watch Number Generator

## 🔍 Analisi Problemi Critici

### 1. **Preview 3D vs 2D Discrepanza**
**Problema**: I numeri nella preview 3D sono in posizioni completamente diverse rispetto al 2D.

**Causa Root**:
- Il 3D preview usa `mesh_generator.create_text_mesh()` che riceve contorni MA non usa le stesse trasformazioni del 2D
- Il 2D applica: posizionamento radiale, rotazione, scaling preciso, centraggio nel settore
- Il 3D riceve solo `contours` grezzi con `center_x`, `center_y` ma:
  - Non applica la stessa rotazione
  - Non rispetta i raggi inner/outer
  - Non scala correttamente

**File coinvolti**:
- `src/ui/preview_2d.py` (genera mesh_data con posizioni 2D)
- `src/ui/preview_3d.py` (visualizza mesh 3D)
- `src/core/mesh_generator.py` (crea mesh 3D dai contorni)
- `src/window.py` (coordina preview 2D e generazione 3D)

### 2. **Mesh 3D Non Stampabili**
**Problema**: Le mesh sembrano vuote e non manifold (non chiuse correttamente).

**Causa Root**:
- `mesh_generator.create_text_mesh()` usa triangolazione con mapbox-earcut
- La gestione di poligoni con buchi (es. "O", "8") potrebbe generare facce degenerate
- Side walls potrebbero avere overlap o gap
- Manca validazione mesh (manifoldness check)

**Indicatori**:
```python
# In mesh_generator.py:285-307
# Triangolazione potrebbe fallire silenziosamente
# Side walls creati manualmente potrebbero non matchare perfettamente
```

### 3. **Filtri Distorsione Inutilizzabili**
**Problema**: I filtri fanno "schifo" o non funzionano.

**Cause**:
- **distortion.py** (3D): Opera sui vertici mesh DOPO la generazione, deformando tutto
- **distortion_2d.py** (2D): Opera sui contorni vettoriali PRIMA della mesh generation
- Doppia implementazione con effetti inconsistenti
- Parametri non calibrati (noise troppo grossolano)
- Effetti troppo distruttivi per oggetti piccoli come numeri

**Problemi specifici**:
- `edge_irregularity`: Sposta vertici random senza preservare topologia
- `surface_roughness`: Noise coherent ma scala male
- `perspective_stretch`: Deforma radialmente ma rompe proporzioni
- `erosion`: Scala verso centro creando artefatti

---

## 📋 Piano di Refactoring

### FASE 1: FIX CRITICO - Allineamento 2D/3D ⚠️ PRIORITÀ ALTA

**Obiettivo**: Far sì che preview 3D mostri ESATTAMENTE la stessa geometria del 2D.

#### Task 1.1: Unificare il Pipeline di Generazione Mesh
**File**: Nuovo `src/core/unified_mesh_pipeline.py`

```python
class UnifiedMeshPipeline:
    """
    Pipeline unificato per generare mesh 3D con posizionamento corretto.
    Usa le stesse trasformazioni del 2D preview.
    """

    def generate_positioned_mesh(
        self,
        numbers_data: List[NumberPosition],
        font_desc: str,
        extrusion_depth: float,
        apply_distortions: bool = False,
        **distortion_params
    ) -> mesh.Mesh:
        """
        Genera mesh 3D con posizionamento esattamente uguale al 2D.

        Steps:
        1. Per ogni numero, ottieni contorni vettoriali dal font
        2. Applica scaling/rotazione/posizionamento IDENTICO al 2D
        3. (Opzionale) Applica distorsioni ai contorni
        4. Estrudi a 3D
        5. Combina tutte le mesh
        """
```

**Benefici**:
- Singola fonte di verità per posizionamento
- 2D e 3D usano lo stesso codice
- Facile da debuggare

#### Task 1.2: Rifattorizzare `preview_2d.py`
**Azione**: Estrarre logica di generazione mesh in `UnifiedMeshPipeline`

```python
# preview_2d.py diventa solo VISUALIZZAZIONE
class Preview2DWidget:
    def generate_mesh_data(self):
        # Chiama UnifiedMeshPipeline invece di fare tutto internamente
        from core.unified_mesh_pipeline import UnifiedMeshPipeline

        pipeline = UnifiedMeshPipeline()
        return pipeline.generate_positioned_mesh(
            numbers_data=self.positions,
            font_desc=self.font_desc,
            extrusion_depth=0.1,  # Mock per 2D
            apply_distortions=False  # Mai in preview
        )
```

#### Task 1.3: Fix `preview_3d.py` per Usare Coordinate Corrette
**File**: `src/ui/preview_3d.py`

**Azioni**:
- Rimuovere tutta la logica di "debug boxes" che mostra coordinate sbagliate
- Assicurarsi che la mesh 3D sia già posizionata correttamente
- Visualizzare solo mesh + grid + axes + dimensioni

**Rimuovere**:
```python
# ELIMINARE _draw_debug_boxes() completamente
# Le mesh dovrebbero già essere posizionate correttamente
```

#### Task 1.4: Aggiungere Dimensioni in Preview 3D
**File**: `src/ui/preview_3d.py`

**Aggiunte**:
```python
def _draw_dimension_lines(self, ctx, width, height):
    """
    Disegna linee quotatura mostrando:
    - Diametro esterno
    - Diametro interno
    - Profondità estrusione
    """
    # Disegna frecce e misure come nel 2D
```

---

### FASE 2: FIX CRITICO - Mesh Manifold e Stampabili ⚠️ PRIORITÀ ALTA

**Obiettivo**: Garantire che le mesh generate siano sempre valide e stampabili.

#### Task 2.1: Validazione e Riparazione Mesh
**File**: Nuovo `src/core/mesh_validator.py`

```python
class MeshValidator:
    """Valida e ripara mesh 3D per stampa."""

    @staticmethod
    def is_manifold(mesh_obj: mesh.Mesh) -> bool:
        """Controlla se la mesh è manifold (chiusa, senza buchi)."""
        # Usa trimesh per validazione

    @staticmethod
    def repair_mesh(mesh_obj: mesh.Mesh) -> mesh.Mesh:
        """Ripara mesh non manifold."""
        # Usa trimesh.repair.fill_holes()
        # Rimuovi facce degenerate
        # Merge vertici duplicati

    @staticmethod
    def get_mesh_stats(mesh_obj: mesh.Mesh) -> dict:
        """Ritorna statistiche mesh per debug."""
        return {
            "is_manifold": ...,
            "is_watertight": ...,
            "has_degenerate_faces": ...,
            "volume": ...,
            "surface_area": ...,
        }
```

#### Task 2.2: Riscrivere `mesh_generator.create_text_mesh()`
**File**: `src/core/mesh_generator.py`

**Problemi attuali**:
```python
# Linea 95-108: Side walls create con offset manuale
# PROBLEMA: Potrebbero non matchare perfettamente i vertici top/bottom
# SOLUZIONE: Usare trimesh.creation.extrude_polygon
```

**Nuovo approccio**:
```python
def create_text_mesh(self, contours, extrusion_depth):
    """
    Strategia migliorata:
    1. Converti contorni in Shapely Polygon (con buchi)
    2. Usa trimesh.creation.extrude_polygon() - GARANTISCE manifoldness
    3. Valida con MeshValidator
    4. Se fallisce, fallback a manual extrusion + repair
    """
    try:
        # Approccio 1: Shapely + Trimesh (più robusto)
        polygon = self._contours_to_shapely_polygon(contours)
        tmesh = trimesh.creation.extrude_polygon(polygon, extrusion_depth)
        stl_mesh = self._trimesh_to_numpy_stl(tmesh)

        # Valida
        if MeshValidator.is_manifold(stl_mesh):
            return stl_mesh

    except Exception as e:
        logging.warning(f"Trimesh approach failed: {e}")

    # Fallback: Manual extrusion + repair
    manual_mesh = self._manual_extrusion(contours, extrusion_depth)
    return MeshValidator.repair_mesh(manual_mesh)
```

#### Task 2.3: Test di Stampabilità
**File**: Nuovo `tests/test_mesh_quality.py`

```python
def test_all_numbers_are_manifold():
    """Test che tutti i numeri generati siano manifold."""
    for number in ["1", "2", ..., "I", "II", ...]:
        mesh = generate_number_mesh(number)
        assert MeshValidator.is_manifold(mesh)
        assert MeshValidator.is_watertight(mesh)
```

---

### FASE 3: RIMOZIONE E RIPENSAMENTO FILTRI DISTORSIONE 🗑️

**Obiettivo**: Rimuovere i filtri attuali e ripensarli completamente.

#### Task 3.1: Rimuovere Filtri Attuali
**Azioni**:
1. ✅ Commentare/rimuovere UI distorsioni da `window.py`
2. ✅ Commentare imports di `distortion.py` e `distortion_2d.py`
3. ✅ Rimuovere parametri distorsione da `preview_2d.update_parameters()`
4. ✅ Nascondere "Distortion Filters" group in UI

**File modificati**:
- `src/window.py`: Commentare `_create_distortion_group()`
- `src/ui/preview_2d.py`: Rimuovere parametri distorsione
- `src/window.py`: Rimuovere slider distorsioni

#### Task 3.2: Analisi Requisiti Nuovi Filtri
**Domande da rispondere**:
- Quali effetti artistici vogliamo DAVVERO?
  - Opzione 1: Vintage/worn look (edges arrotondati, piccole irregolarità)
  - Opzione 2: Handmade look (leggere imperfezioni)
  - Opzione 3: Textured (pattern superficie)
- Come devono essere i parametri?
  - Slider semplici vs preset ("Subtle", "Medium", "Heavy")
- Devono essere visibili nel 2D preview?
  - Consiglio: NO, solo in export (come ora)

#### Task 3.3: Design Nuovi Filtri (FUTURO)
**Approccio migliore**:

```python
class SubtleDistortion:
    """
    Distorsioni sottili e controllate per effetti vintage.
    Non distrugge la leggibilità.
    """

    @staticmethod
    def vintage_edges(contours, intensity=0.5):
        """
        Arrotonda leggermente gli angoli.
        Usa curve smoothing invece di noise.
        """

    @staticmethod
    def slight_irregularity(contours, intensity=0.3):
        """
        Aggiunge piccolissime irregolarità (< 1% dimensione).
        Usa Perlin noise 2D per coerenza.
        """

    @staticmethod
    def surface_texture(mesh, pattern="brushed"):
        """
        Aggiunge texture superficiale senza deformare shape.
        Solo displacement normali, non tangenziale.
        """
```

**Preset consigliati**:
- "None" (default)
- "Subtle Vintage" (slight_irregularity=0.2)
- "Handmade" (vintage_edges=0.3 + irregularity=0.4)
- "Heavily Worn" (tutti i filtri moderati)

---

## 🗂️ FASE 2.5: Export Dialog Implementation

**Obiettivo**: Implementare dialog export professionale con opzioni e validazione.

#### Task 2.4: Export Dialog UI e Funzionalità
**File**: Nuovo `src/ui/export_dialog.py`

**Features**:
```python
class ExportDialog(Adw.Dialog):
    """
    Dialog per export mesh con opzioni:
    - Formato: STL singoli, STL combinato, o entrambi
    - Cartella destinazione (file chooser)
    - Nome base file (es. "watch_numbers")
    - Include preview PNG (checkbox)
    - Include README.txt (checkbox)
    - Validazione mesh prima export
    """
```

**UI Design**:
```
┌─────────────────────────────────────────┐
│ Export Watch Numbers                  × │
├─────────────────────────────────────────┤
│                                         │
│ Export Format:                          │
│ ○ Individual STL files (1.stl, 2.stl...)│
│ ○ Combined STL file (all numbers)       │
│ ● Both                                  │
│                                         │
│ Destination Folder:                     │
│ [/Users/name/Downloads    ] [Browse...] │
│                                         │
│ Base Filename:                          │
│ [watch_numbers_________]                │
│                                         │
│ ☑ Include 2D preview image (PNG)       │
│ ☑ Include README with parameters       │
│                                         │
│ Mesh Info:                              │
│ • Numbers: 12                           │
│ • Triangles: 3,024                      │
│ • Size: 193.9×193.9×2.5mm              │
│ • Valid: ✓ Manifold                    │
│                                         │
│         [Cancel]  [Export]              │
└─────────────────────────────────────────┘
```

**Modifiche a `window.py`**:
```python
def _on_export_clicked(self, widget):
    """Handle export button click."""
    if not self.generated_mesh:
        self.show_toast("Generate 3D mesh first!")
        return

    # Show export dialog
    from ui.export_dialog import ExportDialog

    dialog = ExportDialog(
        transient_for=self,
        mesh=self.generated_mesh,
        parameters=self.get_parameters(),
        preview_widget=self.preview_2d_widget
    )
    dialog.present()
```

**Export Process**:
1. Utente clicca "Export..."
2. Dialog si apre con opzioni precompilate
3. Utente sceglie cartella e opzioni
4. Click "Export" → Progress bar appare
5. Validazione mesh (is_manifold, is_watertight)
6. Se valida: export files
7. Se non valida: mostra warning + opzione "Repair and Export"
8. Genera README.txt con parametri usati
9. Opzionale: salva preview.png
10. Toast "Exported to /path/file.zip"

---

## 📊 Cleanup Generale

### Task 4.1: Rimuovere Codice Morto
**File da pulire**:
- `src/core/cairo_distortions.py` - Sembra non usato? ✅ Verificare e rimuovere
- `src/ui/preview_3d_gl.py` - OpenGL non implementato, rimuovere o documentare come WIP

### Task 4.2: Migliorare Logging e Debug
**Aggiunte**:
```python
# In ogni modulo core
import logging

logger = logging.getLogger(__name__)

# Invece di print(), usare:
logger.debug(f"Mesh generated: {triangles} triangles")
logger.warning(f"Triangulation failed for contour")
logger.error(f"Mesh validation failed: {error}")
```

### Task 4.3: Documentazione
**Creare**:
- `docs/ARCHITECTURE.md` - Diagramma architettura
- `docs/MESH_GENERATION.md` - Spiega pipeline mesh generation
- `docs/COORDINATE_SYSTEM.md` - Spiega sistema coordinate 2D→3D

---

## 🎯 Priorità di Implementazione

### Sprint 1: FIX CRITICI (1-2 giorni)
1. ✅ **Task 1.1**: Crea `UnifiedMeshPipeline`
2. ✅ **Task 1.2**: Rifattorizza `preview_2d.py` per usare pipeline
3. ✅ **Task 1.3**: Fix `preview_3d.py` visualizzazione
4. ✅ **Task 1.4**: Aggiungi dimensioni in 3D preview
5. ✅ **Task 3.1**: Rimuovi filtri distorsione attuali

**Risultato atteso**: Preview 2D e 3D mostrano STESSA geometria, filtri rimossi.

### Sprint 2: MESH QUALITY (1 giorno)
1. ✅ **Task 2.1**: Implementa `MeshValidator`
2. ✅ **Task 2.2**: Riscrivi `mesh_generator` con validazione
3. ✅ **Task 2.3**: Aggiungi test stampabilità

**Risultato atteso**: Mesh sempre valide e stampabili.

### Sprint 2.5: EXPORT DIALOG (0.5 giorni)
1. ⏳ **Task 2.4**: Implementa Export Dialog
   - Dialog con preview mesh
   - Opzioni: formato (STL singoli/combinato), nome file, cartella destinazione
   - Progress bar per export
   - Validazione mesh prima export
   - Generazione README.txt con parametri

**Risultato atteso**: Export funzionale con UI professionale.

### Sprint 3: CLEANUP (0.5 giorni)
1. ✅ **Task 4.1**: Rimuovi codice morto
2. ✅ **Task 4.2**: Migliora logging
3. ✅ **Task 4.3**: Documenta architettura

**Risultato atteso**: Codebase pulita e documentata.

### Sprint 4: NUOVI FILTRI (FUTURO - 2-3 giorni)
1. ⏳ **Task 3.2**: Analizza requisiti
2. ⏳ **Task 3.3**: Implementa nuovi filtri sottili
3. ⏳ Aggiungi UI preset-based

**Risultato atteso**: Filtri artistici funzionali e usabili.

---

## 🔧 Modifiche File per File

### `src/window.py`
```python
# RIMUOVERE:
- self._create_distortion_group() chiamata
- Tutti i parametri distorsione in get_parameters()
- _on_distortion_toggled(), _on_distortion_changed()

# MODIFICARE:
- _on_generate_mesh_clicked() usa UnifiedMeshPipeline
- _update_preview() rimuovi parametri distorsione
```

### `src/ui/preview_2d.py`
```python
# RIMUOVERE:
- Parametri distorsione da update_parameters()
- self.distortion_filter
- Chiamate a _distort_contours()

# AGGIUNGERE:
- Import UnifiedMeshPipeline
- generate_mesh_data() usa pipeline invece di logica interna
```

### `src/ui/preview_3d.py`
```python
# RIMUOVERE:
- _draw_debug_boxes() completo
- show_debug_boxes flag

# AGGIUNGERE:
- _draw_dimension_lines() per mostrare misure
- Migliorare _draw_info_overlay() con stats mesh
```

### `src/core/mesh_generator.py`
```python
# RISCRIVERE:
- create_text_mesh() con approccio trimesh
- Aggiungere validazione
- Migliorare gestione buchi (poligoni con holes)

# AGGIUNGERE:
- Logging dettagliato
- Error handling robusto
```

---

## ✅ Definition of Done

### Per FASE 1 (Allineamento 2D/3D):
- [ ] Preview 2D e 3D mostrano geometria identica
- [ ] Numeri in posizioni corrette (12 in alto, 6 in basso)
- [ ] Numeri rispettano raggi inner/outer
- [ ] Dimensioni visualizzate correttamente in 3D
- [ ] No debug boxes o artefatti visivi

### Per FASE 2 (Mesh Quality):
- [ ] Tutte le mesh passano test is_manifold()
- [ ] Mesh sono watertight (nessun buco)
- [ ] Export STL importabile in slicer (Cura, PrusaSlicer)
- [ ] Nessuna faccia degenerata
- [ ] Volume mesh > 0

### Per FASE 3 (Filtri):
- [ ] UI filtri distorsione nascosta/rimossa
- [ ] Parametri distorsione rimossi da tutti i metodi
- [ ] Codice distortion.py e distortion_2d.py deprecato
- [ ] Nessun warning/error in console

---

## 📝 Note Implementazione

### Coordinate System
```
2D Preview (Cairo):
- Origine: centro schermo
- X: destra positiva
- Y: giù positiva (Cairo standard)
- Angoli: 0° = top (12 o'clock), senso orario

3D Mesh (STL):
- Origine: centro dial
- X: destra
- Y: alto (invertito rispetto Cairo!)
- Z: estrusione (altezza)
- Rotazione: identica a 2D, ma Y invertita

Conversione 2D→3D:
x_3d = x_2d
y_3d = -y_2d  # IMPORTANTE: Inverti Y!
z_3d = 0 (bottom) to extrusion_depth (top)
```

### Gestione Poligoni con Buchi
```python
# Shapely approach (PREFERITO)
from shapely.geometry import Polygon

exterior = [(x1, y1), (x2, y2), ...]  # Outer contour
holes = [
    [(x1, y1), (x2, y2), ...],  # Hole 1 (es. centro "O")
    [(x1, y1), (x2, y2), ...],  # Hole 2 (es. secondo buco "8")
]

polygon = Polygon(exterior, holes=holes)
# Shapely gestisce automaticamente winding order e validazione
```

---

## 🚨 Rischi e Mitigazioni

### Rischio 1: Rottura Backward Compatibility
**Impatto**: Export esistenti potrebbero avere layout diverso
**Mitigazione**:
- Versione file export (v1 → v2)
- Test con file .zip esistenti

### Rischio 2: Performance Degradation
**Impatto**: Mesh generation più lenta con validazione
**Mitigazione**:
- Cache mesh valide
- Progress bar per generazione
- Validazione opzionale (solo se check "Validate for 3D printing")

### Rischio 3: Nuovi Bug in Trimesh
**Impatto**: Trimesh.extrude_polygon potrebbe fallire per font complessi
**Mitigazione**:
- Try-catch con fallback a manual extrusion
- Test suite con font edge-cases

---

## 📚 Riferimenti

- Trimesh docs: https://trimsh.org/trimesh.html
- Shapely docs: https://shapely.readthedocs.io/
- STL format spec: https://en.wikipedia.org/wiki/STL_(file_format)
- Manifold mesh: https://en.wikipedia.org/wiki/Manifold

---

**Data creazione**: 2026-01-04
**Autore**: Analisi tecnica profonda del progetto
**Status**: 📋 PLAN - Ready for Implementation
