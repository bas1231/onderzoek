import json
from pathlib import Path

path = Path('/mnt/c/Users/leonh/Downloads/kalshi_prod.txt')
result = {
    'path_exists': path.is_file(),
    'credential_values_printed': False,
    'live_trading': False,
    'paid_action': False,
    'wallet_action': False
}

if path.is_file():
    text = path.read_text(errors='ignore')
    lines = text.splitlines()
    upper = text.upper()
    result['size'] = path.stat().st_size
    result['line_count'] = len(lines)
    result['contains_private_key_begin'] = '-----BEGIN PRIVATE KEY-----' in text
    result['contains_rsa_private_key_begin'] = '-----BEGIN RSA PRIVATE KEY-----' in text
    result['contains_private_key_end'] = '-----END PRIVATE KEY-----' in text or '-----END RSA PRIVATE KEY-----' in text
    result['contains_api_key_id_label'] = 'API_KEY_ID' in upper or 'API KEY ID' in upper or 'KEY_ID' in upper
    result['contains_private_key_label'] = 'PRIVATE_KEY' in upper or 'PRIVATE KEY' in upper
    result['nonempty_line_metadata'] = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        result['nonempty_line_metadata'].append({
            'index': index,
            'length': len(stripped),
            'has_equals': '=' in stripped,
            'has_colon': ':' in stripped,
            'is_pem_begin': stripped.startswith('-----BEGIN'),
            'is_pem_end': stripped.startswith('-----END')
        })

print(json.dumps(result, sort_keys=True))
