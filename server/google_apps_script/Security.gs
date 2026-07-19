function canonicalStringify(value){if(value===null||typeof value!=='object')return JSON.stringify(value);if(Array.isArray(value))return '['+value.map(canonicalStringify).join(',')+']';return '{'+Object.keys(value).sort().map(k=>JSON.stringify(k)+':'+canonicalStringify(value[k])).join(',')+'}'}
function sha256Hex(text){const bytes=Utilities.newBlob(String(text),'text/plain').getBytes();return Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256,bytes).map(b=>('0'+((b+256)%256).toString(16)).slice(-2)).join('')}
function secretHash(secret){return sha256Hex(props().getProperty('SERVER_PEPPER')+String(secret||''))}
function constantTimeEqual(a,b){a=String(a||'');b=String(b||'');let diff=a.length^b.length;for(let i=0;i<Math.max(a.length,b.length);i++)diff|=(a.charCodeAt(i%Math.max(a.length,1))||0)^(b.charCodeAt(i%Math.max(b.length,1))||0);return diff===0}
function validateReplay(auth){if(!auth||!auth.request_id||!auth.timestamp_utc)return fail('INVALID_AUTH','Thiếu thông tin xác thực');if(!/^[0-9a-f-]{32,36}$/i.test(auth.request_id))return fail('INVALID_AUTH','request_id không hợp lệ');const skew=Math.abs(Date.now()-new Date(auth.timestamp_utc).getTime())/1000;if(!isFinite(skew)||skew>Number(props().getProperty('MAX_CLOCK_SKEW_SECONDS')||300))return fail('CLOCK_SKEW','Thời gian yêu cầu không hợp lệ');const log=findByKey('NHAT_KY_API','request_id',auth.request_id);return log?fail('REQUEST_REPLAY','Yêu cầu đã được xử lý trước đó'):null}
function authenticate(auth,requiredRole){const replay=validateReplay(auth);if(replay)return replay;const device=findByKey('THIET_BI','device_id',auth.device_id);if(!device)return fail('DEVICE_NOT_REGISTERED','Thiết bị chưa đăng ký');if(!constantTimeEqual(device.device_secret_hash,secretHash(auth.device_secret)))return fail('INVALID_DEVICE_SECRET','Device secret không hợp lệ');if(device.status==='PENDING')return fail('DEVICE_PENDING','Thiết bị đang chờ quản trị phê duyệt');if(device.status==='BLOCKED')return fail('DEVICE_BLOCKED','Thiết bị đã bị khóa');if(device.status==='REVOKED')return fail('DEVICE_REVOKED','Thiết bị đã bị thu hồi');if (
  requiredRole &&
  device.role !== requiredRole &&
  !(device.role === 'AGGREGATE' && requiredRole === 'SUBMIT')
) {
  return fail('ROLE_DENIED', 'Thiết bị không có quyền thực hiện tác vụ');
};return {success:true,device:device}}
