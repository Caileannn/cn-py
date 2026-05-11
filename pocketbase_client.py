import os
from collections import defaultdict
from datetime import date, datetime

import requests
from dateutil import parser as date_parser
from dotenv import load_dotenv


load_dotenv()


class PocketBaseClient:
    def __init__(self, base_url=None, collection_name=None, admin_email=None, admin_password=None):
        self.base_url = (base_url or os.getenv('POCKETBASE_URL') or '').rstrip('/')
        self.collection_name = collection_name or os.getenv('POCKETBASE_OPPORTUNITIES_COLLECTION') or os.getenv('POCKETBASE_COLLECTION') or 'Opportunities'
        self.admin_email = admin_email or os.getenv('POCKETBASE_ADMIN_EMAIL')
        self.admin_password = admin_password or os.getenv('POCKETBASE_ADMIN_PASSWORD')
        self.session = requests.Session()
        self._admin_token = None

    def fetch_opportunities(self, start_date, end_date):
        records = self._fetch_all_records()
        opportunities = []

        for record in records:
            opportunity = self._normalize_record(record)
            if opportunity is None:
                continue

            deadline = opportunity['deadline_sort']
            if deadline is None:
                continue

            if start_date <= deadline <= end_date:
                opportunities.append(opportunity)

        # canonicalize types into the four agreed categories
        def canonical_type(raw):
            if not raw:
                return 'Other'
            t = raw.strip().lower()
            if 'open' in t and 'call' in t:
                return 'Open Call'
            if 'workshop' in t:
                return 'Workshop'
            if 'residency' in t:
                return 'Residency'
            if 'fund' in t or 'grant' in t:
                return 'Funding'
            return raw.strip().title()

        for opp in opportunities:
            opp['type'] = canonical_type(opp.get('type'))

        opportunities.sort(key=lambda item: (item['type'], item['deadline_sort'], item['title']))

        grouped = defaultdict(list)
        for opportunity in opportunities:
            grouped[opportunity['type']].append(opportunity)

        # Order the output so the four categories appear first
        ordered = {}
        primary = ['Open Call', 'Workshop', 'Residency', 'Funding']
        for name in primary:
            if name in grouped:
                ordered[name] = grouped[name]

        # append any remaining categories in alphabetical order
        for k in sorted(grouped.keys()):
            if k not in ordered:
                ordered[k] = grouped[k]

        return ordered

    def fetch_events(self, start_date, end_date):
        # fetch records from the Events collection
        records = self._fetch_records_for_collection('Events')
        events = []

        for record in records:
            dt = record.get('datetime') or record.get('date_time') or record.get('date') or record.get('created')
            parsed = self._parse_event_datetime(dt)
            if parsed is None:
                parsed = self._parse_date(record.get('deadline'))

            if parsed is None:
                continue

            # Only include events within the given range
            if not (start_date <= parsed <= end_date):
                continue

            ev = {
                'id': record.get('id'),
                'title': record.get('title') or record.get('name') or 'Untitled event',
                'org': record.get('org') or record.get('organiser') or record.get('organization') or 'N/A',
                'location': record.get('location') or 'N/A',
                'date': parsed.strftime('%d-%m-%Y'),
                'time': record.get('time') or record.get('date_time') and str(record.get('date_time')) or '',
                'summary': record.get('summary') or record.get('description') or '',
                'source': record.get('url') or record.get('source') or '',
                'spotlight': False,
            }

            events.append(ev)

        # sort events by date
        events.sort(key=lambda x: x.get('date'))
        if events:
            return {'Events': events}
        return {}

    def _parse_event_datetime(self, value):
        if value is None:
            return None

        if isinstance(value, datetime):
            return value.astimezone().date() if value.tzinfo else value.date()

        if isinstance(value, date):
            return value

        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
                return parsed.astimezone().date() if parsed.tzinfo else parsed.date()
            except ValueError:
                try:
                    parsed = date_parser.parse(value, dayfirst=False)
                    return parsed.astimezone().date() if parsed.tzinfo else parsed.date()
                except (ValueError, OverflowError):
                    return None

        return None

    def _fetch_all_records(self):
        if not self.base_url:
            return []

        collection_name = self._resolve_collection_name()
        if not collection_name:
            return []

        records = self._fetch_records_for_collection(collection_name)
        if records:
            return records

        return []

    def _collection_candidates(self):
        candidates = [self.collection_name, self.collection_name.lower(), self.collection_name.upper()]
        seen = set()
        ordered_candidates = []

        for candidate in candidates:
            if candidate and candidate not in seen:
                seen.add(candidate)
                ordered_candidates.append(candidate)

        return ordered_candidates

    def _resolve_collection_name(self):
        try:
            response = self.session.get(
                f'{self.base_url}/api/collections',
                headers=self._auth_headers(),
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
            collections = payload.get('items', [])
        except requests.RequestException:
            collections = []

        wanted_names = {candidate.lower() for candidate in self._collection_candidates()}

        for collection in collections:
            collection_id = str(collection.get('id', '')).lower()
            collection_name = str(collection.get('name', '')).lower()
            if collection_id in wanted_names or collection_name in wanted_names:
                return collection.get('id') or collection.get('name')

        return self.collection_name

    def _fetch_records_for_collection(self, collection_name):
        records = []
        page = 1
        per_page = 200

        while True:
            try:
                response = self.session.get(
                    f'{self.base_url}/api/collections/{collection_name}/records',
                    params={'page': page, 'perPage': per_page},
                    headers=self._auth_headers(),
                    timeout=20,
                )
                if response.status_code == 404:
                    return []

                response.raise_for_status()
                payload = response.json()
                items = payload.get('items', [])
            except requests.RequestException:
                return records

            records.extend(items)

            if len(items) < per_page:
                break

            page += 1

        return records

    def _auth_headers(self):
        token = self._get_admin_token()
        if token:
            return {'Authorization': token}

        return {}

    def _get_admin_token(self):
        if self._admin_token:
            return self._admin_token

        if not self.admin_email or not self.admin_password or not self.base_url:
            return None

        try:
            response = self.session.post(
                f'{self.base_url}/api/collections/_superusers/auth-with-password',
                json={'identity': self.admin_email, 'password': self.admin_password},
                timeout=20,
            )
            response.raise_for_status()
            token = response.json().get('token')
            if token:
                self._admin_token = token
                return self._admin_token
        except requests.RequestException:
            return None

        return None

    def _normalize_record(self, record):
        deadline = self._parse_date(record.get('deadline') or record.get('date'))
        if deadline is None:
            return None

        opportunity_type = record.get('type') or record.get('category') or 'Opportunities'

        return {
            'id': record.get('id'),
            'title': record.get('title') or record.get('name') or 'Untitled opportunity',
            'org': record.get('org') or record.get('organiser') or record.get('organization') or 'N/A',
            'type': opportunity_type,
            'summary': record.get('summary') or record.get('description') or '',
            'location': record.get('location') or 'N/A',
            'source': record.get('url') or record.get('source') or '',
            'deadline_sort': deadline,
            'deadline_display': deadline.strftime('%d-%m-%Y'),
        }

    def _parse_date(self, value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.astimezone().date() if value.tzinfo else value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            # Handle ISO 8601 / PocketBase timestamps first
            try:
                parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
                return parsed.astimezone().date() if parsed.tzinfo else parsed.date()
            except ValueError:
                pass

            for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y'):
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue

            try:
                # dayfirst=False is safer for ambiguous dates
                parsed = date_parser.parse(value, dayfirst=False)
                return parsed.astimezone().date() if parsed.tzinfo else parsed.date()
            except (ValueError, OverflowError):
                return None
        return None