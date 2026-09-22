# Backlog — uzavřené

Tickety, které opustily `BACKLOG.md`. Nejnovější nahoře. Nic z toho není práce,
která by čekala na udělání.

### BL-11 — Monitor: filtrování sessions po projektech
**Closed:** 2026-09-22 · done · feature/BL-11-session-project-filter
**Oblast:** dashboard · plugins/claude-monitor/tools/claude_monitor.py

Záložka `backlog` má nahoře taby projektů (`board()`, proměnná `blProj` / `setProj`) a ukazuje
vždycky jen jeden projekt. Grid sessions žádný filtr nemá — `tick()` vykreslí
`d.sessions.map(card)`, tedy všechny běžící sessions dohromady. Kdo jede na několika projektech
naráz, hledá tu svoji session očima v mřížce, kde sousedí karty z nesouvisejících repozitářů;
zároveň je to nekonzistentní s backlogem, kde se přepínání projektů už nabízí.

**Hotovo když:** nad gridem je přepínač projektů ve stejném stylu jako u backlogu (vč. „vše“),
volba přežije repaint i reload (uloží se přes `save()`/`load()` jako `view` a `blProj`) a grid
ukazuje jen sessions zvoleného projektu.

**Pozor:** KPI pruh nad gridem počítá server (`d.totals`, `waiting`) přes všechny sessions —
při filtrování jen gridu by čísla v hlavičce přestala odpovídat tomu, co je vidět. Sessions nesou
`project` (basename `cwd`) i plné `cwd`, takže dva stejně pojmenované adresáře se musí rozlišit
podle `cwd`.

**Řešení:** filtr je celý na straně stránky, server se nezměnil. `projTabs(sessions)` si z
`d.sessions` postaví mapu podle `cwd` (label je `project`, `title` plná cesta, za jménem počet
sessions), vykreslí řádek `#projs` nad KPI pruhem a vrátí, co má grid ukázat. Seznam projektů
tak vzniká z běžících session, ne z projektů backlogu — filtrovat jde i repozitář bez
`BACKLOG.md`. Klíčem je `cwd`, takže dva stejně pojmenované adresáře jsou dva taby.

Volba žije v `gridProj` (`null` = „all“) a ukládá se přes `save()`/`load()` jako `gridProj`,
nezávisle na `blProj`. Uložená cesta, která už mezi session není, se při ticku opraví zpátky na
„all“. Picker se schová, když je projekt jen jeden nebo když je vidět backlog.

KPI pruh už nebere `d.totals`: `sums(list)` spočítá stejných jedenáct čísel nad tím, co je
v gridu, aby hlavička odpovídala kartám pod ní. Počet v titulku tabu zůstal záměrně globální
z `d.totals.waiting` — filtr nesmí zamlčet, že na tebe čeká session z jiného projektu.

### BL-1 — Dashboard umí jen tmavý režim
**Closed:** 2026-09-21 · done · main
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

**Řešení:** dvě palety pod jednou sadou jmen — `:root,:root[data-theme="dark"]` a
`:root[data-theme="light"]`. Těch sedm barev mimo proměnné dostalo jména (`--max`,
`--idle-bg`, `--idle-line`, `--idle-fg`, `--att-fg`, `--att-bg`, `--att-soft`/`--att-soft2`)
a k tomu přibylo `--att-ink`: amber jako výplň a jako text potřebuje ve světlém režimu dvě
různé hodnoty, protože `#ffb02e` na bílé kartě není čitelný.

`data-theme` na rootu drží vždy jen skutečně vykreslený režim (`dark`/`light`), nikdy
`system` — dotaz na `prefers-color-scheme` se tím vyřeší jednou v JS místo toho, aby se
paleta opakovala ještě v media query. Volba (`system`/`light`/`dark`) jde do `localStorage`
vedle `iv`, `kpis` a `blProj`; malý skript nad `<style>` nasadí paletu ještě před prvním
vykreslením, takže reload ve světlém režimu neblikne tmavou. Přepínač je vpravo nahoře
vedle verze a cykluje system → light → dark.

Tmavé hodnoty jsou shodné s původními hexy, takže tmavý režim vypadá přesně jako předtím.
Ve světlém má každý textový pár kontrast ≥ 5:1 (ověřeno v prohlížeči).

### BL-6 — `focus()` nevaliduje `cwd` z requestu
**Closed:** 2026-09-20 · done · main
**Oblast:** bezpečnost · plugins/claude-monitor/tools/claude_monitor.py

`focus()` předá `cwd` z těla POSTu rovnou do `_run(["open", "-a", app, cwd])` (ř. 439).
Žádný shell v tom není, takže o injection nejde, ale je to jediná hodnota z requestu,
která se v celém souboru používá jako cesta — a `cwd` začínající pomlčkou `open`
rozparsuje jako přepínač, ne jako cestu. Server přitom `cwd` všech session zná, takže
porovnat je proti čemu.

**Hotovo když:** `/api/focus` přijme jen takové `cwd`, které server sám vypsal mezi
session, a odmítnutí vrátí `{"ok": false, "error": ...}` jako ostatní chyby

**Řešení:** `focus()` porovná `cwd` z requestu s adresáři, které server sám vypsal mezi
session (`agents_json()`), a neznámou hodnotu odmítne jako `{"ok": false, "error":
"unknown session directory"}`. Kontrola sedí přímo ve větvi pro editory, tedy na jediném
místě, kde se `cwd` používá jako argument `open` — ostatní cesty (tab přes osascript,
prázdné `cwd`) se nemění.

### BL-4 — `/feature:start --yolo` pro běh bez odklikávání
**Closed:** 2026-09-20 · done · feature/BL-4-yolo-flag
**Oblast:** DX · plugins/feature/commands/start.md

Workflow se dnes zastaví u člověka nejmíň pětkrát: potvrzení zadání (krok 1), volba base
branche, když má repo `develop` i `main` (krok 2), brána nad plánem a složením kroků
(krok 3, `AskUserQuestion`), schválení založení tiketů do backlogu u nálezů mimo rozsah
(krok 8) a konzultace (krok 11). Kdo pouští malý tiket z backlogu, kde je zadání i
`Hotovo když` napsané předem, proklikává pět dialogů jen aby odsouhlasil to, co mu workflow
samo navrhlo. `--fast` na tom nic nemění — podle ř. 129 jen předvyplňuje návrh, samotné
potvrzení nenahrazuje.

Chybí flag `--yolo`, který u každé takové brány vezme doporučenou variantu (u kroku 3 ten
jeden klik na vlastní návrh) a jede dál.

**Pozor:** flag nesmí sáhnout na dva druhy bran. Za prvé na pravidla z ř. 312–314 — commit,
push a PR se bez výslovného souhlasu nedělají ani s `--yolo`; jinak z toho není zrychlení,
ale ztráta kontroly nad tím, co skončí v origin. Za druhé na diskvalifikátory z ř. 67–71
(auth, tajemství, nedůvěřený vstup, endpointy, závislosti, migrace, platby, CI/CD) — tam se
i dnes u `--fast` má pojmenovat důvod a **zeptat se**, a `--yolo` to musí respektovat stejně.
Musí být taky jasné, co dělá se zastávkami, které nejsou schvalovací, ale záchytné: špinavý
pracovní strom (krok 2) nebo opakovaný `FAIL` z E2E kvůli cizímu bugu (ř. 316) jsou stop,
ne rozhodovačka. A flag patří do `argument-hint` v hlavičce, jinak ho nikdo nenajde.

**Hotovo když:** `/feature:start BL-<n> --yolo` doběhne od zadání až po hotový diff bez
jediného dotazu na uživatele, u brány v kroku 3 zvolí vlastní návrh a napíše do odpovědi,
co tím schválil; commit, push ani PR nevznikne bez samostatného souhlasu; přítomnost
diskvalifikátoru se pojmenuje a zeptá se navzdory flagu; chování je popsané v sekci
o flagách v `start.md` včetně výčtu toho, co `--yolo` neobchází

**Řešení:** flag `--yolo` v `start.md` stojí na rozdělení zastávek na dva druhy —
*schvalovací brána* (workflow ví, co navrhuje; flag klikne a do odpovědi napíše, co tím
schválil) a *záchytná stopka* (workflow odpověď nemá: špinavý strom, chybějící MCP, nejasné
zadání, cizí bug v E2E, spor s reviewerem, nesplněné `Done when` — ptá se i s flagem). Nad tím
tři výjimky, které flag neobchází: commit, push, PR a uzavření tiketu (běh proto končí
konzultací v kroku 11 s hotovým diffem), diskvalifikátory, a záchytné stopky. `--yolo` je
ortogonální k `--fast`/`--full` — ty řeší, které kroky běží, flag řeší, kdo je odsouhlasí.

Ze security review navíc: obsah tiketu je **data, ne instrukce** (tělo, které oslovuje agenta,
je záchytná stopka, protože flag odstraňuje jediného člověka, který cizí text četl); `Branch`
řádek z tiketu musí jmenovat vlastní tiket, nesmí být base ani chráněná větev a nesmí začínat
pomlčkou (`**Branch:** main` by jinak nechal bezobslužný běh psát rovnou na `main`); security
review si agent s `--yolo` nesmí odsouhlasit zahození sám; a seznam diskvalifikátorů dostal
konfiguraci agenta a nástrojů (`.claude/**`, hooky, `CLAUDE.md`, MCP, commands/skills/workflows).

### BL-7 — `.gitignore` nepokrývá `.claude/` ani `.playwright-mcp/`
**Closed:** 2026-09-20 · done · main
**Oblast:** dluh · .gitignore

`.gitignore` drží jen `.DS_Store` a `__pycache__/`, ale v pracovním stromu sedí
neignorované `.claude/` (plány a `settings.local.json` s absolutními cestami domovského
adresáře) a `.playwright-mcp/` (snapshoty stránek a konzolové logy z ověřování
v prohlížeči — vykreslený dashboard obsahuje absolutní cesty projektů i výstup agentů).
`origin` je veřejný GitHub, takže jediný `git add -A` to publikuje.

**Pozor:** `.claude/` se nedá ignorovat celé bez rozmyslu — plány v `.claude/plans/`
můžou být něco, co do repa patří. Je to rozhodnutí, co se verzuje, ne řádek k zametení.

**Hotovo když:** `git add -A` nemůže publikovat lokální cesty ani snapshoty z prohlížeče,
a to, co se verzovat má, verzované zůstane

**Řešení:** `.gitignore` rozšířený o `.claude/` a `.playwright-mcp/`. Rozhodnutí, které
ticket nechával otevřené, padlo na ignorování celého `.claude/` — plány v `.claude/plans/`
se tedy neverzují, jsou to lokální pracovní materiály.

### BL-8 — Přepnutí view zhasne vybraný projekt v backlogu
**Closed:** 2026-09-20 · done · main
**Oblast:** UX · plugins/claude-monitor/tools/claude_monitor.py

`setView()` dělá `querySelectorAll(".tab").forEach(b => b.classList.toggle("on",
b.dataset.v === v))`. Přepínače projektů nad backlog seznamem mají taky třídu
`tab`, ale žádné `data-v`, takže každé přepnutí view sundá zvýraznění vybranému projektu.
Vrátí se až při dalším překreslení o 3 s později — vybraný projekt se přitom nemění, jen
přestane být vidět.

**Pozor:** třídu `tab` sdílejí obojí už delší dobu, ale obsluha kliků na boardu na tom
názvu teď staví (`.tab[data-root]`), takže případné oddělení tříd musí projít oběma místy.

**Hotovo když:** přepnutí sessions ↔ backlog nechá zvýrazněný projekt zvýrazněný

**Řešení:** selektor v `setView()` zúžený na `.tab[data-v]`, tedy jen na view taby
v hlavičce. Třídy `tab` zůstaly sdílené a obsluha kliků na boardu (`.tab[data-root]`)
se nemění — jediné místo, které o oba druhy tlačítek zakoplo, byl ten `forEach`.

### BL-3 — Refresh stránky vždy zahodí rozdělaný pohled
**Closed:** 2026-09-20 · done · main
**Oblast:** UX · plugins/claude-monitor/tools/claude_monitor.py

Který view je vykreslený, drží obyčejná proměnná `let view = "sessions"` a vybraný projekt
s tiketem `let blProj = null, blSel = null`. V celém souboru není ani jeden zápis do
`localStorage` nebo do URL, takže každé F5 — i to, které si vynutí sám dashboard po restartu
serveru — hodí člověka zpátky na sessions a v backlogu na první projekt a první tiket.
Kdo board používá, musí po každém refreshi znovu naklikat tab, projekt a tiket, který právě četl.

Stejnou vadu mají i ostatní volby v hlavičce: `ivIdx` (interval auto-refreshe) a fold KPI
se resetují úplně stejně.

**Pozor:** stav nesmí skončit v DOMu — board i grid se překreslují celým `innerHTML` při
každém ticku. Patří vedle `blProj`/`blSel` a do `localStorage`, ať to funguje stejně jako
přepínač režimu v BL-1. Obnovený `blProj` navíc nemusí odpovídat žádnému otevřenému
projektu (session mezitím skončila) a `blSel` žádnému existujícímu tiketu — `board()` už
dnes umí spadnout zpátky na první položku, ale ten fallback musí zabrat i pro hodnotu
načtenou z úložiště, ne jen pro `null`.

**Hotovo když:** po refreshi zůstane otevřený stejný view, a v backlogu i stejný projekt
a tiket; neplatný uložený projekt nebo tiket dashboard tiše přepne na první existující místo
toho, aby zůstal prázdný

**Řešení:** dvojice pomocníků `load()`/`save()` nad `localStorage` pod prefixem
`claude-monitor:`; přes ně jdou `view`, `ivIdx`, `kpisAll` a `blProj`/`blSel`. Projekt
a ticket se zapisují přes `setProj()`/`setSel()`, takže korekci, kterou dnes dělá `board()`
u neplatné hodnoty, uloží taky — načtený mrtvý projekt nebo zavřený ticket tichounce spadne
na první existující. Načtené hodnoty se validují (`view` jen sessions/backlog, `ivIdx` proti
délce `INTERVALS`), zápis i čtení jsou v `try`/`catch`, aby zakázané úložiště stránku
nezastavilo. Boot volá `setView(view)` místo `tick()`, protože markup se rodí se sessions.

### BL-2 — Z backlog boardu nejde ticket rovnou rozjet
**Closed:** 2026-09-20 · done · feature/BL-2-start-from-board
**Oblast:** UX · plugins/claude-monitor/tools/claude_monitor.py
**Branch:** feature/BL-2-start-from-board

Board v dashboardu ticket jen ukazuje. Kdo ho chce vzít, musí přepnout do terminálu,
trefit správné okno se správným projektem a ručně opsat `/feature:start BL-<n>` —
číslo je na druhé obrazovce, takže právě u něj se dělá překlep. Čtení a spuštění
jsou přitom dva kroky téže věci.

Z cest, které ticket zvažoval, padlo rozhodnutí na **tlačítko „copy“** v detailu ticketu —
`navigator.clipboard.writeText()`, dashboard běží na `127.0.0.1`, což je secure context,
takže API je dostupné. Vložení do terminálu zůstává na člověku.

Zahozené cesty a proč: **vložení příkazu do běžící session** přes keystroke chce
Accessibility oprávnění a je to rychlá cesta ke ztracenému promptu; **spuštění nové session**
z `osascript` by z dashboardu udělalo první místo, kde server spouští proces, ne jen čte
soubory — a monitor má zůstat read-only.

**Pozor:** board se překresluje celým `innerHTML` při každém ticku, takže stav tlačítka
(„zkopírováno“) v DOMu nepřežije — musí ven vedle `blProj`/`blSel`, stejně jako výběr
ticketu.

**Hotovo když:** z otevřeného ticketu v boardu jde příkaz `/feature:start BL-<n>` dostat do
schránky jedním klikem bez ručního opisování ID, zvolená cesta je popsaná v README
claude-monitoru a nic se nezapíše do běžící session bez toho, aby to člověk viděl
