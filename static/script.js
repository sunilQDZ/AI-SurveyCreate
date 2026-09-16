// // /* -----------------------------------------------------
// //    GLOBAL STATE
// // ----------------------------------------------------- */
// // let questionFlow = [];
// // let currentQuestionIndex = 0;
// // let collectedAnswers = {};
// // let storedTemplates = [];
// // let selectedTemplateIndex = null;

// // let originalUserInput = "";
// // let detectedSurveyType = "";

// // /* -----------------------------------------------------
// //    DOM ELEMENTS
// // ----------------------------------------------------- */
// // const chatEl = document.getElementById("chat");
// // const quickEl = document.getElementById("quick");
// // const userInput = document.getElementById("userInput");
// // const sendBtn = document.getElementById("sendBtn");
// // const restartBtn = document.getElementById("restartBtn");

// // const templateList = document.getElementById("templateList");
// // const customizeBtn = document.getElementById("customizeBtn");
// // const generateMoreBtn = document.getElementById("generateMoreBtn");
// // const finalizeBtn = document.getElementById("finalizeBtn");
// // const downloadJsonBtn = document.getElementById("downloadJsonBtn");

// // /* -----------------------------------------------------
// //    HELPERS
// // ----------------------------------------------------- */
// // function escapeHtml(str) {
// //   return String(str || "").replace(/</g, "&lt;").replace(/>/g, "&gt;");
// // }

// // function appendMessage(msg, type = "bot") {
// //   const div = document.createElement("div");
// //   div.className = `msg ${type}`;
// //   div.innerHTML = msg;
// //   chatEl.appendChild(div);
// //   chatEl.scrollTop = chatEl.scrollHeight;
// // }

// // async function apiPost(url, payload) {
// //   try {
// //     const res = await fetch(url, {
// //       method: "POST",
// //       headers: { "Content-Type": "application/json" },
// //       body: JSON.stringify(payload),
// //     });
// //     return await res.json();
// //   } catch (err) {
// //     appendMessage("⚠️ Network error.", "bot");
// //     console.error("API Error:", err);
// //     return { error: "network" };
// //   }
// // }

// // function clearInlineInputs() {
// //   document.querySelectorAll(".input-inline").forEach((x) => x.remove());
// //   document.querySelectorAll(".options-list").forEach((x) => x.remove());
// // }

// // /* -----------------------------------------------------
// //    START FLOW
// // ----------------------------------------------------- */
// // async function startFlow(text) {
// //   originalUserInput = text.trim();

// //   collectedAnswers = {};
// //   storedTemplates = [];
// //   selectedTemplateIndex = null;

// //   appendMessage(escapeHtml(originalUserInput), "user");
// //   appendMessage("🧠 Understanding your request…", "bot");

// //   // ⭐ FIXED: survey_type should NOT be the user input
// //   const resp = await apiPost("/generate_question_flow", {
// //       user_input: originalUserInput,
// //       survey_type: null     // ← Always null, backend will detect properly
// //   });


// //   // Skip case
// //   if (resp.skip_questions) {
// //     appendMessage("✅ All details understood. Generating templates…", "bot");

// //     collectedAnswers = {
// //       survey_type: resp.detected_survey_type,
// //       audience: resp.detected_audience,
// //       purpose: resp.detected_purpose
// //     };

// //     return generateSurvey();
// //   }

// //   // Normal multi-question flow
// //   questionFlow = (resp.question_flow || []).map((q) => ({
// //     id: q.id,
// //     text: q.q || q.question,
// //     options: q.options || [],
// //     allow_text: q.allow_text_input || false,
// //   }));

// //   currentQuestionIndex = 0;

// //   appendMessage("📝 I need a few quick details…", "bot");
// //   askNextQuestion();
// // }

// // /* -----------------------------------------------------
// //    ASK NEXT QUESTION
// // ----------------------------------------------------- */
// // function askNextQuestion() {
// //   clearInlineInputs();

// //   if (currentQuestionIndex >= questionFlow.length) {
// //     return generateSurvey();
// //   }

// //   const q = questionFlow[currentQuestionIndex];
// //   appendMessage(`❓ ${escapeHtml(q.text)}`, "bot");

// //   // With options (chips)
// //   if (q.options.length > 0) {
// //     const box = document.createElement("div");
// //     box.className = "msg options-list bot";

// //     const optDiv = document.createElement("div");
// //     optDiv.className = "options";

// //     q.options.forEach((op) => {
// //       const btn = document.createElement("button");
// //       btn.className = "chip";
// //       btn.textContent = op;
// //       btn.onclick = () => handleAnswer(op);
// //       optDiv.appendChild(btn);
// //     });

// //     const other = document.createElement("input");
// //     other.type = "text";
// //     other.placeholder = "Type your answer…";
// //     other.className = "input-inline";
// //     other.onkeydown = (e) => {
// //       if (e.key === "Enter" && other.value.trim()) {
// //         handleAnswer(other.value.trim());
// //       }
// //     };

// //     box.appendChild(optDiv);
// //     box.appendChild(other);
// //     chatEl.appendChild(box);
// //     chatEl.scrollTop = chatEl.scrollHeight;
// //   }

// //   // Free-text only
// //   else {
// //     const box = document.createElement("div");
// //     box.className = "msg input-inline bot";
// //     box.innerHTML = `<input id="inlineQ" type="text" placeholder="Type your answer…">`;
// //     chatEl.appendChild(box);

// //     const input = document.getElementById("inlineQ");
// //     input.focus();
// //     input.onkeydown = (e) => {
// //       if (e.key === "Enter" && input.value.trim()) {
// //         handleAnswer(input.value.trim());
// //       }
// //     };
// //   }
// // }

// // /* -----------------------------------------------------
// //    HANDLE ANSWER
// // ----------------------------------------------------- */
// // function handleAnswer(ans) {
// //   const q = questionFlow[currentQuestionIndex];

// //   collectedAnswers[q.id || q.text] = ans;
// //   appendMessage(escapeHtml(ans), "user");

// //   currentQuestionIndex++;

// //   if (currentQuestionIndex >= questionFlow.length) {
// //     generateSurvey();
// //   } else {
// //     askNextQuestion();
// //   }
// // }

// // /* -----------------------------------------------------
// //    GENERATE SURVEYS
// // ----------------------------------------------------- */
// // async function generateSurvey() {
// //   appendMessage("✨ Creating survey templates…", "bot");

// //   const res = await apiPost("/generate_survey", {
// //     user_input: originalUserInput,
// //     survey_type: collectedAnswers["survey_type"] || "",
// //     answers: collectedAnswers,
// //   });

// //   if (!res.surveys || !res.surveys.length) {
// //     appendMessage("⚠️ Could not generate templates.", "bot");
// //     return;
// //   }

// //   storedTemplates = res.surveys;
// //   renderTemplates();

// //   customizeBtn.disabled = false;
// //   generateMoreBtn.disabled = false;
// //   finalizeBtn.disabled = false;
// // }

// // /* -----------------------------------------------------
// //    RENDER TEMPLATES
// // ----------------------------------------------------- */
// // function renderTemplates() {
// //   templateList.innerHTML = "";

// //   storedTemplates.forEach((tpl, idx) => {
// //     const card = document.createElement("div");
// //     card.className = "template-card";

// //     card.innerHTML = `
// //       <div style="display:flex;justify-content:space-between;">
// //         <b>${escapeHtml(tpl.title)}</b>
// //         <button class="chip" data-idx="${idx}">Select</button>
// //       </div>
// //       <div class="small"><b>Purpose:</b> ${escapeHtml(tpl.purpose)}</div>
// //       <div class="small"><b>Duration:</b> ${escapeHtml(tpl.duration)}</div>
// //       <hr>
// //       ${tpl.questions
// //         .map(
// //           (q) =>
// //             `<div class="small">• ${escapeHtml(q.question)} (${q.scale_type})</div>`
// //         )
// //         .join("")}
// //     `;

// //     card.querySelector("button").onclick = () => {
// //       selectedTemplateIndex = idx;
// //       appendMessage(`👍 Selected Template ${idx + 1}`, "bot");
// //     };

// //     templateList.appendChild(card);
// //   });
// // }

// // /* -----------------------------------------------------
// //    FINALIZE TEMPLATE
// // ----------------------------------------------------- */
// // finalizeBtn.onclick = async () => {
// //   if (selectedTemplateIndex === null) {
// //     appendMessage("⚠️ Please select a template first.", "bot");
// //     return;
// //   }

// //   const tpl = storedTemplates[selectedTemplateIndex];

// //   const res = await apiPost("/finalize_template", { final_template: tpl });

// //   if (res.template_id) {
// //     appendMessage(`🎉 Template saved (ID: ${res.template_id})`, "bot");
// //     downloadJsonBtn.disabled = false;
// //   }
// // };

// // /* -----------------------------------------------------
// //    DOWNLOAD JSON
// // ----------------------------------------------------- */
// // downloadJsonBtn.onclick = () => {
// //   if (selectedTemplateIndex === null) return;

// //   const tpl = storedTemplates[selectedTemplateIndex];
// //   const blob = new Blob([JSON.stringify(tpl, null, 2)], {
// //     type: "application/json",
// //   });

// //   const a = document.createElement("a");
// //   a.href = URL.createObjectURL(blob);
// //   a.download = `${tpl.title.replace(/\s+/g, "_")}.json`;
// //   a.click();
// // };

// // /* -----------------------------------------------------
// //    QUICK SELECT
// // ----------------------------------------------------- */
// // quickEl.addEventListener("click", (e) => {
// //   const chip = e.target.closest(".chip");
// //   if (!chip) return;
// //   startFlow(chip.dataset.value);
// // });

// // /* -----------------------------------------------------
// //    SEND BUTTON
// // ----------------------------------------------------- */
// // sendBtn.onclick = () => {
// //   const val = userInput.value.trim();
// //   if (!val) return;
// //   userInput.value = "";
// //   startFlow(val);
// // };

// // userInput.onkeydown = (e) => {
// //   if (e.key === "Enter") sendBtn.click();
// // };

// // /* -----------------------------------------------------
// //    RESTART
// // ----------------------------------------------------- */
// // restartBtn.onclick = () => location.reload();
// /* -----------------------------------------------------
//    GLOBAL STATE
// ----------------------------------------------------- */
// /* -----------------------------------------------------
//    GLOBAL STATE
// ----------------------------------------------------- */
// // let questionFlow = [];
// // let currentQuestionIndex = 0;
// // let collectedAnswers = {};
// // let storedTemplates = [];
// // let selectedTemplateIndex = null;

// // let originalUserInput = "";
// // let currentSurveyType = "general";
// // let detectedAudience = "";
// // let detectedPurpose = "";

// // /* -----------------------------------------------------
// //    DOM ELEMENTS
// // ----------------------------------------------------- */
// // const chatEl = document.getElementById("chat");
// // const quickEl = document.getElementById("quick");
// // const userInput = document.getElementById("userInput");
// // const sendBtn = document.getElementById("sendBtn");
// // const restartBtn = document.getElementById("restartBtn");

// // const templateList = document.getElementById("templateList");
// // const previewSubtitle = document.getElementById("previewSubtitle");
// // const customizeBtn = document.getElementById("customizeBtn");
// // const generateMoreBtn = document.getElementById("generateMoreBtn");
// // const finalizeBtn = document.getElementById("finalizeBtn");
// // const downloadJsonBtn = document.getElementById("downloadJsonBtn");

// // /* -----------------------------------------------------
// //    HELPERS
// // ----------------------------------------------------- */
// // function escapeHtml(str) {
// //   return String(str || "")
// //     .replace(/&/g, "&amp;")
// //     .replace(/</g, "&lt;")
// //     .replace(/>/g, "&gt;");
// // }

// // function appendMessage(msg, type = "bot") {
// //   const div = document.createElement("div");
// //   div.className = `msg ${type}`;
// //   div.innerHTML = msg;
// //   chatEl.appendChild(div);
// //   chatEl.scrollTop = chatEl.scrollHeight;
// // }

// // async function apiPost(url, payload) {
// //   try {
// //     const res = await fetch(url, {
// //       method: "POST",
// //       headers: { "Content-Type": "application/json" },
// //       body: JSON.stringify(payload || {}),
// //     });
// //     return await res.json();
// //   } catch (err) {
// //     appendMessage("⚠️ Network or server error.", "bot");
// //     console.error("API Error:", err);
// //     return { error: "network" };
// //   }
// // }

// // function clearInlineInputs() {
// //   document.querySelectorAll(".input-inline").forEach((x) => x.remove());
// //   document.querySelectorAll(".options-list").forEach((x) => x.remove());
// // }

// // function normalizeTemplate(t) {
// //   return {
// //     title: t.title || "Untitled Template",
// //     purpose: t.purpose || "",
// //     duration: t.duration || "",
// //     questions: (t.questions || []).map((q) => ({
// //       question: q.question || q.text || "",
// //       scale_type: q.scale_type || "text",
// //     })),
// //   };
// // }

// // /* -----------------------------------------------------
// //    START FLOW
// // ----------------------------------------------------- */
// // async function startFlow(text) {
// //   originalUserInput = text.trim();
// //   collectedAnswers = {};
// //   storedTemplates = [];
// //   selectedTemplateIndex = null;
// //   questionFlow = [];
// //   currentQuestionIndex = 0;

// //   appendMessage(escapeHtml(originalUserInput), "user");
// //   appendMessage("🧠 Understanding your request…", "bot");

// //   const resp = await apiPost("/generate_question_flow", {
// //     user_input: originalUserInput,
// //     survey_type: "" // always let backend detect automatically
// //   });

// //   currentSurveyType = resp.detected_survey_type || "";
// //   detectedAudience = resp.detected_audience || "";
// //   detectedPurpose = resp.detected_purpose || "";

// //   /* -----------------------------------------------
// //       ✅ FIXED: Handle skip_questions immediately
// //   -------------------------------------------------- */
// //   if (resp.skip_questions === true) {
// //     appendMessage("✅ All required details already detected. Generating templates…", "bot");

// //     if (currentSurveyType) collectedAnswers["survey_type"] = currentSurveyType;
// //     if (detectedAudience) collectedAnswers["audience"] = detectedAudience;
// //     if (detectedPurpose) collectedAnswers["purpose"] = detectedPurpose;

// //     return generateSurvey(); // 🚀 DIRECT jump
// //   }

// //   /* ---- Normal Flow ---- */
// //   questionFlow = (resp.question_flow || []).map((q) => ({
// //     id: q.id || "",
// //     text: q.q || q.question,
// //     options: q.options || [],
// //     allow_text: q.allow_text_input || false,
// //   }));

// //   currentQuestionIndex = 0;
// //   appendMessage("📝 I need a few quick details…", "bot");
// //   askNextQuestion();
// // }

// // /* -----------------------------------------------------
// //    ASK NEXT QUESTION
// // ----------------------------------------------------- */
// // function askNextQuestion() {
// //   clearInlineInputs();

// //   if (currentQuestionIndex >= questionFlow.length) {
// //     return generateSurvey();
// //   }

// //   const q = questionFlow[currentQuestionIndex];
// //   appendMessage(`❓ ${escapeHtml(q.text)}`, "bot");

// //   if (q.options?.length) {
// //     const box = document.createElement("div");
// //     box.className = "msg options-list bot";

// //     const optDiv = document.createElement("div");
// //     optDiv.className = "options";

// //     q.options.forEach((op) => {
// //       const b = document.createElement("button");
// //       b.className = "chip";
// //       b.textContent = op;
// //       b.onclick = () => handleAnswer(op);
// //       optDiv.appendChild(b);
// //     });

// //     const other = document.createElement("input");
// //     other.type = "text";
// //     other.placeholder = "Type your answer…";
// //     other.className = "input-inline";
// //     other.onkeydown = (e) => {
// //       if (e.key === "Enter" && other.value.trim()) {
// //         handleAnswer(other.value.trim());
// //       }
// //     };

// //     box.appendChild(optDiv);
// //     box.appendChild(other);
// //     chatEl.appendChild(box);
// //   } else {
// //     const box = document.createElement("div");
// //     box.className = "msg input-inline bot";
// //     box.innerHTML = `<input id="inlineQ" type="text" placeholder="Type your answer…">`;
// //     chatEl.appendChild(box);

// //     const inp = document.getElementById("inlineQ");
// //     inp.focus();
// //     inp.onkeydown = (e) => {
// //       if (e.key === "Enter" && inp.value.trim()) {
// //         handleAnswer(inp.value.trim());
// //       }
// //     };
// //   }
// // }

// // /* -----------------------------------------------------
// //    HANDLE ANSWER
// // ----------------------------------------------------- */
// // function handleAnswer(ans) {
// //   const q = questionFlow[currentQuestionIndex];

// //   const key = q.id || q.text;
// //   collectedAnswers[key] = ans;

// //   appendMessage(escapeHtml(ans), "user");

// //   if ((q.id || "").toLowerCase() === "survey_type") {
// //     const low = ans.toLowerCase();
// //     if (low.startsWith("nps")) currentSurveyType = "nps";
// //     else if (low.startsWith("csat")) currentSurveyType = "csat";
// //     else if (low.startsWith("ces")) currentSurveyType = "ces";
// //     else currentSurveyType = "general";
// //   }

// //   currentQuestionIndex++;

// //   if (currentQuestionIndex >= questionFlow.length) {
// //     generateSurvey();
// //   } else {
// //     askNextQuestion();
// //   }
// // }

// // /* -----------------------------------------------------
// //    GENERATE SURVEYS
// // ----------------------------------------------------- */
// // async function generateSurvey() {
// //   appendMessage("✨ Creating survey templates…", "bot");

// //   const res = await apiPost("/generate_survey", {
// //     user_input: originalUserInput,
// //     survey_type: currentSurveyType,
// //     answers: collectedAnswers,
// //   });

// //   if (!res.surveys?.length) {
// //     appendMessage("⚠️ Could not generate templates.", "bot");
// //     return;
// //   }

// //   storedTemplates = res.surveys.map(normalizeTemplate);
// //   renderTemplates();

// //   previewSubtitle.textContent = `${storedTemplates.length} templates`;
// //   customizeBtn.disabled = false;
// //   generateMoreBtn.disabled = false;
// //   finalizeBtn.disabled = false;
// // }

// // /* -----------------------------------------------------
// //    RENDER TEMPLATES
// // ----------------------------------------------------- */
// // function renderTemplates() {
// //   templateList.innerHTML = "";

// //   storedTemplates.forEach((tpl, idx) => {
// //     const card = document.createElement("div");
// //     card.className = "template-card";

// //     card.innerHTML = `
// //       <div style="display:flex;justify-content:space-between;align-items:center;">
// //         <div class="template-title">📄 ${escapeHtml(tpl.title)}</div>
// //         <button class="chip" data-idx="${idx}">Select</button>
// //       </div>
// //       <div class="small"><b>Purpose:</b> ${escapeHtml(tpl.purpose)}</div>
// //       <div class="small"><b>Duration:</b> ${escapeHtml(tpl.duration)}</div>
// //       <div style="margin-top:6px">
// //         ${tpl.questions
// //           .map(
// //             (q, i) => `
// //           <div class="question-row">
// //             <span>${i + 1}. ${escapeHtml(q.question)}</span>
// //             <span class="small">(${escapeHtml(q.scale_type)})</span>
// //           </div>`
// //           )
// //           .join("")}
// //       </div>
// //     `;

// //     card.querySelector("button").onclick = () => {
// //       selectedTemplateIndex = idx;
// //       appendMessage(`👍 Selected Template ${idx + 1}`, "bot");
// //     };

// //     templateList.appendChild(card);
// //   });
// // }

// // /* -----------------------------------------------------
// //    GENERATE MORE SURVEYS
// // ----------------------------------------------------- */
// // generateMoreBtn.addEventListener("click", () => {
// //   if (!storedTemplates.length) {
// //     appendMessage("⚠️ Generate templates first.", "bot");
// //     return;
// //   }

// //   if (document.getElementById("moreFocusInput")) return;

// //   appendMessage("🧾 Which focus area do you want more templates for?", "bot");

// //   const box = document.createElement("div");
// //   box.className = "msg input-inline bot";
// //   box.innerHTML = `<input id="moreFocusInput" type="text" placeholder="Type a focus area…">`;
// //   chatEl.appendChild(box);

// //   const inp = document.getElementById("moreFocusInput");
// //   inp.focus();
// //   inp.addEventListener("keydown", async (e) => {
// //     if (e.key === "Enter" && inp.value.trim()) {
// //       const area = inp.value.trim();
// //       appendMessage(area, "user");
// //       box.remove();

// //       appendMessage(`✨ Generating more templates for: ${area}`, "bot");

// //       const res = await apiPost("/generate_more_surveys", {
// //         focus_area: area,
// //         survey_type: currentSurveyType,
// //       });

// //       if (res.templates?.length) {
// //         const extra = res.templates.map(normalizeTemplate);
// //         storedTemplates = storedTemplates.concat(extra);
// //         renderTemplates();
// //         previewSubtitle.textContent = `${storedTemplates.length} templates`;
// //         appendMessage("✅ Added new templates.", "bot");
// //       } else {
// //         appendMessage("⚠️ No new templates returned.", "bot");
// //       }
// //     }
// //   });
// // });

// // /* -----------------------------------------------------
// //    CUSTOMIZE TEMPLATE (one-shot)
// // ----------------------------------------------------- */
// // customizeBtn.addEventListener("click", async () => {
// //   if (selectedTemplateIndex === null) {
// //     appendMessage("⚠️ Select a template first.", "bot");
// //     return;
// //   }

// //   appendMessage("🛠 How would you like to customize this? (Add / Remove / No Changes)", "bot");

// //   const box = document.createElement("div");
// //   box.className = "msg options-list bot";

// //   const opts = document.createElement("div");
// //   opts.className = "options";

// //   ["Add", "Remove", "No Changes"].forEach((label) => {
// //     const b = document.createElement("button");
// //     b.className = "chip";
// //     b.textContent = label;
// //     b.onclick = () => proceedCustomize(label);
// //     opts.appendChild(b);
// //   });

// //   box.appendChild(opts);
// //   chatEl.appendChild(box);

// //   async function proceedCustomize(choice) {
// //     box.remove();
// //     appendMessage(choice, "user");

// //     const action = choice.toLowerCase();
// //     let focusArea = "";
// //     let complexity = "";
// //     let removeInput = "";

// //     if (action === "add") {
// //       focusArea = await askTextOnce("✏️ Any specific focus area?");
// //       complexity = await askTextOnce("📊 Complexity? (Simple / Moderate / Detailed)");
// //     }

// //     if (action === "remove") {
// //       removeInput = await askTextOnce("✂️ Which questions to remove?");
// //     }

// //     appendMessage("✨ Applying customization…", "bot");

// //     const res = await apiPost("/customize_selected_template", {
// //       templates: storedTemplates,
// //       choice: `Template ${selectedTemplateIndex + 1}`,
// //       action,
// //       focus_area: focusArea,
// //       complexity,
// //       scale_action: "no",
// //       scale_changes: {},
// //       remove_input: removeInput,
// //     });

// //     if (res.selected_template) {
// //       storedTemplates[selectedTemplateIndex] = normalizeTemplate(res.selected_template);
// //       renderTemplates();
// //     }

// //     appendMessage("🎉 Customization complete!", "bot");
// //   }
// // });

// // function askTextOnce(question) {
// //   return new Promise((resolve) => {
// //     appendMessage(question, "bot");

// //     const box = document.createElement("div");
// //     box.className = "msg input-inline bot";
// //     box.innerHTML = `<input type="text" placeholder="Type here…">`;

// //     const inp = box.querySelector("input");
// //     chatEl.appendChild(box);
// //     inp.focus();

// //     inp.addEventListener("keydown", (e) => {
// //       if (e.key === "Enter") {
// //         const val = inp.value.trim();
// //         appendMessage(val || "(skipped)", "user");
// //         box.remove();
// //         resolve(val);
// //       }
// //     });
// //   });
// // }

// // /* -----------------------------------------------------
// //    FINALIZE + DOWNLOAD
// // ----------------------------------------------------- */
// // finalizeBtn.addEventListener("click", async () => {
// //   if (selectedTemplateIndex === null) {
// //     appendMessage("⚠️ Select a template first.", "bot");
// //     return;
// //   }

// //   const tpl = storedTemplates[selectedTemplateIndex];
// //   appendMessage(`📦 Finalizing template: ${tpl.title}`, "bot");

// //   const res = await apiPost("/finalize_template", { final_template: tpl });

// //   if (res.template_id) {
// //     appendMessage(`🎉 Template saved (ID: ${res.template_id})`, "bot");
// //     downloadJsonBtn.disabled = false;
// //   }
// // });

// // downloadJsonBtn.addEventListener("click", () => {
// //   if (selectedTemplateIndex === null) return;

// //   const tpl = storedTemplates[selectedTemplateIndex];
// //   const blob = new Blob([JSON.stringify(tpl, null, 2)], { type: "application/json" });

// //   const a = document.createElement("a");
// //   a.href = URL.createObjectURL(blob);
// //   a.download = `${tpl.title.replace(/\s+/g, "_")}.json`;
// //   a.click();
// // });

// // /* -----------------------------------------------------
// //    QUICK CHIPS / SEND
// // ----------------------------------------------------- */
// // quickEl.addEventListener("click", (e) => {
// //   const chip = e.target.closest(".chip");
// //   if (!chip) return;
// //   startFlow(chip.dataset.value);
// // });

// // sendBtn.addEventListener("click", () => {
// //   const txt = userInput.value.trim();
// //   if (!txt) return;
// //   userInput.value = "";
// //   startFlow(txt);
// // });

// // userInput.addEventListener("keydown", (e) => {
// //   if (e.key === "Enter") sendBtn.click();
// // });

// // /* -----------------------------------------------------
// //    RESTART
// // ----------------------------------------------------- */
// // restartBtn.addEventListener("click", () => location.reload());

// // /* Initial Focus */
// // userInput.focus();
// let questionFlow = [];
// let currentQuestionIndex = 0;
// let collectedAnswers = {};
// let storedTemplates = [];
// let selectedTemplateIndex = null;

// let originalUserInput = "";
// let currentSurveyType = "general";
// let detectedAudience = "";
// let detectedPurpose = "";

// /* -----------------------------------------------------
//    DOM ELEMENTS
// ----------------------------------------------------- */
// const chatEl = document.getElementById("chat");
// const quickEl = document.getElementById("quick");
// const userInput = document.getElementById("userInput");
// const sendBtn = document.getElementById("sendBtn");
// const restartBtn = document.getElementById("restartBtn");

// const templateList = document.getElementById("templateList");
// const previewSubtitle = document.getElementById("previewSubtitle");
// const customizeBtn = document.getElementById("customizeBtn");
// const generateMoreBtn = document.getElementById("generateMoreBtn");
// const finalizeBtn = document.getElementById("finalizeBtn");
// const downloadJsonBtn = document.getElementById("downloadJsonBtn");

// /* -----------------------------------------------------
//    HELPERS
// ----------------------------------------------------- */
// function escapeHtml(str) {
//   return String(str || "")
//     .replace(/&/g, "&amp;")
//     .replace(/</g, "&lt;")
//     .replace(/>/g, "&gt;");
// }

// function appendMessage(msg, type = "bot") {
//   const div = document.createElement("div");
//   div.className = `msg ${type}`;
//   div.innerHTML = msg;
//   chatEl.appendChild(div);
//   chatEl.scrollTop = chatEl.scrollHeight;
// }

// async function apiPost(url, payload) {
//   try {
//     const res = await fetch(url, {
//       method: "POST",
//       headers: { "Content-Type": "application/json" },
//       body: JSON.stringify(payload || {}),
//     });
//     return await res.json();
//   } catch (err) {
//     appendMessage("⚠️ Network or server error.", "bot");
//     return { error: "network" };
//   }
// }

// function clearInlineInputs() {
//   document.querySelectorAll(".input-inline").forEach((x) => x.remove());
//   document.querySelectorAll(".options-list").forEach((x) => x.remove());
// }

// function normalizeTemplate(t) {
//   return {
//     title: t.title || "Untitled Template",
//     purpose: t.purpose || "",
//     questions: (t.questions || []).map((q) => ({
//       question: q.question || q.text || "",
//       scale_type: q.scale_type || "text",
//       options: q.options || []   // ⭐ SUPPORT FOR RADIO OPTIONS
//     })),
//   };
// }

// /* -----------------------------------------------------
//    START FLOW
// ----------------------------------------------------- */
// async function startFlow(text) {
//   originalUserInput = text.trim();
//   collectedAnswers = {};
//   storedTemplates = [];
//   selectedTemplateIndex = null;
//   questionFlow = [];
//   currentQuestionIndex = 0;

//   appendMessage(escapeHtml(originalUserInput), "user");
//   appendMessage("🧠 Understanding your request…", "bot");

//   const resp = await apiPost("/generate_question_flow", {
//     user_input: originalUserInput,
//     survey_type: ""
//   });

//   currentSurveyType = resp.detected_survey_type || "";
//   detectedAudience = resp.detected_audience || "";
//   detectedPurpose = resp.detected_purpose || "";

//   if (resp.skip_questions === true) {
//     appendMessage("✅ All required details detected. Generating templates…", "bot");

//     if (currentSurveyType) collectedAnswers["survey_type"] = currentSurveyType;
//     if (detectedAudience) collectedAnswers["audience"] = detectedAudience;
//     if (detectedPurpose) collectedAnswers["purpose"] = detectedPurpose;

//     return generateSurvey();
//   }

//   questionFlow = (resp.question_flow || []).map((q) => ({
//     id: q.id || "",
//     text: q.q || q.question,
//     options: q.options || [],
//     allow_text: q.allow_text_input || false,
//   }));

//   currentQuestionIndex = 0;
//   appendMessage("📝 I need a few quick details…", "bot");
//   askNextQuestion();
// }

// /* -----------------------------------------------------
//    ASK NEXT QUESTION
// ----------------------------------------------------- */
// function askNextQuestion() {
//   clearInlineInputs();

//   if (currentQuestionIndex >= questionFlow.length) {
//     return generateSurvey();
//   }

//   const q = questionFlow[currentQuestionIndex];
//   appendMessage(`❓ ${escapeHtml(q.text)}`, "bot");

//   if (q.options?.length) {
//     const box = document.createElement("div");
//     box.className = "msg options-list bot";

//     const optDiv = document.createElement("div");
//     optDiv.className = "options";

//     q.options.forEach((op) => {
//       const b = document.createElement("button");
//       b.className = "chip";
//       b.textContent = op;
//       b.onclick = () => handleAnswer(op);
//       optDiv.appendChild(b);
//     });

//     const other = document.createElement("input");
//     other.type = "text";
//     other.placeholder = "Type your answer…";
//     other.className = "input-inline";
//     other.onkeydown = (e) => {
//       if (e.key === "Enter" && other.value.trim()) handleAnswer(other.value.trim());
//     };

//     box.appendChild(optDiv);
//     box.appendChild(other);
//     chatEl.appendChild(box);
//   } else {
//     const box = document.createElement("div");
//     box.className = "msg input-inline bot";
//     box.innerHTML = `<input id="inlineQ" type="text" placeholder="Type your answer…">`;
//     chatEl.appendChild(box);

//     const inp = document.getElementById("inlineQ");
//     inp.focus();
//     inp.onkeydown = (e) => {
//       if (e.key === "Enter" && inp.value.trim()) handleAnswer(inp.value.trim());
//     };
//   }
// }

// /* -----------------------------------------------------
//    HANDLE ANSWER
// ----------------------------------------------------- */
// function handleAnswer(ans) {
//   const q = questionFlow[currentQuestionIndex];
//   const key = q.id || q.text;
//   collectedAnswers[key] = ans;

//   appendMessage(escapeHtml(ans), "user");

//   if ((q.id || "").toLowerCase() === "survey_type") {
//     const low = ans.toLowerCase();
//     if (low.startsWith("nps")) currentSurveyType = "nps";
//     else if (low.startsWith("csat")) currentSurveyType = "csat";
//     else if (low.startsWith("ces")) currentSurveyType = "ces";
//     else currentSurveyType = "general";
//   }

//   currentQuestionIndex++;
//   if (currentQuestionIndex >= questionFlow.length) generateSurvey();
//   else askNextQuestion();
// }

// /* -----------------------------------------------------
//    GENERATE SURVEYS
// ----------------------------------------------------- */
// async function generateSurvey() {
//   appendMessage("✨ Creating survey templates…", "bot");

//   const res = await apiPost("/generate_survey", {
//     user_input: originalUserInput,
//     survey_type: currentSurveyType,
//     answers: collectedAnswers,
//   });

//   if (!res.surveys?.length) {
//     appendMessage("⚠️ Could not generate templates.", "bot");
//     return;
//   }

//   storedTemplates = res.surveys.map(normalizeTemplate);
//   renderTemplates();

//   previewSubtitle.textContent = `${storedTemplates.length} templates`;
//   customizeBtn.disabled = false;
//   generateMoreBtn.disabled = false;
//   finalizeBtn.disabled = false;
// }

// /* -----------------------------------------------------
//    RENDER TEMPLATES (UPDATED WITH RADIO SUPPORT)
// ----------------------------------------------------- */
// function renderTemplates() {
//   templateList.innerHTML = "";

//   storedTemplates.forEach((tpl, idx) => {
//     const card = document.createElement("div");
//     card.className = "template-card";

//     const questionsHtml = tpl.questions
//       .map((q, i) => {
//         let optionsHtml = "";

//         if (q.scale_type === "radio" && Array.isArray(q.options) && q.options.length) {
//           optionsHtml = `
//             <div class="small" style="margin-left:20px; margin-top:2px;">
//               ${q.options.map(op => `<label>🔘 ${escapeHtml(op)}</label><br>`).join("")}
//             </div>
//           `;
//         }

//         return `
//           <div class="question-row">
//             <span>${i + 1}. ${escapeHtml(q.question)}</span>
//             <span class="small">(${escapeHtml(q.scale_type)})</span>
//           </div>
//           ${optionsHtml}
//         `;
//       })
//       .join("");

//     card.innerHTML = `
//       <div style="display:flex;justify-content:space-between;align-items:center;">
//         <div class="template-title">📄 ${escapeHtml(tpl.title)}</div>
//         <button class="chip" data-idx="${idx}">Select</button>
//       </div>

//       <div class="small"><b>Purpose:</b> ${escapeHtml(tpl.purpose)}</div>

//       <div style="margin-top:6px">${questionsHtml}</div>
//     `;

//     card.querySelector("button").onclick = () => {
//       selectedTemplateIndex = idx;
//       appendMessage(`👍 Selected Template ${idx + 1}`, "bot");
//     };

//     templateList.appendChild(card);
//   });
// }

// /* -----------------------------------------------------
//    GENERATE MORE
// ----------------------------------------------------- */
// generateMoreBtn.addEventListener("click", () => {
//   if (!storedTemplates.length) {
//     appendMessage("⚠️ Generate templates first.", "bot");
//     return;
//   }

//   if (document.getElementById("moreFocusInput")) return;

//   appendMessage("🧾 Which focus area do you want more templates for?", "bot");

//   const box = document.createElement("div");
//   box.className = "msg input-inline bot";
//   box.innerHTML = `<input id="moreFocusInput" type="text" placeholder="Type a focus area…">`;
//   chatEl.appendChild(box);

//   const inp = document.getElementById("moreFocusInput");
//   inp.focus();
//   inp.addEventListener("keydown", async (e) => {
//     if (e.key === "Enter" && inp.value.trim()) {
//       const area = inp.value.trim();
//       appendMessage(area, "user");
//       box.remove();

//       appendMessage(`✨ Generating more templates for: ${area}`, "bot");

//       const res = await apiPost("/generate_more_surveys", {
//         focus_area: area,
//         survey_type: currentSurveyType,
//       });

//       if (res.templates?.length) {
//         const extra = res.templates.map(normalizeTemplate);
//         storedTemplates = storedTemplates.concat(extra);
//         renderTemplates();

//         previewSubtitle.textContent = `${storedTemplates.length} templates`;

//         appendMessage("✅ Added new templates.", "bot");
//       } else {
//         appendMessage("⚠️ No new templates returned.", "bot");
//       }
//     }
//   });
// });

// /* -----------------------------------------------------
//    CUSTOMIZE TEMPLATE
// ----------------------------------------------------- */
// customizeBtn.addEventListener("click", async () => {
//   if (selectedTemplateIndex === null) {
//     appendMessage("⚠️ Select a template first.", "bot");
//     return;
//   }

//   appendMessage("🛠 How would you like to customize this? (Add / Remove / No Changes)", "bot");

//   const box = document.createElement("div");
//   box.className = "msg options-list bot";

//   const opts = document.createElement("div");
//   opts.className = "options";

//   ["Add", "Remove", "No Changes"].forEach((label) => {
//     const b = document.createElement("button");
//     b.className = "chip";
//     b.textContent = label;
//     b.onclick = () => proceedCustomize(label);
//     opts.appendChild(b);
//   });

//   box.appendChild(opts);
//   chatEl.appendChild(box);

//   async function proceedCustomize(choice) {
//     box.remove();
//     appendMessage(choice, "user");

//     const action = choice.toLowerCase();
//     let focusArea = "";
//     let complexity = "";
//     let removeInput = "";

//     if (action === "add") {
//       focusArea = await askTextOnce("✏️ Any specific focus area?");
//       complexity = await askTextOnce("📊 Complexity? (Simple / Moderate / Detailed)");
//     }

//     if (action === "remove") {
//       removeInput = await askTextOnce("✂️ Which questions to remove?");
//     }

//     appendMessage("✨ Applying customization…", "bot");

//     const res = await apiPost("/customize_selected_template", {
//       templates: storedTemplates,
//       choice: `Template ${selectedTemplateIndex + 1}`,
//       action,
//       focus_area: focusArea,
//       complexity,
//       scale_action: "no",
//       scale_changes: {},
//       remove_input: removeInput,
//     });

//     if (res.selected_template) {
//       storedTemplates[selectedTemplateIndex] = normalizeTemplate(res.selected_template);
//       renderTemplates();
//     }

//     appendMessage("🎉 Customization complete!", "bot");
//   }
// });

// function askTextOnce(question) {
//   return new Promise((resolve) => {
//     appendMessage(question, "bot");

//     const box = document.createElement("div");
//     box.className = "msg input-inline bot";
//     box.innerHTML = `<input type="text" placeholder="Type here…">`;

//     const inp = box.querySelector("input");
//     chatEl.appendChild(box);
//     inp.focus();

//     inp.addEventListener("keydown", (e) => {
//       if (e.key === "Enter") {
//         const val = inp.value.trim();
//         appendMessage(val || "(skipped)", "user");
//         box.remove();
//         resolve(val);
//       }
//     });
//   });
// }

// /* -----------------------------------------------------
//    FINALIZE & DOWNLOAD
// ----------------------------------------------------- */
// finalizeBtn.addEventListener("click", async () => {
//   if (selectedTemplateIndex === null) {
//     appendMessage("⚠️ Select a template first.", "bot");
//     return;
//   }

//   const tpl = storedTemplates[selectedTemplateIndex];
//   appendMessage(`📦 Finalizing template: ${tpl.title}`, "bot");

//   const res = await apiPost("/finalize_template", { final_template: tpl });

//   if (res.template_id) {
//     appendMessage(`🎉 Template saved (ID: ${res.template_id})`, "bot");
//     downloadJsonBtn.disabled = false;
//   }
// });

// downloadJsonBtn.addEventListener("click", () => {
//   if (selectedTemplateIndex === null) return;

//   const tpl = storedTemplates[selectedTemplateIndex];
//   const blob = new Blob([JSON.stringify(tpl, null, 2)], { type: "application/json" });

//   const a = document.createElement("a");
//   a.href = URL.createObjectURL(blob);
//   a.download = `${tpl.title.replace(/\s+/g, "_")}.json`;
//   a.click();
// });

// /* -----------------------------------------------------
//    QUICK CHIPS
// ----------------------------------------------------- */
// quickEl.addEventListener("click", (e) => {
//   const chip = e.target.closest(".chip");
//   if (!chip) return;
//   startFlow(chip.dataset.value);
// });

// sendBtn.addEventListener("click", () => {
//   const txt = userInput.value.trim();
//   if (!txt) return;
//   userInput.value = "";
//   startFlow(txt);
// });

// userInput.addEventListener("keydown", (e) => {
//   if (e.key === "Enter") sendBtn.click();
// });

// /* -----------------------------------------------------
//    RESTART
// ----------------------------------------------------- */
// restartBtn.addEventListener("click", () => location.reload());

// /* Initial Focus */
// userInput.focus();
// ===============================
// Global State
// ===============================
/* ================= GLOBAL STATE ================ */

// ===============================
// GLOBAL STATE
// ===============================
///// code running here /////
// let questionFlow = [];
// let currentQuestionIndex = 0;
// let collectedAnswers = {};
// let storedTemplates = [];
// let selectedTemplateIndex = null;

// let originalUserInput = "";

// // AI-detected / user-confirmed parameters
// let surveyContext = {
//   survey_type: null,   // "nps" | "csat" | "ces" | "general" | null
//   audience: null,      // dynamic string or null
//   purpose: null,       // dynamic string or null
//   touchpoint: null     // dynamic string or null
// };

// // Convenience for template generation
// let currentSurveyType = "general";

// // ===============================
// // DOM ELEMENTS
// // ===============================
// const chatEl = document.getElementById("chat");
// const quickEl = document.getElementById("quick");
// const userInput = document.getElementById("userInput");
// const sendBtn = document.getElementById("sendBtn");
// const restartBtn = document.getElementById("restartBtn");

// const templateList = document.getElementById("templateList");
// const previewSubtitle = document.getElementById("previewSubtitle");
// const customizeBtn = document.getElementById("customizeBtn");
// const generateMoreBtn = document.getElementById("generateMoreBtn");
// const finalizeBtn = document.getElementById("finalizeBtn");
// const downloadJsonBtn = document.getElementById("downloadJsonBtn");

// // ===============================
// // HELPERS
// // ===============================
// function escapeHtml(str) {
//   return String(str || "")
//     .replace(/&/g, "&amp;")
//     .replace(/</g, "&lt;")
//     .replace(/>/g, "&gt;");
// }

// function appendMessage(msg, type = "bot") {
//   const div = document.createElement("div");
//   div.className = `msg ${type}`;
//   div.innerHTML = msg;
//   chatEl.appendChild(div);
//   chatEl.scrollTop = chatEl.scrollHeight;
// }

// async function apiPost(url, payload) {
//   try {
//     const res = await fetch(url, {
//       method: "POST",
//       headers: { "Content-Type": "application/json" },
//       body: JSON.stringify(payload || {}),
//     });
//     return await res.json();
//   } catch (err) {
//     appendMessage("⚠️ Network or server error.", "bot");
//     console.error("API Error:", err);
//     return { error: "network" };
//   }
// }

// function clearInlineInputs() {
//   document.querySelectorAll(".input-inline").forEach((x) => x.remove());
//   document.querySelectorAll(".options-list").forEach((x) => x.remove());
// }

// function normalizeTemplate(t) {
//   return {
//     title: t.title || "Untitled Template",
//     purpose: t.purpose || "",
//     duration: t.duration || "",
//     questions: (t.questions || []).map((q) => ({
//       question: q.question || q.text || "",
//       scale_type: q.scale_type || "text",
//       options: Array.isArray(q.options) ? q.options : []
//     })),
//   };
// }

// // Map survey type answer text → canonical value
// function interpretSurveyTypeAnswer(ans) {
//   const low = ans.toLowerCase();
//   if (low.includes("nps") || low.includes("net promoter")) return "nps";
//   if (low.includes("csat") || low.includes("satisfaction")) return "csat";
//   if (low.includes("ces") || low.includes("effort") || low.includes("easy")) return "ces";
//   if (low.includes("general") || low.includes("not sure")) return "general";
//   // If nothing matches, keep it null so backend doesn't assume wrongly
//   return null;
// }

// // ===============================
// // START FLOW
// // ===============================
// async function startFlow(text) {
//   originalUserInput = text.trim();
//   if (!originalUserInput) return;

//   // Reset state for new conversation
//   collectedAnswers = {};
//   storedTemplates = [];
//   selectedTemplateIndex = null;
//   questionFlow = [];
//   currentQuestionIndex = 0;

//   surveyContext = {
//     survey_type: null,
//     audience: null,
//     purpose: null,
//     touchpoint: null
//   };
//   currentSurveyType = "general";

//   templateList.innerHTML = `
//     <div class="empty-state">
//       <div class="empty-icon">✨</div>
//       <div class="empty-title">No templates generated yet</div>
//       <div class="empty-text">Describe your survey idea on the left to see ready-made templates here.</div>
//     </div>
//   `;
//   previewSubtitle.textContent = "No templates yet";
//   customizeBtn.disabled = true;
//   generateMoreBtn.disabled = true;
//   finalizeBtn.disabled = true;
//   downloadJsonBtn.disabled = true;

//   appendMessage(escapeHtml(originalUserInput), "user");
//   appendMessage("🧠 Understanding your request…", "bot");

//   // Call new AI-based generate_question_flow
//   const resp = await apiPost("/generate_question_flow", {
//     user_input: originalUserInput,
//     // Let backend + AI fully detect; we don't force survey_type here
//     survey_type: "",
//   });

//   if (resp.error) {
//     appendMessage("⚠️ Something went wrong. Please try again.", "bot");
//     return;
//   }

//   // Store AI-detected values (may be null)
//   surveyContext.survey_type = resp.detected_survey_type || null;
//   surveyContext.audience     = resp.detected_audience     || null;
//   surveyContext.purpose      = resp.detected_purpose      || null;
//   surveyContext.touchpoint   = resp.detected_touchpoint   || null;

//   currentSurveyType = surveyContext.survey_type || "general";

//   // If everything is known, backend sets skip_questions = true
//   if (resp.skip_questions === true) {
//     appendMessage("✅ I understood all required details. Generating templates…", "bot");

//     if (surveyContext.survey_type) collectedAnswers["survey_type"] = surveyContext.survey_type;
//     if (surveyContext.audience)     collectedAnswers["audience"]   = surveyContext.audience;
//     if (surveyContext.purpose)      collectedAnswers["purpose"]    = surveyContext.purpose;
//     if (surveyContext.touchpoint)   collectedAnswers["touchpoint"] = surveyContext.touchpoint;

//     return generateSurvey();
//   }

//   // Otherwise, follow-up questions from backend
//   questionFlow = (resp.question_flow || []).map((q) => ({
//     id: q.id || "",
//     text: q.q || q.question,
//     options: q.options || [],
//     allow_text: q.allow_text_input || false,
//   }));

//   if (!questionFlow.length) {
//     // Safety: if no questions but skip_questions was false
//     appendMessage("❓ I could not determine all details, but I'll try generating templates anyway.", "bot");
//     return generateSurvey();
//   }

//   appendMessage("📝 I need a few quick details to complete your survey setup…", "bot");
//   askNextQuestion();
// }

// // ===============================
// // ASK NEXT QUESTION
// // ===============================
// function askNextQuestion() {
//   clearInlineInputs();

//   if (currentQuestionIndex >= questionFlow.length) {
//     return generateSurvey();
//   }

//   const q = questionFlow[currentQuestionIndex];
//   appendMessage(`❓ ${escapeHtml(q.text)}`, "bot");

//   // Options present → show chips + optional free text
//   if (Array.isArray(q.options) && q.options.length) {
//     const box = document.createElement("div");
//     box.className = "msg options-list bot";

//     const optDiv = document.createElement("div");
//     optDiv.className = "options";

//     q.options.forEach((op) => {
//       const b = document.createElement("button");
//       b.className = "chip";
//       b.textContent = op;
//       b.onclick = () => handleAnswer(op);
//       optDiv.appendChild(b);
//     });

//     const other = document.createElement("input");
//     other.type = "text";
//     other.placeholder = "Type your answer…";
//     other.className = "input-inline";
//     other.onkeydown = (e) => {
//       if (e.key === "Enter" && other.value.trim()) {
//         handleAnswer(other.value.trim());
//       }
//     };

//     box.appendChild(optDiv);
//     box.appendChild(other);
//     chatEl.appendChild(box);
//     chatEl.scrollTop = chatEl.scrollHeight;
//   } else {
//     // Free text only
//     const box = document.createElement("div");
//     box.className = "msg input-inline bot";
//     box.innerHTML = `<input id="inlineQ" type="text" placeholder="Type your answer…">`;
//     chatEl.appendChild(box);
//     chatEl.scrollTop = chatEl.scrollHeight;

//     const inp = document.getElementById("inlineQ");
//     inp.focus();
//     inp.onkeydown = (e) => {
//       if (e.key === "Enter" && inp.value.trim()) {
//         handleAnswer(inp.value.trim());
//       }
//     };
//   }
// }

// // ===============================
// // HANDLE ANSWER
// // ===============================
// function handleAnswer(ans) {
//   const q = questionFlow[currentQuestionIndex];
//   const key = q.id || q.text || `q${currentQuestionIndex + 1}`;

//   appendMessage(escapeHtml(ans), "user");

//   // Save raw answer
//   collectedAnswers[key] = ans;

//   // If this is one of the 4 core parameters, map it to surveyContext
//   const idLower = (q.id || "").toLowerCase();

//   if (idLower === "survey_type") {
//     const mapped = interpretSurveyTypeAnswer(ans);
//     surveyContext.survey_type = mapped;
//     currentSurveyType = mapped || "general";
//     collectedAnswers["survey_type"] = surveyContext.survey_type;
//   }

//   if (idLower === "audience") {
//     surveyContext.audience = ans;
//     collectedAnswers["audience"] = ans;
//   }

//   if (idLower === "purpose") {
//     surveyContext.purpose = ans;
//     collectedAnswers["purpose"] = ans;
//   }

//   if (idLower === "touchpoint") {
//     surveyContext.touchpoint = ans;
//     collectedAnswers["touchpoint"] = ans;
//   }

//   currentQuestionIndex++;

//   if (currentQuestionIndex >= questionFlow.length) {
//     generateSurvey();
//   } else {
//     askNextQuestion();
//   }
// }

// // ===============================
// // GENERATE SURVEYS
// // ===============================
// async function generateSurvey() {
//   appendMessage("✨ Creating survey templates…", "bot");

//   // Make sure collectedAnswers has final context
//   if (surveyContext.survey_type) collectedAnswers["survey_type"] = surveyContext.survey_type;
//   if (surveyContext.audience)    collectedAnswers["audience"]   = surveyContext.audience;
//   if (surveyContext.purpose)     collectedAnswers["purpose"]    = surveyContext.purpose;
//   if (surveyContext.touchpoint)  collectedAnswers["touchpoint"] = surveyContext.touchpoint;

//   const res = await apiPost("/generate_survey", {
//     user_input: originalUserInput,
//     survey_type: surveyContext.survey_type || "general",
//     answers: collectedAnswers,   // backend ignores, but kept for future use
//   });

//   if (!res.surveys || !res.surveys.length) {
//     appendMessage("⚠️ Could not generate templates. Try rephrasing your request.", "bot");
//     return;
//   }

//   storedTemplates = res.surveys.map(normalizeTemplate);
//   renderTemplates();

//   previewSubtitle.textContent = `${storedTemplates.length} templates`;
//   customizeBtn.disabled = false;
//   generateMoreBtn.disabled = false;
//   finalizeBtn.disabled = false;
//   // downloadJson stays disabled until finalize
// }

// // ===============================
// // RENDER TEMPLATES (with radio options)
// // ===============================
// function renderTemplates() {
//   templateList.innerHTML = "";

//   storedTemplates.forEach((tpl, idx) => {
//     const card = document.createElement("div");
//     card.className = "template-card";

//     const questionsHtml = tpl.questions
//       .map((q, i) => {
//         let optionsHtml = "";

//         if (q.scale_type === "radio" && Array.isArray(q.options) && q.options.length) {
//           optionsHtml = `
//             <div class="small" style="margin-left:20px; margin-top:2px;">
//               ${q.options.map(op => `<label>🔘 ${escapeHtml(op)}</label><br>`).join("")}
//             </div>
//           `;
//         }

//         return `
//           <div class="question-row">
//             <span>${i + 1}. ${escapeHtml(q.question)}</span>
//             <span class="small">(${escapeHtml(q.scale_type)})</span>
//           </div>
//           ${optionsHtml}
//         `;
//       })
//       .join("");

//     card.innerHTML = `
//       <div style="display:flex;justify-content:space-between;align-items:center;">
//         <div class="template-title">📄 ${escapeHtml(tpl.title)}</div>
//         <button class="chip" data-idx="${idx}">Select</button>
//       </div>

//       <div class="small"><b>Purpose:</b> ${escapeHtml(tpl.purpose)}</div>
//       ${
//         tpl.duration
//           ? `<div class="small"><b>Duration:</b> ${escapeHtml(tpl.duration)}</div>`
//           : ""
//       }

//       <div style="margin-top:6px">${questionsHtml}</div>
//     `;

//     card.querySelector("button").onclick = () => {
//       selectedTemplateIndex = idx;
//       appendMessage(`👍 Selected Template ${idx + 1}`, "bot");
//     };

//     templateList.appendChild(card);
//   });
// }

// // ===============================
// // GENERATE MORE TEMPLATES
// // ===============================
// generateMoreBtn.addEventListener("click", () => {
//   if (!storedTemplates.length) {
//     appendMessage("⚠️ Generate templates first.", "bot");
//     return;
//   }

//   if (document.getElementById("moreFocusInput")) return;

//   appendMessage("🧾 Which focus area do you want more templates for?", "bot");

//   const box = document.createElement("div");
//   box.className = "msg input-inline bot";
//   box.innerHTML = `<input id="moreFocusInput" type="text" placeholder="Type a focus area…">`;
//   chatEl.appendChild(box);

//   const inp = document.getElementById("moreFocusInput");
//   inp.focus();
//   inp.addEventListener("keydown", async (e) => {
//     if (e.key === "Enter" && inp.value.trim()) {
//       const area = inp.value.trim();
//       appendMessage(area, "user");
//       box.remove();

//       appendMessage(`✨ Generating more templates for: ${area}`, "bot");

//       const res = await apiPost("/generate_more_surveys", {
//         focus_area: area,
//         survey_type: surveyContext.survey_type || "general",
//       });

//       if (res.templates && res.templates.length) {
//         const extra = res.templates.map(normalizeTemplate);
//         storedTemplates = storedTemplates.concat(extra);
//         renderTemplates();

//         previewSubtitle.textContent = `${storedTemplates.length} templates`;

//         appendMessage("✅ Added new templates.", "bot");
//       } else {
//         appendMessage("⚠️ No new templates returned.", "bot");
//       }
//     }
//   });
// });

// // ===============================
// // CUSTOMIZE TEMPLATE
// // ===============================
// customizeBtn.addEventListener("click", async () => {
//   if (selectedTemplateIndex === null) {
//     appendMessage("⚠️ Select a template first.", "bot");
//     return;
//   }

//   appendMessage("🛠 How would you like to customize this? (Add / Remove / No Changes)", "bot");

//   const box = document.createElement("div");
//   box.className = "msg options-list bot";

//   const opts = document.createElement("div");
//   opts.className = "options";

//   ["Add", "Remove", "No Changes"].forEach((label) => {
//     const b = document.createElement("button");
//     b.className = "chip";
//     b.textContent = label;
//     b.onclick = () => proceedCustomize(label);
//     opts.appendChild(b);
//   });

//   box.appendChild(opts);
//   chatEl.appendChild(box);

//   async function proceedCustomize(choice) {
//     box.remove();
//     appendMessage(choice, "user");

//     const action = choice.toLowerCase();
//     let focusArea = "";
//     let complexity = "";
//     let removeInput = "";

//     if (action === "add") {
//       focusArea = await askTextOnce("✏️ Any specific focus area?");
//       complexity = await askTextOnce("📊 Complexity? (Simple / Moderate / Detailed)");
//     }

//     if (action === "remove") {
//       removeInput = await askTextOnce("✂️ Which questions to remove? (e.g., Q2 or a keyword)");
//     }

//     appendMessage("✨ Applying customization…", "bot");

//     const res = await apiPost("/customize_selected_template", {
//       templates: storedTemplates,
//       choice: `Template ${selectedTemplateIndex + 1}`,
//       action,
//       focus_area: focusArea,
//       complexity,
//       scale_action: "no",
//       scale_changes: {},
//       remove_input: removeInput,
//     });

//     if (res.selected_template) {
//       storedTemplates[selectedTemplateIndex] = normalizeTemplate(res.selected_template);
//       renderTemplates();
//     }

//     appendMessage("🎉 Customization complete!", "bot");
//   }
// });

// function askTextOnce(question) {
//   return new Promise((resolve) => {
//     appendMessage(question, "bot");

//     const box = document.createElement("div");
//     box.className = "msg input-inline bot";
//     box.innerHTML = `<input type="text" placeholder="Type here…">`;

//     const inp = box.querySelector("input");
//     chatEl.appendChild(box);
//     inp.focus();

//     inp.addEventListener("keydown", (e) => {
//       if (e.key === "Enter") {
//         const val = inp.value.trim();
//         appendMessage(val || "(skipped)", "user");
//         box.remove();
//         resolve(val);
//       }
//     });
//   });
// }

// // ===============================
// // FINALIZE & DOWNLOAD
// // ===============================
// finalizeBtn.addEventListener("click", async () => {
//   if (selectedTemplateIndex === null) {
//     appendMessage("⚠️ Select a template first.", "bot");
//     return;
//   }

//   const tpl = storedTemplates[selectedTemplateIndex];
//   appendMessage(`📦 Finalizing template: ${tpl.title}`, "bot");

//   const res = await apiPost("/finalize_template", { final_template: tpl });

//   if (res.template_id) {
//     appendMessage(`🎉 Template saved (ID: ${res.template_id})`, "bot");
//     downloadJsonBtn.disabled = false;
//   }
// });

// downloadJsonBtn.addEventListener("click", () => {
//   if (selectedTemplateIndex === null) return;

//   const tpl = storedTemplates[selectedTemplateIndex];
//   const blob = new Blob([JSON.stringify(tpl, null, 2)], { type: "application/json" });

//   const a = document.createElement("a");
//   a.href = URL.createObjectURL(blob);
//   a.download = `${tpl.title.replace(/\s+/g, "_")}.json`;
//   a.click();
// });

// // ===============================
// // QUICK CHIPS & SEND
// // ===============================
// quickEl.addEventListener("click", (e) => {
//   const chip = e.target.closest(".chip");
//   if (!chip) return;
//   startFlow(chip.dataset.value);
// });

// sendBtn.addEventListener("click", () => {
//   const txt = userInput.value.trim();
//   if (!txt) return;
//   userInput.value = "";
//   startFlow(txt);
// });

// userInput.addEventListener("keydown", (e) => {
//   if (e.key === "Enter") sendBtn.click();
// });

let questionFlow = [];
let currentQuestionIndex = 0;
let collectedAnswers = {};
let storedTemplates = [];
let selectedTemplateIndex = null;

let originalUserInput = "";

// AI-detected / user-confirmed parameters
let surveyContext = {
  survey_type: null,   // "nps" | "csat" | "ces" | "general" | null
  audience: null,      // dynamic string or null
  purpose: null,       // dynamic string or null
  touchpoint: null     // dynamic string or null
};

// Convenience for template generation
let currentSurveyType = "general";

// ===============================
// DOM ELEMENTS
// ===============================
const chatEl = document.getElementById("chat");
const quickEl = document.getElementById("quick");
const userInput = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");
const restartBtn = document.getElementById("restartBtn");

const templateList = document.getElementById("templateList");
const previewSubtitle = document.getElementById("previewSubtitle");
const customizeBtn = document.getElementById("customizeBtn");
const generateMoreBtn = document.getElementById("generateMoreBtn");
const finalizeBtn = document.getElementById("finalizeBtn");
const downloadJsonBtn = document.getElementById("downloadJsonBtn");

// ===============================
// HELPERS
// ===============================
function escapeHtml(str) {
  return String(str || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function appendMessage(msg, type = "bot") {
  const div = document.createElement("div");
  div.className = `msg ${type}`;
  div.innerHTML = msg;
  chatEl.appendChild(div);
  chatEl.scrollTop = chatEl.scrollHeight;
}

async function apiPost(url, payload) {
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload || {}),
    });
    const data = await res.json();
    if (!res.ok && data && !data.error) {
      data.error = `HTTP ${res.status}`;
    }
    return data;
  } catch (err) {
    appendMessage("⚠️ Network or server error.", "bot");
    console.error("API Error:", err);
    return { error: "network", message: "⚠️ Network or server error. Please check your connection." };
  }
}

function clearInlineInputs() {
  document.querySelectorAll(".input-inline").forEach((x) => x.remove());
  document.querySelectorAll(".options-list").forEach((x) => x.remove());
}

// 🔹 scale_type ko clean label me convert karo (for UI tag)
function formatScaleTypeLabel(raw) {
  const t = String(raw || "").toLowerCase().trim();

  if (!t) return "text";

  // typical NPS: 0–10 scale
  if (t.includes("nps") || t.includes("0-10") || t.includes("0–10") || t.includes("net promoter")) {
    return "nps";
  }

  // CSAT often rating 1–5 / 1–7
  if (t.includes("csat") || t.includes("satisfaction")) {
    return "csat";
  }

  // CES / effort
  if (t.includes("ces") || t.includes("effort") || t.includes("easy")) {
    return "ces";
  }

  // radio / mcq types
  if (t === "radio" || t.includes("radio")) {
    return "radio";
  }

  if (t.includes("mcq") || t.includes("multiple")) {
    return "mcq";
  }

  // simple open text
  if (t === "text" || t.includes("open")) {
    return "text";
  }

  // fallback
  return t;
}

function normalizeTemplate(t) {
  return {
    title: t.title || "Untitled Template",
    purpose: t.purpose || "",
    // 🔹 default duration like screenshot
    duration: t.duration || "2–2.5 mins",
    questions: (t.questions || []).map((q) => ({
      question: q.question || q.text || "",
      scale_type: formatScaleTypeLabel(q.scale_type || "text"),
      options: Array.isArray(q.options) ? q.options : []
    })),
  };
}

// Map survey type answer text → canonical value
function interpretSurveyTypeAnswer(ans) {
  const low = ans.toLowerCase();
  if (low.includes("nps") || low.includes("net promoter")) return "nps";
  if (low.includes("csat") || low.includes("satisfaction")) return "csat";
  if (low.includes("ces") || low.includes("effort") || low.includes("easy")) return "ces";
  if (low.includes("general") || low.includes("not sure")) return "general";
  // If nothing matches, keep it null so backend doesn't assume wrongly
  return null;
}

// ===============================
// START FLOW
// ===============================
let isGenerating = false;

async function startFlow(text) {
  originalUserInput = text.trim();
  if (!originalUserInput) return;

  if (isGenerating) {
    appendMessage("⏳ Please wait, we are processing your request...", "bot");
    return;
  }

  isGenerating = true;
  if (sendBtn) sendBtn.disabled = true;

  try {
    // Reset state for new conversation
    collectedAnswers = {};
    storedTemplates = [];
    selectedTemplateIndex = null;
    questionFlow = [];
    currentQuestionIndex = 0;

    surveyContext = {
      survey_type: null,
      audience: null,
      purpose: null,
      touchpoint: null
    };
    currentSurveyType = "general";

    templateList.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">✨</div>
        <div class="empty-title">No templates generated yet</div>
        <div class="empty-text">Describe your survey idea on the left to see ready-made templates here.</div>
      </div>
    `;
    previewSubtitle.textContent = "No templates yet";
    customizeBtn.disabled = true;
    generateMoreBtn.disabled = true;
    finalizeBtn.disabled = true;
    downloadJsonBtn.disabled = true;

    appendMessage(escapeHtml(originalUserInput), "user");
    appendMessage("🧠 Understanding your request…", "bot");

    // Call new AI-based generate_question_flow
    const resp = await apiPost("/generate_question_flow", {
      user_input: originalUserInput,
      // Let backend + AI fully detect; we don't force survey_type here
      survey_type: "",
    });

    if (resp.error) {
      appendMessage(resp.message || resp.invalid_message || "⚠️ Something went wrong. Please try again.", "bot");
      return;
    }

    // Store AI-detected values (may be null)
    surveyContext.survey_type = resp.detected_survey_type || null;
    surveyContext.audience = resp.detected_audience || null;
    surveyContext.purpose = resp.detected_purpose || null;
    surveyContext.touchpoint = resp.detected_touchpoint || null;

    currentSurveyType = surveyContext.survey_type || "general";

    if (surveyContext.survey_type) collectedAnswers["survey_type"] = surveyContext.survey_type;
    if (surveyContext.audience) collectedAnswers["audience"] = surveyContext.audience;
    if (surveyContext.purpose) collectedAnswers["purpose"] = surveyContext.purpose;
    if (surveyContext.touchpoint) collectedAnswers["touchpoint"] = surveyContext.touchpoint;

    // All parameters detected → Show summary and generate templates immediately
    if (resp.all_detected === true || resp.skip_questions === true) {
      const summaryMsg = `🧠 <b>I understood your request!</b><br>${resp.summary_text || ""}`;
      appendMessage(summaryMsg, "bot");
      return generateSurvey();
    }

    // Handle Greeting or Invalid messages
    if (resp.is_greeting && resp.greeting_message) {
      appendMessage(resp.greeting_message, "bot");
    } else if (resp.is_invalid && resp.invalid_message) {
      appendMessage(resp.invalid_message, "bot");
    }

    // Otherwise, follow-up questions for missing fields
    questionFlow = (resp.question_flow || []).map((q) => ({
      id: q.id || "",
      text: q.q || q.question,
      options: q.options || [],
      allow_text: q.allow_text_input || false,
    }));

    if (!questionFlow.length) {
      appendMessage("❓ I could not determine all details, but I'll try generating templates anyway.", "bot");
      return generateSurvey();
    }

    const prefix = resp.summary_text ? `📝 <b>Detected:</b> ${resp.summary_text}<br>Please answer the missing details below:` : "📝 Please answer the quick details below:";
    appendMessage(prefix, "bot");
    askNextQuestion();
  } finally {
    isGenerating = false;
    if (sendBtn) sendBtn.disabled = false;
  }
}

// ===============================
// SETUP FULL QUESTION REVIEW
// ===============================
function setupFullQuestionReview(resp) {
  if (resp && Array.isArray(resp.question_flow) && resp.question_flow.length > 0) {
    questionFlow = resp.question_flow.map((q) => ({
      id: q.id || "",
      text: q.q || q.question,
      options: q.options || [],
      allow_text: q.allow_text_input || false,
    }));
  } else {
    questionFlow = [
      {
        id: "survey_type",
        text: "Which type of survey would you like to create?",
        options: ["NPS", "CSAT", "CES", "General / Not sure"],
      },
      {
        id: "audience",
        text: "Who is your target audience for this survey?",
        options: ["Customers", "Employees", "B2B", "Clients", "Users", "Learners", "Vendors", "Parents", "General users"],
      },
      {
        id: "purpose",
        text: "What is the main topic or purpose of this survey?",
        allow_text: true,
      },
      {
        id: "touchpoint",
        text: "Which touchpoint or channel is this survey primarily about?",
        options: ["Website", "Mobile app", "Store visit / Branch visit", "Call center / Phone support", "Email support", "WhatsApp / Chat support", "Delivery experience", "Onboarding / Signup flow", "Billing & payments", "Other"],
        allow_text: true,
      }
    ];
  }
  currentQuestionIndex = 0;
  appendMessage("📝 Reviewing full survey setup questions…", "bot");
  askNextQuestion();
}

// ===============================
// ASK NEXT QUESTION
// ===============================
function askNextQuestion() {
  clearInlineInputs();

  if (currentQuestionIndex >= questionFlow.length) {
    return generateSurvey();
  }

  const q = questionFlow[currentQuestionIndex];
  appendMessage(`❓ ${escapeHtml(q.text)}`, "bot");

  // Options present → show chips + optional free text
  if (Array.isArray(q.options) && q.options.length) {
    const box = document.createElement("div");
    box.className = "msg options-list bot";

    const optDiv = document.createElement("div");
    optDiv.className = "options";

    q.options.forEach((op) => {
      const b = document.createElement("button");
      b.className = "chip";
      b.textContent = op;
      b.onclick = () => handleAnswer(op);
      optDiv.appendChild(b);
    });

    const other = document.createElement("input");
    other.type = "text";
    other.placeholder = "Type your answer…";
    other.className = "input-inline";
    other.id = "inlineQ";
    other.onkeydown = (e) => {
      if (e.key === "Enter" && other.value.trim()) {
        handleAnswer(other.value.trim());
      }
    };

    box.appendChild(optDiv);
    box.appendChild(other);
    chatEl.appendChild(box);
    chatEl.scrollTop = chatEl.scrollHeight;
  } else {
    // Free text only
    const box = document.createElement("div");
    box.className = "msg input-inline bot";
    box.innerHTML = `<input id="inlineQ" type="text" placeholder="Type your answer…">`;
    chatEl.appendChild(box);
    chatEl.scrollTop = chatEl.scrollHeight;

    const inp = document.getElementById("inlineQ");
    inp.focus();
    inp.onkeydown = (e) => {
      if (e.key === "Enter" && inp.value.trim()) {
        handleAnswer(inp.value.trim());
      }
    };
  }
}

function repromptCurrentQuestion() {
  clearInlineInputs();
  const q = questionFlow[currentQuestionIndex];
  if (!q) return;

  // Re-display question title before options for clarity
  appendMessage(`❓ ${escapeHtml(q.text)}`, "bot");

  if (Array.isArray(q.options) && q.options.length) {
    const box = document.createElement("div");
    box.className = "msg options-list bot";

    const optDiv = document.createElement("div");
    optDiv.className = "options";

    q.options.forEach((op) => {
      const b = document.createElement("button");
      b.className = "chip";
      b.textContent = op;
      b.onclick = () => handleAnswer(op);
      optDiv.appendChild(b);
    });

    const other = document.createElement("input");
    other.type = "text";
    other.placeholder = "Type your answer…";
    other.className = "input-inline";
    other.id = "inlineQ";
    other.onkeydown = (e) => {
      if (e.key === "Enter" && other.value.trim()) {
        handleAnswer(other.value.trim());
      }
    };

    box.appendChild(optDiv);
    box.appendChild(other);
    chatEl.appendChild(box);
    chatEl.scrollTop = chatEl.scrollHeight;
  } else {
    const box = document.createElement("div");
    box.className = "msg input-inline bot";
    box.innerHTML = `<input id="inlineQ" type="text" placeholder="Type your answer…">`;
    chatEl.appendChild(box);
    chatEl.scrollTop = chatEl.scrollHeight;

    const inp = document.getElementById("inlineQ");
    if (inp) {
      inp.focus();
      inp.onkeydown = (e) => {
        if (e.key === "Enter" && inp.value.trim()) {
          handleAnswer(inp.value.trim());
        }
      };
    }
  }
}

// ===============================
// HANDLE ANSWER (Backend Validation)
// ===============================
async function handleAnswer(ans) {
  const val = (ans || "").trim();
  if (!val) return;

  const q = questionFlow[currentQuestionIndex];
  if (!q) return;

  const key = q.id || q.text || `q${currentQuestionIndex + 1}`;
  const idLower = (q.id || "").toLowerCase();

  // Validate answer using backend API
  const validation = await apiPost("/validate_input", {
    text: val,
    question_id: idLower
  });

  if (validation.is_valid === false) {
    appendMessage(escapeHtml(val), "user");
    appendMessage(validation.message || "⚠️ Invalid input.", "bot");
    repromptCurrentQuestion();
    return;
  }

  // Answer is valid!
  clearInlineInputs();
  appendMessage(escapeHtml(val), "user");
  collectedAnswers[key] = val;

  if (idLower === "survey_type") {
    const mapped = interpretSurveyTypeAnswer(val);
    surveyContext.survey_type = mapped || "general";
    currentSurveyType = surveyContext.survey_type;
    collectedAnswers["survey_type"] = surveyContext.survey_type;
  } else if (idLower === "audience") {
    surveyContext.audience = val;
    collectedAnswers["audience"] = val;
  } else if (idLower === "purpose") {
    surveyContext.purpose = val;
    collectedAnswers["purpose"] = val;
  } else if (idLower === "touchpoint") {
    surveyContext.touchpoint = val;
    collectedAnswers["touchpoint"] = val;
  }

  currentQuestionIndex++;

  if (currentQuestionIndex >= questionFlow.length) {
    generateSurvey();
  } else {
    askNextQuestion();
  }
}

// ===============================
// GENERATE SURVEYS
// ===============================
async function generateSurvey() {
  clearInlineInputs();
  if (isGenerating) return;
  isGenerating = true;
  if (sendBtn) sendBtn.disabled = true;

  try {
    appendMessage("✨ Creating survey templates…", "bot");

    // Make sure collectedAnswers has final context
    if (surveyContext.survey_type) collectedAnswers["survey_type"] = surveyContext.survey_type;
    if (surveyContext.audience) collectedAnswers["audience"] = surveyContext.audience;
    if (surveyContext.purpose) collectedAnswers["purpose"] = surveyContext.purpose;
    if (surveyContext.touchpoint) collectedAnswers["touchpoint"] = surveyContext.touchpoint;

    const res = await apiPost("/generate_survey", {
      user_input: originalUserInput,
      survey_type: surveyContext.survey_type || "general",
      target_audience: surveyContext.audience || "",
      survey_purpose: surveyContext.purpose || "",
      touchpoint: surveyContext.touchpoint || "",
      answers: collectedAnswers
    });

    const tplsList = res.surveys || res.templates || [];

    if ((res.error || res.message) && !tplsList.length) {
      appendMessage(res.message || res.error || "⚠️ Could not generate templates. Try rephrasing your request.", "bot");
      return;
    }

    if (!tplsList.length) {
      appendMessage("⚠️ Could not generate templates. Try rephrasing your request.", "bot");
      return;
    }

    storedTemplates = tplsList.map(normalizeTemplate);
    renderTemplates();

    previewSubtitle.textContent = `${storedTemplates.length} templates`;
    customizeBtn.disabled = false;
    generateMoreBtn.disabled = false;
    finalizeBtn.disabled = false;
  } finally {
    isGenerating = false;
    if (sendBtn) sendBtn.disabled = false;
  }
}

// ===============================
// RENDER TEMPLATES (screenshot-style format)
// ===============================
function renderTemplates() {
  templateList.innerHTML = "";

  storedTemplates.forEach((tpl, idx) => {
    const card = document.createElement("div");
    const isSelected = selectedTemplateIndex === idx;
    card.className = `template-card ${isSelected ? "selected" : ""}`;

    // questions as ordered list like screenshot
    const questionsHtml = `
      <ol class="question-list">
        ${tpl.questions.map((q) => {
      const typeLabel = formatScaleTypeLabel(q.scale_type);
      const hasOptions = Array.isArray(q.options) && q.options.length > 0;
      const optionsHtml = hasOptions
        ? `<div class="preview-options">${q.options.map(o => `<span class="preview-chip">${escapeHtml(o)}</span>`).join("")}</div>`
        : "";
      return `
            <li>
              <div>${escapeHtml(q.question)} <span class="small">(${escapeHtml(typeLabel)})</span></div>
              ${optionsHtml}
            </li>
          `;
    }).join("")}
      </ol>
    `;

    card.innerHTML = `
      <div class="template-header-row">
        <div class="template-title">
          <span class="template-icon">📄</span>
          <span>${escapeHtml(tpl.title)}</span>
        </div>
        <button class="chip ${isSelected ? "active-select" : ""}" data-idx="${idx}">${isSelected ? "✓ Selected" : "Select"}</button>
      </div>

      <div class="small"><b>Purpose:</b> ${escapeHtml(tpl.purpose || "N/A")}</div>
      <div class="small"><b>Duration:</b> ${escapeHtml(tpl.duration || "2–2.5 mins")}</div>

      <div class="template-questions">
        ${questionsHtml}
      </div>
    `;

    card.querySelector("button").onclick = () => {
      selectedTemplateIndex = idx;
      renderTemplates();
      appendMessage(`👍 Selected Template ${idx + 1}: "${escapeHtml(tpl.title)}"`, "bot");
    };

    templateList.appendChild(card);
  });
}

// ===============================
// GENERATE MORE TEMPLATES
// ===============================
generateMoreBtn.addEventListener("click", async () => {
  if (!storedTemplates.length) {
    const res = await apiPost("/generate_more_surveys", { focus_area: "" });
    if (res && res.message) {
      appendMessage(res.message, "bot");
    }
    return;
  }

  if (document.getElementById("moreFocusInput")) return;

  appendMessage("🧾 Which focus area do you want more templates for?", "bot");

  const box = document.createElement("div");
  box.className = "msg input-inline bot";
  box.innerHTML = `<input id="moreFocusInput" type="text" placeholder="Type a focus area…">`;
  chatEl.appendChild(box);

  const inp = document.getElementById("moreFocusInput");
  inp.focus();
  inp.addEventListener("keydown", async (e) => {
    if (e.key === "Enter" && inp.value.trim()) {
      const area = inp.value.trim();

      const valRes = await apiPost("/validate_input", { text: area, question_id: "purpose" });
      if (valRes.is_valid === false) {
        appendMessage(escapeHtml(area), "user");
        appendMessage(valRes.message || "⚠️ Invalid focus area.", "bot");
        inp.value = "";
        inp.focus();
        return;
      }

      appendMessage(escapeHtml(area), "user");
      box.remove();


      appendMessage(`✨ Generating more templates for: ${escapeHtml(area)}`, "bot");

      const res = await apiPost("/generate_more_surveys", {
        focus_area: area,

        // main survey type from FIRST API
        survey_type: surveyContext.survey_type || "general",

        // full context from FIRST API
        context: {
          original_user_input: originalUserInput,
          detected_survey_type: surveyContext.survey_type,
          detected_audience: surveyContext.audience,
          detected_purpose: surveyContext.purpose,
          detected_touchpoint: surveyContext.touchpoint,
          question_flow: [],
          skip_questions: true
        }
      });

      if (res.message && (!res.templates || !res.templates.length)) {
        appendMessage(res.message, "bot");
      }

      if (res.templates && res.templates.length) {
        const extra = res.templates.map(normalizeTemplate);
        storedTemplates = storedTemplates.concat(extra);
        renderTemplates();

        previewSubtitle.textContent = `${storedTemplates.length} templates`;

        appendMessage("✅ Added new templates matching your focus area.", "bot");
      } else if (!res.message) {
        appendMessage("⚠️ No new templates returned.", "bot");
      }
    }
  });

});

// ===============================
// CUSTOMIZE TEMPLATE
// ===============================
customizeBtn.addEventListener("click", async () => {
  if (selectedTemplateIndex === null) {
    const res = await apiPost("/customize_selected_template", { templates: storedTemplates, choice: "" });
    if (res && res.message) {
      appendMessage(res.message, "bot");
    }
    return;
  }

  appendMessage("🛠 How would you like to customize this? (Add / Remove / No Changes)", "bot");

  const box = document.createElement("div");
  box.className = "msg options-list bot";

  const opts = document.createElement("div");
  opts.className = "options";

  ["Add", "Remove", "No Changes"].forEach((label) => {
    const b = document.createElement("button");
    b.className = "chip";
    b.textContent = label;
    b.onclick = () => proceedCustomize(label);
    opts.appendChild(b);
  });

  box.appendChild(opts);
  chatEl.appendChild(box);

  async function proceedCustomize(choice) {
    box.remove();
    appendMessage(choice, "user");

    const action = choice.toLowerCase();
    let focusArea = "";
    let complexity = "";
    let removeInput = "";

    if (action === "add") {
      focusArea = await askTextOnce("✏️ Any specific focus area?");
      complexity = await askTextOnce("📊 Complexity? (Simple / Moderate / Detailed)");
    }

    if (action === "remove") {
      removeInput = await askTextOnce("✂️ Which questions to remove? (e.g., Q2 or a keyword)");
    }

    appendMessage("✨ Applying customization…", "bot");

    const res = await apiPost("/customize_selected_template", {
      templates: storedTemplates,
      choice: `Template ${selectedTemplateIndex + 1}`,
      action,
      focus_area: focusArea,
      complexity,
      scale_action: "no",
      scale_changes: {},
      remove_input: removeInput,
    });

    if (res.selected_template) {
      storedTemplates[selectedTemplateIndex] = normalizeTemplate(res.selected_template);
      renderTemplates();
    }

    if (res.message) {
      appendMessage(res.message, "bot");
    } else {
      appendMessage("🎉 Customization complete!", "bot");
    }
  }
});

function askTextOnce(question) {
  return new Promise((resolve) => {
    appendMessage(question, "bot");

    const box = document.createElement("div");
    box.className = "msg input-inline bot";
    box.innerHTML = `<input type="text" placeholder="Type here…">`;

    const inp = box.querySelector("input");
    chatEl.appendChild(box);
    inp.focus();

    inp.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        const val = inp.value.trim();
        appendMessage(val || "(skipped)", "user");
        box.remove();
        resolve(val);
      }
    });
  });
}

// ===============================
// FINALIZE & DOWNLOAD
// ===============================
finalizeBtn.addEventListener("click", async () => {
  if (selectedTemplateIndex === null) {
    const res = await apiPost("/finalize_template", { final_template: null });
    if (res && res.message) {
      appendMessage(res.message, "bot");
    }
    return;
  }

  const tpl = storedTemplates[selectedTemplateIndex];
  appendMessage(`📦 Finalizing template: ${tpl.title}`, "bot");

  const res = await apiPost("/finalize_template", { final_template: tpl });

  if (res.message) {
    const savedPathMsg = res.path ? `<br><small style="color:var(--text-muted);">Saved file: <code>${escapeHtml(res.path)}</code></small>` : "";
    appendMessage(`🎉 ${escapeHtml(res.message)}${savedPathMsg}`, "bot");
  } else if (res.template_id) {
    const savedPathMsg = res.path ? `<br><small style="color:var(--text-muted);">Saved file: <code>${escapeHtml(res.path)}</code></small>` : "";
    appendMessage(`🎉 Template saved (ID: ${escapeHtml(res.template_id)})${savedPathMsg}`, "bot");
  }
  if (res.template_id || res.path) {
    downloadJsonBtn.disabled = false;
  }
});

downloadJsonBtn.addEventListener("click", () => {
  if (selectedTemplateIndex === null) return;

  const tpl = storedTemplates[selectedTemplateIndex];
  const blob = new Blob([JSON.stringify(tpl, null, 2)], { type: "application/json" });

  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `${tpl.title.replace(/\s+/g, "_")}.json`;
  a.click();
});

// ===============================
// QUICK CHIPS & SEND
// ===============================
quickEl.addEventListener("click", (e) => {
  const chip = e.target.closest(".chip");
  if (!chip) return;
  startFlow(chip.dataset.value);
});

sendBtn.addEventListener("click", async () => {
  if (isGenerating) return;

  const txt = userInput.value.trim();
  userInput.value = "";

  if (!txt) {
    const valRes = await apiPost("/validate_input", { text: "" });
    if (valRes && valRes.message) {
      appendMessage(valRes.message, "bot");
    }
    return;
  }

  // 1. Active focus area input for "Generate More" variations
  const moreFocusInput = document.getElementById("moreFocusInput");
  if (moreFocusInput) {
    moreFocusInput.value = txt;
    const enterEvent = new KeyboardEvent("keydown", { key: "Enter", bubbles: true });
    moreFocusInput.dispatchEvent(enterEvent);
    return;
  }

  // 2. Active question flow during initial setup (only when templates are not generated yet)
  if (storedTemplates.length === 0) {
    const inlineQ = document.getElementById("inlineQ") || document.querySelector(".input-inline input, input.input-inline");
    if (inlineQ || (Array.isArray(questionFlow) && questionFlow.length > 0 && currentQuestionIndex < questionFlow.length)) {
      if (inlineQ) {
        inlineQ.value = txt;
      }
      handleAnswer(txt);
      return;
    }
  }

  // 3. Templates already generated → send text directly to backend API for refinement/generation
  if (storedTemplates.length > 0) {
    appendMessage(escapeHtml(txt), "user");
    appendMessage(`✨ Generating templates for: "${escapeHtml(txt)}"...`, "bot");

    isGenerating = true;
    if (sendBtn) sendBtn.disabled = true;
    try {
      const res = await apiPost("/generate_more_surveys", {
        focus_area: txt,
        survey_type: surveyContext.survey_type || "general",
        context: {
          original_user_input: originalUserInput,
          detected_survey_type: surveyContext.survey_type,
          detected_audience: surveyContext.audience,
          detected_purpose: surveyContext.purpose,
          detected_touchpoint: surveyContext.touchpoint,
          question_flow: [],
          skip_questions: true
        }
      });

      const extraTemplates = res.templates || res.surveys || [];
      if ((res.error || res.message) && !extraTemplates.length) {
        appendMessage(res.message || res.error || "⚠️ Could not generate more variations.", "bot");
      }

      if (extraTemplates.length) {
        const extra = extraTemplates.map(normalizeTemplate);
        storedTemplates = storedTemplates.concat(extra);
        renderTemplates();

        previewSubtitle.textContent = `${storedTemplates.length} templates`;
        appendMessage("✅ Added new templates matching your update.", "bot");
      } else if (!res.message) {
        appendMessage("⚠️ Could not generate templates for this update.", "bot");
      }
    } finally {
      isGenerating = false;
      if (sendBtn) sendBtn.disabled = false;
    }
    return;
  }

  // 4. Otherwise → start new initial flow
  startFlow(txt);
});


userInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendBtn.click();
});

// ===============================
// RESTART
// ===============================
restartBtn.addEventListener("click", () => location.reload());

// Initial focus
userInput.focus();
