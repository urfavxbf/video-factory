import { test } from "node:test";
import assert from "node:assert/strict";
import worker, {
  authorized, normalizeRequest, validateContentPack,
  parseAIResponse, cleanAssetResults, assetSearch, normalizeStoryboardRequest, validateStoryboard
} from "../src/index.mjs";

const base = () => ({
  title: "Bakit Biglang Umiinit ang Phone Mo?",
  script: Array(12).fill("Kapag ginagamit ang cellphone, ang processor ay kumokonsumo ng enerhiya at may inilalabas na init.").join(" "),
  hook: "Bakit parang umiinit ang phone kahit normal lang ang gamit?",
  caption: "Hindi lahat ng init ay nangangahulugang sira na ang phone. Alamin ang puwedeng dahilan.",
  hashtags: ["#TechPH", "#PhoneTips", "#FilipinoExplains"],
  visualQueries: ["smartphone in hand", "phone charging desk", "mobile gaming closeup"],
  sourceNote: "Verify device-specific operating temperatures.",
});

test("private token comparison and malformed credentials", () => {
  assert.equal(authorized("Bearer abc123", "abc123"), true);
  assert.equal(authorized("Bearer abc124", "abc123"), false);
  assert.equal(authorized(null, "abc123"), false);
  assert.equal(authorized("Bearer abc123", ""), false);
});

test("topic and optional angle validation", () => {
  assert.deepEqual(normalizeRequest({topic:"  battery  health ",angle:" phone users "}).topic, "battery health");
  assert.throws(() => normalizeRequest({topic:"abc"}), /Topic/);
  assert.throws(() => normalizeRequest({topic:"x".repeat(121)}), /Topic/);
});

test("valid AI draft must contain three distinct scenes and a non-template script", () => {
  const pack = validateContentPack(base());
  assert.equal(pack.visualQueries.length, 3);
  assert.equal(pack.humanReviewRequired, true);
  assert.equal(pack.hashtags.length, 3);
  assert.throws(() => validateContentPack(base(), [base().title]), /duplicates/);
  assert.throws(() => validateContentPack({...base(),script:"Short filler"}), /script|Script/);
  assert.throws(() => validateContentPack({...base(),visualQueries:["same words","same words","another image"]}), /Duplicate/);
});

test("parse provider object and fenced JSON", () => {
  assert.deepEqual(parseAIResponse({response: base()}), base());
  assert.equal(parseAIResponse({response: "{" + '"title":"Example"' + "}"}).title, "Example");
});

test("normalize Pixabay image and video results with attribution and source page", () => {
  const photo = cleanAssetResults("images", {hits:[{
    id:12,pageURL:"https://pixabay.com/photos/x-12/",user:"artist",
    previewURL:"https://cdn.pixabay.com/thumb.jpg",
    largeImageURL:"https://cdn.pixabay.com/large.jpg"
  }]});
  assert.equal(photo[0].type, "image");
  assert.equal(photo[0].creator,"artist");
  const video = cleanAssetResults("videos", {hits:[{
    id:13,pageURL:"https://pixabay.com/videos/y-13/",videos:{
      small:{url:"https://cdn.pixabay.com/video.mp4",thumbnail:"https://cdn.pixabay.com/cover.jpg"}
    }
  }]});
  assert.equal(video[0].type, "video");
  assert.equal(video[0].downloadUrl, "https://cdn.pixabay.com/video.mp4");
});

test("worker rejects unauthorized requests before AI calls", async () => {
  const result = await worker.fetch(new Request("https://example.com/v1/generate", {
    method:"POST",body:"{}"
  }), {APP_ACCESS_TOKEN:"private"});
  assert.equal(result.status, 401);
});

test("worker calls AI once and returns validated draft", async () => {
  let calls = 0;
  const env = {
    APP_ACCESS_TOKEN: "private",
    AI: {run:async (_model, options) => {
      calls++;
      assert.match(options.messages[0].content, /Filipino/);
      return {response: JSON.stringify(base())};
    }}
  };
  const result = await worker.fetch(new Request("https://example.com/v1/generate", {
    method:"POST",headers:{"authorization":"Bearer private"},
    body:JSON.stringify({topic:"Bakit umiinit ang phone?"})
  }), env);
  assert.equal(result.status, 200);
  assert.equal(calls, 1);
  assert.equal((await result.json()).humanReviewRequired,true);
});

test("Pixabay search is attributed and rejects invalid query", async () => {
  await assert.rejects(() => assetSearch({PIXABAY_API_KEY:"x"}, "?", "images", null), /Invalid/);
  const previous = globalThis.fetch;
  globalThis.fetch = async () => new Response(JSON.stringify({hits: []}), {status:200});
  try {
    const result = await assetSearch({PIXABAY_API_KEY:"example"}, "blue sky", "images", null);
    assert.deepEqual(result.results, []);
    assert.match(result.attribution,/Pixabay/);
  } finally { globalThis.fetch = previous; }
});

test("owner search still returns media if edge cache backend is unavailable", async () => {
  const previous = globalThis.fetch;
  globalThis.fetch = async () => new Response(JSON.stringify({hits:[]}), {status:200});
  const brokenCache = {
    match: async () => { throw new Error("Cache disabled"); },
    put: async () => { throw new Error("Cache disabled"); },
  };
  try {
    const result = await assetSearch({PIXABAY_API_KEY:"example"}, "moon surface", "videos", brokenCache);
    assert.equal(result.results.length, 0);
  } finally { globalThis.fetch = previous; }
});


test("AI schema request retries invalid provider output and then succeeds", async () => {
  let attempts = 0;
  const data = base();
  const env = {AI:{run: async (_model, opts) => {
    attempts++;
    assert.equal(opts.response_format.type, "json_schema");
    assert.ok(opts.response_format.json_schema.schema.properties.visualQueries);
    return {response: attempts === 1 ? {...data,script:"Too short"} : data};
  }}};
  const kit = await (await import("../src/index.mjs")).generatePack(env, {topic:"charging phone",angle:"",previousTitles:[]});
  assert.equal(attempts,2);
  assert.equal(kit.title,data.title);
});

test("model tags without # are normalized before publication", () => {
  const kit=validateContentPack({...base(),hashtags:["TagalogTech","PhoneTips","SciencePH"]});
  assert.deepEqual(kit.hashtags,["#TagalogTech","#PhoneTips","#SciencePH"]);
});

test("invalid drafts fail with useful safe public message after two attempts", async () => {
  let tries=0;
  const env={APP_ACCESS_TOKEN:"private",AI:{run:async()=>{tries++;return {response:{...base(),script:"Nope"}};}}};
  const req=new Request("https://example.com/v1/generate",{method:"POST",headers:{authorization:"Bearer private"},body:JSON.stringify({topic:"charging phone"})});
  const res=await worker.fetch(req,env);
  assert.equal(tries,2);
  assert.equal(res.status,422);
  assert.equal((await res.json()).code,"CONTENT_VALIDATION_FAILED");
});

const flowDraft = () => ({
  mainSubjectReference:"A Filipino college student, 23 years old, short black hair, cream shirt, blue jeans and brown backpack.",
  scenes: Array.from({length:7},(_,i)=>({
    title:"Scene " + (i+1) + " — cinematic campus moment",
    voiceoverBeat:"Ang spotlight effect sa pang araw araw na buhay at kahihiyan.",
    prompt: "Cinematic vertical video in a realistic university hallway in the Philippines. A young Filipino male student with short black hair, a cream shirt, dark blue jeans and a brown backpack " +
      "walks slowly among other students. The camera follows the nervous subject in a believable live action scene. This is beat " + (i+1) + " of the narrative. Warm window lighting and subtle facial expressions. No dialogue, onscreen text or music.",
  }))
});

test("flow storyboard request is bounded to current episode content", () => {
  const data=base();
  const parsed=normalizeStoryboardRequest(data);
  assert.equal(parsed.title,data.title);
  assert.equal(parsed.script,data.script);
  assert.throws(()=>normalizeStoryboardRequest({title:"abc",script:"x",hook:"foo"}),/title/);
  assert.throws(()=>normalizeStoryboardRequest({title:data.title,script:"Too short",hook:data.hook}),/script/);
});

test("flow storyboard enforces exactly seven standalone cinematic prompts", () => {
  const valid=validateStoryboard(flowDraft());
  assert.equal(valid.scenes.length,7);
  assert.equal(valid.clipDurationSeconds,8);
  assert.equal(valid.aspectRatio,"9:16");
  assert.equal(valid.generatedVideo,false);
  assert.throws(()=>validateStoryboard({...flowDraft(),scenes:flowDraft().scenes.slice(0,6)}),/seven/);
  assert.throws(()=>validateStoryboard({...flowDraft(),scenes:flowDraft().scenes.map(s=>({...s,prompt:"Short"}))}),/prompt/);
});

test("authenticated flow endpoint returns storyboard without making videos",async()=>{
  const data=base();
  let calls=0;
  const env={APP_ACCESS_TOKEN:"secret",AI:{run:async (_model,opts)=>{
    calls++;
    assert.equal(opts.response_format.type,"json_schema");
    assert.ok(opts.response_format.json_schema.schema.properties.scenes);
    assert.match(opts.messages[0].content,/Google Flow/);
    return {response:flowDraft()};
  }}};
  const request=new Request("https://test.local/v1/storyboard",{
    method:"POST",headers:{"authorization":"Bearer secret"},
    body:JSON.stringify({title:data.title,hook:data.hook,script:data.script}),
  });
  const response=await worker.fetch(request,env);
  assert.equal(response.status,200);
  const result=await response.json();
  assert.equal(result.scenes.length,7);
  assert.equal(calls,1);
});

test("invalid Google Flow scene output retries then returns a safe error",async()=>{
  const data=base();let calls=0;
  const env={APP_ACCESS_TOKEN:"secret",AI:{run:async()=>{
    calls++;
    return {response:{...flowDraft(),scenes:[flowDraft().scenes[0]]}};
  }}};
  const request=new Request("https://test.local/v1/storyboard",{
    method:"POST",headers:{"authorization":"Bearer secret"},body:JSON.stringify(data),
  });
  const response=await worker.fetch(request,env);
  assert.equal(response.status,422);
  assert.equal((await response.json()).code,"STORYBOARD_VALIDATION_FAILED");
  assert.equal(calls,2);
});
