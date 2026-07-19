function aggregateAuth(request) {
  ensureAggregateDevice(request);
  const auth = authenticate(request.auth, "AGGREGATE");
  if (!auth.success) return auth;
  if (!aggregateLicenseActive(request.auth.device_id))
    return fail(
      "LICENSE_DENIED",
      "License AGGREGATE không hợp lệ hoặc đã hết hạn",
    );
  return auth;
}
function syncSummary(request) {
  const auth = aggregateAuth(request);
  if (!auth.success) return auth;
  const last = Number(request.last_change_seq || 0),
    latest = Number(props().getProperty("CURRENT_CHANGE_SEQ") || 0);
  return ok(
    latest > last ? "SYNC_AVAILABLE" : "UP_TO_DATE",
    latest > last ? "Có dữ liệu mới" : "Dữ liệu đã cập nhật",
    {
      latest_change_seq: latest,
      pending_changes: Math.max(0, latest - last),
      page_size: Number(props().getProperty("DEFAULT_PAGE_SIZE") || 200),
    },
  );
}
function syncSnapshot(request) {
  const auth = aggregateAuth(request);
  if (!auth.success) return auth;
  const max = Number(props().getProperty("MAX_PAGE_SIZE") || 500),
    size = Math.min(max, Math.max(1, Number(request.page_size || 200))),
    page = Math.max(1, Number(request.page || 1)),
    rows = rowsAsObjects("MAY_TINH_HIEN_TAI"),
    latest = Number(props().getProperty("CURRENT_CHANGE_SEQ") || 0),
    start = (page - 1) * size,
    selected = rows.slice(start, start + size),
    records = selected.map((row, index) => ({
      change_seq: latest,
      change_type: "MACHINE_SNAPSHOT",
      entity_type: "MACHINE",
      entity_id:
        row.serial_number || row.uuid || row.asset_code || String(start + index + 1),
      audit_id: row.current_audit_id || "",
      asset_code: row.asset_code || "",
      employee_code: row.employee_code || "",
      summary_json: row,
      status: row.status || "ACTIVE",
    }));
  return ok("SYNC_SNAPSHOT", "Đã tải dữ liệu hiện thời", {
    page: page,
    page_size: size,
    total: rows.length,
    has_more: start + selected.length < rows.length,
    snapshot_change_seq: latest,
    records: records,
  });
}
function syncChanges(request) {
  const auth = aggregateAuth(request);
  if (!auth.success) return auth;
  const after = Number(request.after_change_seq || 0),
    max = Number(props().getProperty("MAX_PAGE_SIZE") || 500),
    size = Math.min(max, Math.max(1, Number(request.page_size || 200))),
    latest = Number(props().getProperty("CURRENT_CHANGE_SEQ") || 0),
    records = rowsAsObjects("CHANGE_LOG")
      .filter((x) => Number(x.change_seq) > after)
      .sort((a, b) => Number(a.change_seq) - Number(b.change_seq))
      .slice(0, size),
    last = records.length
      ? Number(records[records.length - 1].change_seq)
      : after;
  return ok("SYNC_PAGE", "Đã tải trang dữ liệu", {
    after_change_seq: after,
    last_returned_seq: last,
    latest_change_seq: latest,
    has_more: last < latest,
    records: records,
  });
}
function getAuditDetail(request) {
  const auth = aggregateAuth(request);
  if (!auth.success) return auth;
  const id = request.audit_id,
    audit = findByKey("LICH_SU_KIEM_TRA", "audit_id", id);
  if (!audit) return fail("NOT_FOUND", "Không tìm thấy audit_id");
  const detail = {
    audit: audit,
    ram: rowsAsObjects("RAM").filter((x) => x.audit_id === id),
    disks: rowsAsObjects("O_DIA").filter((x) => x.audit_id === id),
    gpus: rowsAsObjects("GPU").filter((x) => x.audit_id === id),
    network_adapters: rowsAsObjects("CARD_MANG").filter(
      (x) => x.audit_id === id,
    ),
    windows_license: rowsAsObjects("BAN_QUYEN_WINDOWS").filter(
      (x) => x.audit_id === id,
    ),
    office_licenses: rowsAsObjects("BAN_QUYEN_OFFICE").filter(
      (x) => x.audit_id === id,
    ),
    windows11_checks: rowsAsObjects("WINDOWS_11_CHECKS").filter(
      (x) => x.audit_id === id,
    ),
  };
  return ok("AUDIT_DETAIL", "Đã tải chi tiết audit", detail);
}
function listConflicts(request) {
  const auth = aggregateAuth(request);
  if (!auth.success) return auth;
  let rows = rowsAsObjects("XUNG_DOT");
  ["status", "conflict_type", "employee_code"].forEach((k) => {
    if (request[k])
      rows = rows.filter((x) => String(x[k]) === String(request[k]));
  });
  if (request.asset_code)
    rows = rows.filter(
      (x) =>
        x.asset_code_old === request.asset_code ||
        x.asset_code_new === request.asset_code,
    );
  const size = Math.min(500, Math.max(1, Number(request.page_size || 200))),
    page = Math.max(1, Number(request.page || 1));
  return ok("CONFLICT_PAGE", "Danh sách xung đột", {
    page: page,
    page_size: size,
    total: rows.length,
    records: rows.slice((page - 1) * size, page * size),
  });
}
