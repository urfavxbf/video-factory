/** Authenticated AI editorial service and 24-hour cached Pixabay search. */
const MODEL = "@cf/meta/llama-3.1-8b-instruct";
const STYLES = ["relatable problem", "unexpected contrast", "short narrative", "myth versus evidence", "direct curiosity"];
const response = (body, code = 200) => new Response(JSON.stringify(body), {
  status: code, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" }
});
export function authorized(header, expected) {
  if (!expected || !header?.startsWith("Bearer ")) return false;
  const actual = header.slice(7);
  if (actual.length !== expected.length) return false;
  let diff = 0;
  for (let i = 0; i < actual.length; i++) diff |= actual.charCodeAt(i) ^ expected.charCodeAt(i);
  return diff === 0;
}
export function normalizeRequest(input) {
  if (!input || typeof input !== "object" || Array.isArray(input)) throw new Error("Invalid request");
  const topic = String(input.topic || "").trim().replace(/\s+/g, " ");
  const angle = String(input.angle || "").trim().replace(/\s+/g, " ");
  if (topic.length < 5 || topic.length > 120) throw new Error("Topic must have 5–120 characters");
  if (angle.length > 180) throw new Error("Angle is too long");
  const previousTitles = (Array.isArray(input.previousTitles) ? input.previousTitles : [])
    .filter(s => typeof s === "string").slice(-15).map(s => s.slice(0, 100));
  return { topic, angle, previousTitles };
}
function field(v, name, min, max) {
  if (typeof v !== "string") throw new Error("Missing " + name);
  const s = v.trim().replace(/\s+/g, " ");
  if (s.length < min || s.length > max) throw new Error("Invalid " + name);
  return s;
}
export function validateContentPack(value, previousTitles = []) {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Invalid AI response");
  const title = field(value.title, "title", 12, 85);
  if (previousTitles.some(t => t.trim().toLowerCase() === title.toLowerCase()))
    throw new Error("Title duplicates a recent video");
  const script = field(value.script, "script", 250, 1450);
  const wordCount = script.split(/\s+/).length;
  if (wordCount < 65 || wordCount > 200) throw new Error("Script outside 65–200 words");
  const caption = field(value.caption, "caption", 30, 400);
  const hook = field(value.hook, "hook", 8, 160);
  const hashtags = value.hashtags;
  if (!Array.isArray(hashtags) || hashtags.length < 3 || hashtags.length > 6 ||
      !hashtags.every(t => typeof t === "string" && /^#[A-Za-z0-9_]{2,40}$/.test(t)))
    throw new Error("Invalid hashtags");
  const visualQueries = value.visualQueries;
  if (!Array.isArray(visualQueries) || visualQueries.length !== 3 ||
      !visualQueries.every(t => typeof t === "string" && /^[a-zA-Z0-9 ]{4,60}$/.test(t.trim())))
    throw new Error("Expected three English visual queries");
  const queries = visualQueries.map(t => t.trim().toLowerCase().replace(/\s+/g, " "));
  if (new Set(queries).size !== 3) throw new Error("Duplicate visual queries");
  return {
    title, script, caption, hook, hashtags, visualQueries: queries,
    sourceNote: typeof value.sourceNote === "string" ? value.sourceNote.slice(0, 300) : "",
    humanReviewRequired: true, provenance: "AI draft; factual review required",
    voiceTarget: "Filipino narration for ElevenLabs",
  };
}
export function parseAIResponse(result) {
  const raw = result?.response;
  if (raw && typeof raw === "object" && !Array.isArray(raw)) return raw;
  if (typeof raw !== "string" || raw.length > 40000) throw new Error("Invalid AI JSON");
  const text = raw.trim().replace(new RegExp("^\\x60{3}(?:json)?\\s*", "i"), "")
    .replace(new RegExp("\\s*\\x60{3}$"), "");
  return JSON.parse(text);
}
export async function generatePack(env, data) {
  if (!env.AI?.run) throw new Error("Workers AI binding unavailable");
  const style = STYLES[(data.topic.length + data.previousTitles.length) % STYLES.length];
  const system = [
    "Write an ORIGINAL, engaging Filipino YouTube Short editorial content kit.",
    "Use natural spoken Tagalog/Taglish, not stock phrases or fixed templates.",
    "Episode angle:", style + ".", "Avoid opening with Alam mo ba and generic engagement bait.",
    "Write a distinctive hook, payoff and useful conclusion. Be accurate and cautious;",
    "never invent sources, study results, precise numbers or quotes. Do not claim to fact-check.",
    "65-200 spoken words, ideally 85-130, with no stage directions or headings.",
    "Return ONLY JSON with title (12-85 chars), script, hook (8-160 chars),",
    "caption (30-400 chars), hashtags (3-6 strings starting #),",
    "visualQueries (exactly 3 distinct 2-5-word English keywords for Pixabay stock",
    "images or footage, different scenes), sourceNote (claims that need verification).",
    "Ensure that title and caption have fresh wording that differs from prior titles."
  ].join(" ");
  const result = await env.AI.run(MODEL, {
    messages: [
      { role: "system", content: system },
      { role: "user", content: JSON.stringify(data) },
    ],
    response_format: { type: "json_object" }, temperature: 0.75, max_tokens: 1850,
  });
  return validateContentPack(parseAIResponse(result), data.previousTitles);
}
export function cleanAssetResults(kind, json) {
  return (Array.isArray(json?.hits) ? json.hits : []).slice(0, 8).flatMap(hit => {
    const pageUrl = String(hit.pageURL || "");
    const selection = kind === "videos" ? (hit.videos?.small || hit.videos?.medium) : null;
    const downloadUrl = kind === "videos" ? selection?.url : (hit.largeImageURL || hit.webformatURL);
    const previewUrl = kind === "videos" ? selection?.thumbnail : (hit.previewURL || hit.webformatURL);
    if (!Number.isSafeInteger(Number(hit.id)) || !pageUrl.startsWith("https://pixabay.com/") ||
        typeof downloadUrl !== "string" || !downloadUrl.startsWith("https://") ||
        typeof previewUrl !== "string" || !previewUrl.startsWith("https://")) return [];
    return [{
      id: String(hit.id), type: kind === "videos" ? "video" : "image",
      downloadUrl, previewUrl, pageUrl, creator: String(hit.user || "Pixabay contributor").slice(0, 80),
      source: "Pixabay",
    }];
  });
}
export async function assetSearch(env, query, kind, cache) {
  if (!env.PIXABAY_API_KEY) throw new Error("Pixabay API key unavailable");
  const q = query.trim().replace(/\s+/g, " ");
  if (!/^[a-zA-Z0-9 ]{4,60}$/.test(q) || !["videos", "images"].includes(kind))
    throw new Error("Invalid asset search request");
  const cacheKey = new Request("https://cache.videofactory.example/" + kind + "?q=" + encodeURIComponent(q.toLowerCase()));
  if (cache) {
    try {
      const existing = await cache.match(cacheKey);
      if (existing) return existing.json();
    } catch { /* Cache API can be unavailable in development/preview. */ }
  }
  const url = new URL(kind === "videos" ? "https://pixabay.com/api/videos/" : "https://pixabay.com/api/");
  const params = {
    key: env.PIXABAY_API_KEY, q, per_page: "8", safesearch: "true",
    ...(kind === "videos" ? { video_type: "film" } : { image_type: "photo" }),
  };
  for (const [key, value] of Object.entries(params)) url.searchParams.set(key, value);
  const upstream = await fetch(url.toString(), { signal: AbortSignal.timeout(12000) });
  if (!upstream.ok) throw new Error("Pixabay HTTP " + upstream.status);
  const result = { results: cleanAssetResults(kind, await upstream.json()), attribution: "Media by Pixabay contributors" };
  if (cache) {
    try {
      await cache.put(cacheKey, new Response(JSON.stringify(result), {
        headers: { "Cache-Control": "public,max-age=86400", "Content-Type": "application/json" },
      }));
    } catch { /* Do not block owner-initiated searches when cache is unavailable. */ }
  }
  return result;
}
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/health" && request.method === "GET")
      return response({ ok: true });
    if (!authorized(request.headers.get("authorization"), env.APP_ACCESS_TOKEN))
      return response({ error: "Unauthorized. Check access token." }, 401);
    try {
      if (url.pathname === "/v1/generate" && request.method === "POST") {
        if (Number(request.headers.get("content-length") || 0) > 8192)
          return response({ error: "Request too large" }, 413);
        const raw = await request.text();
        if (raw.length > 8192) return response({ error: "Request too large" }, 413);
        return response(await generatePack(env, normalizeRequest(JSON.parse(raw))));
      }
      if (url.pathname === "/v1/assets" && request.method === "GET")
        return response(await assetSearch(env, url.searchParams.get("query") || "",
          url.searchParams.get("kind") || "", typeof caches === "undefined" ? null : caches.default));
      return response({ error: "Not found" }, 404);
    } catch (error) {
      if (error instanceof SyntaxError) return response({ error: "Invalid JSON" }, 422);
      if (error instanceof Error &&
          /Invalid|Missing|Topic|Angle|Duplicate|Expected|outside|too large/.test(error.message))
        return response({ error: error.message }, 422);
      return response({ error: "Service unavailable. Check Worker configuration." }, 503);
    }
  }
};
