import json,uuid
from datetime import datetime,timezone
from core.device_id import collect_device_identity
from core.device_secret_store import DeviceSecretStore
from core.google_apps_script_client import GoogleAppsScriptClient
from core.resource_utils import resource_path
from core.sync_payload_builder import build_sync_payload
from core.sync_queue import SyncQueue

SUCCESS_CODES={"CREATED","UPDATED","ALREADY_EXISTS","HISTORY_ONLY","CONFLICT_RECORDED"}


def sync_config():
    defaults={"enabled":True,"web_app_url":"","api_version":"1","schema_version":"1.1","timeout_seconds":20,"max_response_mb":10,"page_size":200,"auto_submit_after_scan":False,"retry_queue_on_startup":True,"auto_sync_on_aggregate_unlock":True,"aggregate_sync_interval_minutes":10}
    try:defaults.update(json.loads(resource_path("config/app_config.json").read_text(encoding="utf-8")).get("google_sync",{}))
    except Exception:return defaults
    return defaults


class SyncService:
    def __init__(self,client=None,queue=None,secret_store=None,identity=None):
        cfg=sync_config();self.client=client or GoogleAppsScriptClient(cfg["web_app_url"],cfg["timeout_seconds"],cfg["max_response_mb"]);self.queue=queue or SyncQueue();self.secret_store=secret_store or DeviceSecretStore();self.identity=identity or collect_device_identity()
    def auth(self):return {"device_id":self.identity.device_id,"device_secret":self.secret_store.get_or_create(),"request_id":str(uuid.uuid4()),"timestamp_utc":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),"app_version":"1.0.0"}
    def submit(self,result):
        payload=build_sync_payload(result);response=self.client.submit_audit(self.auth(),payload)
        if response.code in SUCCESS_CODES:self.queue.remove(payload["audit_id"])
        elif response.retryable:self.queue.put(payload,response.code,response.message)
        return response
    def retry(self,due_only=False):
        results=[]
        for row,payload in self.queue.items(due_only):
            response=self.client.submit_audit(self.auth(),payload);results.append(response)
            if response.code in SUCCESS_CODES or not response.retryable:self.queue.remove(payload["audit_id"])
            else:self.queue.mark_retry(row,payload,response)
        return results
