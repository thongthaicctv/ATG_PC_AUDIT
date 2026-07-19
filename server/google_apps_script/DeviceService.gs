function ensureSubmitDevice(request) {
  let device = findByKey('THIET_BI', 'device_id', request.auth.device_id);
  if (device) {
    const sameSecret = constantTimeEqual(device.device_secret_hash, secretHash(request.auth.device_secret));
    const role = String(device.role || '').toUpperCase();
    const status = String(device.status || '').toUpperCase();
    // Existing employee devices created by older deployments are promoted
    // automatically. BLOCKED and REVOKED remain under administrator control.
    if (sameSecret && role === 'SUBMIT' && status === 'PENDING') {
      device.status = 'ACTIVE'; device.approved_at = device.approved_at || nowIso();
      device.last_seen = nowIso(); device.app_version = request.auth.app_version;
      device.last_request_id = request.auth.request_id;
      updateObject('THIET_BI', device._row, device);
      return findByKey('THIET_BI', 'device_id', request.auth.device_id);
    }
    return device;
  }
  const p = request.payload || {}, profile = p.profile || {}, system = p.system || {};
  appendObject('THIET_BI', {
    device_id: request.auth.device_id,
    device_secret_hash: secretHash(request.auth.device_secret),
    role: 'SUBMIT', status: 'ACTIVE', asset_code: profile.asset_code,
    computer_name: system.computer_name, first_seen: nowIso(), last_seen: nowIso(),
    approved_at: nowIso(), app_version: request.auth.app_version,
    last_request_id: request.auth.request_id, note: 'Tự động kích hoạt thiết bị gửi dữ liệu'
  });
  return findByKey('THIET_BI', 'device_id', request.auth.device_id);
}

function aggregateLicenseActive(deviceId) {
  const row = licenseRows().find(x =>
    String(x.device_id).trim().toUpperCase() === String(deviceId).trim().toUpperCase() &&
    String(x.product_code).trim().toUpperCase() === 'ATG_PC_AUDIT' &&
    String(x.feature_code).trim().toUpperCase() === 'AGGREGATE' &&
    String(x.status).trim().toUpperCase() === 'ACTIVE');
  if (!row) return false;
  if (!row.expire_date || String(row.expire_date).toUpperCase() === 'PERMANENT') return true;
  return new Date(row.expire_date).getTime() >= Date.now();
}

function ensureAggregateDevice(request) {
  let device = findByKey('THIET_BI', 'device_id', request.auth.device_id);
  if (!aggregateLicenseActive(request.auth.device_id)) return device;
  if (!device) {
    appendObject('THIET_BI', {
      device_id: request.auth.device_id,
      device_secret_hash: secretHash(request.auth.device_secret),
      role: 'AGGREGATE', status: 'ACTIVE', first_seen: nowIso(), approved_at: nowIso(),
      last_seen: nowIso(), app_version: request.auth.app_version,
      last_request_id: request.auth.request_id
    });
    return findByKey('THIET_BI', 'device_id', request.auth.device_id);
  }

  // A licensed administrator PC may have been registered earlier as SUBMIT.
  // Promote only when the same local device secret proves this is that device.
  if (!constantTimeEqual(device.device_secret_hash, secretHash(request.auth.device_secret))) return device;
  const status = String(device.status || '').toUpperCase();
  if (status === 'BLOCKED' || status === 'REVOKED') return device;
  if (String(device.role || '').toUpperCase() !== 'AGGREGATE' || status !== 'ACTIVE') {
    device.role = 'AGGREGATE'; device.status = 'ACTIVE';
    device.approved_at = device.approved_at || nowIso(); device.last_seen = nowIso();
    device.app_version = request.auth.app_version; device.last_request_id = request.auth.request_id;
    updateObject('THIET_BI', device._row, device);
    return findByKey('THIET_BI', 'device_id', request.auth.device_id);
  }
  return device;
}

function registerDevice(request) {
  try {
    const device = ensureSubmitDevice(request);
    if (String(device.status || '').toUpperCase() === 'ACTIVE')
      return ok('DEVICE_ACTIVE', 'Thiết bị đã được tự động kích hoạt', {device_id: device.device_id, role: device.role, status: device.status});
    return fail('DEVICE_' + String(device.status || 'DENIED').toUpperCase(), 'Thiết bị không được phép gửi dữ liệu');
  }
  catch (err) {
    console.error('DEVICE_REGISTRATION_ERROR name=%s message=%s stack=%s', String(err.name || ''), String(err.message || ''), String(err.stack || ''));
    return fail('DEVICE_REGISTRATION_ERROR', 'Không thể đăng ký thiết bị: ' + String(err.message || 'Lỗi không xác định').slice(0, 300));
  }
}

function aggregateAuth(request) {
  ensureAggregateDevice(request);
  const auth = authenticate(request.auth, 'AGGREGATE');
  if (!auth.success) return auth;
  if (!aggregateLicenseActive(request.auth.device_id)) return fail('LICENSE_DENIED', 'License AGGREGATE không hợp lệ hoặc đã hết hạn');
  return auth;
}
