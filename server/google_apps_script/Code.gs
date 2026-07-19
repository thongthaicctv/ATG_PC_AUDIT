function doGet(e) {
  return jsonResponse(
    e && e.parameter && e.parameter.action === "HEALTH"
      ? ok("HEALTHY", "ATG PC AUDIT API đang hoạt động", {
          api_version: props().getProperty("API_VERSION") || "1",
          spreadsheet_id_suffix: String(
            props().getProperty("SPREADSHEET_ID") || "",
          ).slice(-6),
          license_spreadsheet_id_suffix: String(
            props().getProperty("LICENSE_SPREADSHEET_ID") ||
              props().getProperty("SPREADSHEET_ID") ||
              "",
          ).slice(-6),
        })
      : fail("METHOD_NOT_ALLOWED", "doGet chỉ hỗ trợ HEALTH"),
  );
}
function doPost(e) {
  let request;
  try {
    request = JSON.parse(e.postData.contents);
  } catch (err) {
    return jsonResponse(fail("INVALID_JSON", "Nội dung JSON không hợp lệ"));
  }
  let result;
  try {
    const schema = validateSheetSchema();
    if (!schema.success) result = schema;
    else
      switch (request.action) {
        case "REGISTER_DEVICE":
          result = registerDevice(request);
          break;
        case "SUBMIT_AUDIT":
          result = submitAudit(request);
          break;
        case "CHECK_SUBMIT_STATUS":
          const a = findByKey("LICH_SU_KIEM_TRA", "audit_id", request.audit_id);
          result = a
            ? ok(
                a.write_status === "COMPLETED"
                  ? "ALREADY_EXISTS"
                  : a.write_status,
                "Trạng thái lần kiểm tra",
                { audit: a },
              )
            : fail("NOT_FOUND", "Chưa có lần kiểm tra");
          break;
        case "CHECK_LICENSE":
          result = ok(
            aggregateLicenseActive(request.auth.device_id)
              ? "LICENSE_ACTIVE"
              : "LICENSE_DENIED",
            "Trạng thái license",
          );
          break;
      case "SYNC_SUMMARY":
        result = syncSummary(request);
        break;
      case "SYNC_SNAPSHOT":
        result = syncSnapshot(request);
        break;
      case "SYNC_CHANGES":
          result = syncChanges(request);
          break;
        case "GET_AUDIT_DETAIL":
          result = getAuditDetail(request);
          break;
        case "LIST_CONFLICTS":
          result = listConflicts(request);
          break;
        default:
          result = fail("UNKNOWN_ACTION", "Action không được hỗ trợ");
      }
  } catch (err) {
    console.error(
      "ATG_API_ERROR action=%s name=%s message=%s stack=%s",
      String(request.action || ""),
      String(err.name || ""),
      String(err.message || ""),
      String(err.stack || ""),
    );
    result = fail("INTERNAL_ERROR", "Máy chủ không thể xử lý yêu cầu");
  }
  try {
    apiLog(request, result.code, result.message);
  } catch (logError) {
    console.error(
      "ATG_API_LOG_ERROR name=%s message=%s",
      String(logError.name || ""),
      String(logError.message || ""),
    );
  }
  return jsonResponse(result);
}
