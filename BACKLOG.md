# Backlog

Práce, která se zrovna nedělá. Priorita je pořadí sekcí; uzavřený ticket se přesouvá do
`BACKLOG.done.md`. Ticket se bere přes `/feature:start BL-<n>`.

## Vysoká priorita

## Střední priorita

### BL-11 — Monitor: filtrování sessions po projektech
**Area:** dashboard · plugins/claude-monitor/tools/claude_monitor.py

Záložka `backlog` má nahoře taby projektů (`board()`, proměnná `blProj` / `setProj`) a ukazuje
vždycky jen jeden projekt. Grid sessions žádný filtr nemá — `tick()` vykreslí
`d.sessions.map(card)`, tedy všechny běžící sessions dohromady. Kdo jede na několika projektech
naráz, hledá tu svoji session očima v mřížce, kde sousedí karty z nesouvisejících repozitářů;
zároveň je to nekonzistentní s backlogem, kde se přepínání projektů už nabízí.

**Done when:** nad gridem je přepínač projektů ve stejném stylu jako u backlogu (vč. „vše“),
volba přežije repaint i reload (uloží se přes `save()`/`load()` jako `view` a `blProj`) a grid
ukazuje jen sessions zvoleného projektu.

**Watch out:** KPI pruh nad gridem počítá server (`d.totals`, `waiting`) přes všechny sessions —
při filtrování jen gridu by čísla v hlavičce přestala odpovídat tomu, co je vidět. Sessions nesou
`project` (basename `cwd`) i plné `cwd`, takže dva stejně pojmenované adresáře se musí rozlišit
podle `cwd`.

## Nízká priorita

<!-- last-id: BL-11 -->
