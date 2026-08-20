
/* =====================================================
   GLOBAL STATE
===================================================== */
let questionFlow = [];
let currentQuestionIndex = 0;
let collectedAnswers = {};
let storedTemplates = [];
let selectedTemplateIndex = null;

let originalUserInput = "";  // ✅ Fixed: Declared at global scope
let detectedSurveyType = ""; // ✅ Fixed: Declared at global scope
let includePurposeDuration = true;

/* =====================================================
   DOM REFERENCES
===================================================== */
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

/* =====================================================
   HELPER FUNCTIONS
===================================================== */
function escapeHtml(str) {
  if (!str && str !== 0) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function appendMessage(html, type = "bot") {
  const div = document.createElement("div");
  div.className = "msg " + type;
  div.innerHTML = html;
  chatEl.appendChild(div);
  chatEl.scrollTop = chatEl.scrollHeight;
}

function clearInlineInputs() {
  document.querySelectorAll(".input-inline").forEach(el => el.remove());
  document.querySelectorAll(".options-list").forEach(el => el.remove());
}

async function apiPost(url, payload) {
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload || {})
    });
    return await res.json();
  } catch (err) {
    console.error("API Error:", err);
    appendMessage("⚠️ Network error. Check console.");
    return { error: String(err) };
  }
}

/* =====================================================
   QUICK CHIPS HANDLER
===================================================== */
quickEl.addEventListener("click", function(e) {
  const chip = e.target.closest(".chip");
  if (!chip) return;
  startFlow(chip.dataset.value);
});

/* =====================================================
   RESTART
===================================================== */
restartBtn.addEventListener("click", function() {
  location.reload();
});

/* =====================================================
   START QUESTION FLOW
===================================================== */
async function startFlow(inputText) {
  // ✅ Reset global state
  originalUserInput = inputText;
  detectedSurveyType = inputText;
  selectedTemplateIndex = null;
  collectedAnswers = {};
  questionFlow = [];
  currentQuestionIndex = 0;

  templateList.innerHTML = '<div class="muted">Loading...</div>';
  previewSubtitle.textContent = "Working...";

  appendMessage(`<b>📘 ${escapeHtml(inputText)}</b>`, "user");
  appendMessage("🧠 Understanding your request...", "bot");

  const flowResp = await apiPost("/generate_question_flow", {
    user_input: inputText,
    survey_type: inputText
  });

  // ✅ Handle skip scenario
  if (flowResp.skip_questions) {
    appendMessage("✅ Details found. No extra questions needed.", "bot");
    collectedAnswers = flowResp.extracted || {};
    return generateSurvey();
  }

  // ✅ Parse question flow
  const flow = flowResp.question_flow || flowResp.questions || [];
  questionFlow = flow.map(q => ({
    text: q.q || q.question || q.text || "Question",
    options: q.options || []
  }));

  if (questionFlow.length === 0) {
    appendMessage("⚠️ No questions returned. Generating survey directly.", "bot");
    return generateSurvey();
  }

  currentQuestionIndex = 0;
  appendMessage("✅ We need a few more details.", "bot");
  askNextQuestion();
}

/* =====================================================
   ASK NEXT QUESTION
===================================================== */
function askNextQuestion() {
  clearInlineInputs();

  if (currentQuestionIndex >= questionFlow.length) {
    return generateSurvey();
  }

  const q = questionFlow[currentQuestionIndex];
  appendMessage(`🧠 ${escapeHtml(q.text)}`, "bot");

  // ✅ Render options if available
  if (q.options && q.options.length) {
    const box = document.createElement("div");
    box.className = "msg options-list bot";
    box.style.padding = "8px";

    const optsDiv = document.createElement("div");
    optsDiv.className = "options";

    q.options.forEach(opt => {
      const btn = document.createElement("button");
      btn.className = "option-btn";
      btn.textContent = opt;
      btn.onclick = () => handleAnswer(opt);
      optsDiv.appendChild(btn);
    });

    // ✅ Add custom input
    const other = document.createElement("input");
    other.type = "text";
    other.placeholder = "Type custom answer...";
    other.style.marginTop = "8px";
    other.className = "input-inline";
    other.onkeydown = e => {
      if (e.key === "Enter" && other.value.trim()) {
        handleAnswer(other.value.trim());
      }
    };

    box.appendChild(optsDiv);
    box.appendChild(other);
    chatEl.appendChild(box);
    chatEl.scrollTop = chatEl.scrollHeight;
  } else {
    // ✅ Plain text input
    const box = document.createElement("div");
    box.className = "msg input-inline bot";
    box.innerHTML = '<input id="inlineResp" type="text" placeholder="Type answer and press Enter">';
    chatEl.appendChild(box);
    chatEl.scrollTop = chatEl.scrollHeight;

    setTimeout(() => {
      const inp = document.getElementById("inlineResp");
      if (inp) {
        inp.focus();
        inp.addEventListener("keydown", e => {
          if (e.key === "Enter" && inp.value.trim()) {
            handleAnswer(inp.value.trim());
          }
        });
      }
    }, 50);
  }
}

/* =====================================================
   HANDLE ANSWER
===================================================== */
function handleAnswer(ans) {
  const q = questionFlow[currentQuestionIndex];
  collectedAnswers[q.text] = ans;

  appendMessage(escapeHtml(ans), "user");

  currentQuestionIndex++;
  
  if (currentQuestionIndex >= questionFlow.length) {
    generateSurvey();
  } else {
    setTimeout(askNextQuestion, 400);
  }
}

/* =====================================================
   GENERATE SURVEY TEMPLATES
===================================================== */
async function generateSurvey() {
  appendMessage("✨ Generating survey templates...", "bot");

  const payload = {
    user_input: originalUserInput,
    survey_type: detectedSurveyType,
    answers: collectedAnswers
  };

  const res = await apiPost("/generate_survey", payload);

  if (!res.surveys || !res.surveys.length) {
    appendMessage("⚠️ No templates returned.", "bot");
    return;
  }

  storedTemplates = res.surveys.map(normalizeTemplate);
  renderTemplates();

  appendMessage(`✅ ${storedTemplates.length} templates ready!`, "bot");
  previewSubtitle.textContent = `${storedTemplates.length} templates`;
  
  generateMoreBtn.disabled = false;
  customizeBtn.disabled = false;
  finalizeBtn.disabled = false;
}

/* =====================================================
   NORMALIZE TEMPLATE
===================================================== */
function normalizeTemplate(t) {
  return {
    title: t.title || t.name || "Untitled Template",
    purpose: t.purpose || "",
    duration: t.duration || "",
    questions: (t.questions || []).map(q => ({
      question: q.question || q.text || "Question",
      scale_type: q.scale_type || q.scale || "text"
    }))
  };
}

/* =====================================================
   RENDER TEMPLATES
===================================================== */
function renderTemplates() {
  templateList.innerHTML = "";

  storedTemplates.forEach((tpl, idx) => {
    const card = document.createElement("div");
    card.className = "template-card";

    card.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div class="template-title">📋 ${escapeHtml(tpl.title)}</div>
        <button class="option-btn" data-idx="${idx}">Select</button>
      </div>
      <div class="small"><b>Purpose:</b> ${escapeHtml(tpl.purpose)}</div>
      <div class="small"><b>Duration:</b> ${escapeHtml(tpl.duration)}</div>
      <div style="margin-top:8px">
        ${tpl.questions.map(q => `
          <div class="question-row">
            <span>${escapeHtml(q.question)}</span>
            <span class="small">(${q.scale_type})</span>
          </div>
        `).join("")}
      </div>
    `;

    card.querySelector("button").onclick = () => selectTemplate(idx);
    templateList.appendChild(card);
  });

  downloadJsonBtn.disabled = false;
}

/* =====================================================
   SELECT TEMPLATE
===================================================== */
function selectTemplate(idx) {
  selectedTemplateIndex = idx;
  const tpl = storedTemplates[idx];
  
  appendMessage(`✅ Selected: <b>${escapeHtml(tpl.title)}</b>`, "bot");
  customizeTemplate(idx);
}

/* =====================================================
   CUSTOMIZE TEMPLATE
===================================================== */
async function customizeTemplate(idx) {
  const res = await apiPost("/customize_selected_template", {
    templates: storedTemplates,
    choice: `Template ${idx + 1}`
  });

  if (res.error) {
    appendMessage(`⚠️ ${escapeHtml(res.error)}`, "bot");
    return;
  }

  if (res.selected_template) {
    storedTemplates[idx] = normalizeTemplate(res.selected_template);
    renderTemplates();
  }

  if (res.customization_questions && res.customization_questions.length) {
    runCustomizationFlow(idx, res.customization_questions);
  } else {
    appendMessage("✅ Template ready for finalization.", "bot");
  }
}

/* =====================================================
   CUSTOMIZATION FLOW
===================================================== */
async function runCustomizationFlow(idx, steps) {
  appendMessage("🛠️ Customization started.", "bot");

  let step = 0;
  let answers = {};

  function ask() {
    if (step >= steps.length) {
      return applyCustomization();
    }

    const q = steps[step];
    appendMessage(`🧩 ${escapeHtml(q.question)}`, "bot");

    const box = document.createElement("div");
    box.className = "msg options-list bot";
    box.style.padding = "8px";

    // ✅ Options
    if (q.options && q.options.length) {
      const optsDiv = document.createElement("div");
      optsDiv.className = "options";

      q.options.forEach(opt => {
        const btn = document.createElement("button");
        btn.className = "option-btn";
        btn.textContent = opt;
        btn.onclick = () => {
          answers[q.question] = opt;
          appendMessage(escapeHtml(opt), "user");
          box.remove();
          step++;
          setTimeout(ask, 400);
        };
        optsDiv.appendChild(btn);
      });

      box.appendChild(optsDiv);
    }

    // ✅ Text input
    if (q.allow_text_input) {
      const inp = document.createElement("input");
      inp.type = "text";
      inp.placeholder = "Type here...";
      inp.style.marginTop = "8px";
      inp.onkeydown = e => {
        if (e.key === "Enter" && inp.value.trim()) {
          answers[q.question] = inp.value.trim();
          appendMessage(escapeHtml(inp.value), "user");
          box.remove();
          step++;
          setTimeout(ask, 400);
        }
      };
      box.appendChild(inp);
    }

    chatEl.appendChild(box);
    chatEl.scrollTop = chatEl.scrollHeight;
  }

  ask();

  async function applyCustomization() {
    appendMessage("✨ Applying customization...", "bot");

    const payload = {
      templates: storedTemplates,
      choice: `Template ${idx + 1}`,
      ...answers
    };

    const res = await apiPost("/customize_selected_template", payload);
    
    if (res.selected_template) {
      storedTemplates[idx] = normalizeTemplate(res.selected_template);
      renderTemplates();
    }

    appendMessage("✅ Customization complete!", "bot");
  }
}

/* =====================================================
   FINALIZE TEMPLATE
===================================================== */
finalizeBtn.addEventListener("click", async function() {
  if (selectedTemplateIndex === null) {
    appendMessage("⚠️ Please select a template first.", "bot");
    return;
  }

  const tpl = storedTemplates[selectedTemplateIndex];
  appendMessage(`🎯 Finalizing: <b>${escapeHtml(tpl.title)}</b>`, "bot");

  const res = await apiPost("/finalize_template", {
    final_template: tpl
  });

  if (res.template_id) {
    appendMessage(`🎉 Template saved! ID: <b>${res.template_id}</b>`, "bot");
    downloadJsonBtn.disabled = false;
  } else {
    appendMessage("⚠️ Failed to finalize template.", "bot");
  }
});

/* =====================================================
   DOWNLOAD JSON
===================================================== */
downloadJsonBtn.addEventListener("click", function() {
  if (selectedTemplateIndex === null) {
    appendMessage("⚠️ Select a template first.", "bot");
    return;
  }

  const tpl = storedTemplates[selectedTemplateIndex];
  const blob = new Blob([JSON.stringify(tpl, null, 2)], {
    type: "application/json"
  });

  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = tpl.title.replace(/\s+/g, "_") + ".json";
  a.click();
});

/* =====================================================
   SEND BUTTON
===================================================== */
sendBtn.addEventListener("click", function(e) {
  e.preventDefault();
  const text = userInput.value.trim();
  if (!text) return;

  userInput.value = "";
  startFlow(text);
});

userInput.addEventListener("keydown", function(e) {
  if (e.key === "Enter") {
    e.preventDefault();
    sendBtn.click();
  }
});

/* =====================================================
   INITIALIZE
===================================================== */
userInput.focus();