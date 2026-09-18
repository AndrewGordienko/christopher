"""Optional, advisory ChatGPT-web critique records. Never a sending capability."""
import hashlib
import json


def fingerprint(subject, body):
    return hashlib.sha256((subject + '\n\n' + body).encode()).hexdigest()


def summary(folder, subject, body):
    file = folder / 'external-critic.json'
    if not file.exists():
        return 'not run'
    record = json.loads(file.read_text())
    if record.get('status') != 'reviewed':
        return record.get('status', 'pending')
    if record.get('after_hash') != fingerprint(subject, body):
        return 'stale after edit'
    if not record.get('chat_url', '').startswith('https://chatgpt.com/c/') or not record.get('observed_at') or not record.get('feedback'):
        return 'receipt incomplete'
    n = len(record.get('accepted_fixes', []))
    return f'{n} issue' + ('' if n == 1 else 's') + ' fixed' if n else 'reviewed · retained'
