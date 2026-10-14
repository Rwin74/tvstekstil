"""Company-wide admin workspace through Supabase's authenticated RPC, never local disk."""
import httpx
from .site_auth import TOKEN, config
from .store import Conflict
from .models import domain_key
from .buyers import saved_exclusion


def item(lead):
    key = domain_key(lead.website) if lead.website else ':'.join(
        (lead.name.casefold(), lead.city.casefold(), lead.country.casefold()))
    return {'dedupe': 'real:' + key, 'payload': lead.model_dump()}


class SupabaseStore:
    pg = True

    def rpc(self, operation, **arguments):
        token = TOKEN.get()
        if not token:
            raise RuntimeError('Authenticated context required')
        url, key = config()
        with httpx.Client(timeout=5, follow_redirects=False, trust_env=False) as client:
            response = client.post(url + '/rest/v1/rpc/boutique_workspace',
                headers={'apikey': key, 'Authorization': 'Bearer ' + token},
                json={'operation': operation, 'arguments': arguments})
        if response.status_code == 409:
            raise Conflict('Firma zaten kayıtlı veya kayıt başka bir pencerede değişti. Listeyi yenileyin.')
        if response.status_code != 200:
            # Do not reflect database internals, headers, tokens or request payloads.
            raise RuntimeError('Butik veritabanı işlemi tamamlanamadı. Kurulumu ve bağlantıyı kontrol edin.')
        return response.json()

    def list(self, include_legacy=False):
        rows = self.rpc('list')
        return rows if include_legacy else [r for r in rows if not r.get('is_demo') and not saved_exclusion(r)]

    def save(self, lead, lead_id=None, version=None):
        return self.rpc('save', **item(lead), id=lead_id, version=version)

    def delete(self, lead_id, version):
        self.rpc('delete', id=lead_id, version=version)

    def restore(self, leads):
        added = self.rpc('restore', items=[item(lead) for lead in leads if not lead.is_demo])
        return added, len(leads) - added

    def add_history(self, payload):
        self.rpc('add_history', payload=payload)

    def history(self):
        return [r for r in self.rpc('history') if r.get('provider') != 'demo']

    def rate_limit(self, bucket, maximum, cost=1):
        return self.rpc('rate_limit', bucket=bucket, maximum=maximum, cost=cost)

    def cached(self, key):
        return self.rpc('cached', key=key)

    def cache(self, key, result):
        self.rpc('cache', key=key, payload=result)
