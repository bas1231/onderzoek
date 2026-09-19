# YOUTUBE_SCOUT

Datum: 2026-09-19
Status: METHODOLOGY / DISCOVERY SOURCE ONLY

## Doel

Gebruik YouTube als grootschalige discoverybron voor prediction-marketmechanismen, echte trader/builderservaringen, executiondetails, mislukte experimenten, obscure API/features en onverwachte strategiedetails.

Een YouTube-video is **nooit zelfstandig bewijs van edge**. Video's genereren claims, mechanismen en testbare hypotheses die daarna via primaire bronnen en onafhankelijke onderzoekshoeken moeten worden gevalideerd.

## Zoekscope

Zoek onder meer naar:

- Kalshi / Polymarket bots en trading-experimenten;
- makers die echte resultaten, fouten, fills, fees en timing laten zien;
- orderbook, microstructure en market-making;
- weather markets;
- arbitrage, synthetic relations en contractstructuren;
- API tutorials met obscure endpoints/features;
- interviews met grote traders / market makers;
- video's in de trant van "I built a Kalshi bot", "what actually worked", "lost money doing X";
- walkthroughs waarin onverwacht details van strategie, fills, fees, queue, latency of settlement zichtbaar worden;
- nieuwe venues, rule changes, reward programs, oracle/settlementgedrag en incidentanalyses.

Gebruik niet alleen directe zoektermen. Zoek ook op aangrenzende termen zoals sportsbook exchange, event contracts, binary markets, CLOB, market maker, liquidity rewards, orderbook bot, settlement dispute, oracle markets en event derivatives.

## Pipeline

```text
YouTube result
  -> metadata screen
  -> transcript/captions indien beschikbaar
  -> claim + timestamp extractie
  -> deduplicatie tegen onderzoek-Git
  -> primaire bron zoeken
  -> mechanisme formuleren
  -> minimaal drie onafhankelijke onderzoekshoeken waar praktisch
  -> candidate / weak signal / negative evidence
```

## Technische aanpak op de Strix

### Metadata-first

Download standaard geen video/audio. Verzamel eerst alleen metadata zoals:

- video_id;
- URL;
- title;
- channel/uploader;
- publish/upload date;
- duration;
- description;
- view count waar beschikbaar;
- language;
- caption availability;
- discovery query;
- first_seen_at;
- metadata hash.

`yt-dlp` kan metadata simuleren/dumpen zonder mediabestand te downloaden. Gebruik een lokale cache/download-archive-achtige dedup zodat reeds beoordeelde video-ID's niet opnieuw zwaar worden verwerkt.

### Transcript-on-demand

Alleen video's die de goedkope metadatafilter overleven krijgen transcriptverwerking.

Voorkeursvolgorde:

1. menselijke/originele captions;
2. automatisch gegenereerde captions;
3. geen transcript -> alleen metadata/description claim extraction en status `NO_TRANSCRIPT`;
4. audio-transcriptie alleen later als aparte build warrant dit rechtvaardigt; geen standaard audio/video-download.

Bewaar captiontype en taal expliciet. Auto-captions zijn lagere betrouwbaarheid dan menselijke captions.

### Rate limiting

De scout is cache-first en backoff-aware:

- geen agressieve herhaalde requests;
- dedup op video_id + transcript/caption hash;
- bounded concurrency;
- exponential backoff bij 429/temporary failures;
- mislukte transcriptfetch wordt niet eindeloos opnieuw geprobeerd;
- metadata en transcripts lokaal cachen;
- zoekfrequentie loskoppelen van analysefrequentie.

## Claim extractie

Iedere materiële claim krijgt minimaal:

```yaml
claim_id: YT-CLAIM-...
video_id: ...
channel: ...
published_at: ...
source_class: YOUTUBE_PUBLIC_CLAIM
timestamp_start: ...
timestamp_end: ...
claim: "..."
claim_type: result|mechanism|api_feature|execution|failure|rule|anecdote
speaker_role: trader|developer|market_maker|unknown
caption_type: manual|auto|unknown
confidence: low|medium|high
primary_source_found: false
related_mechanisms: []
related_existing_records: []
```

Geen lange transcriptkopieën in Git. Bewaar alleen korte claimparafrases, timestamps, hashes en provenance.

## Evidence ladder

Een overtuigende maker, screenshot of PnL-claim blijft `ANECDOTAL` totdat onafhankelijk bevestigd.

Promotie:

```text
YouTube claim
 -> ANECDOTAL / WEAK_SIGNAL
 -> primaire docs/data/wallet/code/venue evidence
 -> independent reproduction / semantic check
 -> execution/data/statistical falsification
 -> pas dan eventueel STRUCTURAL_CANDIDATE / RESEARCH_POSITIVE
```

### Screenshots / P&L

Screenshots van fills, P&L, dashboards of code zijn discovery-signalen. Ze bewijzen niet automatisch:

- volledigheid van trade history;
- fees/slippage;
- survivorship/selectie;
- daadwerkelijke execution;
- winstgevendheid van de strategie;
- causaliteit.

## Prioritering

Geef hogere score aan video's die:

- exacte fills/fees/timestamps/orderbooks tonen;
- code/repo/wallet/primary evidence koppelen;
- eigen mislukkingen of negatieve resultaten laten zien;
- obscure product/API/rule details tonen;
- strategievoorwaarden concreet en falsificeerbaar maken;
- minder marketing/affiliate-incentive hebben;
- nieuwe mechanismen bevatten die ver van bestaande knowledge-graph nodes liggen.

Geef lagere score aan:

- pure PnL-flex zonder audittrail;
- affiliate/promotional content;
- clickbait met alleen theoretische midpoint-arbitrage;
- screenshots zonder context;
- generieke tutorials zonder nieuwe mechanismen.

## Drie onderzoekshoeken

Een bruikbare claim wordt waar mogelijk vanuit drie verschillende failure modes getest:

1. **Bron/semantiek** — klopt de genoemde rule/API/fee/productmechaniek in primaire venue-documentatie?
2. **Data/reproduceerbaarheid** — is de claim met onafhankelijke data/code/wallet/history reproduceerbaar zonder hindsight?
3. **Execution/economie** — blijft het mechanisme overeind na executable bid/ask, depth, fees, queue/fills, slippage, latency, collateral en finality?

## Anti-conventionele discovery

De scout moet niet alleen populaire video's ranken. Reserveer querybudget voor:

- kleine kanalen;
- video's met lage view counts maar technische titels;
- failure/postmortem-content;
- oude video's over verdwenen mechanismen die op nieuwe venues kunnen terugkomen;
- API walkthroughs;
- settlement/dispute/rule edge cases;
- livestream/VOD-beschrijvingen of interviews waarin executiondetails incidenteel worden genoemd.

Populariteit is geen evidencescore.

## Integratie met News & Weak Signals

`YOUTUBE_SCOUT` is een discovery-subsystem van de News/Weak-Signal laag. Nieuwe claims gaan eerst naar de candidate/knowledge-dedup, niet direct naar strategy-builds.

Alle duurzame findings worden gekoppeld aan mechanism IDs en bestaande negative evidence.

## Harde grens

Publieke video's mogen worden geanalyseerd voor economische/mechanische intelligence. Claims over fraude, manipulatie, ongeautoriseerde toegang of software/securitymisbruik mogen alleen op mechanisme- en risiconiveau worden opgeslagen; geen operationele exploitstappen of facilitering.

## Succesmetric

Niet het aantal bekeken video's.

Meet:

- nieuwe unieke mechanismen per 100 video's;
- claims die primaire bevestiging krijgen;
- claims die een bestaande hypothese falsificeren;
- claims die een cheap-kill test opleveren;
- duplicate rate;
- false-positive rate;
- engineering/research time saved.

Een goede `YOUTUBE_SCOUT` kijkt dus vooral **niet** honderden video's volledig: hij filtert honderden video's goedkoop en verdiept alleen waar de expected information gain hoog genoeg is.
