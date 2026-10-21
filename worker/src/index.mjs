/** Authenticated AI editorial service and 24-hour cached Pixabay search. */
const MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast";
const CONTENT_SCHEMA = { type: "object", properties: { title:{type:"string"},script:{type:"string"},hook:{type:"string"},caption:{type:"string"},hashtags:{type:"array",items:{type:"string"}},visualQueries:{type:"array",items:{type:"string"}},sourceNote:{type:"string"} }, required:["title","script","hook","caption","hashtags","visualQueries","sourceNote"], additionalProperties:false };
const STORYBOARD_SCHEMA = {
  type: "object",
  properties: {
    mainSubjectReference: {type:"string"},
    scenes: {
      type:"array",
      items:{
        type:"object",
        properties:{
          title:{type:"string"},
          voiceoverBeat:{type:"string"},
          prompt:{type:"string"}
        },
        required:["title","voiceoverBeat","prompt"],
        additionalProperties:false
      }
    }
  },
  required:["mainSubjectReference","scenes"],
  additionalProperties:false
};
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
  const hashtags = Array.isArray(value.hashtags) ? value.hashtags.map(s => typeof s === "string" ? (s.trim().startsWith("#") ? s.trim() : "#" + s.trim()) : s) : value.hashtags;
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
  // Strict JSON schemas ensure arrays remain arrays, but cannot guarantee word
  // budgets. Retry once with concrete validation feedback instead of returning
  // unrelated filler or silently dropping to a repetitive template.
  let feedback = "";
  for (let attempt = 0; attempt < 2; attempt++) {
    const result = await env.AI.run(MODEL, {
      messages: [
        {role:"system",content:system + " Your response must follow the JSON schema. Hashtags must be strings with #. Narration must be at least 85 spoken Filipino words, ideally 100-125. Caption must be descriptive (at least 30 characters). Avoid generic slogans and unverified explanations."},
        {role:"user",content:JSON.stringify(data) + (feedback ? "\nREWRITE PREVIOUS DRAFT: " + feedback + ". Keep the factual content careful, do not invent claims." : "")},
      ],
      response_format: {type:"json_schema",json_schema:{name:"content_kit",schema:CONTENT_SCHEMA,strict:true}},
      temperature:0.65,max_tokens:2200,
    });
    try { return validateContentPack(parseAIResponse(result),data.previousTitles); }
    catch(error) {
      if (!(error instanceof Error)) throw error;
      feedback = error.message;
      if (attempt === 1) throw new Error("CONTENT_VALIDATION_FAILED");
    }
  }
  throw new Error("CONTENT_VALIDATION_FAILED");
}
export function normalizeStoryboardRequest(input) {
  if (!input || typeof input !== "object" || Array.isArray(input))
    throw new Error("Invalid storyboard request");
  return {
    title: field(input.title, "title", 12, 100),
    hook: field(input.hook, "hook", 8, 180),
    script: field(input.script, "script", 250, 1600),
  };
}

export function validateStoryboard(value) {
  if (!value || typeof value !== "object" || Array.isArray(value))
    throw new Error("Invalid storyboard response");
  const mainSubjectReference = field(value.mainSubjectReference, "mainSubjectReference", 10, 450);
  if (!Array.isArray(value.scenes) || value.scenes.length !== 7)
    throw new Error("Expected exactly seven storyboard scenes");
  const scenes = value.scenes.map((scene, index) => {
    if (!scene || typeof scene !== "object" || Array.isArray(scene))
      throw new Error("Invalid scene " + (index + 1));
    return {
      title: field(scene.title, "scene title", 6, 95),
      voiceoverBeat: field(scene.voiceoverBeat, "voiceoverBeat", 10, 200),
      prompt: field(scene.prompt, "scene prompt", 125, 1100),
    };
  });
  if (new Set(scenes.map(s => s.prompt.toLowerCase())).size !== 7)
    throw new Error("Duplicate scene prompts");
  return {
    mainSubjectReference,
    scenes,
    clipDurationSeconds: 8,
    aspectRatio: "9:16",
    generatedVideo: false,
    needsHumanReview: true,
  };
}

export async function generateStoryboard(env, data) {
  if (!env.AI?.run) throw new Error("Workers AI binding unavailable");
  const prompt = [
    "You are a cinematic storyboard director making seven ORIGINAL Google Flow VIDEO GENERATION PROMPTS.",
    "The supplied Filipino voice-over SCRIPT is the source of truth. Storyboard only its actual scenes and claims.",
    "Create a coherent seven-scene video, approximately 8 seconds per scene, vertical 9:16,",
    "for a Filipino YouTube Short edited later in CapCut.",
    "CRITICAL: The output is not seven suggested stock-search terms; each PROMPT must be a",
    "complete detailed standalone English video prompt of 35-100 words.",
    "Each scene prompt should describe: location, concrete action, character appearance and clothing",
    "when the main character recurs, facial performance, composition, camera movement, lighting,",
    "photorealistic cinematic style and the psychology/emotion of the beat.",
    "Make mainSubjectReference a reusable exact description of the recurring character or",
    "relevant recurring subject's age, appearance, clothing and setting.",
    "Repeat relevant character details INSIDE EVERY standalone scene prompt;",
    "do not write only 'same student as scene 1'.",
    "Use a varied visual arc: emotional hook, relatable event, explanatory conceptual image,",
    "character reaction, perspective shift, realization, memorable visual conclusion.",
    "Do not insert unsupported research claims or quotations, identifiable celebrities,",
    "logos, onscreen typography, subtitles, dialogue, synthetic voice-over, or music.",
    "No visible text or captions. Leave narration and music for ElevenLabs and CapCut.",
    "The imagined feeling of other people looking at the character must be represented",
    "as imagined when needed, not as a factual claim that everyone is staring.",
    "Write voiceoverBeat as a SHORT Tagalog summary of the PART of the provided script",
    "shown during the corresponding 8-second scene; cover the narration in order.",
    "Return ONLY JSON matching the schema with mainSubjectReference and exactly 7 scenes.",
    "Each scene: title, voiceoverBeat, prompt. Scene titles should be specific and varied.",
  ].join(" ");
  let feedback = "";
  for (let attempt = 0; attempt < 2; attempt++) {
    const result = await env.AI.run(MODEL, {
      messages: [
        {role:"system",content:prompt},
        {role:"user",content:JSON.stringify(data) + (feedback ? "\nREWRITE TO PASS VALIDATION: " + feedback : "")},
      ],
      response_format:{type:"json_schema",json_schema:{name:"flow_storyboard",schema:STORYBOARD_SCHEMA,strict:true}},
      temperature:0.65,
      max_tokens:3600,
    });
    try { return validateStoryboard(parseAIResponse(result)); }
    catch(error) {
      if (!(error instanceof Error)) throw error;
      feedback = error.message;
      if (attempt === 1) throw new Error("STORYBOARD_VALIDATION_FAILED");
    }
  }
  throw new Error("STORYBOARD_VALIDATION_FAILED");
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
      if (url.pathname === "/v1/storyboard" && request.method === "POST") {
        if (Number(request.headers.get("content-length") || 0) > 8192)
          return response({error:"Request too large"},413);
        const raw = await request.text();
        if (raw.length > 8192) return response({error:"Request too large"},413);
        return response(await generateStoryboard(env, normalizeStoryboardRequest(JSON.parse(raw))));
      }
      if (url.pathname === "/v1/assets" && request.method === "GET")
        return response(await assetSearch(env, url.searchParams.get("query") || "",
          url.searchParams.get("kind") || "", typeof caches === "undefined" ? null : caches.default));
      return response({ error: "Not found" }, 404);
    } catch (error) {
      if (error instanceof SyntaxError) return response({ error: "AI returned invalid structured JSON. Retry." }, 502);
      if (error instanceof Error && error.message === "STORYBOARD_VALIDATION_FAILED")
        return response({error:"Google Flow storyboard did not pass quality checks after retry. Try again.",code:"STORYBOARD_VALIDATION_FAILED"},422);
      if (error instanceof Error && error.message === "CONTENT_VALIDATION_FAILED")
        return response({ error: "AI draft did not pass quality checks after retry. Try a more specific topic.", code:"CONTENT_VALIDATION_FAILED" }, 422);
      if (error instanceof Error && /quota|rate.limit|capacity|limit.exceeded|429/i.test(error.message))
        return response({ error: "AI service limit or quota reached. Try later.", code:"AI_QUOTA" }, 503);
      if (error instanceof Error &&
          /Invalid|Missing|Topic|Angle|Duplicate|Expected|outside|too large/.test(error.message))
        return response({ error: error.message }, 422);
      return response({ error: "Service unavailable. Check Worker configuration." }, 503);
    }
  }
};
