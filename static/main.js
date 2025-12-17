const chat = document.getElementById('chat');
const msgInput = document.getElementById('msg');
const userForm = document.getElementById('user-input');
const paramForm = document.getElementById('param-form');
const requiredFields = document.getElementById('required-fields');
const optionalFields = document.getElementById('optional-fields');
const paramsForm = document.getElementById('param-form');

// Allowed report names
const reportNames = ["Packslip", "CommercialInvoice", "SLI"];

// Add chat bubble
function addBubble(text, who = "bot") {
  const wrapper = document.createElement('div');
  wrapper.className = "d-flex mb-2 " + (who === "user" ? "justify-content-end" : "justify-content-start");

  const bubble = document.createElement('div');
  bubble.className = who === "user" ? "bubble-user" : "bubble-bot";
  bubble.innerHTML = text.replace(/\n/g, '<br>');

  wrapper.appendChild(bubble);
  chat.appendChild(wrapper);
  chat.scrollTop = chat.scrollHeight;
}

// Display welcome message on load
window.addEventListener('DOMContentLoaded', () => {
  addBubble("👋 Welcome to GTM Chat! Ask me about Item Details, CoC Information, BI Reports, or Delivery Tracking.");
});

// Handle user message
userForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const message = msgInput.value.trim();
  if (!message) return;

  addBubble(message, "user");
  msgInput.value = "";

  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message })
    });
    const data = await res.json();
    addBubble(data.reply, "bot");

    if (data.ask_params) showParamForm(data.required || [], data.optional || []);
    else hideParamForm();
  } catch (err) {
    addBubble("Error contacting server: " + err, "bot");
  }
});

// Handle Parameters Form Submission
paramsForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const inputs = paramsForm.querySelectorAll('input, select');
  const params = {};
  inputs.forEach(inp => params[inp.name] = inp.value.trim());

  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "Providing parameters", params })
    });
    const data = await res.json();
    addBubble(data.reply, "bot");

    if (data.ask_params) showParamForm(data.required || [], data.optional || []);
    else hideParamForm();
  } catch (err) {
    addBubble("Error submitting parameters: " + err, "bot");
  }
});

// Show parameters form
function showParamForm(required, optional) {
  requiredFields.innerHTML = "";
  optionalFields.innerHTML = "";

  required.forEach(name => {
    let div = document.createElement('div');
    div.className = "form-group mb-2";

    if (name === "report_name") {
      let options = reportNames.map(r => `<option value="${r}">${r}</option>`).join('');
      div.innerHTML = `<label class="form-label">Report Name (required):</label>
                       <select name="report_name" class="form-control" required>${options}</select>`;
    } else {
      let label = name === "item" ? "Item Number" :
                  name === "model_item" ? "Model Number" : name;
      div.innerHTML = `<label class="form-label">${label} (required):</label>
                       <input name="${name}" class="form-control" required>`;
    }
    requiredFields.appendChild(div);
  });

  optional.forEach(name => {
    const label = name === "country_query" ? "Country (optional)" : `${name} (optional)`;
    const div = document.createElement('div');
    div.className = "form-group mb-2";
    div.innerHTML = `<label class="form-label">${label}:</label>
                     <input name="${name}" class="form-control">`;
    optionalFields.appendChild(div);
  });

  paramForm.style.display = 'block';
}

// Hide parameters form
function hideParamForm() {
  requiredFields.innerHTML = "";
  optionalFields.innerHTML = "";
  paramForm.style.display = 'none';
}
