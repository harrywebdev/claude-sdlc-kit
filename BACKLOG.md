# Backlog

Práce, která se zrovna nedělá. Priorita je pořadí sekcí; uzavřený ticket se přesouvá do
`BACKLOG.done.md`. Ticket se bere přes `/feature:start BL-<n>`.

## Vysoká priorita

## Střední priorita

### BL-1 — Dashboard umí jen tmavý režim
**Oblast:** UX · plugins/claude-monitor/tools/claude_monitor.py

Paleta je natvrdo tmavá: `:root` drží jedenáct proměnných, ale v `PAGE` je
osmnáct různých hexů, takže sedm barev stojí mimo ně — `.card.idle`
(`#1d1b1a`, `#2b2927`, `#c9c2b8`), `.kpi.max .bar>i` (`#f2776b`),
`.pill.att` (`#191817`), `.att-row` (`#3a2c12`) — plus dvě `rgba()` ve stínu
pulzujícího rámečku. Stránka nezná `prefers-color-scheme` ani žádný přepínač.
Na světlém monitoru za dne se dashboard čte špatně a vedle světlého systému
svítí jako díra v obrazovce.

**Pozor:** samotné prohození `:root` nestačí, dokud těch sedm barev nejsou
proměnné; a volba režimu musí přežít reload, takže patří do `localStorage` —
sám stav v proměnné nestačí, jak to má fold KPI nebo výběr ticketu v backlogu
**Hotovo když:** dashboard respektuje `prefers-color-scheme`, přepínač v hlavičce
umí tmavý/světlý/podle systému, volba přežije reload a ve světlém režimu je
čitelná i oranžová karta `needs you`, plan tiles a stavové pilulky

## Nízká priorita

### BL-6 — `focus()` nevaliduje `cwd` z requestu
**Oblast:** bezpečnost · plugins/claude-monitor/tools/claude_monitor.py

`focus()` předá `cwd` z těla POSTu rovnou do `_run(["open", "-a", app, cwd])` (ř. 439).
Žádný shell v tom není, takže o injection nejde, ale je to jediná hodnota z requestu,
která se v celém souboru používá jako cesta — a `cwd` začínající pomlčkou `open`
rozparsuje jako přepínač, ne jako cestu. Server přitom `cwd` všech session zná, takže
porovnat je proti čemu.

**Hotovo když:** `/api/focus` přijme jen takové `cwd`, které server sám vypsal mezi
session, a odmítnutí vrátí `{"ok": false, "error": ...}` jako ostatní chyby

<!-- last-id: BL-10 -->
