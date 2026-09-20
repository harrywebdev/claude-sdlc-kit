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

### BL-4 — `/feature:start --yolo` pro běh bez odklikávání
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
