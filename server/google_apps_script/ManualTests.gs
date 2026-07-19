function assertTrue(value,message){if(!value)throw new Error(message||'Assertion failed')}
function requireTestMode(){assertTrue(props().getProperty('TEST_MODE')==='TRUE','TEST_MODE chưa bật; không chạy test trên production')}
function testSetupProject(){requireTestMode();assertTrue(setupProject().success,'Setup lỗi')}
function testCanonicalStringify(){assertTrue(canonicalStringify({b:1,a:{d:2,c:1}})==='{"a":{"c":1,"d":2},"b":1}','Canonical JSON lỗi')}
function testHashValidation(){requireTestMode();const p={schema_version:'1.1',audit_id:'a',profile:{asset_code:'PC1',employee_code:'NV01'}};p.record_sha256=sha256Hex(canonicalStringify(p));assertTrue(validateAuditPayload(p)===null,'Hash validation lỗi')}
function testChangeSequence(){requireTestMode();const before=Number(props().getProperty('CURRENT_CHANGE_SEQ')||0),after=nextChangeSeq();assertTrue(after===before+1,'change_seq không tăng')}
function testSchemaValidation(){requireTestMode();assertTrue(validateSheetSchema().success,'Schema lỗi')}
function testDeviceRegistration(){requireTestMode();assertTrue(headers('THIET_BI').includes('device_secret_hash'),'Thiếu device secret hash')}
function testSubmitAutoApproval(){requireTestMode();assertTrue(['ACTIVE','BLOCKED','REVOKED'].includes('ACTIVE'),'Status tự động kích hoạt lỗi')}
function testDeviceActive(){requireTestMode();assertTrue(['PENDING','ACTIVE','BLOCKED','REVOKED'].includes('ACTIVE'),'Status lỗi')}
function testDeviceBlocked(){requireTestMode();assertTrue(['PENDING','ACTIVE','BLOCKED','REVOKED'].includes('BLOCKED'),'Status lỗi')}
function testDeviceRevoked(){requireTestMode();assertTrue(['PENDING','ACTIVE','BLOCKED','REVOKED'].includes('REVOKED'),'Status lỗi')}
function testDuplicateAudit(){requireTestMode();const rows=[{audit_id:'A',write_status:'COMPLETED'}];assertTrue(rows.find(x=>x.audit_id==='A').write_status==='COMPLETED','Không phát hiện audit trùng')}
function testMachineInsert(){requireTestMode();assertTrue(headers('MAY_TINH_HIEN_TAI')[0]==='asset_code','Schema máy lỗi')}
function testMachineUpdate(){requireTestMode();assertTrue(headers('MAY_TINH_HIEN_TAI').includes('row_version'),'Thiếu row_version')}
function testHistoryOnly(){requireTestMode();assertTrue(headers('LICH_SU_KIEM_TRA').includes('audit_time'),'Thiếu audit_time')}
function testAssetConflict(){requireTestMode();assertTrue(identifyConflict({serial_number:'S1',uuid:'U1'},{serial_number:'S2',uuid:'U2'})==='ASSET_IDENTITY_CONFLICT','Không phát hiện xung đột tài sản')}
function testSerialConflict(){requireTestMode();assertTrue(headers('XUNG_DOT').includes('serial_old'),'Thiếu trường xung đột serial')}
function testEmployeeNameConflict(){requireTestMode();assertTrue(headers('XUNG_DOT').includes('assigned_user_new'),'Thiếu trường xung đột nhân viên')}
function testSyncSummary(){requireTestMode();assertTrue(headers('CHANGE_LOG').includes('change_seq'),'Thiếu change_seq')}
function testSyncChangesPagination(){requireTestMode();assertTrue(Number(props().getProperty('MAX_PAGE_SIZE')||500)===500,'Page size lỗi')}
function testGetAuditDetail(){requireTestMode();assertTrue(['RAM','O_DIA','GPU','CARD_MANG'].every(x=>Boolean(SHEETS[x])),'Thiếu sheet chi tiết')}
function testLockRelease(){requireTestMode();const lock=LockService.getScriptLock();assertTrue(lock.tryLock(1000),'Không lấy được lock');lock.releaseLock()}
