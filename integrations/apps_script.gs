// Google Apps Script: Google Forms/Sheets → SAVE API (compute + store)
const API_URL = "https://YOUR_RENDER_URL/v1/save/assessments";
const API_KEY = "YOUR_BEARER_TOKEN_OR_EMPTY";

function keyFromTitle(title) {
  const parts = title.split("|");
  return parts.length > 1 ? parts[0].trim() : title.trim();
}

function onFormSubmit(e) {
  const named = e.namedValues || {};
  const responses = {};
  Object.keys(named).forEach((title) => {
    const key = keyFromTitle(title);
    const v = named[title];
    responses[key] = Array.isArray(v) ? (v.length ? v[0] : "") : v;
  });

  const meta_public = {
    sector: responses["META_sector"] || "",
    employment: responses["META_employment"] || "",
    years_experience: responses["META_years"] || ""
  };

  const payload = { consent_research: true, meta_public: meta_public, responses: responses };

  const params = { method: "post", contentType: "application/json", payload: JSON.stringify(payload), muteHttpExceptions: true };
  if (API_KEY && API_KEY.trim().length > 0) params.headers = { "Authorization": "Bearer " + API_KEY.trim() };

  const res = UrlFetchApp.fetch(API_URL, params);
  Logger.log(res.getResponseCode() + " " + res.getContentText());
}
