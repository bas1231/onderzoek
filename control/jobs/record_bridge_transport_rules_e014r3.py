from pathlib import Path
import subprocess

ROOT = Path.cwd()
p = ROOT / 'AGENTS.md'
text = p.read_text(encoding='utf-8')
heading = '## Browser bridge visible-chat transport'
start = '<<<PREDICTION_' + 'BRIDGE_TASK>>>'
end = '<<<END_PREDICTION_' + 'BRIDGE_TASK>>>'
section = '

## Browser bridge visible-chat transport

Harde operationele regels voor de Prediction browser bridge:

- Een bridge-taak werkt alleen betrouwbaar wanneer de volledige task-marker letterlijk zichtbaar staat in de gewone assistant-chattekst die de gebruiker in de ChatGPT-interface ziet. Een marker die alleen via commentary, tool-output of een andere niet-zichtbare laag wordt verstuurd, geldt als NIET VERZONDEN.
- De zichtbare vorm is: ' + start + ' ... ' + end + '.
- Bridge-taken moeten daarom altijd via zichtbare assistant-chattekst worden aangeboden. Commentary en toolcalls mogen ondersteunend zijn, maar nooit de enige transportlaag voor een bridge-taak.
- Als de gebruiker meldt dat de taak niet zichtbaar is, stuur dezelfde taak opnieuw zichtbaar en wacht niet op de onzichtbare poging.
- Plaats de ruwe bridge start- of eind-sentinel nooit opnieuw binnen een payloadveld zoals files[].content, documentatie of embedded code. De browser-parser kan zo een interne sentinel aanzien voor het einde van de buitenste taak en de JSON voortijdig afkappen. Bouw zulke sentineltekst lokaal uit losse fragmenten op wanneer documentatie dit vereist.
- Een taak geldt pas als bewezen werkend na de keten: zichtbaar in chat -> discover -> enqueue -> executor -> result -> ack.
'

if heading not in text:
    p.write_text(text.rstrip() + section + '
', encoding='utf-8')
    subprocess.run(['git','add','AGENTS.md'], cwd=ROOT, check=True)
    subprocess.run(['git','commit','-m','docs: persist bridge visible-chat transport rules','--','AGENTS.md'], cwd=ROOT, check=True)
    print('AGENTS_BRIDGE_TRANSPORT_RULES_ADDED')
else:
    print('AGENTS_BRIDGE_TRANSPORT_RULES_ALREADY_PRESENT')

print(subprocess.run(['git','rev-parse','HEAD'], cwd=ROOT, text=True, capture_output=True, check=True).stdout.strip())
