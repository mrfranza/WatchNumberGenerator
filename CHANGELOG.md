# Changelog

## [Unreleased]

### Fixed (2025-12-19)

1. **Input Validation**
   - Rimossa validazione bloccante per i raggi quando si digita manualmente
   - Ora mostra solo un avviso toast senza impedire l'inserimento del valore
   - Fix in: `src/window.py:329-342`

2. **Rotazione Numeri nel Quadrante**
   - CORRETTO: Il numero 12 ora è posizionato in alto (ore 12)
   - Formula angolo corretta: `(hour % 12) * 30` gradi
   - Prima il 3 appariva in alto (formula errata)
   - Fix in: `src/utils/geometry.py:56-73`

3. **Calcolo Margini e Fitting**
   - Corretta logica di calcolo dimensioni disponibili
   - I margini ora vengono applicati correttamente
   - Margine 0 = numeri che toccano esattamente i due raggi
   - Aggiunto controllo dimensioni minime (0.1mm) per evitare valori negativi
   - Fix in: `src/utils/geometry.py:113-127`

4. **Scaling Numeri nella Preview**
   - I numeri ora scalano automaticamente per fittare nel bounding box
   - Font size si adatta sia all'altezza che alla larghezza disponibile
   - Usa 90% dello spazio per lasciare un piccolo padding visivo
   - Fix in: `src/ui/preview_2d.py:234-264`

5. **Preview 3D Placeholder**
   - Migliorato messaggio placeholder per tab 3D Preview
   - Aggiunta nota chiara: "Distortion filters are applied only during export"
   - Layout centrato con titolo e descrizione formattata
   - Fix in: `src/window.py:313-342`

### Known Issues

- Le distorsioni non sono visibili nella preview 2D (normale, si applicano solo alle mesh 3D)
- La funzionalità di export non è ancora collegata all'UI
- Preview 3D non ancora implementata (placeholder attivo)

### Next Steps

- [ ] Implementare dialog export con selezione file
- [ ] Collegare generazione mesh al bottone export
- [ ] Aggiungere progress bar per generazione mesh
- [ ] Implementare preview 3D con mesh reali (opzionale)
