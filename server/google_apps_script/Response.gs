function jsonResponse(value){return ContentService.createTextOutput(JSON.stringify(value)).setMimeType(ContentService.MimeType.JSON)}
function ok(code,message,data){return Object.assign({success:true,code:code,message:message||'',server_time:nowIso()},data||{})}
function fail(code,message){return {success:false,code:code,message:message||'',server_time:nowIso()}}

